# 原始數據

| 檔案 | 內容 |
|---|---|
| `runs.jsonl` | 每次 `delegate.py` 執行一行：tag（= arm）、每次嘗試的模型/耗時/token、agy 額度差、檔案、稽核結果、行為軌跡 |
| `quota.jsonl` | 每次讀取 agy `/usage` 的額度快照 |
| `arms.json`、`arms_r3.json`、`arms_front.json`、`arms_large.json` | 各輪對照組定義（arm → 說明、工作目錄、任務） |
| `report_rows*.json` | 各輪對照組的 Claude IET、回合、output、hidden tests 結果 |
| `blind_map*.json` | 盲評時截圖代號 ↔ arm 的對照表 |
| `screenshots/<arm>/` | 前端截圖（桌面／手機／亮暗） |

路徑中的 `<repo>`、`<subagent-transcripts>` 是原本的本機路徑，已去識別化；子代理 transcript 本身未公開（含完整對話內容）。

## Gemini 4（2026-11-19）
- `runs.jsonl` / `quota.jsonl`：新增 tag `Y_*`（Hydrogen 四種 effort，T7–T10）、`B6_*`（T1–T6：hy=Hydrogen、ne=Neon、ar=Argon、or=Orchestrator(Neon)、oa=Orchestrator(Argon)）、`Y7_*`、`F_*`（F1 前端）。
- `blind_map_b6.json`、`blind_map_f1_g4.json`：盲審代號對照。
- `gemini4_audit_probe.md`：稽核能力測試的原始回覆。
- `screenshots/F_hy`、`F_ne`、`F_ar`：各組 F1 截圖；`screenshots/compare_gemini4/`：五組並排比較圖。
