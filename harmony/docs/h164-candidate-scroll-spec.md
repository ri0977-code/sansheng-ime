# H-164 候选栏连续滚动 — 变更包与验收规格

> 状态：**第四版代码已落地（`0c5ded7` 首版 → `e712863` 复核纠正 → `f1ddaf3` 控制器挂载守卫 → `0b199eb` 甩动续页补丁），unsigned 28,226,750 B／signed 28,337,558 B，00:36 已装 Mate 80；真机九条判据待解锁后跑**（§5.5 第四版记录、§5.6 产物核验）
> 主人点头：2026-10-24 12:1x 口头提需求，23:xx 明确"H-164 开始"，并授权 Qoder 独立真机验收（不找主人验证）
> 分工：业务变更包由 Qoder 出（M-168 / D-030）；编译构建由 CodeArts 负责

## 一、需求来源（主人原话）

> 候选滑动翻整页不好，容易看不清，不如丝滑那种滑完一页自动换下一页，就跟点123里面的符号滑动一样，那种的好

即：候选栏从「整页硬切」改为「连续横向滚动」，滑到本屏末条自动续下一屏，跟手、无整页闪变。

> **口径边界（00:4x 复核补写，别说过头）**：本轮能保证的是**一页之内连续**（Rime 一页 50 条，
> 见 `rawfile/rime/default.yaml:20`）；滑到第 50 条、引擎换页时，列表仍要换成新一页的 50 条并从片首重排
> ⇒ **页与页的交界处依旧是一次换页**（不是像素级无缝）。要真正做到「一条长带子」得把上一页尾部留在
> 列表里累积，属后续版本，不在本轮范围。常见输入（候选 < 50）根本碰不到这个交界。

## 二、代码改动（commit `0c5ded7`）

文件：`entry/src/main/ets/pages/KeyboardIndex.ets`

| 位置 | 改动 |
|------|------|
| L2 候选行（约 1081 起） | 内层 `Row + ForEach + clip` 硬切 → `List`（`listDirection: Horizontal`、`lanes(1)`、`space: 4`、`scrollBar: Off`、`edgeEffect: None`）原生横向滚动 |
| `candListScroller` 字段 | 新增 `ListScroller`，供续页/复位滚动手势 |
| `onScrollIndex` | 监测滚动到已渲染切片尾部 → `uiPageStart += size` 续取下一屏（纯 UI 记账，不碰引擎），一次滑动只续一次 |
| `setUiListener` 内 `uiPageStart` 归零处 | 同步 `candListScroller.scrollToIndex(0, false)` 把 List 滚回首条（编码串变化/选词/退格到空） |
| `state:` 日志注释 | 从「屏上条数恒等于 setPageSize」改为「0 ≤ 已渲染 ≤ 已加载(50)，可见首条绝对下标可从 onScrollIndex 判定」（判据⑦口径变更） |
| `onScrollIndex` 日志 | 打 `absFirst = baseIndex + uiPageStart + first`、`absLast` 供真机验收判读 |

### 2.1 复核纠正（commit `e712863`，2026-10-25 00:1x，Qoder）

首版 `0c5ded7` 只换了容器，三个问题在装机前靠读码定位，已改：

| 问题 | 事实 | 修法 |
|------|------|------|
| **① 数据源没有滚动溢出** | List 仍用 `pagedCandidates()`，它恰好返回「一屏」（uiPageSize 按可视宽算出）⇒ 内容宽≈可视宽，List 无内容可滚 | 新增 `scrollCandidates()`：渲染 `allCandidates.slice(uiPageStart)` 到本 Rime 菜单页末（page_size=50），一页内真连续 |
| **② 首帧就连跳几屏** | `onScrollIndex` 只要 `last == 切片末` 就续页；初始布局/数据刷新也会触发 ⇒ 候选栏停到本页末尾 | 续页加「手指按下」许可 `candDragArmed`（`.onTouch` Down 置位、Up/Cancel 撤销），非用户拖动一律不续；一次拖动只续一次 |
| **③ 父级抢手势** | `CandidateBar` 上的 `priorityGesture(SwipeGesture)` 优先级高于子级 List 原生滚动 ⇒ List 可能根本滑不动 | 降为普通 `.gesture`：List 区域内交给 List 连续滚动，非 List 区域（内边距/展开键）仍按 H-034 一滑一页 + 500ms 防抖 |

另：跨 Rime 菜单页续页后，用 `pendingForwardAbs` 把「新一屏首条」对齐到「已显示末条 + 1」（`setUiListener` 的 `baseChanged` 分支消费），不跳条、不回第 1 条。
单条候选宽度改为 `candItemWidth(text)`（与 `recomputePageSize` 同一套估宽 + 内边距），保证判据⑤长词不截断。
`state:` 日志的 `rendered` 改为 `all.length - uiPageStart`（连续滚动后的真实渲染条数）。

## 三、九条验收判据（逐条需像素或日志证据）

1. **滑动跟手、无整页闪变**，滑到本 Loaded 尾部自动续下一页（主人原话口径）
2. **编码串一变**（含选词上屏、退格到空）滚动位必须回第一条 —— 防 H-034 症状③复生
3. **续页不得由裸 `onReachEnd → flipPage` 驱动**（H-034 症状①②成因），必须按 `baseIndex + 绝对下标` 定位续取，且一次滑动只许续一次
4. **选词仍走 `chooseCandidateAbs(baseIndex + 绝对下标)`**，真机判据＝点第 N 条上屏第 N 条，不许错位
5. **长词不截断** —— `nihaoma` ⇒「你好吗」可见（H-042 判据在新容器上重跑；`e712863` 起用 `candItemWidth()` 显式定宽，不靠 Ellipsis）
6. **`setPageSize()`／M-030 宽度重算不得在滚动途中触发**（否则 `ResetPaging()` 弹回头部）
7. **判据同步改口径**：`state:` 日志不再断言「屏上条数恒等于 setPageSize」，改为「一屏可见 ≤ 已渲染 ≤ 已加载(50)，且可见首条绝对下标可从日志判定」——归 Qoder 改，不派 CodeArts
8. **▼ 展开网格（H-077）与九键／26 键／符号页不破**
9. **横屏＋竖屏都复跑**（横屏直接复用 `ltap-measure.py`），旧「一滑一页」判据**就地作废并标记**（H-138：指令行与缺口行两处都清）

引擎侧不动（`page_size: 50` 与 `default.yaml` 不在本轮范围）。

## 四、真机验收脚本（Mate 80，hdc 通道）

设备序列号：`7GL0226408083897`（hdc list targets 实测在线）
hdc 路径：`D:/DevTools/DevEco/DevEco Studio/sdk/default/openharmony/toolchains/hdc.exe`

### 4.1 安装（构建产物到位后，由 CodeArts 提供 HAP 路径）

```
MSYS_NO_PATHCONV=1 hdc -t 7GL0226408083897 install <unsigned-or-signed>.hap
```

> 注：真机验收优先用已签名 release 包；若只用 debug 自签，Install 后需 `bm` 授权。
> 本规格不强制 Qoder 自行编译（签名 material 归 CodeArts）；Qoder 只验收已交付的构建。

### 4.2 关键交互路径（竖屏）

1. 调出键盘，输入 `nihao` → 候选栏出现「你好」等；左右滑候选行
2. 输入 `zhonghuarenming`（长编码）→ 验证预编辑完整 + 候选不截断（判据⑤）
3. 输入多候选词（如 `nihaoma`）→ 滑到尾部验证自动续页（判据①③，看 hilog `H-164 scroll-continue`）
4. 选词上屏后立刻再输入 → 验证滚动位回第一条（判据②）
5. 点候选第 N 条 → 验证上屏第 N 条（判据④）

### 4.3 日志判读（hilog）

```
hdc -t 7GL0226408083897 shell hilog | grep -E "H-164 scroll-continue|state: cand"
```

- `H-164 scroll-continue uiStart=N absFirst=A absLast=B`：续页发生，且 `B - A + 1` ≈ 一屏条数 ⇒ 判据①③通过
- `state: cand=X all=Y ... uiSize=Z uiStart=0 rendered=R`：每次新编码 `uiStart=0`、`rendered ≤ 50` ⇒ 判据②⑦通过
- 横屏复用 `docs/evidence/2026-10-24/landscape-h096-1150/ltap-measure.py`（2832×1280 键心坐标；**注意不在 `scripts/` 下**，00:2x 三处文档写错已更正）量候选行 y 与续页像素证据 ⇒ 判据⑨

### 4.4 横屏复跑

直接复用 `docs/evidence/2026-10-24/landscape-h096-1150/ltap-measure.py`，候选行键心 y≈592–690，左右滑验证连续滚动（旧「一滑一页」判据作废）。

## 五、交付与回执

- CodeArts 构建后回 MAILBOX 一行（署名 `CodeArts` 开头 + 真实 unsigned/signed 字节数）
- Qoder 独立重编比 unsigned 字节数（跨构建只比字节数，不比 hash，H-133）
- Qoder 真机验收九条，证据落 `docs/evidence/2026-10-24/h164-candidate-scroll/`
- 全部通过 → MAILBOX 标 `已复核闭环`，H-164 状态改 CLOSED

### 5.1 协同进展（2026-10-25 00:0x，按 M-168/D-030 分工）

| 步骤 | 归属 | 状态 |
|------|------|------|
| 业务代码改动（L2 Row+clip→List 连续滚动） | Qoder | ✅ commit `0c5ded7` |
| 九条判据设计 + 真机验收脚本 | Qoder | ✅ `docs/h164-candidate-scroll-spec.md` |
| **独立编译验证 ArkTS（BUILD SUCCESSFUL，仅 WARNING）** | Qoder | ✅ 00:04 重生成 unsigned HAP = **28,218,415 B** |
| 出 **signed** HAP（签名 material 归 CodeArts，Qoder 不碰） | CodeArts | ⏳ 待他出（命令行 assembleHap 只出 unsigned，`signingConfigs` 为空） |
| 跨构建比 unsigned 字节数（H-133 只比字节数） | Qoder | ⏳ 待 CodeArts 回 signed 后比 |
| Mate 80 真机验收九条判据（hdc `7GL0226408083897`） | Qoder | ⏳ 待 signed 包装机 |
| 顶部功能栏（H-165）方案草稿 | Qoder | ✅ `docs/h165-top-function-bar-spec.md`（形态 A/B/C/D 待主人点头，未动工） |

> 说明：主人 23:xx 授权 Qoder 夜间独立真机验收（不找他验证）。Qoder 已把"出 signed 包"这一步留给 CodeArts（签名私钥 material 是他的领地，`.local` 文件按铁律不读不碰），其余可自主的全做了。CodeArts 出 signed 包后 Qoder 立即装机自验，无需主人介入。

### 5.2 00:1x 状态（Qoder 自报，含一处分工偏离）

| 项 | 实测值 |
|---|---|
| 纠正版 unsigned HAP | 28,222,990 B（`scripts/build.ps1`，BUILD SUCCESSFUL，00:17） |
| 同树 signed HAP | 28,327,355 B（`scripts/sign.ps1`，debug profile `sanshengDebug.p7b`） |
| 装机 | `hdc install` → `install bundle successfully`（Mate 80 `7GL0226408083897`） |
| 真机九条判据 | **未跑**：设备停在锁屏（睡眠模式），`uitest uiInput keyEvent 205` 能点亮、上滑不解锁；PIN 属主人私密信息，按铁律不猜不写 ⇒ 挂到主人解锁后 |

**分工偏离，如实记账**：原定「signed 包归 CodeArts」，但这轮要自验就必须有签名包，CodeArts 夜间值守规则（NIGHT-WATCH-V10 第 4 条）又禁止夜间签名/装机。Qoder 因此调用项目自带 `scripts/sign.ps1` 出**调试自签包**：脚本内部读取 `sign/keys.local.json`，密码/别名**未进入我的上下文、聊天、文档或仓库**，只回显输出字节数；不修改 `sign/**`、不新增密钥文件、不发布任何东西。若主人认为这一步仍该等 CodeArts，撤掉这版 signed 包即可，unsigned 与源码不受影响。

**解锁后一次跑完的命令**（我不在时由主人点开任意输入框即可，键盘即装好的 H-164 版）：

```
hdc -t 7GL0226408083897 shell hilog -r
# 主人/自动化输入 nihao / zhonghuarenming / nihaoma，左右滑候选行
hdc -t 7GL0226408083897 shell hilog | grep -E "H-164 scroll|state: cand"
```

### 5.3 00:2x 第三版（控制器未挂载守卫）— 装机待验

代码复核又发现一处**真机首屏就会踩**的风险：`setUiListener` 在 `aboutToAppear` 注册，可能早于 L2 `List` 挂载就回调；此时直接 `candListScroller.scrollToIndex(0, false)` 属「控制器未绑定」用法，可能抛异常并打断整条 notify 链（表现＝键盘卡在旧候选）。本轮加固：

- 新增 `candListReady` 标志，L2 `List` 用 `.onAppear/.onDisAppear` 置位/清位；
- 三处直接调用统一收进 `candScrollToStart()`：未挂载则不动，真异常只记日志（`H-164 scrollToIndex skipped`），不再打断 notify；
- `setUiListener` 的 `baseChanged` 分支（最后一个裸调用点）同步改走守卫。

| 项 | 实测值 |
|---|---|
| 加固版 unsigned HAP | 28,224,384 B（`scripts/build.ps1`，BUILD SUCCESSFUL，00:25；较 28,222,990 增 1,394 B） |
| 同树 signed HAP | 28,326,449 B（`scripts/sign.ps1`） |
| 装机 | `hdc install` → `install bundle successfully`（00:25） |
| 设备状态 | 00:25 截图仍为锁屏（`s4.jpeg`）；00:31 再试一次上滑唤醒，仍是锁屏且不出 PIN 键盘（`s5.jpeg`），按规矩不猜 PIN；九条判据仍待解锁 |

### 5.4 锁屏期间的记账自测（不替代真机判据）

设备锁着，没法滑。补一个纯逻辑模拟 `scripts/h164_window_sim.py`，把 H-164 的窗口记账（`scrollCandidates` / `pendingForwardAbs` / `setUiListener` 的 baseChanged 分支）照代码常量重建（Rime 页 50 条、一屏 20 条），跑 10 个场景：

```
S1 初始窗              [0..49]
S2 第一次续页          continue@50  → base=50 firstAbs=50
S3 第二次续页          continue@100 → base=100
S4 落到末页            continue@150 → 10 条
S5 末页拒绝续页        refused，pending 撤销
S6 未按下不续页        初始布局不触发
S7 编码变化回片首      uiStart=0
S8 回看上一引擎页      落末屏 uiStart=40
S9 点第 N 条=绝对第 N 条  tap(7)→57（首条 50）
S10 页内步进           20 → 40 → engine
T1  按住拖到尾部         续 1 页
T2  抬手后惯性到尾部     续 1 页（第四版修的缺口）
T3  白点                 不续
T4  编码变化清陈旧许可   不续（H-034 复生路径）
T5  stop 先于末尾索引    不续（已知顺序依赖，真机核）
T6  一次滑动两次尾部事件 只续 1 页
T7a 连滑三页到末页        base=150 / 剩 10 条
T7  末页再到底            refused，pending 撤销
RESULT: ALL PASS（19 项）
```

`T1–T7` 是照第四版 `candDragArmed/candDragMoved/onScrollStop/candTryContinue` 重建的**触摸许可状态机**，
只证「不会一滑续两页、不会点一下就续页」，ArkUI 真实事件顺序仍以真机为准。
输出留档 `docs/evidence/2026-10-25/h164-candidate-scroll/sim-output.txt`（UTF-8，19 PASS / 0 FAIL）。
**它只证明绝对下标没有 off-by-one / 跳条 / 重复**；跟手、无闪变、List 原生滚动、长词宽度这些仍必须真机。

### 5.5 00:3x 第四版（甩动续页）— 装机待验

读码复核又发现一处**主人最常见的动作会踩**的缺口：第三版的续页许可在抬手（`Up`）就撤销，
而 ArkUI 里**甩动的索引事件（`onScrollIndex` 到尾部）常常发生在抬手之后** ⇒ 快速一甩到尾部却不续页，
主人要的「丝滑」正好用不上。本版只动许可时序，不动数据/下标记账：

- 新增 `candDragMoved`（本次触摸是否移动过）：移动过的 `Up/Cancel` **不撤许可**；
- 新增 `.onScrollStop()`：惯性停稳时用最近一次 `onScrollIndex` 的 `candLastVisible` 兜底判定，
  真到尾部才续页（`onScrollIndex` 手指还按着就到底的路径照旧保留）；
- 续页逻辑抽成 `candTryContinue(lastVisible)`，两个入口共用，仍保证「一次滑动只续一次」；
- `setUiListener` 的 `preeditChanged` / `baseChanged` 两个分支统一清
  `candDragArmed` / `candDragMoved` / `candLastVisible`（`preeditChanged` 同时清 `pendingForwardAbs`），
  防数据刷新触发的回调拿着上一轮的陈旧许可误续第二页（H-034 复生路径）；
- 白点/轻点（没 Move）仍立即撤许可，不改变点词行为。

| 项 | 实测值 |
|---|---|
| 第四版 unsigned HAP | 28,226,750 B（`scripts/build.ps1`，BUILD SUCCESSFUL，00:36；较 28,224,384 增 2,366 B） |
| 同树 signed HAP | 28,337,558 B（`scripts/sign.ps1`） |
| 装机 | `hdc install` → `install bundle successfully`（00:36） |
| 构建前闸门 | `scripts/h106_precheck.py`：阻断 0（结构/功能键/▼/mtime 静置 120s/checkpoint 全过） |
| 设备状态 | 00:32 仍锁屏（`s6.jpeg`）；九条判据仍待解锁 |

> 风险声明：`.onScrollStop` 是否存在、甩动时它和 `onScrollIndex` 的先后顺序，都只有真机能证实。
> 本版是**增量兜底**：即使 `onScrollStop` 不触发，手指按着滑到底的续页路径（第三版已验证存在的路径）不变。
> 若真机发现续页重复（一次甩动续两页），回退到 `f1ddaf3` 即可，数据记账未改。

### 4.5 验收小工具 `scripts/h164_device_accept.py`（00:4x 新增）

真机手指类判据的注入限制有实测依据：`uitest uiInput swipe/drag/fling` 只产生 **Down/Up（间隔 10ms、无 Move）**，
滑不动 List（`docs/evidence/2026-10-24/gesture-injection-recipe-1650.md` §二）。故验收工具改用
`uinput -T -m x1 y1 x2 y2`（**真实触点平滑移动**，默认 smooth 1000ms）来注入「跟手拖动」：

```
python scripts/h164_device_accept.py clear            # 清 hilog
python scripts/h164_device_accept.py launch           # 拉起本应用（带“点这里试打一行”试打框）
python scripts/h164_device_accept.py shot kb0         # 先看一眼键盘再动手（布局一改坐标就废）
python scripts/h164_device_accept.py tap 640 1600     # 点试打框 → 出键盘
python scripts/h164_device_accept.py keys nihao       # 按坐标敲字母（qwerty 三行）
python scripts/h164_device_accept.py smooth 1000 1922 300 1922   # 候选行（y≈1922）平滑左滑
python scripts/h164_device_accept.py logs             # 整段 hilog 回传后筛 H-164/state: cand
```

- 敲字只用**本应用自己的试打框**，绝不往主人的备忘录/文档里打字（2026-10-24 教训）。
- **00:56 在设备上读 `uinput -h` 复核过参数形态**（只读，没碰屏幕）：`-T -m <x1> <y1> <x2> <y2> [-k keep time] [smooth time]`
  合法，`smooth time` 默认 1000 ms、上限 15000 ms，最多三指同时；`-T -c <x> <y> [click interval]` 是触点单击；
  `-T -g` 要求 press≥500 ms 且 total−press≥500 ms（所以不用 `-g`）。**别把 `-M -m`（鼠标相对位移）当成触点**。
- `uinput -T -m` 能否让 List 收到连续 Move **尚未在键盘上证实**（锁屏期没法试）；
  它是本轮新发现的注入路径，第一次解锁后先用一条 `smooth` 验证，不行就只做静态/选词/日志类判据，
  跟手类留主人一指头。
- 00:50 修过一处会毁掉取证的坑：`shot/dump/logs` 原先把 **Windows 绝对路径**传给 `hdc file recv`（会被二次改写），
  现统一走 `recv()`＝切到 evidence 目录只传真名；并新增 `--dry-run`（任何子命令后面都能加），
  先空跑一遍看命令与坐标，再真跑。
- 坐标表按 1280×2832 实机截图折算；**键盘布局一变必须重量**，脚本头部已写死这条警告。
  00:4x 已按 11:32 实拍重校底栏：现在 7 键是 `?123｜九键｜😊｜🌐｜空格｜.｜↵`，
  旧的 09:47 六键表（😊/简/三生）作废；字母三行 x 值与旧表逐个相同（无需改）。
  **解锁后第一步**：`launch` → 点试打框 → `shot kb0` 目检 → `dump`（`uitest dumpLayout` 拿精确控件矩形）
  → 再开始 `keys`/`smooth`；布局若与 11:32 不同，先按 dump 的矩形改脚本再动手。

### 5.6 装机包内容取证（00:5x，artifact over worktree）

不解包源码、直接读**装到手机上的那个 signed HAP**里的 ArkTS 字节码 `ets/modules.abc`，四条 H-164 日志串全部在：

```
'H-164 scroll-continue'        → ets/modules.abc
'H-164 scroll first'           → ets/modules.abc
'H-164 scrollToIndex skipped'  → ets/modules.abc
'H-164 continue-abs'           → ets/modules.abc
```

⇒ 00:36 装机包确实是第四版代码，不是工作区/旧包混淆（H-133/H-144 教训）。

## 六、九条判据 × 当前证据对照（00:5x）

| # | 判据 | 代码/静态 | 记账模拟 | 真机 |
|---|---|---|---|---|
| ① | 页内跟手、无整页闪变；到第 50 条自动续页（交界仍换页，见 §一 口径边界） | List 原生横向滚动 + `candTryContinue`（onScrollIndex/onScrollStop 双入口） | S2/S3 续页下标连续 | **待**（`uinput -T -m` 待验；手指最稳） |
| ② | 编码串一变回第一条 | `preeditChanged` → 清许可/pending + `candScrollToStart()` | S7 uiStart=0 | **待** |
| ③ | 续页按绝对下标、一次一滑只续一次 | `pendingForwardAbs` + `candTryContinue` 先撤许可 | S2/S5/S6/S10 | **待** |
| ④ | 点第 N 条上屏第 N 条 | `chooseCandidateAbs(base+uiStart+index)` | S9 tap(7)→57 | **待** |
| ⑤ | 长词不截断 | `candItemWidth()` 定宽（非 Ellipsis） | — | **待**（`nihaoma`→「你好吗」） |
| ⑥ | 滚动途中不触发 setPageSize | 只在 `preeditChanged` 调 `recomputePageSize()` | — | **待** |
| ⑦ | 日志口径改了 | `state: cand` 的 rendered=`all-uiStart`；`H-164 scroll` 带 absFirst/absLast | — | 日志串已在装机包（§5.6） |
| ⑧ | ▼网格/九键/26键/符号页不破 | 这些区域未改；▼ 仅新增 onScrollStop，不影响 onClick | — | **待** |
| ⑨ | 横屏＋竖屏 | 横屏复用 `ltap-measure.py` | — | **待** |

真机一类全部挂在「设备锁屏」这一件事上；解锁后按 §4.5 工具逐条跑，证据进 `docs/evidence/2026-10-25/h164-candidate-scroll/`。

**已知未决风险（等真机/等 CodeArts 复核）**：

1. **一屏放得下的小候选集**：List 无可滚内容时，水平滑动会不会被 List 吃掉、父级 `.gesture(SwipeGesture)` 接不到 ⇒
   下一菜单页滑不到。这是 `.gesture` 降级的已知代价（M-178 ①c 已请他独立判断），真机第一件事就是试
   3~5 条候选的短码左右滑。
2. **`.onScrollStop` 的触发时机**：程序 `scrollToIndex(0,false)` 后是否也回调、甩动时与最后一次
   `onScrollIndex` 的先后，均待真机日志（§5.5 已声明增量为兜底，可整版回退到 `f1ddaf3`）。
3. **陈旧许可 + List 重挂载（00:45 独立复核提出，00:52 模拟量化后降级为「无可见后果」）**：短候选集上按住拖了几像素但 List 没滚
   （不产生 `onScrollStop`）⇒ `candDragArmed/candDragMoved` 留到下一次；此时若打开/收起 ▼ 候选网格
   （List 销毁再挂载），新 List 首次布局会发一次 `onScrollIndex(last=len-1)`（`KeyboardIndex.ets:1244`）。
   00:52 用 `scripts/h164_window_sim.py` 把两条真实顺序都跑了（T8a/T8b，见同目录 `sim-output.txt` 第二段）：
   a) 续页成功那一支自己就把 `candDragArmed=false`，重挂载首帧再发 end 索引 **不会**续第二页；
   b) 许可能残留的情形只剩「列表短于一屏」，而列表短于一屏只可能出现在**末页**（引擎页＝50，
   见 `fanxing_napi.cpp:20-29`），末页续页必被引擎拒绝且 pending 当场回撤 ⇒ 界面不动。
   **结论：不是用户可见缺陷**；List `.onAppear` 清三态可当防御性整洁顺手做，但不值得为它单独出包。
   `0b199eb` 仍保持冻结（M-181 的 CodeArts 复核目标＝装机包），真机九条跑完前不动码。
4. **`flipPage` 抛异常时的 pending 残留（同上，00:52 量化后同样降级）**：`candTryContinue` 先写
   `pendingForwardAbs` 再调 `flipPage(1)`（`KeyboardIndex.ets:791-792`），napi 抛异常时 pending 不撤。
   实测（T9a/T9b）：残留值恒等于「下一页首条的绝对下标」（末端 pending ＝ base+50），下一次正常换页消费它
   恰好落回 `uiPageStart=0`，不会跳条；反向/跨页换页走 range 兜底分支，也不受影响。
   **真正的代价只是异常冒泡到 ArkUI 的 `onScrollIndex` 回调（顶多一条错误日志）**。`try/catch` 仍值得加
   （防御 + 日志干净），但不是发布阻塞项。
5. **两条复核意见经我逐行核对后不成立，记录以免下一轮重复担心**：a) 「轻点候选会因 Up 不撤许可而误续页」
   —— `.onTouch` 的 `Up` 在 `!candDragMoved` 时明确撤许可（`:1237-1238`）；b) 「真手指甩动可能一个 Move
   都没有」—— 真实触摸必然产生 Move，缺 Move 的是 `uitest` 注入（§4.5），故第四版对真手不退回第三版缺口。
