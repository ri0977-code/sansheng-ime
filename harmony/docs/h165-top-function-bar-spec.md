# H-165 顶部功能栏（安卓 `>` 工具栏参照）— 设计方案草稿（**已落地，见 §十一**）

> 状态：**本文前半（§一~§十）是 10-25 的设计推演，保留作决策来源；实现早已不是草稿** ——
> 图标行、七枚、手动折叠、空格滑移光标都已进包并在真机上见过（H-176/H-177/H-179/H-183/H-187/H-188~H-192）。
> **要改这一块，只看 §十一「落地现状」的常量与规则**，别照前面那些「待定」的推演动手。
> 来源：主人 2026-10-24 23:xx「现在键盘最上方是空白栏，右上角有个向下的箭头，浪费，去参考三生安卓版，加上功能左右展开折叠的三角，把功能做进去，然后你再对比安卓，继续完善」
> 分工：业务变更包由 Qoder 出；构建由 CodeArts

## 一、安卓参照（已核实，权威来源 `F:/dshdesktopwork/sansheng-ime-android/README.md` 第 360 行）

安卓三生（Trime 系）的**工具栏（toolbar）**：

- 最左边一个 **`>` 折叠三角**，点开向右/向下展开一排**功能磁贴**
- 磁贴大字＝当前状态，下面小字＝再点会切到的目标
- 磁贴内容（README 原文）：`繁體→简体` / `中英对照→Off` / `commentOn` / `半角→全角` / `常用→增廣` / `Reload Config`

> **00:2x 实物修正（以此为准）**：`>` 展开的是**图标工具栏**（‹/撤销/重做/光标/剪贴板/`…`/▼），
> README 说的磁贴在 `…` 打开的**开关菜单**里，不是工具栏上的一排。截图见第九节。

> 注意：安卓 README 的「工具栏」与「键盘顶部候选栏」是**两个独立区域**。三生安卓的候选栏在上方，工具栏（带 `>`）是另一个可展开的功能条。主人说的「顶部空白栏 + 右上角下箭头」指鸿蒙候选栏右侧那个 `chevron_down`（目前被复用为候选网格展开/收起，H-109 双功能）。

## 二、鸿蒙现状（已定位）

文件：`entry/src/main/ets/pages/KeyboardIndex.ets`

- 顶部唯一栏 = `CandidateBar()`（L1 预编辑行 + L2 候选行）
- L1 预编辑行：空闲（无编码、无候选）时只显示一行 12fp 灰字，看着空 ⇒ 主人说的「空白栏」
- L2 右侧 `chevron_down/up` 三角：H-109 双功能（有候选=展开/收起候选网格；无候选=折叠键盘），长按恒折叠
- **状态机已存在**：`asciiMode`（中英，声明 `:270`／首帧回填 `:458`／切换 `:2614-2615`）、`tradMode`（简繁，声明 `:271`／长按语言键 `:2628-2629`／底栏键 `:2738-2739`）、comment 行常显（反查，`commentLine()` `:392`，用在 `:1168`）；Reload 对应 librime 重载配置（需确认鸿蒙端 API）
  - **行号会随编辑漂移**（H-137 教训）：上列行号是 2026-10-25 00:4x 对 `0b199eb` 树的实测值，引用时以**符号名 grep**为准，别照抄数字。

## 三、设计形态选择（需主人点头；A/B/C/D 四选一，D 最贴安卓）

### 方案 A：右上角三角升级为「功能入口」
把现有 `chevron_down` 区域（或旁边）改成安卓式 `>` 折叠三角，点开在候选栏下方/上方展开一排功能磁贴（简繁/中英/半角全角/comment/Reload）。
- 优点：不动现有候选栏布局，复用右上角空间
- 风险：与现有「候选网格展开」三角功能冲突，需重新定义三角语义（或新增一个 `>` 紧邻现有三角）

### 方案 B：顶部左侧新增 `>` 折叠三角（安卓原版形态）
在 `CandidateBar()` 最左侧新增一个 `>` 三角，点开向右/向下展开功能磁贴行。现有右上角 `chevron_down` 保持候选网格展开语义不变。
- 优点：与安卓形态一致、不破坏现有候选网格交互
- 风险：顶部栏多一个元素，需处理横屏紧凑布局（L1 隐藏时）

### 方案 C：合并——左侧 `>` 展开功能磁贴 + 右上 `chevron` 仍管候选网格
功能分区最清晰，但改动最大（两套入口并存，用户要学两次）。

## 四、待确认项（动工前必须主人拍板）

1. **形态选 A / B / C / D**（上节；D＝安卓原样图标行，00:2x 新增，见第九节）
2. **磁贴清单**：简繁、中英、半角↔全角、commentOn、Reload —— 是否全做？鸿蒙端 `Reload Config`（librime 重载）是否有 API？需 CodeArts 确认引擎侧能力
3. **展开方向**：A/B/C 是向右/向下展开磁贴；D 是向下展开一行图标（安卓实物如此）
4. **横屏适配**：横屏 L1 隐藏时，功能三角放哪

## 五、不做的事（边界）

- 不动引擎（`page_size`、schema、default.yaml）
- 不擅自定产品形态（等主人选 A/B/C/D）
- 不与 H-164（候选栏连续滚动）同树互踩：若 H-164 先构建，本项待其闭环后再开，或并入同一棵构建树一次交付

## 六、参考资料

- 安卓 README：`F:/dshdesktopwork/sansheng-ime-android/README.md`（第 360 行工具栏描述）
- 安卓反编译布局：`F:/dshdesktopwork/sansheng-ime-android/_emulator_runs/apktool/main/res/`
- 鸿蒙候选栏：`entry/src/main/ets/pages/KeyboardIndex.ets` 的 `CandidateBar()` / `ExpandedPanel()`
- 鸿蒙状态机：`asciiMode` / `tradMode` / `commentLine()` / `setOption('ascii_mode'|'zh_trad')`

## 七、能力可行性（2026-10-25 00:2x 代码实测，非推测；00:4x 复核行号）

> 路径：schema＝`entry/src/main/resources/rawfile/rime/*.schema.yaml`；napi 导出＝`entry/src/main/cpp/fanxing_napi.cpp`。

| 安卓磁贴 | 对应开关 | 鸿蒙现状 | 初版能否做 |
|---|---|---|---|
| `繁體→简体` | `zh_trad` | 状态机 `tradMode` 已在（`KeyboardIndex.ets` 声明 `:271`、切换 `:2628-2629`/`:2738-2739`，`setOption('zh_trad')`）；`sansheng_t9.schema.yaml:41`、`wubi_pinyin.schema.yaml:25` 均声明 | ✅ 可做 |
| `中英对照→Off` | `ascii_mode` | 状态机 `asciiMode` 已在（声明 `:270`／回填 `:458`／切换 `:2614-2615`，`setOption('ascii_mode')`） | ✅ 可做 |
| `commentOn` | `phraseComment`（**00:4x 更正**） | `wubi_pinyin.schema.yaml:28-30` 声明 `phraseComment` 开关（states `Off/commentOn`）并挂 `lua_filter@phraseComment_Filter`（`:64`）；`commentLine()` 恒显在 L1 16vp。**原写「无引擎开关」是错的**——引擎开关存在，它管的是**候选注释**，不是 L1 预编辑注释，两者 UI 归属动工前要分清 | ✅ 可做（用 `setOption('phraseComment')` + `getOption` 回填） |
| `半角→全角` | `full_shape` | schema 声明：`wubi_pinyin.schema.yaml:19`、`sansheng_t9.schema.yaml:37`；`setOption('full_shape')` 走通用接口（`fanxing_napi.cpp:1015`） | ✅ 可做（首帧用 `getOption` 回填，别把文案写反） |
| `常用→增廣` | `extended_charset` | `wubi_pinyin.schema.yaml:21-22` 明写 `states: [ 常用, 增廣 ]` | ✅ 可做（同上回填） |
| `。，↔．，`（**09:2x 补**，原稿漏这枚） | `ascii_punct` | 两个方案都声明：`wubi_pinyin.schema.yaml:23`、`sansheng_t9.schema.yaml:39`；`setOption('ascii_punct')` 走通用接口（与 `full_shape` 同一条 `fanxing_napi.cpp:1015`）。代码里无状态机，`getOption` 回填即可 | ✅ 可做（第六枚） |
| `Reload Config` | — | napi 导出只有 `switchSchema/processKey/selectCandidate/selectCandidateAbs/deleteBackward/flipPage/clear/getContext/finalizeEngine/setOption/getOption/setPageSize`（`fanxing_napi.cpp:1070-1083`），**无 reload** | ❌ 初版不做：要么引擎加 `reloadConfig`，要么这枚先不放——**不做假重载** |

结论：安卓六枚里 **六枚现有 API 就能真做**（`zh_trad`/`ascii_mode`/`full_shape`/`extended_charset`/`phraseComment`/`ascii_punct`），只有 Reload 需要引擎侧动刀。
（09:2x 更正：原写「五枚」是漏了 `ascii_punct`——CodeArts 交叉核对指出，我按两个 schema 复验确认。）

**按方案分可用性（00:4x 实测 yaml，动工前必须看这一格）**：`schema_list` 只有两个方案
——`wubi_pinyin`（主方案）与 `sansheng_t9`（九键），`pinyin_simp` 只是依赖不在列表里。

| 开关 | wubi_pinyin | sansheng_t9 | 说明 |
|---|---|---|---|
| `ascii_mode` | ✅ | ✅ | 中英 |
| `full_shape` | ✅ | ✅ | 半角/全角 |
| `zh_trad` | ✅ | ✅ | 简繁 |
| `ascii_punct` | ✅ | ✅ | 中英标点（09:2x 补） |
| `extended_charset` | ✅ | ❌ | 九键方案没声明 ⇒ 九键下点「增廣」无效果，磁贴应按当前方案置灰/隐藏 |
| `phraseComment` | ✅ | ❌ | 同上，九键下「反查」注释开关不可用 |

⇒ 方案 D 的磁贴不能一律常亮：**先 `getOption` 回填，未声明的项置灰**（否则主人点了没反应＝假按钮）。

## 八、尺寸预算（代码常量 + 现有日志口径，非真机重测）

- 竖屏候选栏宽 `candBarWidth ≈ 356vp`：由 `recomputePageSize()` 的
  `availW = candBarWidth - 36(展开键) - 2*CAND_PAD_H(8)` 与注释「竖屏 304vp 恒 false」（`KeyboardIndex.ets:670-676`）反推。
- 候选栏高：L1 16vp + L2 28vp；`candBarHeight()` 横屏（`barHeight<40`）再压 6vp（`:385-386`）。
- 安卓磁贴是两行字（大字当前状态 + 小字目标状态），估 68×44vp/枚：

| 排法 | 宽度/高度代价 | 结论 |
|---|---|---|
| 6 枚一行 | 6×68 = 408vp > 356vp | 放不下 |
| 横向 Scroll 一行 | 高 +44vp，可见约 5 枚 | 可行 |
| 两行 × 3 枚 | 高 +88vp，主键区少 88vp | 可行但挤压明显 |
| 初版只放 4 枚 | 4×68 = 272vp，一行放得下 | 可行、改动最小 |
| 覆盖式功能层（像 `ExpandedPanel()`） | 不撑高键盘，覆盖键盘区顶部，点空白收起 | 可行，需新面板 |

以上只列代价，**形态 A/B/C/D 仍等主人拍板**；§九 已按安卓实物把「磁贴进 `…`」纳入方案 D，拍板后「初版放哪几枚」按 §七 的 5 枚直接定。

## 九、安卓实物核实（2026-10-25 00:2x，截图证据）

之前 §三/§八 建立在「一排 6 枚磁贴」的推断上。这轮在安卓模拟器运行产物里翻到**实物截图**，推断需要修正：

- 证据 1（折叠态）：`docs/evidence/2026-10-25/h165-android-toolbar/s_toolbar.png`
  —— 与鸿蒙现状几乎同构：预编辑行「hao」+ 一条带反查注释的长候选 + 右侧 `▼`。
- 证据 2（展开态）：`docs/evidence/2026-10-25/h165-android-toolbar/k1_toolbar.png`
  —— 展开后是**一条独立图标行**，不是磁贴行：`‹`（收起）/ 撤销 / 重做 / 移动光标 / 剪贴板 / `…`（开关菜单）/ `▼`（收起）。
  该行高约 48dp，图标深藏青，底色浅米；图标等距，左 `‹` 与右 `▼` 都能收起。

**结论修正**：

1. 安卓的「简体/中英/半角/增廣/Reload」**不在工具栏上**，而在 `…` 打开的开关菜单里（README 第 360 行描述的磁贴＝那个菜单的条目）。
2. 所以 §八「6 枚一行 408vp > 356vp 放不下」**不再是阻塞**：磁贴进 `…` 面板，宽度不受 356vp 限制（可 2 列×N 行或全宽列表）。
3. 工具栏本身是**图标行**，6 个图标在 356vp 内完全放得下（每枚 ≈48vp）。

### 方案 D：安卓原样（新增，推荐但等主人点头）

折叠态＝现在的候选栏（预编辑 + 候选 + `▼`）；点 `▼` （或左侧新增的 `›`）展开一条 **44vp 图标行**：

```
[‹] [中英] [简繁] [半角/全角] [增廣] [反查] […] [▼]
```

- 前 5 枚直接调 `setOption`（§七 已核实 5/6 可做），`…` 打开「开关磁贴」覆盖层（大字当前状态、小字目标状态，照安卓），Reload 在引擎补 API 前不放。
- 收键盘动作可放在 `…` 里或长按 `▼`（保持 H-109 长按语义）。
- 优点：与安卓实物一致；不再受 6×68vp 宽度约束；不改现有候选网格语义（网格仍归 `▼` 的单击/长按）。
- 风险：候选栏多一行后键盘总高 +44vp（竖屏需确认不挤主键区）；横屏 `barHeight<40` 时 L1 已隐藏，图标行放哪需定（建议横屏只保留 `…` + `▼` 两枚）。
- 示意图（现状/展开态/安卓实物三行对照）：`docs/evidence/2026-10-25/h165-android-toolbar/h165-mockup-D.png`（生成脚本 `scripts/h165_mockup.py`，图上已标「未实现」）。

## 十、安卓那 8 枚图标，鸿蒙端逐枚能不能做（2026-10-25 09:03 代码实测）

§九 说「方案 D 照安卓实物的图标行」。这节把安卓行的每一枚（`‹` 撤销 重做 移动光标 剪贴板 `…` `▼`）在鸿蒙源码里查了一遍，结论先给：**「照搬安卓」只成立一半**——位形能照搬，图标内容不能。D 的 v1 仍是 §九 那行文字开关 + `…` + `▼`。

| 安卓那一枚 | 鸿蒙端现状（实测） | 结论 |
|---|---|---|
| `‹` 收起 / `▼` 收起 | 纯 UI 状态；`sys.symbol.chevron_down`／`chevron_up` 已在用（`KeyboardIndex.ets:1263/1267`） | v1 做 |
| `…` 开关菜单 | 纯 UI + `setOption`（§七 5/6 项可做） | v1 做 |
| 撤销 | `undoLastAction()` 在 `KeyboardController.ets:533`，但**全仓零调用点**；生产它读的 `'clear'` 记录的 `clearAllAndRecord()` :498 也**同样零调用点**——`7ba71d7`（H-167，主人 2026-10-24 定「退格不做上下滑」）把唯一触发点删了。且它只认 `'clear'`（:537），`'commit'` 记录被跳过（:531 注释），撤销后只 `insertText` 补文字、光标位置不还原 | **不放 v1**：不是加按钮，是「撤销什么」要重新定义＋记录方（清空入口）得先有，单开一单 |
| 重做 | `redoStack` / `redo` 在 `entry/src/main/ets` **0 命中** | **不放**：要从零写栈，且与上面那条同属一套语义 |
| 移动光标 | `InputClient.moveCursor(direction)` `@ohos.inputMethodEngine.d.ts:1336`／`moveCursorSync` :1371／`selectByMovement` :1428 齐备，但 `entry/src/main/ets` **0 处调用**（与安卓同一功能，鸿蒙端从未接过） | **可做但延后**：API 够，缺的是方向键 UI 与长按连发；v1 先不进 `…` |
| 剪贴板（历史） | 「贴当前内容」**已有入口**：长按 `v` → `sendExtendAction(PASTE)`（`KeyboardIndex.ets:1774-1777`，免权限，同处长按 a/x/c 全选/剪切/复制）。要「最近 N 条」得走 `@ohos.pasteboard.getDataSync` :1307，其 `@permission ohos.permission.READ_PASTEBOARD` :1267 —— 直接撞内容闸门 ⑧（`scripts/check_app_content.py:350-355` 断言权限**恰好**为 `['ohos.permission.VIBRATE']`），还动「单机应用」申报口径 | 历史面板**不放 v1**；工具栏不必再放「粘贴」（长按 v 已有），免得两处语义 |
| 图标素材 | 仓库 `resources/base/media` 只有 `app_icon.png` 一张图；键面一律 `SymbolGlyph` 系统符号，现用 6 个名字（chevron_up/down、delete_left、return_down_left、arrow_up、x） | 撤销/重做/剪贴板/光标对应的系统符号名**没在真机核实过，不猜**；名字验证前用单字或两字标签 |

因此 **选 D ≠ 键面上会多出「撤销／重做／剪贴板」按钮**。若主人要的是那几个动作本身，它们各自是独立单子（撤销/重做一张、光标一张、剪贴板一张），与本条的工具栏形态解耦，可以分别排期。

### 待主人一句话

原 §四 第 1 问已从「A/B/C」变成「A/B/C/D」；若选 D，磁贴清单按 §七 的 5 枚（Reload 暂缺）即可，**不需要再逐枚讨论**。§十 已说明：D 的 v1 只有那 5 个开关 + `…` + `▼`，撤销/重做/剪贴板不在其中。

---

## 十一、落地现状（**权威**，2026-10-26 11:3x · Qoder 实测源码常量）

> 上面 §一~§十 是设计推演与当时的可行性判断，**多处已被实现推翻**（例如 §十 说撤销/重做/光标/剪贴板「不放 v1」，H-177/H-183 全接上了）。
> 要改工具栏，以本节为准。源码位置：`entry/src/main/ets/pages/KeyboardIndex.ets`。

### 11.1 两种形态

| 状态 | 条形内容 | 高度 |
|---|---|---|
| 收起（有候选/有 preedit） | 左 › ＋横向滚动候选 List ＋ 右 ▼ 候选网格三角 | `candBarHeight()`（竖屏 44vp = L1 16 + L2 28；横屏 24vp） |
| 收起（Idle，无候选无 preedit） | 左 › ＋ 空 ＋ 右 ▼（单击＝收键盘） | 同上 |
| 展开（用户点 › 或手动 pin） | 图标行 7 枚：‹ 撤销 重做 光标 剪贴板 ··· ▼ | 同上（**整栏互换，不增高**） |

### 11.2 几何（真机基准屏宽 360vp）

| 量 | 值 | 常量 |
|---|---|---|
| 工具栏左右内边距 | 2vp | `Row.padding({left:2,right:2,...})` |
| 图标盒 | `min(36, candBarHeight())` 见方；字形 20vp，盒矮时 16→12vp | `FUNC_ICON_SIZE=20`、`funcIconBox()`、`funcIconGlyphSize()` |
| 首枚图标中心 | 2＋18 = **20vp**（5.6% 屏宽） | — |
| 末枚图标中心 | 360−2−18 = **340vp**（94.4%，安卓实测值） | — |
| 收起态左 › 宽 | **24vp** ⇒ 中心 8＋12 = 20vp，与首枚图标**同一竖线**（H-188） | `FUNC_TRI_LEFT_W=24`、`CAND_PAD_H=8` |
| 收起态右 ▼ 宽 | 36vp，候选行右内边距 **2vp** ⇒ 中心 340vp，与末枚图标同一竖线（H-188） | `FUNC_TRI_WIDTH=36` |
| 两枚三角的命中盒高 | `candRowHeight()`（跟随行高，横屏不会溢出） | — |
| 图标墨色 | `#17203A`（安卓实物 rgb(23,32,58)） | `FG_TOOLBAR` |

### 11.3 过渡与折叠规则（H-189/H-192/H-187）

- 展开/收起：80ms 淡出 → 换内容 → 140ms 淡入（只淡内容、不动栏高，所以高度预算不变）；网格展开另加 180ms 淡入＋12vp 轻上移。
- **只有三处会收起**：首枚 ‹、末枚 ▼、`···`。撤销/重做/光标/剪贴板点完**保持展开**（主人原话「操作还没完成，改成手动折叠工具」）。
- 打字/退格：立刻收起（H-180，主人原话「打字的时候会覆盖候选，逻辑有问题」）。
- 手动展开（pinned）后打字 → 收起；commit 回 Idle（无 preedit 无候选）时工具栏**自动回来**（H-187，照安卓 `KawaiiBarStateMachine` 的 Idle 态）。用户主动点 ‹/▼ 则不回来。

### 11.4 七枚各自的落地状态

| 枚 | 状态 | 实现 |
|---|---|---|
| ‹ / ▼ | 已接 | `setFuncBar(false)`＋`funcBarPinned=false` |
| 撤销 | 已接（H-177） | `undoCommit()` 逐字撤回最近一次上屏（`deleteForwardSync(1)` 逐个删，因 IME Kit 的 n 只删 1 个） |
| 重做 | 已接（H-177） | `redoCommit()` 放回；有新动作即清 redoStack |
| 光标 | 已接（H-177） | `moveEditorCursor(3/4)` → `InputClient.moveCursorSync`；按键面另有空格左右滑移（10vp 一步，H-180） |
| 剪贴板 | 已接（H-183）**但只是「贴当前内容」** | `sendExtendAction(PASTE)`，让宿主编辑框执行；**历史面板没做**（要 `READ_PASTEBOARD`，system_basic，撞内容闸门 ⑧） |
| ··· | **未做，等主人拍板形态**（H-184） | 现在只等于「收起」；`toggleFuncOption` 等实现还在，磁贴形态曾被主人否掉 |

### 11.5 未做的三件已派 CodeArts（M-221 / H-194）

光标移动面板（四向＋按住连发）、剪贴板面板（贴当前内容＋历史置灰）、`···` 菜单层——**组件归 CodeArts（`entry/src/main/ets/components/ToolPanels.ets`），集成归 Qoder**；他不得改本文件与 `KeyboardController.ets`，也不得申请权限。

### 11.6 谁在守这块

| 闸门 | 管什么 |
|---|---|
| `scripts/h190_bar_ux_check.py`（15 项＋5 负控） | 三角 x 与工具栏首末枚同线、pressed 反馈、barAlpha 过渡链、L1 只 preedit、动作键不收起 |
| `scripts/h165_bar_height_check.py` | 行级＋行内子节点高度预算（横屏 24vp 不许溢出） |
| `scripts/h180_space_swipe_sim.py` | 空格滑移的 5 条不变式 |
| `scripts/h180_device_accept.py align|letters` | 真机：三角对位、撤销不收起、‹ 收起、commit 后自动回来、字母行右端 <180px |


---

### 11.7 字母键长按落地表（M-235(Qoder) 派单 A/B · CodeArts 2026-10-26 21:3x）

> **口径**：键面文案与动作取自三生 Trime 部署产物 `docs/evidence/2026-10-26/trime-build.yaml` `qwerty`（`預設40鍵`）段，**797–803 行**；「鸿蒙侧」一列只写**代码里能指到行号**的东西，指不到就写「未找到 API」。
> **状态说明**：`已接` = 现有代码就在跑；`待接` = 接口在、键面分支没写；`缺数据` = 只是配置改动；`缺 API` = 没找到。
> **⚠️ 前提**：三生 40 键是 **5 排**（数字行 / q~p / a~l; / z~m,./ / 底栏 7 枚），我们是 **3 排字母 + 底栏**（`LETTER_ROW_1/2/3`，`KeyboardIndex.ets:140-142`）。下表**只列现有键面存在的键**；数字行 10 枚、`;` `,` `.` `/` `'` 五枚的对应长按，要等排布扩充后才谈得上。

| 键 | 三生长按 | 三生键面文案 | 鸿蒙侧对应 | 落地接口 | 状态 |
|---|---|---|---|---|---|
| a | `select_all` | 全選 | `ExtendAction.SELECT_ALL` | `sendEditorAction()` | **已接**（`KeyboardIndex.ets:2712`） |
| x | `cut` | 剪下 | `ExtendAction.CUT` | `sendEditorAction()` | **已接**（`:2716`） |
| c | `copy` | 複製 | `ExtendAction.COPY` + 收拢选区 | `copyThenCollapse()` | **已接**（`:2720`，H-204） |
| v | `paste` | 貼上 | 安全控件注册不上（正式签名后验） | 打开剪贴板面板 | **已接但受限**（`:2727`，M-237） |
| s | `Home` | **行首**（H-220 主人「不是全首全尾，是行」） | 自己算：`getForwardSync`（光标**前**文）取到最后一个 `
` 之后，落位用 `selectByRangeSync({pos,pos})`（`:869-895`） | `moveCursorToLineStart()` | **已接**（H-220，`KeyboardIndex.ets` 长按 s） |
| d | `End` | **行尾**（H-220） | 用 `getBackwardSync`（光标**后**文）找第一个 `
` 前长度 | `moveCursorToLineEnd()` | **已接**（H-220）；全文首/尾留在 ⇆ 面板「全首」「全尾」格 |
| h | `Left` | ← | `moveCursorSync(3)` | `moveEditorCursor(3)` | **已接**（H-210，`KeyboardIndex.ets:2767`） |
| j | `Down` | **↑ 上移**（H-220r3 主人「下移上移，互换位置」⇒ 故意偏离三生 `Down`，安卓参照表 `evidence/2026-10-26/nova6-ime-research.md:118` 里 j=↓，别再改回） | `moveCursorSync(1)` | `moveEditorCursor(1)` | **已改**（H-220r3） |
| k | `Up` | **↓ 下移**（H-220r3 与 j 对调） | `moveCursorSync(2)` | `moveEditorCursor(2)` | **已改**（H-220r3） |
| l | `Right` | → | `moveCursorSync(4)` | `moveEditorCursor(4)` | **已接**（H-210，`:2782`） |
| m |C `Delete` | 刪除（删光标**右边**） | **`deleteBackwardSync(1)`**＝删光标后文（d.ts:1135）；`deleteForwardSync`(:1086) 是删光标**前**文＝退格 | `deleteAfterCursor()` | **已改**（H-220r3，主人「不是左边那，和退格重复了」） |
| n | `Insert` | **选择**（H-220 主人点名安卓选择键） | 扩展选区模式：`selectByMovementSync`（主，宿主记锚点）/`selectByRangeSync`（兜底） | `toggleSelectionMode()`，开着时 h/j/k/l 与面板四向变扩选 | **已接**（H-220，非 Insert 覆盖模式） |
| f | `Page_Up` | 上頁 | **滚编辑框**——主人确认；IME Kit 无翻屏/scroll 接口 | — | **不做**（M-247③，不留角标） |
| g | `Page_Down` | 下頁 | 同上 | — | **不做**（M-247③，不留角标） |
| q w e r t y u i o p | `_ - + = \| \ [ ] { }` | 同左 | 符号 | 现有气泡 `ALT_CHARS`/`HIDDEN_SYMS`（`KeyboardIndex.ets:182`/`:249`） | **缺数据·口径待定** |
| z b | `` ` `` / `~` | 同左 | 符号 | 同上 | **缺数据** |
| 回车 | `CommitComment` | **編碼** | 引擎 `commitComposition` 未在 cpp 导出 | 需 cpp 加导出 | **缺 API（cpp 侧，Qoder）** |
| 符號 长按 | `Keyboard_number` | 數字 | 现有符號面板切换 | — | **已接（现面板）** |

**M-247(Qoder) 三件拍板已落地（CodeArts 2026-10-26 22:3x）**：

1. **s/d 文案（H-220 已改口径）**：先按 M-247① 做过「全文首/全文尾」，主人 14:4x 打回「不是全首全尾，是行」⇒ 键面长按改**行首/行尾**（自己按换行符算，鸿蒙无按行 API），全文首尾挪进 ⇆ 面板格子。
2. **h/j/k/l/m 与 HIDDEN_SYMS 冲突**：已解决——五组置空（`KeyboardIndex.ets:265-277`），长按做编辑动作，符号挪到 ?123 页。
3. **f/g/n 判不做**：f/g = 滚编辑框（主人 21:4x 确认），IME Kit 无翻屏 API；n = Insert 覆盖模式，未找到 API。不留角标，n 回普通字母键。

**谁在守**：h/l 与 a/x/c/v 已接（H-210/H-204）；**s/d/n 与 j/k/m 的语义由 Qoder 按 H-220/H-220r3 定稿（CodeArts 别改回）**；q~p+z+b 17 键符号等排布口径；回车长按等 cpp 导出。

### 11.8 滤镜实机验证 + UI 补丁取舍（2026-10-27 00:4x · Qoder，M-235/M-246 留的尾巴）

**滤镜（phoneComment_Filter，CodeArts 已挂链，aabdf87 带入）**：Mate80 真机 00:4x 实测——键面打 `ghos`，空闲栏出 `下灯 xiadeng`、`规划欧式 guihuaoushi`，展开网格出 6 格双列（`规划 guihua program(v.);`、`更换 genghuan replacement(n.)…` 等）。注释全部**拼音先行、无撑行、无 3 行爆格**；`更换` 尾部 `…` 是滤镜 `MAX_WIDTH=20` 显示宽度预算的正常截尾（滤镜头注释自证「从右边截，[vbrq]/拼音永远先保住，砍掉的只是末尾词典释义」）⇒ **滤镜真机生效，VERIFIED**。证据 `docs/evidence/2026-10-27/h233_ghos_bar.jpeg`、`h233_grid.jpeg`。

**UI 补丁两处（M-235(Qoder) 里我自己加的）——定夺＝都保留，不回退**：
1. `candCommentText()` 剥 `[编码]` 段：**保留**。滤镜不剥反查前置码（`[vbrq]` 是它明确要保的东西），剥掉 `[编码]` 是显示层的活，两层各管一段，不重复；回退了窄格子就会重新出现 `[fwaj] guihua` 挤爆。
2. 网格注释 `maxLines(1→2)`：**保留**。20 列预算折成空格后仍是单行文本，但 ASCII 宽注释（`genghuan replacement(n.)…` 26 字符）在半格宽度里物理上就是两行；回退成 1 行会把这格腰斩。滤镜管「数据不爆」，maxLines 管「显示装得下」，不冲突。
**判据**：两边改的是不同层（引擎数据预算 vs UI 显示），M-235 说的「别两边同时改同一现象」不成立——真机两态（空闲栏/展开网格）都无同一现象重复处理痕迹。
