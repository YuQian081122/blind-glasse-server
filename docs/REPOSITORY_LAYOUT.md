# 倉庫目錄結構（本機子目錄 + GitHub 根目錄）

最後更新：採用 **Git Submodule** 同時滿足兩件事：

1. **GitHub `blind-glasses-firmware`**：仍是 **根目錄扁平**（`include/`、`src/`、`platformio.ini` 在倉庫根），給 CI、給只 clone 韌體的人用。
2. **你本機整包**：韌體在 **`firmware/` 子目錄** 底下（例如 `…/blind_glasses/firmware/include/config.h`），與 `server/` 並列。

兩者靠 **子模組** 連結：父目錄的 `firmware/` 資料夾本身就是一個 **完整的** `blind-glasses-firmware` clone，只是路徑在子目錄。

---

## 本機應長這樣（父工作區）

```
blind_glasses/                 ← 父 git 根（本 README 所在）
├── .git
├── .gitmodules                ← 宣告 submodule
├── firmware/                  ← 子模組（內部是韌體倉庫根）
│   ├── .git
│   ├── include/
│   ├── src/
│   ├── platformio.ini
│   └── README.md              ← 韌體專案說明（在子模組內）
├── server/                    # 可未納入父版控；依你習慣
├── docs/
│   └── REPOSITORY_LAYOUT.md   ← 本檔
└── clone_build_upload_firmware.bat
```

- **改韌體、pio、git push 韌體**：一律 `cd firmware` 再操作。
- **父目錄不要 `git push` 到 `blind-glasses-firmware`**（會破壞遠端版面）；韌體只從 `firmware` 裡面推。

---

## GitHub 上的韌體倉庫（不變）

`https://github.com/YuQian081122/blind-glasses-firmware` 內容為：

```
include/
src/
platformio.ini
.github/workflows/…
README.md
…
```

**沒有**多一層 `firmware/` 目錄名稱在遠端。

---

## 常見指令

| 目的 | 指令 |
|------|------|
| 第一次拉子模組 | 在父目錄：`git submodule update --init --recursive` |
| 韌體編譯 | `cd firmware` → `pio run` |
| 韌體推送 GitHub | `cd firmware` → `git push origin main` |
| 拉遠端最新韌體到子模組 | `cd firmware` → `git pull origin main`；回到父目錄執行 `git add firmware` 並 **commit**，才能把子模組指向的新 SHA 記進父倉庫（給其他 clone 父專案的人） |

---

## 不要做的事

| 不要 | 原因 |
|------|------|
| 在父目錄把 `include/` 再複製一份 | 與子模組重複，易推錯、易分叉。 |
| 把 `origin` 指回 `blind-glasses-firmware` 然後在父目錄 `git push` | 可能把父結構推上韌體倉庫。 |
| 手動把韌體檔只放在父目錄而不更新子模組 | GitHub 與本機 `firmware/` 會不一致。 |

---

## 其他電腦

- **只要韌體**：照舊 `git clone …/blind-glasses-firmware.git` 即可（根目錄即 PIO）。
- **要整包（含子模組）**：clone 父倉庫後務必執行 `git submodule update --init --recursive`（或 clone 時加 `--recursive`）。
