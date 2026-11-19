# 實驗結果

> **2026-11-19 更新**：Gemini 4（Hydrogen / Neon / Argon / Orchestrator）的結果在 [第 10 節](#10-gemini-42026-11-19)。
> 第 1–9 節是 3.8 Flash 時期（2026-11-11）的數據，保留作為對照。

所有數字的量法見 [METHODOLOGY.md](METHODOLOGY.md)。**IET** = Claude 加權 token（input + 1.25×cache write + 0.1×cache read + 5×output）。
每個對照組（arm）都是一個 Sonnet 子代理在獨立工作目錄執行同一批任務；品質用雙方都看不到的 hidden tests 衡量。

## 1. 後端

### T1–T6（儲存層、parser、查詢 DSL、CLI、WSGI API、bug fix；50 個 hidden tests）
| arm | 做法 | Claude IET | vs 自己寫 | 回合 | hidden |
|---|---|---|---|---|---|
| A | Claude 自己寫 | 115.7k | 100% | 5 | 50/50 |
| B | 無腦外包＋讀完整 diff 審查 | 217.0k | **188%** | 29 | 50/50 |
| C1 | skill v1 | 207.5k | 179% | 17 | 50/50 |
| C2 | skill v2 | 155.2k | 134% | 14 | 50/50 |
| C3 | skill v3 | 130.6k | 113% | 7 | 50/50 |
| **C6** | **skill v4** | **78.9k** | **68%** | 9 | **50/50** |

### T7–T10（CSV/iCal 匯入匯出、undo/redo、循環任務、統計報表；17 個 hidden tests）
| arm | 做法 | Claude IET | vs 自己寫 | hidden |
|---|---|---|---|---|
| A2 | Claude 自己寫 | 112.7k | 100% | 17/17 |
| C4 | skill v3 | 105.7k | 94% | 17/17 |
| **C5** | **skill v4** | **69.9k** | **62%** | **17/17** |
| C7 | skill v6 | 89.7k | 80%（含子代理回報機制多出的 ~19k；扣除後 ≈ 62–70%） | 17/17 |

## 2. Flash effort：low vs high

同一個起始 commit，只改 effort；hidden tests 打平，所以另請 Sonnet **盲審**兩份實作（不知道哪份是哪個）。

| 任務 | effort | hidden | 耗時 | 5 小時額度 | 盲審分數 |
|---|---|---|---|---|---|
| T1–T6 | low | 50/50 | ~5 分 | 2.9% | 6.5 |
| T1–T6 | high | 50/50 | ~20 分 | 15.2% | **8.3** |
| T7–T10 | low | 17/17 | ~3.5 分 | 2.9% | 7 |
| T7–T10 | high | 17/17 | ~13.5 分 | 13.6% | **8** |

- low 有 hidden tests 沒抓到、但審查者可重現的 bug：CLI 以 `-` 開頭的參數失敗、PATCH 可存入錯誤型別、特定輸入造成 500、limit=0 切片錯誤、tag 大小寫重複計數。
- high 也有 bug（`splitlines()` 吃掉 U+2028 等字元），但較少、較輕；自寫測試多約 70%。
- 兩邊的 agy 自我稽核都回報 `NO_ISSUES`。⚠️ 更正：high 組（H6/H7）的稽核其實是以 Flash **low** 執行（當時 auditor 尚未改為 high），所以「high 的自我稽核也抓不到」當時並未證實；第 10 節另做了稽核能力測試。high 組的額度也因此略為低估。
- **結論：預設 Flash high**。代價是 agy 額度約 5 倍、時間約 4 倍。

## 3. 子代理中的等待成本

Claude 子代理的 prompt cache 只有 5 分鐘（主對話是 1 小時）。Flash high 一批要 10–20 分鐘，子代理必定經歷一次快取失效。

| arm | 等待方式 | Claude IET | 回合 | hidden |
|---|---|---|---|---|
| C9 | 閒置等通知（失效一次） | 142.1k | 11 | 17/17 |
| C8 | 每 ≤4.5 分鐘喚醒以保溫快取 | 172.7k | 20 | 17/17 |

- 失效只發生一次，代價約 30k（系統提示仍命中快取），與等待長短無關；保溫每次喚醒約 5–6k，等待一長就反超，而且 harness 會把超過約 3 分鐘的指令自動轉背景，節奏不穩定 → **不採用保溫**。
- C9 (142k) 高於 Claude 自己寫 (113k)：**在子代理裡用 Flash high 委派中型批次並不划算。** `plan_split.py --subagent` 已把這 30k 計入門檻。
- 主對話沒有這個問題 → 建議從主對話委派。

## 4. 小型前端（F1：單頁任務清單，5 個 Playwright 測試＋Opus 盲評截圖）

| arm | 做法 | Claude IET | vs 自己寫 | 功能 | 盲評 #1 | 盲評 #2 |
|---|---|---|---|---|---|---|
| FA | Claude 自己寫 | 94.6k | 100% | 5/5 | 7.7 | 7.0 |
| FG | 全交給 Gemini | 126.4k | 134% | 5/5 | **5.6（最後）** | **5.6（最後）** |
| FH | Claude 寫 HTML/CSS，Gemini 寫 JS | 151.1k | 160% | 5/5 | 7.0 | 7.4 |
| FH2 | 同上＋設計 checklist＋frontend_rules | 150.3k | 159% | 5/5 | – | **7.9** |

- Gemini 獨做的視覺兩次都墊底：行動版排版崩、深色模式原生控制項刺眼、層級弱。
- 小 UI 的 JS 很短，委派省不到錢。評審本身有約 ±0.7 分變異（FA 兩次 7.7 / 7.0）。

## 5. 大型前端（F2：5 個頁面的 SPA，7 個 Playwright 測試，Opus 盲評 9 張截圖）

| arm | 分工 | Claude IET | vs 自己寫 | 功能 | 盲評 |
|---|---|---|---|---|---|
| LA | Claude 全包 | 187.9k | 100% | 7/7 | 6.9 |
| LH | Claude 全部 HTML+CSS，Gemini 全部 JS | 202.2k | 108% | 6/7 | 7.4 |
| **LS** | **Claude 設計系統＋外殼＋1 個參考頁；Gemini 其餘頁面＋全部 JS** | **171.6k** | **91%** | **7/7** | **7.3** |

- LH 唯一的失敗來自 **Claude 自己的交接文件與模板矛盾** → 加入「交接自我檢查」與「衝突時以規格為準並回報」兩條規則。

## 6. 觀察 Gemini 的行為

- **工具呼叫軌跡**（agy 本機 SQLite）：前端任務中 Gemini 有 51–58% 的呼叫在輪詢背景測試；要求同步執行後多數降到 0%。之後每份報告都附一行統計。
- **自述決策紀錄**（要求 Gemini 寫 DECISIONS.md）：Opus 對照程式碼後發現是事前計畫而非事後紀錄，內容有不實（描述不存在的檔案、宣稱沒用的寫法其實有用），也沒抓到真 bug → 不建議例行使用。

## 7. 分工模型（`plan_split.py` 的依據）

```
Claude 節省 ≈ 12 × 被卸載的 output tokens − 35k（每批固定成本）
被卸載的 output ≈ 行數 × 每行 token（後端 20、前端 34）× 可卸載比例（後端 0.7、前端邏輯 0.25、視覺 0）
```
- 乘數 12 而不是 output 價格的 5：Claude 自己寫的程式碼之後每回合都會被重讀。
- 驗算：後端 470 行預測 +44k / 實測 +37–43k；大型 UI 分工 +13k / +16k；小 UI 預測為負 / 實測 −55k。
- 門檻：同一批可卸載的後端程式約 **300 行**以上才委派（子代理中約 550 行）。

## 8. 真實專案驗證

在一個真實的 Flask 專案（學生出缺席監控儀表板，作者的私人 repo）上走完整流程：
- `plan_split.py` 判定後端 4 項（~470 行）委派、安全與前端視覺由 Claude 做。
- Gemini（**3.8 Flash low**，v6 時期）在獨立 worktree 重構後端並寫 28 個測試：2 次嘗試、246 秒、輪詢 0%、稽核 `NO_ISSUES`、用掉 5 小時額度 1%。
- Claude 同時在主工作目錄改前端，截圖時抓到 2 個原有 bug；最後只抽查測試涵蓋不到的瀏覽器抓取段（~30 行），合併後 28/28 通過並開成 PR。

## 9. Gemini 端代價

| effort | 每批耗時 | 5 小時額度 | 週額度 |
|---|---|---|---|
| low | 3–5 分 | ~3% | ~1% |
| high | 10–20 分 | 14–17% | 4–5% |

週額度的前後差值很不穩定（例如 Hydrogen low 1.3% 反而高於 medium 0.43%），比較成本請以 5 小時額度為準。

## 10. Gemini 4（2026-11-19）

同樣的起始 commit，只換模型；`delegate.py` 平行 worktree＋同模型自我稽核。Orchestrator 不平行（它自己規劃整批），稽核用 Hydrogen high。
hidden tests 對所有組都滿分，因此另外加了兩種品質量法：
- **邊界探針**：依規格寫的自動檢查（T1–T6 35 項 `experiment/tools/edge_probe_t1_6.py`、T7–T10 21 項 `edge_probe_t7_10.py`），包含 2026-11-11 盲審找到的 bug 類型。
- **程式碼盲審**：Sonnet 對各組匿名的 T3–T5（query / cli / api）實際跑重現，只計可重現的 bug。

### 10.1 後端 T1–T6

| 模型 | hidden | 探針 | 盲審 | 盲審發現 | 耗時 | Gemini 5h | 其他額度 |
|---|---|---|---|---|---|---|---|
| Claude 自寫（Sonnet，A） | 50/50 | 33/35 | 5.5 | CLI 用法錯誤丟 `SystemExit`、PATCH 接受 `true` | – | – | – |
| 3.8 Flash low（C6） | 50/50 | 33/35 | – | – | ~5 分 | 2.9% | – |
| 3.8 Flash high（H6） | 50/50 | 35/35 | 6 | PATCH 接受 `true`/`2.0`、結尾斜線未回 404 | ~20 分 | 15.2% | – |
| Hydrogen high | 50/50 | 33/35 | 7 | PATCH 接受 `2.0`、接受阿拉伯–印度數字 | **4.7 分** | 4.9% | 週 1.8% |
| Neon high | 50/50 | 34/35 | **9** | 只有六組共通的深層巢狀 JSON 問題 | 9.9 分 | 12.7% | 週 4.0% |
| Argon high | 50/50 | 34/35 | 7.5 | PATCH 接受 `2.0` | 10.3 分 | – | Argon 週 14.8% |
| Orchestrator (Neon) | 50/50 | 34/35 | 8 | PATCH 接受 `2.0` | 8.7 分 | ~4%* | 週 1.1% |
| **Orchestrator (Argon)** | 50/50 | **35/35** | **8.5** | 空 `CONTENT_LENGTH` 回 400 | 8.7 分 | **2.3%** | Argon 週 1.6% |

\* 與 Argon 組同時執行，估計值。Argon 有獨立額度桶，交叉比對顯示它不吃 Gemini 共用額度。

- **Orchestrator** = 規劃模型（Argon / Neon）＋執行模型 Hydrogen high。從 agy 本機軌跡看，同一個對話中約 6 次規劃模型生成、12 次 Hydrogen 生成，沒有開子代理。
- Orchestrator 的品質比 Hydrogen 單獨做高（8–8.5 對 7），額度卻比平行 6 個 worktree 更低：單一 session 省掉每個規格各自約 25k 的固定開銷，也不需要合併後修正。
- 六組共通的漏洞：PATCH 收到極深巢狀 JSON（10 萬層 `[`）會丟 `RecursionError`。

### 10.2 後端 T7–T10（17 hidden + 21 項探針）

| 模型 | hidden | 探針 | 耗時 | Gemini 5h |
|---|---|---|---|---|
| 3.8 Flash low（C7） | 17/17 | 20/21（tag 大小寫重複計數） | ~3.5 分 | 2.9% |
| 3.8 Flash high（H7） | 17/17 | 20/21（`splitlines()` 吃掉 U+2028） | 13.6 分 | 13.6% |
| Hydrogen low / medium / high / xhigh | 17/17 | 21/21 | 1.4 / 2.3 / 3.7 / 7.1 分 | 2.1 / 1.5 / 3.5 / 8.1% |
| Neon high | 17/17 | 21/21 | 9.4 分 | 9.5% |
| Argon high | 17/17 | 21/21 | 8.1 分 | Argon 週 8.6% |

探針重現了 2026-11-11 盲審指出的兩個 bug，代表那次盲審結論可信。Hydrogen xhigh 成本是 high 的兩倍多，沒有看到品質差別。

### 10.3 小型前端 F1（Gemini 獨自完成 HTML/CSS/JS，Opus 盲評 25 張截圖）

| 作者 | 功能 | 階層 | 版面 | 暗色 | 手機 | 狀態 | **總分** | Gemini 額度 |
|---|---|---|---|---|---|---|---|---|
| **Neon high** | 5/5 | 8 | 9 | 8 | 8 | 9 | **8.5** | 5h 4.0% |
| Claude 自寫（FA） | 5/5 | 8 | 8 | 8 | 9 | 7 | 8 | – |
| Hydrogen high | 5/5 | 7 | 7 | 7 | 7 | 8 | 7 | 5h 2.0% |
| Argon high | 5/5 | 6 | 5 | 7 | 3 | 7 | 5 | Argon 週 4.6% |
| 3.8 Flash low（FG） | 5/5 | 6 | 5 | 3 | 3 | 5 | 4.5 | – |

- 截圖並排比較：[`data/screenshots/compare_gemini4/`](../data/screenshots/compare_gemini4/)（亮色、暗色、手機、錯誤＋焦點、空狀態）。
- 只評一次，評審變異約 ±0.7，因此 Neon 與 Claude 應視為**打平**。不過「Gemini 獨做視覺一定墊底」這個 3.8 Flash 時期的結論已經不成立。
- Gemini 的程式量明顯較多（Neon 896 行，Claude 164 行），所以 Claude 只看截圖、不讀程式碼。

![桌面亮色比較](../data/screenshots/compare_gemini4/1_desktop_light.png)

### 10.4 自我稽核能力

把 3.8 Flash low 寫的 T1–T6（含 2 個已知 bug）交給各模型，用 `delegate.py` 同一份稽核提示詞審查（`experiment/tools/audit_probe.py`，原文見 `data/gemini4_audit_probe.md`）：

| 稽核模型 | 已知 bug 抓到 | 其他回報 |
|---|---|---|
| Hydrogen high | **1/2**（CLI 遇到 `-` 開頭字詞失敗） | 4 項邊角（非 `YYYY-MM-DD` 的 ISO 日期、`$` 對比 `\Z`） |
| Neon high | 0/2（`NO_ISSUES`） | – |
| Argon high | 0/2（`NO_ISSUES`） | – |
| 3.8 Flash high | 0/2（`NO_ISSUES`） | – |

→ 稽核角色改用 Hydrogen high，但「重要模組由 Claude 抽查」仍然必要。

### 10.5 對其他結論的影響
- **子代理快取**：Hydrogen high 平行一批約 4–5 分鐘，接近子代理 5 分鐘的快取期限，C9 的快取失效懲罰可能變小。`delegate.py --fast` 就是為此保留；尚未實測 Claude 端的 IET。
- **Claude 端成本**：v9 的 Claude 流程與 v7 相同（寫合約、讀報告），預期 Claude IET 不變；本次沒有重新量測。
