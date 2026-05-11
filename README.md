# 智慧導盲眼鏡（本機整包工作區）

本目錄為整包專案（例如與 `server/` 並列）。**韌體**請在子資料夾 **`firmware/`** 內以 **單獨 `git clone`** 取得，與 GitHub 上 **`blind-glasses-firmware`** 倉庫一對一對應。

## 目錄約定（必讀）

**[docs/REPOSITORY_LAYOUT.md](docs/REPOSITORY_LAYOUT.md)** — 內含 GitHub 根目錄版面與本機 `MyProject/server` + `MyProject/firmware` 的對照圖。

## 第一次拉韌體到本機

在**本目錄**（與 `server` 同層）執行：

```powershell
git clone https://github.com/YuQian081122/blind-glasses-firmware.git firmware
```

若已有 `firmware` 目錄請勿重複 clone。

## 日常指令

| 動作 | 作法 |
|------|------|
| 編譯／燒錄韌體 | `cd firmware` → `pio run` / `pio run -t upload` |
| 韌體 commit / push | `cd firmware` → `git add` … → `git push origin main` |
| 整包父目錄版控 | 只 commit 父目錄內容（**不含** `firmware/`，已 `.gitignore`） |

## 韌體倉庫

<https://github.com/YuQian081122/blind-glasses-firmware>
