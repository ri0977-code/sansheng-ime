# CodeArts 夜间值守目标（2026-10-26 22:3x 起）

> 整理：(CodeArts) 本文件是 CodeArts 侧夜间值守的 goal 声明与任务清单。
> 值守 cron taskId: `08a88c15`（每 5 分钟轮询）

## 目标

完成 M-205~M-209 全部只读复核任务，在 MAILBOX.md 回执，更新 HANDOFF.md 和 ISSUES.md。

## 任务清单与结论

### M-205（已完成）：H-165/H-170 三缺陷返工只读复核

复核四处改动，全部确认到位：

1. **三角内联**（`KeyboardIndex.ets:1408-1424`）：折叠三角 `SymbolGlyph(chevron_up).rotate({angle:90})` 作为 L2 候选行 Row 首子节点，0 额外高度——修掉了"独立 20vp 三角行溢出压键"
2. **整栏互换**（`KeyboardIndex.ets:1353-1386`）：`showFuncBar=true` 时磁贴行独占 `candBarHeight()`，L1/候选行 `Visibility.None` 让位——修掉了"独立 34vp 磁贴行溢出"
3. **FuncTile 单参读 @State**（`KeyboardIndex.ets:548-584`）：`funcTileLabel()/funcTileState()` 在 builder 体内读 `@State` 派生（`this.tradMode/this.asciiMode/this.fullShape/this.asciiPunct/this.extendedCharset/this.phraseComment`），不走按值参数——修掉了"@Builder 按值参数不随 @State 刷新"
4. **candBarHeight() 竖屏 max**（`KeyboardIndex.ets:423-428`）：`Math.max(this.barHeight, this.commentRowHeight() + this.candRowHeight())`——构造上保证容器不小于可见行高之和

闸门 `h165_bar_height_check.py` 竖屏 4 种组合全绿，横屏 2 种 WARN（H-096 遗留，不阻断）。

### M-206（已完成）：duty_watch 误报澄清

确认 M-178/181/182/184 在任务执行表中状态分别为 `已交付`/`已复核闭环`/`（M-182 无表行）`/`已复核闭环`，全部非 OPEN。误报根因＝整行含 `OPEN` 子串（历史行正文提到 OPEN）。`mail_open.py` 判据只看状态列精确等于 `OPEN`，rc=1 无 OPEN。

### M-207（已完成）：三件只读活

**① 安卓图标行逐枚核对**：

| 位序 | 安卓实物 | 鸿蒙代码 | 状态 |
|---|---|---|---|
| 1 | ‹（收起） | `FuncIcon('back')` → `chevron_up.rotate(270)` | 已接 |
| 2 | 撤销 | `FuncIcon('undo')` → 文字标签"撤销" | 已接（H-177） |
| 3 | 重做 | `FuncIcon('redo')` → 文字标签"重做" | 已接（H-177） |
| 4 | 移动光标 | `FuncIcon('cursor')` → 文字标签"光标" | 已接（H-177） |
| 5 | 剪贴板 | `FuncIcon('clipboard')` → 文字标签"剪贴" | 未接（置灰+toast） |
| 6 | ···（更多） | `FuncIcon('more')` → 文字"···" | 已接（收起） |
| 7 | ▼（收起） | `chevron_down` | 已接 |

位形照搬安卓，7 枚每枚约 48vp（`FUNC_ICON_SIZE+16`），整行在 360vp 屏宽内。顺序与 spec §十 一致。

**② SymbolGlyph 符号名核实**：

仓库现用 5 个已核实符号：`arrow_up`/`chevron_down`/`chevron_up`/`delete_left`/`return_down_left`。

撤销/重做/光标/剪贴板对应的系统符号名**未在真机核实过**。此前用 `return_down_left`(回车) 冒充撤销、`delete_left`(退格) 冒充剪贴板，真机图形完全不对（主人一眼看穿）。

**结论：不猜符号名，保持文字标签。** 需要在真机上逐个 `$r('sys.symbol.xxx')` 试渲染并截图，或查 SDK 符号表资源清单。值守期间无法做真机渲染测试，等主会话或主人协助。

**2026-10-26 22:4x 更新——SDK 字体验证**：从 `D:/DevTools/DevEco/DevEco Studio/sdk/default/hms/previewer/resources/fonts/HMSymbolVF.ttf` 中用 fontTools 提取 glyph 名，已验证：

| 功能 | glyph 名 | Unicode | `$r('sys.symbol.xxx')` 推断 | 状态 |
|---|---|---|---|---|
| 撤销 | `undo` | U+F01F3 | `$r('sys.symbol.undo')` | 字体中存在 ✓ |
| 重做 | `redo` | U+F01F4 | `$r('sys.symbol.redo')` | 字体中存在 ✓ |
| 剪贴板 | `text_clipboard` | U+F019D | `$r('sys.symbol.text_clipboard')` | 字体中存在 ✓ |
| 光标移动 | `move` | U+F05B4 | `$r('sys.symbol.move')` | 字体中存在 ✓ |
| 光标移动(备选) | `position` | U+F01CA | `$r('sys.symbol.position')` | 字体中存在 ✓ |

已用的5个符号名（arrow_up/chevron_down/chevron_up/delete_left/return_down_left）全部在字体中找到对应 glyph，且在代码中通过 `$r('sys.symbol.xxx')` 正常使用 ⇒ glyph 名与 sys.symbol 资源名高度对应。

**注意**：字体中有 glyph 不100%等于资源系统注册了对应资源条目，仍需真机渲染验证。但这是目前最强的离线证据——比"不猜"前进了一大步。

**③ 撤销/重做/光标/剪贴板可行性复核**：

| 功能 | API | 可行性 | 结论 |
|---|---|---|---|
| 撤销 | `deleteForwardSync(1)` 逐个删 + redoStack | 可行（已接） | H-177 VERIFIED |
| 重做 | `insertText(rec.text)` 从 redoStack 弹出 | 可行（已接） | H-177 VERIFIED |
| 光标移动 | `InputClient.moveCursorSync(direction)` | 可行（已接） | H-177 VERIFIED |
| 剪贴板历史 | `READ_PASTEBOARD` 权限 | **不可行** | 会撞内容闸门 ⑧（权限恰为 VIBRATE） |

### M-208（已完成，与 M-207②合并）：符号名核实催办

结论同 M-207②：不猜符号名，保持文字标签，等真机或 SDK 符号表核实后再换。

### M-209（已完成）：H-177 复核五处实现 + 剪贴板结论

**五处实现复核**：

1. **`undoCommit()`**（`KeyboardController.ets:562-586`）：从 undoStack 弹出 type='commit' 的记录，按 `rec.text.length` 逐个 `deleteEditor(n)`（因 `deleteForward(n)` 真机只删 1），删完挪到 redoStack。缓冲区 `sessionCommitText` 用 `endsWith` 判断后 slice 保持账实一致。✓
2. **`redoCommit()`**（`KeyboardController.ets:589-599`）：从 redoStack 弹出，`insertText(rec.text)` 放回，挪回 undoStack。✓
3. **`moveEditorCursor(direction)`**（`KeyboardController.ets:604-617`）：走 `client.moveCursorSync(direction)`，direction 3=左 4=右（与 SDK `@ohos.inputMethodEngine.d.ts:1371` 一致）。try/catch 包裹。✓
4. **`redoStack` 清栈时机**（`KeyboardController.ets:488-496`）：`pushUndo` 有新动作即清 redoStack——标准撤销栈语义，防止"撤两次再做一次"错乱。✓
5. **`pushUndo` 调用时机**（`KeyboardController.ets:479-481`）：在 `insertText` 的 **then 成功回调**里执行（P1-2 修复），失败不入栈。✓

**剪贴板结论：不做。**

理由：
- 剪贴板历史需要 `ohos.permission.READ_PASTEBOARD` 权限
- 内容闸门 ⑧ 断言权限**恰为** `['VIBRATE']`，新增权限会阻断上架
- "粘贴当前内容"长按 v 已有（`KeyboardIndex.ets:1774`）
- 如未来需要，需主人拍板是否接受新增权限（会改变上架策略）

## 值守协议

- 每 5 分钟读 `docs/MAILBOX.md`，检查发给 CodeArts 的新消息
- 用 `python scripts/mail_open.py --who CodeArts -v` 检查 OPEN 行
- 有新消息就处理，没有就保持待机
- 不自行关机；BLOCKED 时在 MAILBOX.md 写明等什么
- 不碰 `entry/src/main/ets/engine/**`、`entry/src/main/cpp/**`、`sign/**`
- 构建用 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1`
- 所有共享编辑区改动加 agent 标识 (CodeArts)

## 完成标准

- M-205~M-209 全部在 MAILBOX.md 回执（状态改为已回执）
- 复核结论写入 `docs/reviews/` 或 `ISSUES.md`
- `HANDOFF.md` 更新当前状态
---

## 追加阶段（2026-10-26 21:1x–21:5x）：40 键长按派单的答复与三处拍板请求

> 整理：(CodeArts) 本段是 goal 第一阶段（M-205~M-209）完成后的追加任务，全部来自 M-235(Qoder) 派单与主人 21:4x 当面答复。

### 已完成

| 事项 | 证据 |
|---|---|
| **⑥ 滤镜替换落地**（M-235 拍板「换」） | `wubi_pinyin.custom.yaml:60`：`laneChangeAndSpace_Filter` → `lua_filter@phoneComment_Filter`；`python yaml.safe_load` 打印 `engine/filters` 仍 **13 项**、顺序未动；ISSUES H-209 已补记 |
| **M-240 停手警告回执并转 DONE** | M-241(CodeArts) 报「entry/src 零改动」；M-240 状态格 OPEN→DONE |
| **f/g 三度定论并正式降级** | 主人 21:4x「滚编辑框」；IME Kit `InputClient` 全方法集（`@ohos.inputMethodEngine.d.ts:1003-1600`）无 scroll/pageUp/scrollCursor，`moveCursorSync` 是单格移光标，`moveTo(x,y)`（`:2155`）是移面板窗口 ⇒ **判不做**。已改 `h210-40key-layout-facts.md` §5.1.1/§5.3、`h165-top-function-bar-spec.md` §11.7 |
| **排布差异落成事实表** | `h210-40key-layout-facts.md`：三生 5 排逐格 vs 我们 3 排（`LETTER_ROW_1/2/3`，`KeyboardIndex.ets:140`）；结论「现有 3 排上做长按编辑功能可行，`;` `,` `.` `/` `'` 5 枚与数字行 10 枚符号长按要等排布扩充」 |
| **§11.7 长按落地表** | `h165-top-function-bar-spec.md` 22 行，逐键给接口行号；标注已接/待接/缺数据/缺 API/不做 |

### 未完成（等 Qoder 拍板，已发 M-246）

~~1. `s/d` 键面文案：叫「行首/行尾」但鸿蒙只能到**全文首尾**（无按行 API），要么保留全文语义要么改文案；~~
~~2. `h/j/k/l/m` 与 `HIDDEN_SYMS` 符号气泡冲突（`h=[/,H]`、`j=[#,J]`、`k=[(,K,[,{]`、`l=[),L,],},ł]`、`m=[\,M]`），二选一或重分配；~~
~~3. 是否同意 `f/g`、`n` 两项判不做。~~

**M-247(Qoder) 三件拍板已全部落地（2026-10-27 00:0x）**：

1. ~~s/d 文案改「全文首/全文尾」——分支占位，等 Qoder 加 `moveCursorToStart()`/`moveCursorToEnd()` 控制器封装；~~ **（Qoder 15:2x 更正：主人 14:4x 打回「不是全首全尾，是行」，H-220r3 已把长按 s/d 改为 `moveCursorToLineStart()`/`moveCursorToLineEnd()`＝行首/行尾，全文首尾挪进 ⇆ 面板「全首」「全尾」格。本节以下 00:0x 记录里的 s/d 一律按此理解。）**
2. h/j/k/l/m 长按做编辑动作、HIDDEN_SYMS 五组置空、符号挪 ?123 页——**已落地**；
3. f/g/n 判不做、不留角标、n 回普通字母键——**已落地**。

### H-210 落地明细（2026-10-27 00:0x）

| 项 | 状态 | 位置 |
|---|---|---|
| h 长按 = 光标左移 | **已接** | `KeyboardIndex.ets:2767-2771` → `moveEditorCursor(3)` |
| j 长按 = 光标**上移** | **已改（H-220r3 Qoder 15:0x）** | 主人「下移上移，互换位置」⇒ j/k 对调，`moveEditorCursor(1)`；**注意：这条故意偏离安卓参照表**（`evidence/2026-10-26/nova6-ime-research.md:118` 里 j=↓），主人话为准，别再改回去 |
| k 长按 = 光标**下移** | **已改（H-220r3 Qoder 15:0x）** | 同上对调 ⇒ `moveEditorCursor(2)` |
| l 长按 = 光标右移 | **已接** | `:2782-2786` → `moveEditorCursor(4)` |
| m 长按 = 删除（光标**后**） | **已改（H-220r3 Qoder 15:0x）** | 主人「不是左边那，和退格重复了」⇒ 由 `onBackspace()` 改 `deleteAfterCursor()`=`deleteBackwardSync(1)`；`deleteForwardSync` 才是删光标前 |
| s 长按 = **行首** | **已接（H-220 Qoder）** | 主人「不是全首全尾，是行」⇒ `moveCursorToLineStart()`；全文首留在 ⇆ 面板「全首」格 |
| d 长按 = **行尾** | **已接（H-220 Qoder）** | 同上 ⇒ `moveCursorToLineEnd()`；全文尾在面板「全尾」格 |
| HIDDEN_SYMS h/j/k/l/m 置空 | **已接** | `:267-270/277` |
| HIDDEN_SYMS f/g/n 置空 | **已接** | `:265-266/276` |
| §11.7 落地表更新 | **已接** | `h165-top-function-bar-spec.md:227-260` |

### 红线遵守情况

- `entry/src` 改动**仅在 LetterKey 长按回调 + HIDDEN_SYMS 数据区**（M-240 划界允许）；
- 未碰 `computePanelSize`/`candBarHeight`/`barIdle`/`FuncMenu`/`bs_row` onTouch；
- 未构建、未签名、未装机；
- 未碰 `engine/**`、`cpp/**`、`sign/**`、`KeyboardController.ets`；
- 信箱 M-249 CLOSED（Qoder M-250 已回，H-210 六键真机全过）。

### 2026-10-27 值守 prep：HIDDEN_SYMS vs Trime 40 键符号对照

> (CodeArts) 信箱无 OPEN，做只读 prep：对照 `HIDDEN_SYMS` 与 Trime 40 键长按符号，供 Qoder 拍板。

**发现**：q~p 长按符号**全部不匹配**——我们放数字 1-0（无数字行设计），Trime 40 键放编程符号 `_ - + = | \ [ ] { }`（有独立数字行）。z/b 也不匹配（我们 `['!', 'B', '¡']` / `["'", 'Z', ...]` vs Trime `~` / `` ` ``）。s/d 的 HIDDEN_SYMS 是死数据（已被编辑动作拦截）。

**决策点**：q~p 要不要改成 Trime 符号？改的前提是先加数字行。折中方案：z/b 先改（不依赖排布），q~p 等数字行。

详见 `docs/evidence/2026-10-26/h210-40key-layout-facts.md` §七。
