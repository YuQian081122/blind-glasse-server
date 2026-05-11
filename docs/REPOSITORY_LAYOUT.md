# 目錄結構約定（正確版）

以下為**唯一建議**版面：GitHub 韌體倉庫保持根目錄扁平；本機用 **`firmware/` 子資料夾內單獨 `git clone`**，**不要用 submodule** 把韌體嵌進父 git。

---

## GitHub：`blind-glasses-firmware`（倉庫根）

```
（blind-glasses-firmware 倉庫根）
├── .github/
├── include/           ← 標頭檔
├── src/               ← 原始碼
├── platformio.ini
├── sdkconfig.defaults.template
├── TUNING_PROFILES.md
└── README.md
```

- 編譯：在 **clone 根目錄**（與 `platformio.ini` 同層）執行 `pio run`。
- CI、只拉韌體的人，都只面對這一層目錄。

---

## 本機：`MyProject/`（整包）

```
MyProject/
├── server/                    # FastAPI，可獨立 clone 或複製
└── firmware/                  # 單獨：git clone …/blind-glasses-firmware.git
    ├── .git
    ├── include/
    ├── src/
    └── platformio.ini         # 此層即 PlatformIO 根
```

### 第一次建立 `firmware/`（在 `MyProject` 根目錄執行）

```powershell
git clone https://github.com/YuQian081122/blind-glasses-firmware.git firmware
```

之後改韌體、推送韌體：

```powershell
cd firmware
git pull
git add -A
git commit -m "…"
git push origin main
pio run
```

### 父目錄（整包）的 git

- 父專案只版控 **`server/`、文件、腳本** 等；**不要**把 `firmware/` 目錄 commit 進父倉庫（本專案已將 `firmware/` 列入 `.gitignore`）。
- 韌體的歷史與遠端**只**存在 `firmware/.git`（即 `blind-glasses-firmware` 倉庫）。

---

## 不要做的事

| 不要 | 原因 |
|------|------|
| 在父倉庫用 **submodule** 指到同一個韌體 URL | 易與「單獨 clone 到 firmware」混淆，且父目錄 `git push` 風險較高。 |
| 把韌體檔複製一份到父目錄 `include/` | 與 `firmware/` 內 clone 重複，必然分叉。 |
| 把 `firmware/` 目錄 commit 進父倉庫 | 會把嵌套 `.git` 或大量二進位弄進父歷史。 |

---

## 其他電腦

- **只要韌體**：`git clone https://github.com/YuQian081122/blind-glasses-firmware.git`
- **要整包**：建立 `MyProject/`，先處理 `server/`，再在 `MyProject` 根執行上面的 `git clone … firmware`。
