# H-155 第二批手势/功能规格（三生输入法·鸿蒙）

- **里程碑**：H-155（承接 H-154 第一批：上滑符号 / 下滑大写 / 退格清除撤销 / 空格"三生"）
- **日期**：2026-10-23
- **归属**：CodeArts（鸿蒙 UI / 输入逻辑）
- **验证设备**：Mate80（hdc `7GL0226408083897`）真机人工滑键验证；不做设备自动测试
- **参照基准**：nova6 安卓三生 —— **本次明确不参照安卓**（用户 2026-10-23 拍板：纯通用键盘长按符号设计），故隐藏符号表为通用集，不抓 nova6

## 1. 背景与已确认事实

- H-154 第一批已提交（`b5fda68`）：字母键 `priorityGesture(PanGesture Vertical, distance:12)` 上滑出 ALT 字符、下滑出一次性大写；退格键 PanGesture Up=清空/Down=撤销；空格文案改"三生"；`main_pages.json` 摘 H-098 两探测页。已 build+sign+装机 Mate80，`ime -s` 切回。
- 官方 API 已确认（`@ohos.inputMethodEngine`，API 10+）：`InputClient.sendExtendAction(action: ExtendAction)` 支持编辑框级全选/剪切/复制/粘贴：
  - `ExtendAction.SELECT_ALL = 0`
  - `ExtendAction.CUT = 3`
  - `ExtendAction.COPY = 4`
  - `ExtendAction.PASTE = 5`
  - `KeyboardController` 已 import `inputMethodEngine`，私有字段 `inputClient` 在 `inputStart` 回调里赋值。需新增一个公开封装方法（如 `sendEditorAction(action)`）调用 `this.inputClient?.sendExtendAction(action)`。
- **关键限制（真机验务必注意）**：`PASTE` 需要**宿主编辑框 app 自己申请** `ohos.permission.READ_PASTEBOARD` 权限，不是输入法侧权限。备忘录等系统 app 通常支持；个别 app 可能静默失败。NOT a code bug。
- `LetterKey(ch)` 当前结构（`KeyboardIndex.ets` ~L1357）：`.onTouch` 处理短按发送（Down 记录 press、Up 发送 `sendLetter(ch)` 除非 `swipeAltDone`）；`.priorityGesture(PanGesture Vertical distance12)` 处理上/下滑（`onActionEnd` 按 offsetY 正负走 ALT/大写，并置 `swipeAltDone`）。
- `getAltChar(ch)` 已存在（返回 ALT_CHARS 表二级字符，非空才渲染右上角小符号）。H-155 新增独立 `getHiddenSymbols(ch)`（隐藏符号气泡集，与 ALT 不同源）。

## 2. 范围

本批只做两件事：
1. **a / s / v / c 四个字母键长按 = 直接操作窗口文字内容**（全选/剪切/复制/粘贴），不弹菜单、不发送字母本身。
2. **其余字母键长按 = 弹出"气泡跟随"隐藏符号面板**（通用符号集），手指滑动选择、松手上屏、松手取消关闭。

> 注：第一批的"字母键上滑符号 / 下滑大写"保持不变，本批须**不破坏** H-154 已修复的上滑触发逻辑。

## 3. 功能 1：a/s/v/c 长按 → sendExtendAction

### 触发
- 用户长按 `a` / `s` / `v` / `c` 键约 400–500ms 不抬起，且期间手指位移未超过滑动阈值（不进入上/下滑分支）。
- 长按时**不得**触发短按上屏（不发 a/s/v/c 字母本身）、**不得**触发上/下滑（ALT/大写）。

### 映射
| 键 | ExtendAction | 枚举值 |
|----|--------------|--------|
| a  | SELECT_ALL   | 0      |
| s  | CUT          | 3      |
| c  | COPY         | 4      |
| v  | PASTE        | 5      |

### 行为
- 调用 `keyboardController.sendEditorAction(...)`（封装 `inputClient.sendExtendAction`）。
- 长按激活后应置一个标志（如 `longPressEditorDone`），抬手（onTouch Up / 手势结束）时消费该标志，**不重复发送字母**。
- 若 `inputClient` 为空（理论异常），静默忽略，不要抛错崩溃。

### 实现提示（非强制，满足行为判据即可）
- 在 `LetterKey` 内对 `ch` 为 a/s/v/c 做特判：长按计时到点 → 调 sendEditorAction 并置标志；`onTouch` Up 时若标志已置则只清标志、跳过 `sendLetter`。
- 也可在 `priorityGesture` 组合 `LongPressGesture`，但须保证与现有上下滑 PanGesture 共存、优先级合理（建议沿用 `.priorityGesture` 容器包 `GestureGroup` 或自行 onTouch 计时，逻辑-coder 决策）。

## 4. 功能 2：字母键长按气泡隐藏符号（气泡跟随）

### 适用键
- 全部字母键 **除 a/s/v/c**（这四个走功能 1，不显示气泡）。

### 显示
- 长按（约 400–500ms 不抬起、未进入滑动）→ 在**该键键面正上方**弹出小气泡（悬浮 Stack，覆盖在键盘层之上，不引入新 Page/自定义弹窗组件，跟随键位置）。
- 气泡内水平列出 `getHiddenSymbols(ch)` 得到的若干符号（建议每键 4–8 个），当前手指指向的符号高亮。
- 符号集为**通用键盘长按符号**（重音字母 + 常见符号），不参照安卓三生。建议默认映射（logic-coder 可直接采用或微调，须写在常量表 `HIDDEN_SYMBOLS`）：

  | 键 | 隐藏符号（建议） |
  |----|------------------|
  | e/E | é è ê ë ē € E |
  | i/I | Ì Í Î Ï ī |
  | o/O | Ò Ó Ô Õ Ö Ø ō |
  | u/U | Ù Ú Û Ü Ū |
  | n/N | Ñ ñ |
  | c/C | Ç ç © （注：c 长按走 COPY，此集实际不触发，可保留或省略） |
  | s/S | ß § （s 同理走 CUT，可省略） |
  | l/L | £ |
  | y/Y | ÿ ¥ |
  | x/X | × |
  | d/D | ð |
  | t/T | þ |
  | p/P | ¶ |
  | r/R | ® |
  | m/M | µ |
  | z/Z | ž |
  | f/F | ƒ |
  | w/W | ŵ |
  | 其他(q/j/k/g/h/b) | 可空（空则不弹气泡，长按无效果） |

### 交互
- 长按激活后，手指**不抬起、在屏幕上滑动** → 高亮随手指在气泡符号间移动（按手指相对气泡的 X 位移映射到符号索引）。
- **松手**：
  - 指向某个符号 → 上屏该符号（`keyboardController.onKey(symbol)`），关闭气泡。
  - 未指向任何符号（滑出气泡区 / 指向空隙）→ 取消，关闭气泡，**不上屏**。
- 松手后该次按键**不重复**触发短按字母上屏（置标志消费，同功能 1 思路）。

### 与上下滑共存
- 长按判定须在"手指先按下、计时未到前发生滑动"时让位给 H-154 的上下滑：即短距离快速滑动应仍走 ALT/大写；只有"按住不动超过阈值"才进入气泡。
- 严禁改动 `priorityGesture(PanGesture Vertical, distance:12)` 的现有上/下滑行为，否则回归 H-154 上滑 bug。

## 5. 成功判据（Mate80 真机人工验）

1. 长按 `a` → 编辑框内已有文字被全选；长按 `s` → 选区被剪切；长按 `c` → 选区被复制；长按 `v` → 剪贴板内容粘贴（宿主支持时）。四次操作均**不**在编辑框留下 a/s/v/c 字符。
2. 长按 `e`（及其他非 a/s/v/c 字母）→ 键面上方出现符号气泡；手指滑动可切换高亮；松手在符号上 → 该符号上屏、气泡消失；松手在空隙 → 无输入、气泡消失。
3. 上滑 `e` 仍出 `é`（或 ALT 表对应二级字符）、下滑 `e` 仍出 `E` —— H-154 行为不变。
4. 短按 `a/s/v/c/e` 仍正常上屏对应字母（长按与短按不串）。
5. 退格上滑清空 / 下滑撤销、空格"三生" —— H-154 行为不变。

## 6. 风险与注意

- **PASTE 静默失败**属宿主权限问题，非本代码缺陷；验收时优先用"备忘录"等系统 app 验证。
- 气泡实现**不得**引入新 Page 或全屏弹窗，必须覆盖在键盘面板之上、跟随键位置（用户要的是"气泡跟随"，不是独立面板）。
- 长按计时与现有 `onTouch`/`priorityGesture` 共存是主要技术风险点；logic-coder 须保证三态（短按 / 上滑下滑 / 长按）互斥不串。
- 不改动 `module.json5` 的 `ohos.entry.mainability` metadata（归 Qoder，走变更请求）。

## 7. 涉及文件

- `entry/src/main/ets/inputmethod/KeyboardController.ets` —— 新增 `sendEditorAction(action)` 封装 + `HIDDEN_SYMBOLS` 常量表（或表放 KeyboardIndex）。
- `entry/src/main/ets/pages/KeyboardIndex.ets` —— `LetterKey` 增加长按分支（a/s/v/c 走 editorAction；其余走气泡）；新增 `getHiddenSymbols(ch)`；新增气泡 Stack 与长按/滑动选择状态。
- 不新增页面、不改 `main_pages.json`（H-098 已摘页，本批无新增页面）。