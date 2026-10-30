# 给所有 AI Agent 的工程规则

本文件是 Qoder、CodeArts 以及任何后续接手的 AI 的**共同契约**。开工前必须读，违反即视为交接不合格。

## 0. 唯一仓库

- 正式工程：`F:\qoderwork\sansheng-ime-harmony`
- 旧目录 `F:\codeartswork` 与 `F:\codeartswork\_ref_harmonyos-rime` **只读归档**，不再作为写入点。
- 不删除、不搬空旧目录；只允许从旧目录复制需要的资料。

## 1. 开工前必读（按顺序）

1. `docs/DECISIONS.md` — **主人唯一会读的决策台账**：路线级决定（换开源参考、换布局、换引擎、砍功能）必须先写一条 `D-0xx`（决定/为什么/影响/主人可推翻哪点），**写完才允许动代码**；台账类文档不算通知主人
2. `docs/PROGRESS.md` — 当前阶段、下一步、阻塞
2. `docs/MAILBOX.md` — 有没有发给自己的 OPEN 消息；开工/收工都要写
3. `docs/HANDOFF.md` — 当前谁在写、文件归属、交接状态
3. `docs/ISSUES.md` — 已知问题，避免重复踩坑
4. `docs/INTERFACE.md` — UI/引擎接口契约
5. `docs/BUILD.md` — 构建、签名、装机步骤
6. `docs/OPEN-SOURCE.md` — 开源复用规则与候选清单

如果 `HANDOFF.md` 写着「当前不交接」，**不要动代码**，只读文档或做只读调研。

## 2. 角色

| 角色 | 工具 | 负责 |
|---|---|---|
| **主控／集成负责人** | Qoder | 需求拆解、架构与接口契约、**业务代码变更包输出**、NAPI 桥、Rime 数据/滤镜移植、构建/签名/装机、git 提交、真机验收、对 CodeArts 派单与催办 |
| **鸿蒙 ArkTS 合规工程师／仓库管理员／构建负责人** | CodeArts（「鸿蒙开发」agent） | ArkTS 类型/Sendable/Stage 模型规范适配、权限声明、资源路径、静态告警修复、跑 `build.ps1`、git 提交、信箱回执 |
| 备用 | opencode | 本轮不参与；未获明确指派不得写入 |

> **20:3x 主人确认的新分工**（依据 `docs/DECISIONS.md` D-030）：
> - Qoder **放开编码权**（不再只审查），业务逻辑／页面交互架构／接口时序的变更包由 Qoder 输出。
> - CodeArts **不再私自改业务逻辑**：`onTouch` 手势、按键行为、`clearAllAndRecord()`、`insertText()` 入栈时机、键面文案这类改动一律等 Qoder 出新版变更包；只做鸿蒙规范侧适配，遇这类问题发 `BLOCKED` 退回。
> - **失联接管**：CodeArts 连续两次催办无回应（即 BLOCKED(失联)），或明确自述卡死超过 30 分钟，Qoder **可直接写入其独占区**并在信箱声明「临时授权」，事后不必补等主人拍板。
> - **git 双方均可提交**，硬规则＝提交前信箱 DONE + Qoder 回执；提交信息带工单号。
> - 唯一可信源＝本仓 git，**不是任何一方的私有仓库**。

## 3. 文件归属

### Qoder 独占

- `entry/src/main/cpp/**`
- `entry/src/main/ets/engine/**`
- `fanxing_rime_har/**`
- `entry/src/main/resources/rawfile/rime/**`（后续创建）
- `scripts/**`
- 根目录 `build-profile.json5`、`oh-package.json5`、`hvigor/**`
- `entry/build-profile.json5`、`entry/oh-package.json5`
- `entry/src/main/module.json5`
- `AppScope/**`
- `sign/**`（本地，gitignore）
- `docs/PROGRESS.md`、`docs/VERSION_LOG.md`、`docs/BUILD.md`、`docs/INTERFACE.md`、`docs/ARCHITECTURE.md`、`docs/OPEN-SOURCE.md`、`README.md`、`AGENTS.md`

### CodeArts 独占

- `entry/src/main/ets/inputmethod/**`
- `entry/src/main/ets/pages/**`

> **20:3x 起这两个目录改为「共享热点区」**（H-165/H-166/H-167 三处缺陷全在这两个目录、由 Qoder 越界修复并真机验证，主人两次授权）：
> - **单一写入者（硬规则）**：同一批文件同一时刻只一个 agent 写；谁写谁先在信箱声明占用，写完释放；严禁两人同时编辑 `KeyboardIndex.ets` 这类热点文件。
> - **业务逻辑/交互架构/接口时序归 Qoder 出变更包**；CodeArts 只做规范适配，不得私改。
> - Qoder 写入前在信箱声明「本轮临时授权 Qoder 写入 `<文件>`，CodeArts 本轮只读不写」。
- `entry/src/main/resources/base/profile/input_method_config.json`
- `entry/src/main/resources/base/profile/main_pages.json`（2026-10-20 CR-20261020-01 批准）
- `entry/src/main/resources/base/media/keyboard/**`（新建）
- `docs/HANDOFF.md`、`docs/ISSUES.md`（只追加/更新，不重写历史）

### 只读

- `entry/src/main/ets/engine/**` 只能 import，不能改
- `entry/src/main/cpp/**` 只能读
- `docs/reference/**` 只读

需要改别人拥有的文件时：在 `docs/HANDOFF.md` 写「变更请求」，由拥有者改；不要直接动手。

## 4. 工作流

1. 认领任务：先读 `MAILBOX.md` 中发给自己的 OPEN 消息；更新 `PROGRESS.md`（Qoder）或 `HANDOFF.md`（CodeArts）里的当前状态，并在信箱回一行 `ACK`。
2. 只改自己拥有的文件。
3. 改完必须跑构建：

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1
   ```

4. 构建绿了才算完成；红了先修，不得把红工程交接出去。
5. 更新记录：
   - CodeArts：更新 `docs/HANDOFF.md` 和 `docs/ISSUES.md`
   - Qoder：更新 `docs/PROGRESS.md`、`docs/VERSION_LOG.md`、`docs/ISSUES.md`
6. 交接：写清「做了什么、证据、没做什么、下一步」；不写等于没做。
7. 收工：在 `MAILBOX.md` 给对方留一行（DONE/BLOCKED + 一句结果），再结束会话。
8. **值守与停机（2026-10-21 主人更正，必须遵守）**：
   - **任何 agent 不得自行关机**。夜里 01:47 因「30 分钟没消息」自动关机，把正在等指示的 CodeArts 一起关掉，主人明确批评「浪费好多个小时」。
   - 关机只有两种情况：① 主人明确说「关机」；② 主人已授权，且 Qoder 与 CodeArts **都**明确 `BLOCKED`（额度、权限、硬件故障等真干不下去），不是「暂时没消息」。
   - 「没新消息」不等于「没活」：Qoder 收到 `-re` 后必须复核/构建/装机，或给 CodeArts 下一条明确任务；确实要等主人时，在 `MAILBOX.md` 写明「等主人什么」，并保持值守。
   - CodeArts 交付后若没收到下一步，**不许自己停机**：在 `MAILBOX.md` 留 `BLOCKED: 等 Qoder 指示`，继续按 5 分钟轮询；Qoder 有责任在收工前把下一步指派写清楚。
9. **Goal 使用协议（2026-10-21 主人要求）**：
   - 每个会话/定时任务开工先看自己的 goal；**没有就为当前里程碑建一个**。目标写**可验收的结果**（含真机证据），不要写「继续做 X」这种没有终点的动作。
   - 同一时间每个 agent 只保持一个 goal；换阶段先把旧 goal 收口（complete 或按规则 blocked），再建新的。
   - 目标达成前不主动收工；达成标准与 DoD 一致（构建通过 + 真机证据 + 文档更新），**构建绿不算过**。
   - goal 是会话本地的，**不能代替信箱**：跨 agent 的请求、交付、阻塞仍写 `MAILBOX.md`；目标本身也要在 `PROGRESS.md`/`HANDOFF.md` 有对应文字。
   - 同一阻塞连续三轮仍无解，才把 goal 标 `blocked`，同时写信箱；不得因为「暂时没消息」标 blocked 或关机。
   - 主人明确给轮次预算时才设 `max_turns`，不自行臆造。

## 5. 硬规则

1. **单一写入者**：同一时间只允许一个 agent 改同一批文件；不要并行编辑。
2. **不提交密钥**：`sign/`、`*.p12`、`*.p7b`、`*.cer`、`agconnect-services.json`、任何口令，绝不进 git，绝不写进公开文档。
3. **不删旧成果**：旧目录、旧 HAP、旧文档保留；要清理先备份并记录。
4. **不说“应该能跑”**：所有结论要有构建产物、日志、截图或真机现象作证据；没有就写「未验证」。
5. **不改包名/签名**：`com.sansheng.ime` 与签名配置由 Qoder 管；CodeArts 需要改时走变更请求。
6. **不碰上游引擎**：`fanxing_rime_har/**` 与 `librime.a` 等静态库不改；要重编另开分支/目录。
7. **不把工作放进聊天**：聊天不是记录；所有成果、问题、决定必须落到本仓库文档。
8. **开源优先**：键盘、面板、皮肤、布局等优先复用许可证兼容的开源实现（Apache-2.0/MIT/BSD），官方 Sample 优先；GPL/AGPL/无许可证只参考思路，不复制代码。复用前登记到 `docs/OPEN-SOURCE.md`，保留版权头。
   - **「照抄」≠「整块搬」**：搬每一处前先写下「它的架构前提是什么、我们的是什么」。H-048 教训（2026-10-21）：kanonIME 的横向 `List` 是**它自己的翻页载体**（滑 List 即翻页），我们是**引擎分页 + 手势翻页**，原样搬过来就变成「手指能把候选条拖走、首列裁半、偏移跨输入残留」——主人已否过两次的 H-034 老毛病复发。凡与翻页、手势、状态持有有关的代码，搬之前先对差异点。
9. **不靠主人传话**：Qoder 与 CodeArts 之间的请求、回复、阻塞一律写 `docs/MAILBOX.md`；只有需要改包名/签名/发布或两轮无结论时，才升级给主人。
10. **不自动关机**：见 4.8。违反一次即按流程事故记录到 `ISSUES.md`，不因「省电」「夜间规则」再犯。
11. **调研必须落到「这份配置到底是不是它在跑」**（2026-10-26 主人两次退回后立规）：
    - 读配置文件不等于读实机行为。**同一份 yaml / json 里可能有十几套并行定义**（Trime 一份 `trime.yaml` 有 18 个 `preset_keyboards`），读到哪一套 ≠ 用户在用哪一套。
    - 取证优先级（从高到低）：**① 引擎实际加载的部署产物**（如 rime 的 `build/trime.yaml`）→ ② 设备上的源配置（`adb pull` 实际文件，记 md5）→ ③ 仓库里存的副本 → ④ 文件头注释。**注释永远不能当证据**（`trime.yaml` 第 10 行说改 `qwerty`，实际改的是 `default`，害得我误判两轮）。
    - 给数量结论必须**用脚本逐段统计并写出统计口径**（哪个文件、哪段行号、正则是什么），不许目测、不许「应该有」。
    - 用户的直观观察（「a/s 没有那些功能」）**优先于我的配置解读**；两者冲突时，说明我读错了对象，回去重查，不要辩。
12. **做事做到底，不许敷衍了事**（2026-10-26 主人原话：「之前那是狗屁啊」「做事就要认真负责做到底」）：
    - 主人点名要调研的东西，必须做到**逐项、可核对、带可行性判断**的粒度，而不是列个功能清单就交差。反例：初版 Nova 6 调研只写「Trime 有手势功能，值得移植」——没查它在哪个键盘、没查鸿蒙有没有对应 API，等于没做。
    - 每一条「可移植」必须给出**鸿蒙侧对应的 API 或明确的「做不到」结论**；不做「应该能行」的推测。
    - 调研完要自问三句：① 这个结论的行为证据在哪？② 有没有另一套配置会推翻它？③ 主人拿到能不能直接照着做？三问答不上就还没做完。

13. **收信先回「收到」，再回内容；两边都照此办**（2026-10-26 主人原话：「收信后，应该先回信收到。再回信具体内容，他那边也应该一样，要不回信也要等半天」）：
    - 读完对方一条消息后，**立刻**在 `docs/MAILBOX.md` 追一条 `ACK`（一行即可：`| M-xxx-re | 时间 | 我 → 对方 | (署名) 收到 M-xxx，正在处理：<一句话> |`），不要等事情做完才回。
    - 具体结论、答复、派活另起一条完整消息。**先 ACK 后正文**，两条分开写，引用时带上被 ACK 的 ID。
    - 这条对 **Qoder 与 CodeArts 双向生效**：CodeArts 收到我的消息也要先 ACK 再给正文。
    - 为什么：主人在中间等着，对方不知道你收到没收到，只能干等；ACK 让他知道「有人在办」，正文让内容可追。

## 6. 版本与提交

- 工程版本用 `v0.x.y-阶段`，如 `v0.1.0-baseline`、`v0.2.0-shell`。
- 每次真机可安装的构建，必须在 `docs/VERSION_LOG.md` 增加一行，记录 commit、HAP 路径、真机结果。
- git 提交由 Qoder 统一执行；CodeArts 不提交。基线已建立：`6d504a6` / `v0.1.0-baseline`（2026-10-20）。
- 每个里程碑打 tag：`v0.1.0-baseline`、`v0.2.0-shell`、`v0.3.0-engine`、`v0.4.0-data`。

## 7. agent 标识规则（2026-10-24 20:4x 主人要求，共享编辑区强制）

> 主人原话：「共享热点区那个我提个建议，自己写的东西加个自己的 agent 标识，好查。推广一下，凡是共享编辑区，都要加自己的 agent 标识。」

### 7.1 标识字面量

| 场景 | 写法 | 例 |
|---|---|---|
| 代码注释（ArkTS/TS/C++） | `// <工单号>(<agent>):` 或 `/* …(<agent>)… */` | `// H-167(Qoder): 缓冲区与真实正文同步` |
| 配置／YAML／JSON 注释 | `# <工单号>(<agent>):` | `# D-030(Qoder): 反斜杠映射口径` |
| 台账表格行（ISSUES/WIP/MAILBOX/PROGRESS/HANDOFF） | 行已有署名列，另在正文首标 `(<agent>)` | `…（20:2x；越界改 entry/src）(Qoder)` |
| commit message | `(<agent>)` 尾缀 | `H-165 … (Qoder)` |
| 证据文档（docs/evidence/**） | 文首「整理：<agent>」 | `> 整理：Qoder` |

### 7.2 适用范围（凡是共享编辑区就要加）

- `entry/src/main/ets/pages/**`、`entry/src/main/ets/inputmethod/**`（共享热点区，D-030）
- `entry/src/main/cpp/**`、`entry/src/main/ets/engine/**`、`fanxing_rime_har/**`、`rawfile/rime/**`
- `scripts/**`、根与 entry 的 `*.json5`、`hvigor/**`
- `docs/**` 全部（ISSUES/WIP/MAILBOX/PROGRESS/HANDOFF/DECISIONS/ROADMAP/OWNER-ACTIONS/evidence）

独占区不强制（文件归属已能定位），鼓励加。

### 7.3 为什么（今日两次实证）

1. **git 作者不可用**：本仓 git 身份共用，我提交的也显示 `CodeArts` ⇒ 无法用 `git log` 判归属，只能靠标识。
2. **H-160 归属错账**：他 M-167 自称「H-160 四项全闭」，实际两项是我 16:5x–17:0x 补的；有标识就不必靠记忆和时间线倒推。

### 7.4 自检

回查某处改动是谁干的：`git blame` 不可信 ⇒ 用 `grep -rn <工单号> entry/src docs` 看标识后缀；
 收工前跑一次 `grep -rn "(Qoder)\|(CodeArts)" entry/src/main/ets | wc -l`，本轮新增改动应能被数到。
## 7. 给 CodeArts 的额外要求

- 必须选择 **「鸿蒙开发」** 专属 agent，不用通用 agent。
- 必须打开 `F:\qoderwork\sansheng-ime-harmony` 作为工作区，不要打开旧目录。
- 每次会话开始先读 `docs/MAILBOX.md`，处理发给自己的 OPEN 消息；结束前回一行。
- 任务书见 `docs/TASK-CODEARTS-M1.md`；只做 M1 键盘壳，不接真引擎。
- **M1 优先移植 hMixedKeyboard（Apache-2.0）**，不要从零画键盘；复用边界见 `docs/OPEN-SOURCE.md`。
- 交付前必须跑 `scripts/build.ps1`，并在 `docs/HANDOFF.md` 写构建结果和产物路径。
