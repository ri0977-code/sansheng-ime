# H-154 滑键手势修复与功能补齐 — 需求规格

> 2026-10-23 20:3x，主人（三生输入法作者）在 Mate80 鸿蒙真机反馈，键盘布局基本定形，进入"修小毛病、找补功能"阶段。第一批 4 项。
> 参照基准：主人即 nova6 安卓三生的作者与实测者，按主人描述实现（nova6 adb 当前离线，无法抓真机）。

## 需求 1（Bug 修复）：字母键上滑出符号"出不了"

**主人原话**：「键盘上的符号上滑现在出不了」。

**现状**：功能其实已实现 —— `KeyboardIndex.ets:1384-1393` 的 `LetterKey()` 挂了 `PanGesture({ direction: PanDirection.Up, distance: 20 }).onActionEnd()`，`getAltChar()`（L941）查 ALT_LETTERS/ALT_CHARS 表，命中就 `keyboardController.onKey(alt)` 并用 `swipeAltDone` 防与 onTouch(Up) 双上屏（L1376）。

**要查的根因**（实现前先定位，不盲目改）：
1. `.gesture(PanGesture)` 与 `.onTouch()` 同时挂在同一个 Text 上时手势是否被 onTouch 吞掉（触摸事件优先级）；
2. PanGesture 的 `distance: 20` 在 Mate80 上是否过大导致手势不触发（对照候选栏 priorityGesture 的 speed/distance 参数）；
3. `onActionEnd` 是否根本没进（加 hilog 打点或用 hitrace 验证）；
4. ALT_LETTERS/ALT_CHARS 表本身是否为空或错位。

**验收**：Mate80 真机上滑 a 键（次级字符）直接上屏对应符号，且上滑后**不**额外上屏字母 a。

## 需求 2（新增）：字母键下滑出大写

**主人原话**：「下滑出大写」。已澄清（AskUserQuestion）：**该键直接出大写**（滑 a 直接上屏 A、滑 b 出 B），一次性上档，**不**开 shift 锁定，不点亮 shift。

**实现**：`LetterKey()` 加 `PanGesture({ direction: PanDirection.Down, distance: 20 })`，onActionEnd 里 `keyboardController.onKey(ch.toUpperCase())` 并置 `swipeAltDone = true`（复用现有防双上屏标志，方向增加 Down 分支）。
注意：不能复用 `sendLetter()`（它会读 shiftActive 并复位 shiftOn），下滑路径要绕过 shift 逻辑直接发大写。

**验收**：Mate80 真机下滑 a 直接上屏 `A`；下滑后不额外上屏小写 a；shift 状态不被下滑改变。

## 需求 3（新增）：退格键上滑清除内容、下滑撤销

**主人原话**：「退格键，上滑清除内容，下滑撤消消除」。已澄清（AskUserQuestion）：**撤销 = 撤销最近上屏 + 撤销上滑清除**。

拆解：
- **上滑清除内容**：清空输入状态。编码态（有 preedit）→ `keyboardController.clear()` 清编码；无编码态（已上屏）→ 删除编辑器里刚上屏的文本（见下方"撤销栈"）。
- **下滑撤销**：撤销两类"清除"的结果——
  ① 撤销最近一次上屏（刚打出来/刚选上屏的字词，回退到上屏前状态）；
  ② 撤销上滑清除（把被上滑清除掉的内容恢复回来）。

**撤销栈设计**（UI 侧，不动引擎桥）：
- 因为引擎（`ets/engine/**`）只读且无 undo 接口，撤销能力在 **KeyboardController/UI 侧**实现：
  - UI 维护 `undoStack`：记录"最近一次上屏文本"（`insertText` 时入栈）与"最近一次上滑清除的文本"（清除时入栈，栈顶标记类型）；
  - 撤销 = 从栈顶取一条记录：若为"上屏记录"→ `deleteForward(n)` 删掉 n 个字符后 `clear()`（回编码前态由主人按当时场景判断，最低要求是删掉字）；若为"清除记录"→ `insertText(savedText)` 恢复。
  - 栈上限（如 10 条）防内存膨胀；跨面板切换/输入法重启时清空（不持久化，避免与宿主编辑器状态不一致）。
- **归属确认**：`KeyboardController.ets` 在 `entry/src/main/ets/inputmethod/**` —— **CodeArts 独占**，本次不动 `engine/**`、`cpp/**`，**不需要 Qoder 改桥**。

**验收**：Mate80 真机
1. 有编码时上滑退格 = 编码清空（候选栏空）；
2. 无编码时（刚上屏"三生"）上滑退格 = 编辑器里"三生"被删掉；
3. 下滑退格 = 被上滑删掉/清掉的内容恢复回来（至少覆盖"最近一次上滑清除"这一场景）；
4. 下滑撤销不影响编码态。

## 需求 4（纯 UI）：空格键文案改"三生"

**主人原话**：「空格两个字，能不能换成三生」。

**现状**：`KeyboardIndex.ets:2229` 底栏空格键 `Text('空格')`（layoutWeight 4.5，主键盘 else 分支）。另有数字键盘 `NumpadPanel` 的 `Text('空')`（L1601）—— 主人说的"空格两个字"明确指主键盘底栏，数字键盘不在本次范围（如需另议）。

**实现**：`Text('空格')` → `Text('三生')`。字号 16 不变（两字与两字等宽）。

**验收**：Mate80 真机主键盘底栏空格位显示"三生"，短按仍上屏空格。

## 存量事项（M-131 遗欠，随本批一起收）

| 项 | 内容 | 归属 |
|----|------|------|
| H-098 | `main_pages.json` 摘除 `LandscapeProbe`/`M3Probe`（内容闸门第⑩项会挡提审包） | CodeArts（profile 归我） |
| L1005 注释 | 注释写「短按展开/长按折叠」与代码相反（代码是单击折叠/长按恒折叠） | CodeArts |
| module.json5 metadata | `ohos.entry.mainability` 那条要么退掉要么加注释 | **Qoder**（module.json5 归他）—— 本批不改，走 HANDOFF 变更请求 |

## 边界

- **不做**：数字键盘空格改文案（L1601 不动）；nova6 侧抓图比对（adb 离线）；引擎侧 undo（engine 只读）。
- **冲突记录**：无新增。手势仅挂在 26 键字母键与底栏退格键，不影响候选栏翻页手势与符号面板 Swiper。
- **hvigor 会重编码 PNG**：本批无资源改动，字节数仍只比 unsigned（H-133 口径）。

## 交付判据

1. `scripts/build.ps1` 构建绿，unsigned/signed 字节数记入 WIP 交付行（带 B 标记，M-125 时钟口径：先跑 date 取真实时间）；
2. 装机 Mate80 + `hdc shell ime -s com.sansheng.ime` 切回（干净重装会弹回小艺，已知）；
3. 上表 4 条真机验收逐条过（主人验）；
4. 存量三项：H-098 摘除 + L1005 注释改正随本批完成；module.json5 走 HANDOFF 变更请求等 Qoder。