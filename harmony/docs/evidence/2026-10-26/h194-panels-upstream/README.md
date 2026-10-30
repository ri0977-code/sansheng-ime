# H-194 上游面板调研：光标移动 / 剪贴板 / ··· 菜单

> 整理：CodeArts  
> 许可证：上游代码 LGPL-2.1-or-later，仅参考思路不复制代码  
> 来源：fcitx5-android GitHub master 分支，2026-10-26 拉取

---

## 一、窗口模型（回答 ①面板挂在哪个窗口层）

### 1.1 InputWindow 基类

`InputWindow.kt`（`org.fcitx.fcitx5.android.input.wm`）是所有面板窗口的基类：

- `SimpleInputWindow<T>` — 简单窗口，无标题栏、无扩展
- `ExtendedInputWindow<T>` — 扩展窗口，有 `title`、`showTitle`、`onCreateBarExtension()` 返回栏扩展 View

三个面板都是 `ExtendedInputWindow` 子类：
- `TextEditingWindow` — `InputWindow.ExtendedInputWindow<TextEditingWindow>()`
- `ClipboardWindow` — `InputWindow.ExtendedInputWindow<ClipboardWindow>()`
- `StatusAreaWindow` — `InputWindow.ExtendedInputWindow<StatusAreaWindow>()`

### 1.2 窗口挂载方式

`KawaiiBarComponent.kt:300-308`：

```kotlin
cursorMoveButton.setOnClickListener {
    windowManager.attachWindow(TextEditingWindow())    // :300-302
}
clipboardButton.setOnClickListener {
    windowManager.attachWindow(ClipboardWindow())      // :303-305
}
moreButton.setOnClickListener {
    windowManager.attachWindow(StatusAreaWindow())     // :306-308
}
```

**结论 ①**：三个面板都是**另起一层键盘窗口**（通过 `InputWindowManager.attachWindow()` 挂载），**不是 toolbar 同栏替换**。挂载后触发 `ExtendedWindowAttached` 事件，`KawaiiBarStateMachine` 从 Idle/Candidate 切到 Title 状态（`KawaiiBarStateMachine.kt:39-42`），Title 状态下栏显示面板标题 + 返回按钮 + `onCreateBarExtension()` 返回的扩展 View。面板内容本身占据键盘主区域（栏下方）。

退出方式：Title 状态的返回按钮调用 `windowManager.attachWindow(KeyboardWindow)`（`KawaiiBarComponent.kt:467-469`），即切回键盘窗口。`WindowDetached` 事件让状态机回到 Idle 或 Candidate（`:43-47`）。

---

## 二、光标移动面板（TextEditingWindow）

### 2.1 布局（回答 ②占多高、几个键、每键多大）

`TextEditingUi.kt` 使用 `ConstraintLayout`，布局分左右两部分：

**左侧：方向键十字 + 首尾键**
```
┌─────┬─────┬─────┐
│ ←   │  ↑  │  →  │
├─────┼─────┼─────┤
│     │选选 │     │
│     │择择 │     │
├─────┼─────┼─────┤
│ ⏮   │  ↓  │  ⏭  │
└─────┴─────┴─────┘
```
- `leftButton`（←）、`upButton`（↑）、`downButton`（↓）、`rightButton`（→）— 四向箭头
- `selectButton`（"选择"文字按钮）— 居中，带 activated 状态
- `homeButton`（⏮ 首页图标）— 跳到行首
- `endButton`（⏭ 末页图标）— 跳到行尾

**右侧：操作键列**（`matchConstraintPercentWidth = 0.3f`，约占 30% 宽度）
```
┌──────────┐
│ 全选     │
├──────────┤
│ 剪切(隐藏)│
├──────────┤
│ 复制     │
├──────────┤
│ 粘贴     │
├──────────┤
│ ⌫ 删除   │
└──────────┘
```
- `selectAllButton`（"全选"文字）— 有选择时隐藏，改为显示 `cutButton`（"剪切"）
- `cutButton`（"剪切"文字）— 默认 `View.GONE`，有选择时 `View.VISIBLE`
- `copyButton`（"复制"文字）
- `pasteButton`（"粘贴"文字）
- `backspaceButton`（⌫ 图标，altStyle）

**栏扩展**（`TextEditingUi.kt:139-141`）：
```kotlin
val clipboardButton = ToolButton(ctx, R.drawable.ic_clipboard, theme)
val extension = horizontalLayout {
    add(clipboardButton, lParams(dp(40), dp(40)))
}
```
栏右侧有一个剪贴板按钮（40dp × 40dp），点击跳转到 `ClipboardWindow`。

**键尺寸**：`TextEditingButton` 继承 `CustomGestureView`，尺寸由 ConstraintLayout 约束决定，无固定 dp。右侧列每个按钮 `matchConstraintPercentWidth = 0.3f`。方向键区域占左侧约 70% 宽度，3×3 网格中每个按钮约 23% 宽度。

**面板高度**：不写死，由 `InputWindowManager` 的布局决定（占据键盘主区域，即栏下方全部空间）。

### 2.2 长按连续（回答 ③长按是否连续、节流多少 ms）

`TextEditingWindow.kt:41-49`：
```kotlin
fun CustomGestureView.onClickWithRepeating(block: () -> Unit) {
    setOnClickListener { block() }
    repeatEnabled = true
    onRepeatListener = {
        block()
        if (hapticOnRepeat) InputFeedbacks.hapticFeedback(this)
    }
}
```

四个方向键和 backspace 键使用 `onClickWithRepeating`：
- `leftButton.onClickWithRepeating { sendDirectionKey(KEYCODE_DPAD_LEFT) }`（:51）
- `upButton.onClickWithRepeating { sendDirectionKey(KEYCODE_DPAD_UP) }`（:53）
- `downButton.onClickWithRepeating { sendDirectionKey(KEYCODE_DPAD_DOWN) }`（:55）
- `rightButton.onClickWithRepeating { sendDirectionKey(KEYCODE_DPAD_RIGHT) }`（:57）
- `backspaceButton.onClickWithRepeating { sendDownUpKeyEvents(KEYCODE_DEL) }`（:79-81）

**节流**：`CustomGestureView.repeatEnabled = true` 启用重复，节流间隔由 `CustomGestureView` 内部实现控制（不在本次拉取的文件中，需进一步查 `CustomGestureView.kt`）。`hapticOnRepeat` 是用户偏好开关，控制重复时是否震动反馈。

**非连续键**：`homeButton`、`endButton`、`selectButton`、`selectAllButton`、`cutButton`、`copyButton`、`pasteButton` 都用普通 `setOnClickListener`，不连续。

### 2.3 退出方式（回答 ④怎么退出）

- **栏返回按钮**：Title 状态下栏左侧有返回按钮，点击调用 `windowManager.attachWindow(KeyboardWindow)`（`KawaiiBarComponent.kt:467-469`），切回键盘窗口
- **无"点空白退出"**：面板占据键盘区域，没有空白可点
- **无"再点一次退出"**：面板内无此机制
- **剪贴板按钮跳转**：点栏扩展的剪贴板按钮 → `windowManager.attachWindow(ClipboardWindow())`（`TextEditingWindow.kt:84-86`），从光标面板跳到剪贴板面板

### 2.4 选择逻辑

`TextEditingWindow.kt:31-37`：
```kotlin
private var hasSelection = false
private var userSelection = false

private fun sendDirectionKey(keyEventCode: Int) {
    service.sendCombinationKeyEvents(keyEventCode, shift = hasSelection || userSelection)
}
```

- `hasSelection` — 系统报告的实际选择状态（`onSelectionUpdate` 回调，`:89-92`）
- `userSelection` — 用户点击"选择"按钮的意图状态
- 方向键发送时，如果 `hasSelection || userSelection` 为 true，则带 Shift 键（即选择式移动）
- `selectButton` 点击：有选择 → 取消选择（`cancelSelection()`）；无选择 → 切换 `userSelection`
- `selectAllButton` → `performContextMenuAction(android.R.id.selectAll)`
- `cutButton` → `performContextMenuAction(android.R.id.cut)`
- `copyButton` → `performContextMenuAction(android.R.id.copy)`
- `pasteButton` → `performContextMenuAction(android.R.id.paste)`

---

## 三、剪贴板面板（ClipboardWindow）

### 3.1 列出什么、点条目做什么（回答 ⑤）

`ClipboardWindow.kt:97-117` — `ClipboardAdapter` 回调：

| 操作 | 行为 | 源码位置 |
|---|---|---|
| `onPaste(entry)` | `service.commitText(entry.text)`；若 `clipboardReturnAfterPaste` 为 true 则切回键盘窗口 | `:112-115` |
| `onPin(id)` | `ClipboardManager.pin(id)` — 固定条目 | `:99-101` |
| `onUnpin(id)` | `ClipboardManager.unpin(id)` — 取消固定 | `:102-104` |
| `onEdit(id)` | `AppUtil.launchClipboardEdit(context, id)` — 打开编辑页 | `:105-107` |
| `onShare(entry)` | `Intent.ACTION_SEND` 分享文本 | `:108-111` |
| `onDelete(id)` | `ClipboardManager.delete(id)` + 显示撤销 Snackbar | `:116-119` |

条目布局：`StaggeredGridLayoutManager(2, VERTICAL)` — 2列瀑布流（`:131`）。

滑动删除：`ItemTouchHelper` 左滑/右滑删除（`:136-153`），删除后显示 Snackbar 可撤销。

### 3.2 三态状态机

`ClipboardStateMachine.kt`：

| 状态 | 含义 | UI |
|---|---|---|
| `Normal` | 有剪贴板条目 | RecyclerView + 删除全部按钮 |
| `AddMore` | 监听已启用但数据库空 | "添加更多"提示 |
| `EnableListening` | 监听未启用 | "启用监听"按钮 |

### 3.3 栏扩展

`ClipboardUi.kt:56-58`：
```kotlin
val deleteAllButton = ToolButton(ctx, R.drawable.ic_baseline_delete_sweep_24, theme)
val extension = horizontalLayout {
    add(deleteAllButton, lParams(dp(40), dp(40)))
}
```
栏右侧有"删除全部"按钮（40dp × 40dp），仅在 Normal 状态可见。

### 3.4 剪贴板数据来源

`ClipboardManager`（`org.fcitx.fcitx5.android.data.clipboard.ClipboardManager`）维护剪贴板历史数据库（Room DB），需要 `clipboardListening` 偏好开启。这是 fcitx5-android **自己的剪贴板监听+存储**，不是系统剪贴板 API。

**关键差异**：我们的鸿蒙版**不做剪贴板历史面板**（H-165 §七，撞闸门⑧ READ_PASTEBOARD）。我们的 `ClipboardPad` 只做"粘贴当前系统剪贴板内容"（调 `sendExtendAction(PASTE)`），不做历史列表。

---

## 四、··· 菜单（StatusAreaWindow）— 任务 D 证据

### 4.1 列出哪些项

`StatusAreaWindow.kt:60-81` — 4 个静态条目 + 动态 fcitx 条目：

**静态条目**（`StatusAreaEntry.Android`）：

| 标签 | 图标 | 类型 | 点击行为 |
|---|---|---|---|
| 主题 | `ic_baseline_palette_24` | `ThemeList` | `AppUtil.launchMainToThemeList(context)` — 跳到主 app 主题列表页 |
| 输入法选项 | `ic_baseline_language_24` | `InputMethod` | `AppUtil.launchMainToInputMethodConfig(context, uniqueName, displayName)` — 跳到主 app 输入法配置页 |
| 重新加载配置 | `ic_baseline_sync_24` | `ReloadConfig` | `fcitx.reloadConfig()` + Toast "完成" — 重载 fcitx5 配置 |
| 虚拟键盘 | `ic_baseline_keyboard_24` | `Keyboard` | `AppUtil.launchMainToKeyboard(context)` — 跳到主 app 键盘设置页 |

**动态 fcitx 条目**（`StatusAreaEntry.Fcitx`）：

由 `fcitx.statusArea()` 返回的 `Action[]` 动态生成（`:168-171`）。每个 `Action` 有：
- `shortText` — 显示标签
- `icon` — 图标名（fcitx 内部命名，映射到 Android drawable）
- `isChecked` / `active` — 是否激活态
- `menu` — 子菜单（有的话点击弹出 `PopupMenu`）

常见动态条目（来自 `StatusAreaEntry.kt:30-46` 的图标名映射）：

| fcitx 图标名 | 对应功能 | Android 图标 |
|---|---|---|
| `fcitx-chttrans-active/inactive` | 简繁转换开关 | 繁体/简体图标 |
| `fcitx-punc-active/inactive` | 标点符号开关（中/英标点） | 标点激活/非激活图标 |
| `fcitx-fullwidth-active/inactive` | 全角/半角开关 | 全角激活/非激活图标 |
| `fcitx-remind-active/inactive` | 联想词开关 | 联想激活/非激活图标 |
| `tools-check-spelling` | 拼写检查 | `ic_baseline_spellcheck_24` |

### 4.2 布局

`StatusAreaWindow.kt:155-161`：
```kotlin
context.recyclerView {
    layoutManager = gridLayoutManager(4)  // 4列网格
    adapter = this@StatusAreaWindow.adapter
}
```

4 列网格 RecyclerView，每个条目有图标 + 标签。有子菜单的条目点击弹出 `PopupMenu`（`:92-130`）。

### 4.3 栏扩展

`StatusAreaWindow.kt:163-176`：
```kotlin
private val barExtension by lazy {
    context.horizontalLayout {
        if (editorInfoInspector) {
            add(editorInfoButton, lParams(dp(40), dp(40)))  // 编辑器信息（调试用）
        }
        add(settingsButton, lParams(dp(40), dp(40)))  // 设置按钮
    }
}
```
栏右侧有设置按钮（始终显示）和编辑器信息按钮（仅调试模式）。

---

## 五、对我们组件实现的指导

### 5.1 CursorPad（任务 B）

基于上游证据，我们的 `CursorPad` 应包含：
- **四向箭头**（上/下/左/右）— 调 `keyboardController.moveEditorCursor(1/2/3/4)`
- **按住连续** — 上游用 `CustomGestureView.repeatEnabled`，我们用 ArkTS 定时器实现（建议 120ms 一步）
- **不需要** home/end/select/selectAll/cut/copy/paste/backspace — 上游的 TextEditingWindow 是完整文本编辑面板，Qoder 只要求四向箭头

### 5.2 ClipboardPad（任务 B）

基于上游证据 + 我们的约束：
- **"粘贴当前内容"按钮** — 调 `keyboardController.sendEditorAction(inputMethodEngine.ExtendAction.PASTE)`
- **"历史"行置灰** — 写明"需要宿主应用自己申请 READ_PASTEBOARD"，不做假按钮
- 上游的剪贴板历史功能依赖 fcitx5-android 自己的 `ClipboardManager` + Room DB，我们**不做**（闸门⑧）

### 5.3 尺寸约束

- 整层高度由外部传入的 `height` 决定（竖屏 `candBarHeight()` 44vp，横屏 24vp）
- 宽度可横向滚动
- 组件内不许写死高度

---

## 六、源码文件清单

| 文件 | 包路径 | 行数 | 关键内容 |
|---|---|---|---|
| `TextEditingWindow.kt` | `input.editing` | 97 | 光标面板窗口，按钮事件绑定，选择逻辑 |
| `TextEditingUi.kt` | `input.editing` | 141 | ConstraintLayout 布局，4向+选择+操作列 |
| `TextEditingButton.kt` | `input.editing` | 116 | 按钮组件，继承 CustomGestureView，支持 repeat |
| `ClipboardWindow.kt` | `input.clipboard` | 192 | 剪贴板面板窗口，Adapter 回调，三态状态机 |
| `ClipboardUi.kt` | `input.clipboard` | 68 | ViewAnimator 三态切换，RecyclerView 2列瀑布流 |
| `ClipboardStateMachine.kt` | `input.clipboard` | 55 | Normal/AddMore/EnableListening 三态 |
| `StatusAreaWindow.kt` | `input.status` | 178 | ··· 菜单窗口，4静态+动态条目，4列网格 |
| `StatusAreaEntry.kt` | `input.status` | 67 | 条目数据类，Android/Fcitx 两种，图标映射 |
| `InputWindow.kt` | `input.wm` | 78 | 窗口基类，Simple/Extended 两种，动画/生命周期 |
| `KawaiiBarComponent.kt` | `input.bar` | 548 | 栏组件，按钮→attachWindow，状态机切换 |

所有文件许可证：LGPL-2.1-or-later，仅参考思路不复制代码。