# 使用說明

以下 `$COWORK` 指 skill 安裝位置，預設 `~/.claude/skills/agy-cowork`。

## 1. 判斷要不要委派：`plan_split.py`

把要做的項目列出來，它依實測模型回答每項由誰做、整批值不值得：

```bash
python3 $COWORK/tools/plan_split.py '[
  {"name":"parser","kind":"backend","lines":120,"testable":true},
  {"name":"tests backfill","kind":"tests","lines":220,"testable":true},
  {"name":"auth check","kind":"bugfix","lines":25,"judgment":true}
]'
```
```
AGY    parser                       backend            120 lines  offloadable ≈ 20k IET
AGY    tests backfill               tests              220 lines  offloadable ≈ 48k IET
CLAUDE auth check                   bugfix              25 lines  needs design/security judgment
BATCH: delegate 2 item(s) in ONE delegate.py call (--parallel for independent ones); expected Claude saving ≈ 33k IET
```

| 欄位 | 說明 |
|---|---|
| `kind` | `backend` `logic` `bugfix` `refactor` `tests` `docs` `frontend-logic` `frontend-visual` |
| `lines` | 預估程式行數（含測試） |
| `testable` | 能否用自動測試驗收；`false` → Claude |
| `judgment` | 需要架構／安全／設計判斷；`true` → Claude |

規則：`frontend-visual` 一律 Claude；<40 行的項目 Claude；整批可卸載量低於門檻 → 全部 Claude 自己做。
在子代理中執行時加 `--subagent`（門檻會提高，見 [RESULTS.md](RESULTS.md#子代理中的等待成本)）。

## 2. 後端委派

1. 只讀需要的介面／型別檔案。
2. 寫 `tests/acceptance/test_golden.py`：每個任務 2–4 個 assert，釘住最容易錯的規則（正常、邊界、錯誤）。完整測試交給 Gemini 寫。
3. 背景執行，然後結束回合（不要輪詢）：

```bash
python3 $COWORK/tools/delegate.py --preset backend --workdir <repo> \
  --spec specs/a.md --spec specs/b.md [--then-spec specs/c.md] [--fast] \
  --accept "python -m pytest -q tests" --tag <label> > <repo>/.delegate_report.txt 2>&1
```

4. 讀報告：

```
[B6_oa] ACCEPTED=True attempts=2 models=['gemini-pro-orchestrator-g1-pro', 'gemini-4-hydrogen-high']
agy tokens=216758 quota_used={'Gemini Models/gemini-weekly': 0.0136, 'Gemini Models/gemini-5h': 0.0227}
files=['evtrack/api.py', 'evtrack/cli.py', 'evtrack/parser.py', …, 'tests/test_storage.py']
public=['JsonStore', 'filter_tasks', 'main', 'make_app', 'next_occurrence', 'parse_quick', …]
worker trace: wall=523s calls=55 tests=7 polls=0 waste=0%
audit: NO_ISSUES
```

- `ACCEPTED=True`、audit 為 `NO_ISSUES` 或已修正、沒有 `WARNING` → 完成，不需要打開程式碼。
- Worker 回報 spec 衝突 → 只檢查那一點。
- `ACCEPTED=False` → 看報告尾端；小問題自己修，或重新委派一次。
- `waste` > 20% 代表 Gemini 在空轉輪詢，不影響 Claude，但反覆出現值得留意。

### `delegate.py` 參數

| 參數 | 說明 |
|---|---|
| `--preset backend` | 一次帶入實測最佳設定：**Orchestrator**（單一 session，不平行；沒額度時退回 Hydrogen high＋`--parallel`）、`--audit`（Hydrogen high）、重試 2 次、保護 `tests/acceptance/*` |
| `--fast` | 搭配 `--preset backend`：跳過 Orchestrator，直接用 Hydrogen high 平行（約 5 分鐘）。在 Claude 子代理中使用 |
| `--preset frontend-js` | Hydrogen high、不平行、`--audit`，並附上 `frontend_rules.md` |
| `--spec FILE` | 規格檔，可多個；`--parallel` 時每個在自己的 git worktree 平行執行 |
| `--then-spec FILE` | 依賴同批新建模組的規格，等前面合併後才跑 |
| `--accept CMD` | 驗收指令（必填）；失敗輸出會自動回餵給 Gemini 重試 |
| `--protect GLOB` | 受保護檔案；被改動會自動還原 |
| `--role` / `--escalate-role` | 模型角色（見第 4 節）；`worker_fast` 只用在很瑣碎的機械式修改；`designer` 用於小型 UI 試做 |
| `--retries N` | 重試次數，預設 2 |
| `--timeout S` | 單次 agy 呼叫上限秒數（預設 1800） |

退出碼：`0` 通過、`1` 未通過、`3` agy 額度用完（換帳號後再試）、`4` agy 執行錯誤。

## 3. 前端

| 規模 | 做法 |
|---|---|
| 小型（≲300 行） | Claude 自己寫，照 SKILL.md 的設計 checklist；或（試行）讓 `designer`（Neon high）先做，Claude 只看截圖 |
| 大型（多頁、大量互動） | 設計系統分工 ↓ |

小型 UI 試行做法（Gemini 4 Neon 盲評 8.5，與 Claude 8 打平，但只評過一次）：
```bash
python3 $COWORK/tools/delegate.py --role designer --audit --protect 'tests/acceptance/*' --workdir <repo> \
  --spec specs/ui.md --accept "python -m pytest -q tests" --tag ui
```
完成後截圖（亮／暗／手機／錯誤／空狀態）對照設計 checklist；不要讀它的程式碼（約是 Claude 寫法的 5 倍長）。不合格就自己修 CSS 或重寫。

設計系統分工：
1. Claude 寫 `css/design.css`（明暗色彩 token、間距字級、所有元件 class 與狀態、RWD；檔頭列出 class 索引）、`index.html` 外殼，和**一個完整的參考頁面**。
2. Claude 寫關鍵流程的 Playwright golden tests。
3. 交接前自我檢查：規格中每個 id / testid 都和 markup 一致；要「顯示某值」的 testid 必須包住該值的文字。
4. 委派：`delegate.py --preset frontend-js --spec <規格> --spec <交接說明> --protect 'css/design.css' …`
5. 截圖一次（亮／暗／手機），CSS 問題 Claude 自己修。

`frontend_rules.md` 會一起交給 Gemini，內容是 Opus 審查 Gemini 前端程式碼後整理的必守規則（`hidden` 屬性、事件委派、焦點還原、AbortController、先檢查 `res.ok`、`aria-live`、不用 `innerHTML` 插資料…）。

## 4. 模型選擇（不寫死）

`config/model_policy.json` 只描述「角色 → 模型家族（依偏好排序）+ effort」，執行時讀 `agy models` 和 `/usage`，挑第一個有額度的家族中最新的版本：

| 角色 | 預設（依序嘗試） | 用途 |
|---|---|---|
| `orchestrator` | Orchestrator (Carbon → Argon → Neon) | `--preset backend` 預設；規劃者額度和 Gemini 共用額度都要 ≥10%，否則退回 `worker_hard` |
| `worker_hard` | Hydrogen → Flash，high | `--fast`、退回時、`frontend-js` |
| `worker` | Hydrogen → Flash，medium | |
| `worker_fast` | Hydrogen → Flash，low | 只用於瑣碎修改 |
| `auditor` | Hydrogen → Flash，high | 稽核（唯一在稽核測試抓到已知 bug 的模型） |
| `designer` | Neon，high | 小型 UI 試做 |
| `planner` | Carbon / Argon / Neon / Pro，high | 額度 <15% 時降級為 `worker_hard` |

Orchestrator 由 `agy models` 的顯示名稱 `Orchestrator (<規劃者>)` 辨識，額度同時檢查 Gemini 共用桶和規劃者自己的桶（例如 Argon 的獨立週額度）。
新版本（同家族）上線會自動被選上；新家族（例如 Carbon 以外的新代號）要加進偏好清單。

## 5. 額度

```bash
python3 $COWORK/tools/agy_quota.py        # 列出各額度桶的剩餘比例與重置時間（不耗額度）
```
`delegate.py` 每次執行前會檢查；額度用完時退出碼為 `3`，Claude 會停止委派並提醒你切換 agy 帳號。

## 6. 查看 Gemini 實際做了什麼

```bash
python3 $COWORK/tools/agy_trace.py --last 3   # 從 agy 本機軌跡統計工具呼叫：讀/寫/測試/輪詢次數
```
Gemini 的思考內容不會存在本機，但每個工具呼叫都有紀錄。
