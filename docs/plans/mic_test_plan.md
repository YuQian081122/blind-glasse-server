# 麥克風端到端測試計畫（獨立計畫，MT 系列）

> 建立：2026-07-15｜狀態：待執行｜執行者：**一個獨立的 mic-test agent**（非四大 agent）
> 目標流程：**ESP32 內建麥克風錄音 → 上雲端伺服器 → `www.blind-glasses.org/mictest` 顯示波形＋轉文字 → 產生語音回覆傳回眼鏡用喇叭播出**
> 狀態檔：`docs/plans/status/mictest_status.md`（不存在則第一輪自行建立，格式仿其他 status 檔）。

## 0. 與主計畫的關係

- 本計畫**獨立於**四大 agent 的計畫，可在主 loop 開跑前單獨執行；它同時觸碰 `firmware/` 與 `server/` 兩個 repo（範圍見 §2 邊界）。
- **不要與韌體 agent／伺服器 agent 同時跑**，避免兩個 agent 改同一個 repo 互踩；若主 loop 已在跑，先停掉那兩個。
- 本計畫完成後，順帶完成主計畫 `firmware_plan.md` **F-1b 的麥克風實測項**（把結果抄進 firmware status 的硬體基線表）。
- 新增的 HTTP 介面已登記在 `contracts.md`（C-004），主計畫的 agent 之後會看到。

## 1. 背景（現有資產，全部可重用）

| 資產 | 位置 | 現況 |
|------|------|------|
| PDM 麥克風錄音＋WAV 封裝 | `firmware/src/mic_upload.cpp` | 已實作：I2S0、DATA=GPIO41、CLK=GPIO42、16kHz 16-bit mono、自寫 WAV header、POST `/api/asr`。**麥克風硬體從未實測過——本計畫就是它的首測。** |
| 喇叭播放 | `firmware/src/audio_player.cpp` | ESP32-audioI2S 函式庫，`I2S_NUM_1`（D0–D2 → MAX98357A），可播 MP3 URL |
| 自動錄音旗標 | `firmware/include/config.h` | `MIC_AUTO_TEST_ENABLE`／`MIC_AUTO_TEST_INTERVAL_MS`（預設關） |
| Whisper ASR | `server/local_whisper_asr.py` | faster-whisper，既有 `/api/asr` 流程在用 |
| edge-tts 語音合成 | `server/tts_queue.py` | zh-TW 語音、產 MP3、`/audio/latest` 有 ETag/304 模式可抄 |
| 雲端入口 | `https://www.blind-glasses.org`（Cloudflare Tunnel → 本機 uvicorn :4000） | 運作中 |

### 1.1 實際接線（2026-07-15 使用者確認，**以此為唯一真值**）

- **喇叭（MAX98357A）：LRC＝GPIO1、BCLK＝GPIO2、DIN＝GPIO3**。
- **麥克風：板子內建 PDM 腳位**（DATA=GPIO41、CLK=GPIO42，與 `mic_upload.cpp` 現碼一致，不用改）。
- ⚠️ `config.h` 目前的定義是 `I2S_DOUT_PIN=1、I2S_BCLK_PIN=3、I2S_LRC_PIN=2`，**與實際接線不符**（README 的腳位表又是第三種）。MT-F1 時把 `config.h` 三個 I2S 常數改成上面實際接線（`I2S_LRC_PIN=1、I2S_BCLK_PIN=2、I2S_DOUT_PIN=3`）並在註解標「2026-07-15 依實際接線校正」；mictest 程式一律引用 `config.h` 常數，不得自寫死腳位。若喇叭無聲，第一個排查點就是這三根線。

## 2. 邊界

- 可寫：`firmware/`（僅 `platformio.ini` 增段落＋新增 `src/mictest/`＋必要時 `include/config.h` 加常數）、`server/`（僅新增 `mictest_api.py`／`static/mictest.html`／`tests/test_mictest.py`＋在 `main.py` 掛 router 的最小修改）、本檔勾選、`status/mictest_status.md`。
- 禁止：動主韌體 `src/` 既有檔案的邏輯、動伺服器既有 endpoint 行為、`App1/`、根目錄共用檔（CHANGELOG 由雜務 agent 彙整）。
- 密鑰規則同 `00_coordination.md` §6：Wi‑Fi 帳密與 token 不進 git。
- 遵守 `00_coordination.md` §8（實機測試）與 §8.1（資源佔用防呆：port 4000、COM port、誰開的誰關）。
- **裝置無實體按鈕**（§7.1）：錄音觸發只能用「自動間隔」或「序列埠指令」，不得設計按鈕流程。

## 3. 任務清單（優先序＝列出順序；一輪一項；每項完成即 commit＋push 到對應 repo）

### 伺服器端（先做——沒有裝置也能用假 WAV 開發到好）

- [x] **MT-S1** 建 `server/mictest_api.py`（FastAPI APIRouter）＋掛進 `main.py`：
  - `POST /api/mictest`：收 WAV bytes（`audio/wav`，帶 `X-Device-Token`，驗證邏輯與既有 middleware 一致）；存單一槽位記憶體（bytes＋收到時間＋序號遞增）。
  - `GET /api/mictest/latest.wav`：回最新錄音（無則 404）。
  - `GET /api/mictest/state`：JSON——`{seq, received_at, duration_sec, asr_text, asr_ms, reply_text, tts_ready, tts_ms}`。
  - 驗證：`uvicorn` 起本機，PowerShell 腳本 POST 一段現成 16kHz WAV → 三個端點行為正確。
- [x] **MT-S2** ASR 接入：收到上傳後（背景 task）丟 `local_whisper_asr` 轉寫，結果與耗時寫進 state。模型未載時 state 要顯示明確錯誤字串，不得靜默。
  - 驗證：POST 一段中文語音樣本 WAV → `state.asr_text` 出現合理文字。
- [x] **MT-S3** 語音回覆產生：ASR 完成後組回覆文字（模板：「我聽到了：〈轉寫內容〉」；`.env` 有 `GEMINI_API_KEY` 時可選 Gemini 一句話回覆，失敗退回模板），edge-tts 合成 MP3 存單一槽位；`GET /api/mictest/reply.mp3` 帶 **ETag/304**（抄 `/audio/latest` 的模式），不要共用主 TTS 佇列（避免干擾正式流程）。
  - 驗證：POST WAV → 幾秒內 `reply.mp3` 200 且 ETag 變化；重複 GET 帶 If-None-Match 得 304。
- [x] **MT-S4** `/mictest` 監看頁（`server/static/mictest.html`，路由 `GET /mictest`）：
  - 每 2s 輪詢 `state`；`seq` 變化時抓 `latest.wav`，用 **Web Audio API `decodeAudioData` ＋ canvas** 畫波形（客戶端畫，伺服器零依賴）。
  - 顯示：波形、錄音時間、ASR 文字與耗時、回覆文字、TTS 狀態、端到端各段延遲。
  - 頁面可播放 `latest.wav` 與 `reply.mp3`（HTML `<audio>`），方便沒戴眼鏡時人工核對。
  - 驗證：瀏覽器（cursor-ide-browser）開 `http://127.0.0.1:4000/mictest`，POST 假 WAV 後 2s 內波形與文字更新。
- [x] **MT-S5** 回歸腳本：把 MT-S1～S4 的驗證整理成 `server/tests/test_mictest.py`（需要跑著的 server 的標 integration marker），可重複執行。

### 韌體端（獨立空白環境，不動主韌體）

- [x] **MT-F1** 在 `firmware/platformio.ini` 新增 `[env:mictest]`：同板子（`seeed_xiao_esp32s3`）、同 lib_deps，**`build_src_filter = -<*> +<mictest/>`** 只編 `src/mictest/`——這就是「空白韌體環境」，與主韌體同 repo 共用工具鏈與腳位定義，但互不影響（主環境的 filter 同時加 `-<mictest/>`）。
  同時依 §1.1 把 `config.h` 的 I2S 腳位改成實際接線（`I2S_LRC_PIN=1、I2S_BCLK_PIN=2、I2S_DOUT_PIN=3`），並在 status 檔記一筆「腳位校正」提醒之後更新韌體 README 的腳位表。
  - 驗證：`py -3 -m platformio run -e mictest` 綠（先放一個空 `setup/loop`）；`pio run -e seeed_xiao_esp32s3` 仍綠。
- [x] **MT-F2** `src/mictest/main_mictest.cpp` 最小流程：連 Wi‑Fi（沿用 config.h/secrets 機制）→ 錄 3 秒 PDM 16kHz WAV（搬用 `mic_upload.cpp` 的 I2S0 初始化與 WAV header 程式碼，複製到 mictest 內，不 include 主 src）→ HTTPS POST `https://www.blind-glasses.org/api/mictest`（帶 `X-Device-Token`）。
  - 觸發方式（無按鈕）：預設由 `/mictest` 網頁「開始錄音」按鈕下發一次性命令；序列埠輸入 `r` 立即錄一次、`i <ms>` 開啟自動間隔、`i 0` 關閉自動間隔。
  - 序列日誌統一 `[MICTEST]` 前綴：錄音樣本數、上傳耗時、HTTP 狀態碼。
  - 驗證：燒錄 `-e mictest`，serial 看到 POST 200；`/mictest` 頁面出現真實波形（**環境音即可，尚不需人講話**）。
- [x] **MT-F3** 回覆播放：POST 成功後輪詢 `GET /api/mictest/reply.mp3`（If-None-Match，最多等 30s），拿到新音檔用 ESP32-audioI2S（`I2S_NUM_1`）播放；播放期間暫停錄音（先錄後播、不同 I2S port，時序上完全錯開最保險）。
  - 序列日誌：等待耗時、播放開始/結束。
  - 驗證：燒錄後 serial 顯示播放開始；喇叭是否真的出聲需人耳確認（NEEDS-HUMAN）。

### 端到端驗收

- [ ] **MT-E1** 全鏈路實測（NEEDS-HUMAN，一次做完）：請使用者對眼鏡講一句話（例如「今天天氣如何」），驗收：
  1. `/mictest` 頁面波形有明顯語音包絡（不是平線＝麥克風硬體 OK，**這是麥克風首測的判定點**）；
  2. ASR 文字大致正確；
  3. 喇叭播出「我聽到了：…」回覆；
  4. 把各段延遲（錄音→上傳→ASR→TTS→取回→播放）記進 status 檔。
  - 若波形平線：跑韌體 README 的 IMU 式診斷思路——serial 確認 I2S read 回傳的 bytes 非全零、檢查 CLK/DATA 腳位定義，結果記 status，硬體疑似故障就標 BLOCKED 通知使用者。
- [ ] **MT-E2** 收尾：把麥克風實測結果回填 `firmware_plan.md` F-1b 基線表的「麥克風」列（透過 status 檔告知，不直接改對方計畫檔的其他部分）；兩個 repo 各自 push；status 檔寫 LOOP-DONE 總結（含已知限制）。

## 4. 技術選型與原因

| 事項 | 選擇 | 原因 |
|------|------|------|
| 韌體隔離 | 同 repo 多 env（`build_src_filter`）而非新 repo | 共用工具鏈、腳位、secrets 機制；不會產生第二份會過時的副本（Arduino/ 的教訓） |
| 錄音格式 | 16kHz 16-bit mono WAV（自寫 header，沿用現碼） | Whisper 原生取樣率、3 秒僅約 96KB，Cloudflare 上傳無壓力 |
| 錄放並存 | 先錄後播、時序錯開（mic=I2S0、喇叭=I2S1） | 雖然 port 不同，錯開最穩，測試場景不需全雙工 |
| 波形顯示 | 瀏覽器 Web Audio API＋canvas | 伺服器零新依賴；波形計算丟給客戶端 |
| 回覆音檔 | 獨立單槽位＋ETag/304 | 不污染主 `/audio/latest` 與 TTS 佇列；裝置輪詢省流量 |
| 觸發 | 自動間隔＋序列埠指令 | 裝置無按鈕（§7.1）；序列埠在測試場景永遠可用 |

## 5. 工具（Skills / MCP）與原因

| 工具 | 原因 |
|------|------|
| PlatformIO CLI（`py -3 -m platformio run -e mictest -t upload`） | 建置＋燒錄；板子已插 USB，agent 自己燒 |
| Skill `.cursor/skills/esp32-serial-logging/SKILL.md` | `[MICTEST]` 日誌限時擷取斷言（不留互動式 monitor，§8.1） |
| Skill `.cursor/skills/fastapi-python/SKILL.md` | mictest router 寫法 |
| MCP `cursor-ide-browser` | 開 `/mictest` 頁面目視波形與文字 |
| PowerShell `Invoke-RestMethod`／`Invoke-WebRequest` | 無裝置時 POST 假 WAV 煙霧測試 |
| Skill `systematic-debugging` | 波形平線／I2S 全零時的分層排查 |

## 6. 受阻與求助

- port 4000／COM port 被占 → 依 `00_coordination.md` §8.1 清理，重試一次，仍失敗標 BLOCKED。
- 需要人講話、聽喇叭 → §8 通知格式（status 檔 `NEEDS-HUMAN` ＋ 回覆末尾醒目段落），等待期間先做其他任務。
- Whisper 模型缺 → 先讓 state 顯示明確錯誤並完成其餘鏈路，模型下載標 NEEDS-HUMAN（檔案大，讓使用者決定何時下載）。

## 7. 完成條件（LOOP-DONE）

MT-S1～S5、MT-F1～F3、MT-E1～E2 全部 `[x]` 或 BLOCKED/NEEDS-HUMAN；兩個 repo 變更已 commit＋push；`pio run` 兩個 env 皆綠；`pytest tests -m "not integration"` 綠；端到端延遲數據已記錄。

---

## 8. 給 mic-test agent 的啟動提示詞（複製整段）

```text
你是「盲人眼鏡」專題的麥克風測試 agent，在工作區 c:\Users\sl131\Downloads\blind_glasses 工作。
你的唯一任務來源是 docs/plans/mic_test_plan.md（MT 系列任務），共同規範在 docs/plans/00_coordination.md
（特別是 §7.1 硬體清單／無按鈕、§8 實機測試、§8.1 資源佔用防呆）。
狀態檔 docs/plans/status/mictest_status.md 不存在就先建立（格式仿同資料夾其他 status 檔）。

每一輪迭代固定流程：
1. 重讀 mic_test_plan.md 與自己的 status 檔，確認上一輪進度。
2. 挑一項未完成、未被依賴阻擋的最高優先任務（清單順序＝優先序），一輪只做一項。
3. 實作並以「實際執行」驗證：伺服器任務要真的起 uvicorn 打端點、韌體任務要真的
   pio run -e mictest（需要時 -t upload 燒錄＋限時擷取 serial 日誌）。禁止「理論上可行」就打勾。
4. 在 plan 檔打勾、status 檔最上方追加迭代紀錄（最後兩行固定：「驗證：指令→實際結果」、
   「push：commit hash 或未推原因」）。
5. 在對應 repo commit（Conventional Commits，如 feat(mictest): ...）並立刻 push
   （firmware → blind-glasses-firmware、server → origin=YuQian081122/blind-glasse-server）。

特別注意：
- 板子已插 USB、平板與伺服器都在這台電腦上；能自動測的自己測。
- 裝置沒有任何實體按鈕：錄音觸發只能用自動間隔或序列埠指令。
- 只能動計畫 §2 邊界內的檔案；不得改主韌體既有邏輯與伺服器既有 endpoint。
- 需要人講話、聽喇叭出聲時：status 檔寫 NEEDS-HUMAN，並在該輪回覆最後用醒目段落
  告訴使用者「要做什麼、預期看到什麼、做完怎麼回報」，等待期間跳去做下一項。
- port 4000／COM 被占用：找出殘留程序殺一次→重試一次→仍失敗標 BLOCKED，禁止空轉。
- 同一任務連續 2 輪失敗標 BLOCKED 換下一項；全部完成或受阻時寫 LOOP-DONE 停止。

最容易被遺忘、絕對不可省略的兩件事：每項任務完成後「實際執行驗證」與「commit + push」。
沒做這兩件事就不算完成。
```
