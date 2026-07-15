import json
import os
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    ImageSendMessage,
    LocationMessage,
    LocationSendMessage,
    MessageEvent,
    TextMessage,
    TextSendMessage,
)

import config
from line_bot import handler, line_bot_api
from navigation import start_navigation_to_home
from navigation_state import get_nav_session
from tts_queue import enqueue as tts_enqueue

# 避免和 main 產生循環依賴：在事件函式內才 import main
router = APIRouter()

_DEFAULT_BASE_URL = getattr(
    config, "DEFAULT_PUBLIC_BASE_URL", "https://www.blind-glasses.org"
)
PUBLIC_SNAPSHOT_BASE_URL = (
    getattr(config, "PUBLIC_BASE_URL", "")
    or _DEFAULT_BASE_URL
).rstrip("/")

HOME_LOCATION_FILE = os.path.join(os.path.dirname(__file__), "home_location.json")


def load_home_location():
    if os.path.exists(HOME_LOCATION_FILE):
        try:
            with open(HOME_LOCATION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"lat": None, "lng": None, "address": None}


def save_home_location(loc):
    try:
        with open(HOME_LOCATION_FILE, "w", encoding="utf-8") as f:
            json.dump(loc, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Error] Failed to save home location: {e}")


_home_location = load_home_location()


@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    global _home_location
    _home_location["lat"] = event.message.latitude
    _home_location["lng"] = event.message.longitude
    _home_location["address"] = event.message.address
    save_home_location(_home_location)

    res = (
        "🏠 系統已成功將住家位置設定為：\n"
        f"「{event.message.address}」\n\n"
        "未來只要說「導航回家」，就會引導使用者回到這個地方喔！"
    )
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res))


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    import main

    msg = event.message.text.strip()
    user_id = getattr(event.source, "user_id", "")
    print(f"DEBUG: 收到來自 LINE 的訊息 -> |{msg}| (來自 ID: {user_id})")

    if msg.lower() in ["id", "我的id", "userid", "user_id", "my id"]:
        res = (
            "【您的 LINE User ID】\n"
            f"您的唯一識別碼為：\n{user_id}\n\n"
            "請將此 ID 複製並填入伺服器目錄下的 .env 檔案中。\n"
            "例如：\n"
            f'LINE_TARGET_IDS="{user_id}"'
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res))
        return

    help_text = (
        "您好！我是導盲眼鏡的小幫手 🦉\n"
        "以下是您可以隨時輸入的關鍵字：\n\n"
        "【查詢位置】：查看戴著眼鏡的家人現在在哪裡。\n"
        "【眼鏡畫面】：回傳眼鏡目前的即時視角。\n"
        "【眼鏡狀態】：確認連線、電量、WiFi 與最新語音指令。\n"
        "【導航回家】：遠端啟動導航，引導家人回家。\n"
        "【緊急求助】：回傳目前位置與現場畫面。\n\n"
        "💡 傳送「功能」或「幫助」即可再次呼叫此清單。"
    )

    if "查詢位置" in msg or "位置" in msg or "在哪" in msg:
        gps_live = main._get_last_gps(max_age_sec=60)
        if gps_live:
            map_url = f"https://www.google.com/maps?q={gps_live['lat']},{gps_live['lng']}"
            res = f"📍 馬上為您回報！家人目前的位置在這裡：\n{map_url}"
        else:
            gps_last_known = main._get_last_gps(max_age_sec=900)
            if gps_last_known:
                age_min = max(1, int((time.time() - gps_last_known.get("ts", time.time())) // 60))
                map_url = (
                    f"https://www.google.com/maps?q={gps_last_known['lat']},{gps_last_known['lng']}"
                )
                res = (
                    "📍 目前可能處於室內或遮蔽處，暫無即時 GPS。\n"
                    f"這是 {age_min} 分鐘前最後回報的位置：\n{map_url}"
                )
            else:
                res = (
                    "📍 目前無法取得有效 GPS（超過 15 分鐘未更新）。"
                    "請確認眼鏡已開機並在戶外，或直接聯繫使用者。"
                )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res))

    elif "拍攝畫面" in msg or "眼鏡畫面" in msg or "看看" in msg or "環境" in msg:
        frame = main._get_latest_frame_bytes()
        if not frame:
            res = "📸 眼鏡鏡頭目前無畫面回傳，可能是設備待機或網路訊號不佳。"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res))
        else:
            image_url = f"{PUBLIC_SNAPSHOT_BASE_URL}/api/line_snapshot?t={int(time.time())}"
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text="📸 沒問題，正在為您擷取眼鏡目前的即時畫面..."),
                    ImageSendMessage(original_content_url=image_url, preview_image_url=image_url),
                ],
            )

    elif "眼鏡狀態" in msg or "狀態" in msg:
        nav_session = get_nav_session()
        mode = nav_session.get_state().value
        last_voice = main._recent_voice_intents[-1]["text"] if main._recent_voice_intents else "無"

        health = main._server_health.snapshot()
        imu_age = health.get("last_imu_age_sec")
        uptime = health.get("uptime_sec", 0)
        last_error = health.get("last_error", "")

        if uptime > 3600:
            uptime_str = f"{int(uptime // 3600)} 小時 {int((uptime % 3600) // 60)} 分鐘"
        elif uptime > 60:
            uptime_str = f"{int(uptime // 60)} 分鐘"
        else:
            uptime_str = f"{int(uptime)} 秒"

        device_status = getattr(main, "_current_device_status", None) or {}
        battery_raw = (
            device_status.get("battery")
            or device_status.get("batteryPercent")
            or device_status.get("battery_percent")
        )
        if battery_raw is not None:
            battery_str = (
                f"{int(battery_raw)}%"
                if isinstance(battery_raw, (int, float))
                else str(battery_raw)
            )
        else:
            battery_str = "未知 (配戴者 App 尚未透過藍牙回報)"

        wifi_raw = (
            device_status.get("wifi")
            or device_status.get("wifiSsid")
            or device_status.get("ssid")
        )
        wifi_str = str(wifi_raw) if wifi_raw else "未知"

        if imu_age is None:
            conn_status = "設備尚未連線 (或正在重新啟動)"
        elif imu_age > 30:
            minutes = int(imu_age // 60)
            if minutes > 0:
                conn_status = f"設備已離線 (最後連線: {minutes} 分鐘前)"
            else:
                conn_status = "設備已離線 (最後連線: 剛剛)"
        else:
            conn_status = "🟢 正常運作中"

        res = (
            "👓 【設備狀態回報】\n"
            f"● 連線狀態：{conn_status}\n"
            f"● 剩餘電量：{battery_str}\n"
            f"● WiFi：{wifi_str}\n"
            f"● 伺服器運行：{uptime_str}\n"
            f"● 目前模式：{mode}\n"
            f"● 最新語音指令：{last_voice}\n"
        )
        if last_error:
            res += f"● 最近警告：{last_error}\n"
        if conn_status.startswith("🟢"):
            res += "\n一切平安，請您放心！"
        else:
            res += "\n⚠️ 設備可能離線，請嘗試聯繫使用者確認安全。"

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res))

    elif "回家" in msg or "導航回家" in msg:
        global _home_location
        if _home_location["lat"] is None:
            res = (
                "⚠️ 您還沒有設定住家位置喔！\n"
                "請點擊 LINE 聊天室左下角的「+」，選擇「位置資訊」，"
                "搜尋並傳送您家的位置給我，就能完成設定了。"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res))
        else:
            start_navigation_to_home(tts_enqueue, main._get_last_gps, config.LAST_GPS_MAX_AGE_SEC)
            res = (
                "🏠 已經幫您遠端啟動「導航回家」功能！\n"
                f"眼鏡現在會開始用語音引導家人，朝著「{_home_location['address']}」的方向前進囉。"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res))

    elif "緊急求助" in msg or ("緊急" in msg and "求助" in msg):
        gps = main._get_last_gps(max_age_sec=60)
        sos_msg = "⚠️ 【緊急求助通知】\n使用者發出了求助訊號！\n請家屬立即確認下方位置與現場畫面。"

        messages = [TextSendMessage(text=sos_msg)]

        if gps:
            messages.append(
                LocationSendMessage(
                    title="使用者緊急位置",
                    address="點擊開啟導航",
                    latitude=gps["lat"],
                    longitude=gps["lng"],
                )
            )

        frame = main._get_latest_frame_bytes()
        if frame:
            image_url = f"{PUBLIC_SNAPSHOT_BASE_URL}/api/line_snapshot?t={int(time.time())}"
            messages.append(
                ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
            )

        line_bot_api.reply_message(event.reply_token, messages)

    elif "設定住家" in msg or "設定家" in msg:
        current_address = _home_location.get("address")
        if current_address:
            res = (
                f"您目前已設定的住家位置為：\n{current_address}\n\n"
                "若要更改，請在 LINE 點「＋」→「位置資訊」傳送新地址即可。"
            )
        else:
            res = (
                "您尚未設定住家位置。\n"
                "請在 LINE 點「＋」→「位置資訊」傳送住家地址即可。"
            )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res))

    elif "功能" in msg or "幫助" in msg or "選單" in msg:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=help_text))

    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=help_text))


@router.post("/api/line/webhook")
@router.post("/callback")
async def callback(request: Request):
    """LINE Bot Webhook（LINE Developers 請填 https://你的網域/api/line/webhook）"""
    signature = request.headers.get("X-Line-Signature", "")
    body = (await request.body()).decode("utf-8")
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return JSONResponse({"error": "Invalid signature"}, status_code=400)
    return "OK"


@router.get("/api/line_snapshot")
async def line_snapshot():
    import main

    frame_b = main._get_latest_frame_bytes()
    if not frame_b:
        return JSONResponse({"error": "No frame available"}, status_code=404)
    return Response(content=frame_b, media_type="image/jpeg")
