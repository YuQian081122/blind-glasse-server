# 智慧導盲眼鏡（本機整包工作區）

本目錄為**父專案**：韌體在子目錄 **`firmware/`**（Git **子模組** submodule），與 `server/` 等並列。

## 目錄約定（必讀）

請閱讀 **[docs/REPOSITORY_LAYOUT.md](docs/REPOSITORY_LAYOUT.md)** — 說明「本機 `firmware/` 子目錄」與「GitHub 韌體倉庫根目錄扁平」如何同時成立。

## 韌體（PlatformIO）

- 路徑：`firmware/include/`、`firmware/src/`、`firmware/platformio.ini`
- 編譯／燒錄：

```powershell
cd firmware
pio run
pio run -t upload
```

- 修改韌體、**推送到 GitHub**（`blind-glasses-firmware`）一律在 **`firmware` 目錄內**執行：

```powershell
cd firmware
git pull origin main
git add -A
git commit -m "你的說明"
git push origin main
```

## 遠端說明

- 本父專案**已移除**原本指向 `blind-glasses-firmware` 的 `origin`，避免在父目錄誤執行 `git push` 把整包結構推壞韌體倉庫。
- 韌體子模組內仍有 `origin` → `https://github.com/YuQian081122/blind-glasses-firmware.git`
- 伺服器遠端仍為：`glasse-server` → `blind-glasse-server`（若你有使用）

## 第一次 clone 本工作區

```powershell
git clone <你的父倉庫-URL> blind_glasses
cd blind_glasses
git submodule update --init --recursive
```

若父倉庫尚未上 GitHub，可只 clone 韌體子模組單獨使用：見 `clone_build_upload_firmware.bat` 或單獨 `git clone …/blind-glasses-firmware.git`。
