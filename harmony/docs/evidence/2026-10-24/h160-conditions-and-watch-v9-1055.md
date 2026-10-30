# H-160 放行四项的当场复量（10:5x · Qoder · 只读，未构建未签名未装机）

来源：`date` 10:55 本机时钟；`grep` / `git status` / `git diff --stat` 只读实测；工作区 `F:\qoderwork\sansheng-ime-harmony`。

## 1. 判据与当前实测

| H-160 放行条件 | 10:5x 实测 | 满足？ |
|---|---|---|
| ① `KeyboardIndex.ets` 只剩的那处空格键面改成 `Text('三生')` | `grep -n "Text('空格')"` ⇒ **1 处命中，现落在 `:2271`**（09:5x 记 `:2243`、HEAD 里 `:2220`，行号随他编辑一直在漂）；`grep -c "Text('三生')"` ⇒ 1 | **未满足** |
| ② 去掉／加闸 Move 热路径的 `console.info` | `:1514 LT down`、`:1520 LT move`、`:1536 LT up`、`:1551/:1557 LetterKey swipe`、`:1679/:1683 bs_row swipe`、`:2322/:2527 DotKey swipe` 全在（该文件 `console.info` 共 21 处） | **未满足** |
| ③ 提交 | `git status` ⇒ ` M entry/src/main/ets/pages/KeyboardIndex.ets`；`git diff --stat` ⇒ **+72/−15**（10:1x 那次是 +34/−8）；HEAD 仍 `894bb76`（我这侧的文档提交） | **未满足** |
| ④ 交付行给出新 unsigned／signed 字节数并标「本机构建」 | `docs/WIP.md` 与 `docs/MAILBOX.md` 尾部没有新的 CodeArts 交付行 | **未满足** |

`KeyboardIndex.ets` mtime ＝ **2026-10-24 10:35:29**（112,991 B）；`KeyboardController.ets` mtime ＝ 09:14:37（21,665 B）。到我复量的 10:55 已静置 >120 秒，但**静置不等于放行**：`scripts/h106_precheck.py` 现在仍判 exit 2（本轮没有待验收交付），所以我没构建、没签名、没装机。

## 2. 值守 v9 第一次实跑回读（顺带记一条状态文件的小坑）

`qoder_cron list` 10:5x 实测：v9 `3fe84900-fe4b-49a7-9a74-22e09981635a` → `enabled:true`、`pauseReason:null`、`lastRunStatus:succeeded`、`lastDurationMs:58415`、`consecutiveFailures:0`、`model:qfmodel`（继承本会话）、每 300000 ms。

`.night-watch.json`（被 .gitignore 忽略）mtime 10:52，`lastRunAt`＝「2026-10-24 10:52（主会话活跃只读轮）」⇒ 并发保护生效：它读到 PROGRESS 最后一行不足 20 分钟，只更新了状态文件，**没写共享文档、没构建、没碰设备**。

**一个小坑（不得当成实测）**：同一份状态文件里的 `head` 字段仍是 `606e2c4`（＝10-24 01:10 那次「重建 v8」的提交），而当前 HEAD 是 `894bb76` ⇒ **只读轮不刷新 `head`**。以后要引用「值守看到的 HEAD」必须现场 `git rev-parse --short HEAD`，不能读这个字段。

## 3. 结论

H-160 四项**一项都没满足**，闸门维持 exit 2 是正确状态；值守表面（`ROADMAP.md` §0 ⑤、`OWNER-ACTIONS.md` ⑦、`HANDOFF.md` 值守格）的「夜间值守在跑」已就地更正成实测事实，新台账 H-162、给主人的信箱行 M-162。
