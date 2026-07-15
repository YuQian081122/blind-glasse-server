# 麥克風測試 Agent 狀態檔

> 新迭代紀錄加在「迭代日誌」最上方。

## 待人類處理（NEEDS-HUMAN）

（無）

## 受阻（BLOCKED）

（無）

## 硬體備註

- 喇叭 MAX98357A I2S 腳位：LRC=GPIO1、BCLK=GPIO2、DIN=GPIO3。
- 麥克風：XIAO ESP32-S3 Sense 板載內建 PDM 麥克風。
- 裝置無實體按鈕；mictest 韌體觸發只能使用自動間隔或序列埠指令。

## 迭代日誌

### 迭代 9 — 2026-07-15 13:25
- 任務：MT-F3 COM3 釋放後重試燒錄與回覆播放驗證。
- 結果：DONE（喇叭是否實際出聲仍留到 MT-E1 人耳確認）。
- 變更檔案：`firmware/src/mictest/main.cpp`、`docs/plans/mic_test_plan.md`、`docs/plans/status/mictest_status.md`。
- 備註：COM3 已可開啟後，成功燒錄 MT-F3 韌體。mictest 韌體會在 POST 200 後輪詢 `/api/mictest/reply.mp3`，取得新 ETag 後使用 ESP32-audioI2S（I2S1）播放；播放期間持續呼叫 `audio->loop()` 並等待 `isRunning()` 結束，避免錄音與播放重疊。serial 已顯示 `playback start` 與 `playback done ran=yes`，代表韌體播放流程完成；實體喇叭是否有聲音需 MT-E1 請使用者人耳確認。
- 驗證：`py -3 -m platformio run -e mictest` → SUCCESS；`py -3 -m platformio run -e mictest -t upload` → SUCCESS（COM3）。啟動 mictest-only server 與 Cloudflare tunnel 後，serial monitor 顯示：`POST /api/mictest code=200 upload_ms=7105 bytes=96044`、`playback start wait_ms=2142 etag="2-150d72407d7fec8a"`、`playback done elapsed_ms=8717 ran=yes`；下一輪也顯示 `POST /api/mictest code=200` 與 `playback start wait_ms=2772`。公開 state：`seq=3`、`duration_sec=3.0`、`tts_ready=true`。`ReadLints` 仍為既有 clang/PlatformIO 參數與 Arduino include 誤報，實際 PlatformIO build/燒錄通過。
- push：`8c650b1` 已推送到 firmware `origin/main`。

### 迭代 8 — 2026-07-15 13:08
- 任務：MT-F3 回覆 MP3 輪詢與喇叭播放。
- 結果：BLOCKED（程式碼已完成且 build 通過；實機燒錄/播放驗證受 COM3 鎖定阻塞）。
- 變更檔案：`firmware/src/mictest/main.cpp`、`docs/plans/status/mictest_status.md`。
- 備註：mictest 韌體新增 ESP32-audioI2S 播放流程：初始化 I2S1 喇叭（引用 `config.h` 的 `I2S_BCLK_PIN`/`I2S_LRC_PIN`/`I2S_DOUT_PIN`）、POST 成功後最多 30 秒輪詢 `/api/mictest/reply.mp3`，送 `If-None-Match` 並用 `collectHeaders()` 讀 ETag；拿到新 ETag 後呼叫 `audio->connecttohost()` 播放，播放 loop 期間不進入下一輪錄音，serial 會輸出 `reply wait`、`playback start`、`playback done`。確認 ESP32-audioI2S 此版本無 memory-bytes 播放入口；播放 URL 無法附自訂 header，但目前 `main.py` token middleware 只精確保護 `/api/mictest`，不攔 `/api/mictest/reply.mp3` 子路徑，mictest-only server 也無 middleware。
- 驗證：`py -3 -m platformio run -e mictest` → SUCCESS。啟動 mictest-only server 與 Cloudflare tunnel 後 `https://www.blind-glasses.org/mictest` → 200。`py -3 -m platformio run -e mictest -t upload` → FAILED，COM3 PermissionError；`.NET SerialPort('COM3').Open()` → 拒絕存取；`Get-CimInstance Win32_Process` 查無含 `COM3`/`platformio device monitor`/`esptool` 的可見程序。13:12 自動重試：COM3 仍可列舉（COM1/COM3）但 SerialPort open 仍拒絕存取，且 port 4000 空閒。`ReadLints` 僅為既有 clang/PlatformIO 參數與 Arduino include 誤報，實際 PlatformIO build 通過。
- push：未推送（MT-F3 尚未完成實機驗證；若需保留目前 build-pass 程式碼，可另行 commit partial）。

### 迭代 7 — 2026-07-15 12:58
- 任務：MT-F2 mictest 韌體錄音並上傳 `/api/mictest`。
- 結果：DONE（serial 二次觀察受 COM3 鎖定限制，改以 server state / WAV 分析佐證）。
- 變更檔案：`firmware/src/mictest/main.cpp`、`docs/plans/mic_test_plan.md`、`docs/plans/status/mictest_status.md`。
- 備註：`src/mictest/main.cpp` 現在為自包含測試韌體：連 Wi-Fi、初始化板載 PDM 麥克風（DATA=GPIO41、CLK=GPIO42、I2S0）、錄 3 秒 16kHz/16-bit/mono PCM、封 WAV header、HTTPS POST `https://www.blind-glasses.org/api/mictest` 並帶 `X-Device-Token`；預設每 15 秒自動一輪，serial 支援 `r` 立即錄音與 `i <ms>` 改間隔。首次 serial 擷取時公開入口未開，POST 回 530；確認開發機打公開網址同為 530 且本機 4000 未開後，啟動 mictest-only server 與 Cloudflare tunnel，再由 `/api/mictest/state` 看到真機自動上傳成功（`seq=8+`、`duration_sec=3.0`、TTS ready）。下載本機 latest WAV 分析：96044 bytes、48000 samples、peak=1392、RMS=1349.14、nonzero=48000，表示麥克風資料非全零。
- 驗證：`py -3 -m platformio run -e mictest` → SUCCESS；`py -3 -m platformio run -e mictest -t upload` → SUCCESS（COM3）；首次 `platformio device monitor` → `[MICTEST] POST /api/mictest code=530 ... bytes=96044`（tunnel 未開）；啟動 tunnel 後 `https://www.blind-glasses.org/mictest` → 200，`https://www.blind-glasses.org/api/mictest/state` → 200 且 `duration_sec=3.0`；WAV RMS/peak 分析如上。二次 serial monitor 因 COM3 `PermissionError(13)` 失敗，已依規則查無可辨識 python/platformio 殘留程序；`ReadLints` 僅為既有 clang/PlatformIO 參數與 Arduino include 誤報，實際 PlatformIO build 通過。
- push：`f8c28bd` 已推送到 firmware `origin/main`。

### 迭代 6 — 2026-07-15 12:48
- 任務：MT-F1 建立韌體 mictest 獨立環境與 I2S 腳位校正。
- 結果：DONE。
- 變更檔案：`firmware/platformio.ini`、`firmware/include/config.h`、`firmware/src/mictest/main.cpp`、`docs/plans/mic_test_plan.md`、`docs/plans/status/mictest_status.md`。
- 備註：新增 `[env:mictest]`，使用 `build_src_filter = -<*> +<mictest/>` 只編 `src/mictest/`；主環境加 `-<mictest/>` 避免測試程式混進正式韌體。`src/mictest/main.cpp` 先放最小 `setup/loop` 與 `[MICTEST] boot` 日誌。依使用者實際接線校正 `config.h`：`I2S_LRC_PIN=1`、`I2S_BCLK_PIN=2`、`I2S_DOUT_PIN=3`。提醒：韌體 README 腳位表之後需同步更新；使用者 Wi-Fi 資訊仍未寫入任何新追蹤檔。
- 驗證：`py -3 -m platformio run -e mictest` → SUCCESS；`py -3 -m platformio run -e seeed_xiao_esp32s3` → SUCCESS；`ReadLints` 僅回報既有 clang/PlatformIO 參數相容與 Arduino include 診斷，實際 PlatformIO build 通過。
- push：`cec31ea` 已推送到 firmware `origin/main`。

### 迭代 5 — 2026-07-15 12:43
- 任務：MT-S5 整理 mictest 回歸測試。
- 結果：DONE。
- 變更檔案：`server/tests/test_mictest.py`、`docs/plans/mic_test_plan.md`、`docs/plans/status/mictest_status.md`。
- 備註：`tests/test_mictest.py` 現在涵蓋 MT-S1～S4 的單元/靜態頁測試，並新增 live-server integration marker：設定 `MICTEST_INTEGRATION_BASE_URL=http://127.0.0.1:4000` 後會測 `/mictest`、`POST /api/mictest`、`state`、`latest.wav`、`reply.mp3`、ETag/304；未設定時 integration 測試會明確 skip，方便日常重複執行。使用者提供的 Wi-Fi 資訊僅作後續實機連線使用，未寫入任何追蹤檔。
- 驗證：一般回歸 `.local_cache\mictest-venv\Scripts\python.exe -m unittest discover -s tests -p "test_mictest.py" -v` → 8 tests OK、1 integration skipped；live integration `MICTEST_INTEGRATION_BASE_URL=http://127.0.0.1:4000 .local_cache\mictest-venv\Scripts\python.exe -m unittest tests.test_mictest.MicTestIntegrationTest -v` → 1 test OK；第一次 integration 啟動遇 port 4000 被 Python 殘留佔用，已確認 PID 後清理並重試通過；`ReadLints` 無診斷錯誤；port 4000 已釋放。
- push：`7c9b8df` 已推送到 server `origin/main`。

### 迭代 4 — 2026-07-15 12:36
- 任務：MT-S4 建立 `/mictest` 監看頁。
- 結果：DONE。
- 變更檔案：`server/static/mictest.html`、`server/main.py`、`server/tests/test_mictest.py`、`docs/plans/mic_test_plan.md`、`docs/plans/status/mictest_status.md`。
- 備註：新增 `/mictest` 頁面，前端每 2 秒輪詢 `/api/mictest/state`；`seq` 變化時抓 `/api/mictest/latest.wav`，用 Web Audio API `decodeAudioData` 與 canvas 畫波形；頁面顯示錄音時間、長度、ASR/TTS 耗時、ASR 文字、回覆文字與 TTS 狀態，並提供 latest WAV / reply MP3 兩個播放器。`main.py` 新增 `GET /mictest` 最小路由回傳靜態檔。
- 驗證：`.local_cache\mictest-venv\Scripts\python.exe -m unittest discover -s tests -p "test_mictest.py" -v` → 7 tests OK；臨時 uvicorn 於 `127.0.0.1:4000` 開 `/mictest`，POST 0.5s 非靜音假 WAV → 瀏覽器 DOM 顯示 `seq=1`、`duration=0.5s`、ASR/回覆文字更新、TTS ready，canvas bright pixel 計數 52825；截圖 `page-2026-07-15T04-36-01-042Z.png` 顯示波形與播放器；`ReadLints` 無診斷錯誤；臨時服務已停止。
- push：`570f22e` 已推送到 server `origin/main`。

### 迭代 3 — 2026-07-15 12:31
- 任務：MT-S3 產生語音回覆 MP3 與 `reply.mp3` ETag/304。
- 結果：DONE。
- 變更檔案：`server/mictest_api.py`、`server/tests/test_mictest.py`、`docs/plans/mic_test_plan.md`、`docs/plans/status/mictest_status.md`。
- 備註：ASR 完成後會用模板產生 `reply_text`（「我聽到了：...」），呼叫 edge-tts 直接合成獨立 mictest MP3 bytes，存單一槽位並更新 `tts_ready`/`tts_ms`。新增 `GET /api/mictest/reply.mp3`，回傳 `audio/mpeg`、`ETag`、`X-Mictest-Seq` 與 `Cache-Control`；帶相同 `If-None-Match` 時回 304。未共用主 `tts_queue`，避免干擾正式 `/audio/latest`。
- 驗證：`.local_cache\mictest-venv\Scripts\python.exe -m unittest discover -s tests -p "test_mictest.py" -v` → 6 tests OK；`.local_cache\mictest-venv\Scripts\python.exe -m pip install edge-tts` → 成功；臨時 uvicorn 於 `127.0.0.1:4000` POST 假 16kHz WAV（ASR mock 為 `hello`、TTS 使用真 edge-tts）→ `reply.mp3` 200、MP3 14256 bytes、ETag `"1-28b2620b18f764c5"`、帶 `If-None-Match` 重取 304；`ReadLints` 無診斷錯誤。
- push：`dfd7e34` 已推送到 server `origin/main`。

### 迭代 2 — 2026-07-15 12:27
- 任務：MT-S2 接入 mictest ASR 背景轉寫。
- 結果：DONE。
- 變更檔案：`server/mictest_api.py`、`server/tests/test_mictest.py`、`docs/plans/mic_test_plan.md`、`docs/plans/status/mictest_status.md`。
- 備註：`POST /api/mictest` 儲存 WAV 後會排入背景任務呼叫 `local_whisper_asr.transcribe_wav_bytes()`，以 `seq` 防止舊轉寫覆蓋新上傳；`state.asr_text` 與 `state.asr_ms` 會在完成後更新。若模型未載入、音訊無語音或轉寫為空，`asr_text` 會顯示 `ASR_EMPTY: ...`，不再靜默。此輪工作區無現成中文 WAV 樣本，實際中文語音辨識留待後續實機／人工語音驗收。
- 驗證：`.local_cache\mictest-venv\Scripts\python.exe -m unittest discover -s tests -p "test_mictest.py" -v` → 4 tests OK；臨時 uvicorn 於 `127.0.0.1:4000` POST 假 16kHz WAV → `GET /api/mictest/state` 200 且 `asr_text` 更新為 `ASR_EMPTY...`、`asr_ms` 有值；`ReadLints` 無診斷錯誤。
- push：`be8e074` 已推送到 server `origin/main`。

### 迭代 1 — 2026-07-15 12:23
- 任務：MT-S1 建立 mictest FastAPI router 與主 app 掛載。
- 結果：DONE。
- 變更檔案：`server/mictest_api.py`、`server/main.py`、`server/tests/test_mictest.py`、`docs/plans/mic_test_plan.md`、`docs/plans/status/mictest_status.md`。
- 備註：新增單槽 WAV 記憶體、`seq`/`received_at`/`duration_sec` 狀態、`latest.wav` 404/200 行為；`POST /api/mictest` 已加入既有 device token middleware 保護路徑。完整 `main.py` 在輕量測試 venv 會缺 `cv2`，因此 HTTP smoke 使用只掛 `mictest_api.router` 的臨時 uvicorn app 驗證端點本體。
- 驗證：`.local_cache\mictest-venv\Scripts\python.exe -m unittest discover -s tests -p "test_mictest.py" -v` → 2 tests OK；臨時 uvicorn 於 `127.0.0.1:4000` POST 假 16kHz WAV → `POST /api/mictest` 200、`GET /api/mictest/state` 200、`GET /api/mictest/latest.wav` 200 且 bytes 相同；`ReadLints` 無診斷錯誤。
- push：`957f60f` 已推送到 server `origin/main`。
