# Skill 版本紀錄

每一版都由實驗數據觸發；各版原文在 `experiment/skill_versions/`。Claude 成本以「Claude 自己寫 = 100%」表示。

| 版本 | 改了什麼 | 為什麼 | Claude 成本 |
|---|---|---|---|
| v1 | Claude 寫完整驗收測試，agy 實作，自動驗收＋重試 | 起點 | 179% |
| v2 | Claude 只寫 2–4 個 golden asserts，完整測試交給 agy；加 agy 自我稽核；禁止為通過測試硬寫特例 | v1 的 Claude output 和自己寫一樣多；agy 曾為了錯誤的測試硬寫特例 | 134% |
| v3 | 獨立 spec 平行跑在 git worktree；背景執行、不輪詢 | agy 跑 15 分鐘讓子代理快取過期，一次重寫吃掉大半節省 | 113% / 94% |
| v4 | worker 預設 Flash low，失敗才升級；`--then-spec` 只用於依賴同批新模組 | low 總時長 <5 分鐘，快取不再過期，品質（hidden tests）不變 | **68% / 62%** |
| v5 | 前端：`frontend_rules.md`＋設計 checklist；小 UI Claude 自己寫 | Gemini 獨做視覺盲評墊底；Opus 審查找出 JS 共通問題 | — |
| v6 | `plan_split.py`、`--preset`、交接自我檢查、規格衝突規則、完工前自查、行為軌跡統計；大型 UI 設計系統分工 | 軌跡顯示 51–58% 空轉輪詢；大型 UI 唯一失敗來自 Claude 的交接矛盾 | 62–70% |
| **v7** | preset 預設 **Flash high**（稽核也 high）；`plan_split.py --subagent` | 盲審 high 8.3 vs 6.5、8 vs 7，low 有 tests 抓不到的 bug；子代理中長等待多付一次快取失效 | 主對話不變；agy 額度約 5× |
| (v8) | 子代理每 ≤4.5 分鐘喚醒以保溫快取 | 想避免 v7 的快取失效 | 實測多花 22% → **未採用** |
