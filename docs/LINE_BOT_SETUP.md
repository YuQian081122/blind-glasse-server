# LINE Bot 設定與伺服器資料來源

## 1. LINE Developers 要填的 Webhook

在 Messaging API → Webhook settings：

- **Webhook URL**：`https://你的公開網域/api/line/webhook`  
  例：`https://www.blind-glasses.org/api/line/webhook`
- **Use webhook**：ON
- 按 **Verify**（伺服器須已啟動，且 `.env` 有正確 `LINE_CHANNEL_SECRET`）

舊版若填 `/callback` 仍可用（與 `/api/line/webhook` 同一處理）。

## 2. `.env` 必填（於 `blind-glasse-server/` 目錄）

```env
HTTP_PORT=4000
LINE_CHANNEL_ACCESS_TOKEN=（Channel access token）
LINE_CHANNEL_SECRET=（Channel secret）
LINE_TARGET_IDS=（家屬 LINE userId，對 Bot 傳「id」可取得）
LINE_SNAPSHOT_BASE_URL=https://www.blind-glasses.org
```

主動推播（跌倒／緊急）另設 `LINE_NOTIFY_ENABLE=1`。

## 3. LINE Bot 從哪裡讀伺服器資料

| 家屬在 LINE 輸入 | 資料來源 |
|------------------|----------|
| 查詢位置／位置 | `main._get_last_gps()`（眼鏡 POST `/api/gps`） |
| 眼鏡畫面 | `main._get_latest_frame_bytes()` + `GET /api/line_snapshot` |
| 眼鏡狀態 | IMU：`ServerHealth`；電量／WiFi：`_current_device_status`（配戴者 App POST `/api/status`） |
| 導航回家 | `home_location.json`（家屬在 LINE 傳位置訊息設定） |

## 4. 配戴者 App 與家屬 App

1. **配戴者手機**定期 `POST /api/status`：`{"battery": 85, "wifi": "MyHomeWiFi"}`
2. **家屬手機** `GET /api/status`（含 `gps` 欄位）
3. **LINE** 讀伺服器記憶體，不需 App 再轉給 LINE

## 5. Cloudflare Tunnel

公開網域須指到 **`http://localhost:4000`**。
