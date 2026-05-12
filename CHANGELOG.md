# 變更紀錄（專題進度／版本追蹤）

本檔供專題進度與版本追蹤使用。  
每次可交付變更請在 **`[Unreleased]`** 區塊最上方新增一則條目（繁體中文、含範圍與摘要）。

---

## [Unreleased]

### 2026-05-11 — Server 依賴完整安裝驗證與遠端同步

**範圍：** `server/`（含 `requirements.txt`）

**版本：** 未 bump

**變更摘要：**
- 於本機 venv 執行 `pip install -r requirements.txt`、`pip check`，確認 `import main` 可載入。
- `requirements.txt` 頂部補充環境／驗證說明，並顯式加入 `python-multipart`（FastAPI 常見相依）。

**驗證：** `pip check` 通過；`python -c "import main"` 通過（含既有 google.generativeai FutureWarning）

---

### 2026-05-12 — 建立版本紀錄規則與本檔

**範圍：** 文件／設定

**版本：** 未 bump

**變更摘要：**
- 約定：每次更新須同步撰寫版本／變更說明於本檔，供專題進度報告使用。
- 新增 `CHANGELOG.md` 作為單一匯總處（含 `server/` 子目錄變更時亦在此摘要）。

**驗證：** 無（僅新增規則與範本）

---
