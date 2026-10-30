# 鸿蒙端 vs 安卓三生 · 键盘功能逐项对照

> Qoder，2026-10-25 16:2x。依据：安卓实物截图 `docs/evidence/2026-10-25/h165-android-toolbar/s_toolbar.png`（nova6 三生 APK，键盘全景）与 `k1_toolbar.png`（工具栏展开态），以及 nova6 真机实测表（H-155，源自 APK 内 `org.fcitx.fcitx5.android.input.popup.PopupPreset`）。
> 主人 2026-10-25 16:5x 原话：「继续吧，对照安卓各功能，抄他」。
> **口径**：能自己真机验的自己做；必须主人拍板的挂起；**不做假按钮**（H-165 §七）；不申请新权限（会撞内容闸门 ⑧）。

## 一、逐项对照表

| # | 安卓行为（实测） | 鸿蒙现状 | 结论 |
|---|---|---|---|
| 1 | 候选栏上方一行显示「编码 · 词性注释」（`hao` → `好 [vb]`） | L1 `commentLine()` 显示 `preedit · comment`，真机实测 `nihao · [wqvb]` | **已抄**（H-178：注释改为跟随连续滚动切片，此前读旧切片会与屏上候选脱节） |
| 2 | 候选行横排、可左右滑 | H-164 连续横向滚动 `List`（主人点头） | **已抄** |
| 3 | 候选行最右 `▾` 展开候选网格、多屏可上下滑翻页 | H-168 已做（7 屏、末屏可达、`animateTo` 过渡） | **已抄** |
| 4 | 工具栏 `‹ 撤销 重做 移动光标 剪贴板 … ▾`（七枚满宽等距，中心 5.4%…94.4%，同为深藏青 #17203A） | H-176/H-177 图标行同构＋撤销/重做/光标真功能；**H-179 换成系统符号**（`undo`/`redo`/`arrow_left_arrow_right`/`text_clipboard`），行改 `SpaceBetween`＋左右 2vp ⇒ 七枚中心推算 5.5%…94.6%，色改 `FG_TOOLBAR=#17203A` | **已抄**（剪贴板仍置灰，见 §二.1；符号名核验见 §三） |
| 5 | 长按字母键弹符号气泡（数字/大写/变音） | H-155 `HIDDEN_SYMS` 逐键对齐 nova6 实测 | **已抄** |
| 6 | 长按 a/x/c/v ＝ 全选/剪切/复制/粘贴 | 已接（`sendEditorAction`） | **已抄** |
| 7 | 退格上滑删到上一标点、下滑撤销 | H-175 已接，真机 dy=32.3 清空／dy=32.6 恢复 | **已抄** |
| 8 | 字母键上滑出次级字符（q→1）、下滑出大写 | H-154/H-165 已接，真机验过 | **已抄** |
| 9 | 底栏 `?123 / 表情 / 语言 / Rime(五) / 回车` | 底栏 `?123 / 表情 / 简英 / 空格(三生) / . / 回车` | **部分**，见 §二.2 |
| 10 | 空格位那颗显示**当前方案名**（`Rime(五)`），可切方案 | H-178 已接读取链路，空格位显示「五笔/九键/拼音」，真机来回切验过（`s1_bottom.png`／`t9ok_bottom.png`／`t9back_bottom.png`） | **已抄**（点击仍只出空格，切方案走 `简英` 与设置，见 §二.2） |
| 11 | 九宫格（T9）布局与分词 | 已做（`T9Panel`，长按语言键切 26键/九键） | **已抄** |
| 12 | 剪贴板历史面板（最近 N 条） | 未做 | **未做**，见 §二.1 |

## 二、未做项与卡点（诚实记录）

### 1. 剪贴板历史面板
- **卡点**：要 `ohos.permission.READ_PASTEBOARD`，而内容闸门 `scripts/check_app_content.py` ⑧ 断言权限**恰为** `['ohos.permission.VIBRATE']`；且「单机应用」上架口径明确不上网、不扩权。
- **现状**：工具栏那枚置灰＋点了 toast「还没做」，不做静默假按钮。
- **能做且不扩权的部分**：「粘贴当前剪贴板」早已有（长按 v → `sendEditorAction(PASTE)`），历史面板才是要权限的那个。
- **结论已请 CodeArts 拍板**（M-209⑤）：做/不做＋理由，不擅自决定。

### 2. 底栏「当前方案名」＋方案切换
- 安卓那颗 `Rime(五)` 显示当前方案、点击/长按可切方案；我们空格位固定「三生」。
- **卡点**：引擎侧只有 `selectSchema(id)`，**没有「读取当前 schema 名」的接口**（`RimeEngine.ets`/`RealRimeEngine.ets` 只有 `getOption`）。要显示当前方案名，得在 `entry/src/main/cpp/fanxing_napi.cpp` 加一个 napi 绑定（`getSchemaId` 之类），再在 ArkTS 侧接。
- **不在本轮做**：动 cpp＋napi 的面比 UI 大，且改完要重新真机验整条链；本轮先把 UI 侧能抄的抄完。
- **建议做法**（留给下一轮或 CodeArts）：napi 加 `getSchemaId()` → ArkTS `KeyboardController.getSchemaId()` → 空格键文案改 `this.schemaLabel()`（五笔/拼音/英文），长按弹方案菜单（复用现有长按语言键那套菜单几何）。

## 三、本轮真机实证（Mate80，signed 28,379,523 B）

| 判据 | 结果 |
|---|---|
| H-178 反查注释跟随滚动 | L1 显示 `nihao · [wqvb]`，与屏上第一条候选「你好」对应（`cm1_bar.png`） |
| H-177 撤销 | `H-177 undoCommit: removed 2 chars, redo depth 1` ⇒「你好」消失 |
| H-177 重做 | `H-177 redoCommit: restored 2 chars` ⇒「你好」回来 |
| H-177 光标 | `H-177 moveEditorCursor dir=3 ok`，无抛错 |
| H-175 退格上滑/下滑 | `clearToLastSeparator dy=32.3`／`undoLastAction dy=32.6` |
| H-168 网格多屏+末屏 | `off=40->42 screen=6/7`，末屏可达 |
| H-176 工具栏形态 | `‹ 撤销 重做 光标 剪贴 ··· ▾`（`u4_bar.png`），右上角网格三角未失踪 |

## 三、H-179 工具栏图标：符号名怎么核实的（不猜）

2026-10-25 一天内同一类错犯了三次（回车冒充撤销、三枚落到同一个 chevron_down、`Text('▶')` 被 emoji 字体渲染），
全是「凭感觉写符号名」+ 只在真机才看得见。H-179 换成两条独立离线证据，再上机。

| 功能 | 系统符号 | 证据① SDK 资源表 `sysResource.js` symbol 节（共 4043 名） | 证据② 编译产物 `modules.abc` 里该资源 id 命中次数 |
|---|---|---|---|
| 撤销 | `sys.symbol.undo` | 在表中 | id 125831265 × 1 |
| 重做 | `sys.symbol.redo` | 在表中 | id 125831266 × 1 |
| 移动光标 | `sys.symbol.arrow_left_arrow_right` | 在表中（系统符号**没有 I 型光标**，取语义最近：点击动作就是左右移光标） | id 125831296 × 1 |
| 剪贴板 | `sys.symbol.text_clipboard` | 在表中 | id 125831925 × 1 |
| 收起 ‹/▼ | `sys.symbol.chevron_up` / `chevron_down` | 在表中 | id 125832665 × 4 / 125832666 × 3 |

- 证据①口径：`<SDK>/openharmony/ets/build-tools/ets-loader/sysResource.js` 是编译器认的**权威**名字表；
  名字不在表里 hvigor 的报错不直观（有时只是运行时空白），所以做成闸门 `scripts/check_symbol_names.py`。
- 证据②口径：名字若拼错，ArkTS 会把它解析成 0/空而不是真 id；逐个 `struct.pack('<I', id)` 在 `modules.abc`
  里数命中，四个各 1 次 ⇒ 名字真的落到了资源 id。
- **仍未证**：字形在真机上的观感（大小/粗细/与安卓是否神似）。这条只能截图看，等设备连上补证据。

### 证据③ 字形长得对不对（离线渲染，不靠猜）

用 `fontTools` 读 `HMSymbolVF.ttf` 的 cmap 反查 codepoint，再用 PIL 把候选字形画成图（`docs/evidence/2026-10-26/symbol-shapes.png`）：

| 名字 | 画出来是什么 | 与安卓实物比 |
|---|---|---|
| `undo` | 弯箭头向左（↩） | 与安卓第二枚一致 |
| `redo` | 弯箭头向右（↪） | 与安卓第三枚一致 |
| `text_clipboard` | 带夹子的剪贴板 | 与安卓第五枚一致 |
| `arrow_left_arrow_right` | 两条水平箭头（⇄） | 安卓第四枚是**I 型竖线＋左右箭头**，系统符号里没有 I 型 ⇒ 取语义最近的 ⇄ |
| `move` / `position` | 四向移动箭头 / 十字准星 | 形状都不是光标，不用 |

另渲染了 10 个「可能像光标」的候选（`cursor-candidates.png`：`text_and_arrow_up_and_down`、`text_arrow_up_and_down`、`arrow_up_and_down_square_portrait`、`input_mode`、`input_set`、`arrow_left_to_line`、`half_dash_rectangle_and_line_vertical`、`short_vertical_line` 等），**没有一个是 I 型竖线**（分别是「文本行＋上下箭头」「输入框图标」「竖线」）。⇒ 光标这枚就用 ⇄，等真机看观感再定要不要手绘复合图标。
