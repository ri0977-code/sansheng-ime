# 设置页契约（H-239 起 · Qoder 起草 2026-10-28 02:0x · CodeArts 在下方「接手区」追加）

> **为什么先写契约再写代码**：H-090 那次是两个人各写各的，结果设置页摆了 **71 项、实测 0 项生效**
> （取证 `docs/evidence/2026-10-22/h090-settings-entry-recheck.md:43-97`），主人 10-22 因此拍 **D-021
> 「只留真实生效的项」**并把入口整段摘掉。今晚主人重新点单要做设置页 ⇒ **本轮唯一硬规矩＝
> 每一项都必须「有 prefKey ＋ 键盘侧有读取点 ＋ 改完屏上有可量的变化」三条齐全，缺一条就不许出现在页面上**。
> 这份文件是 Qoder／CodeArts 的**共同接口**，不是散文：键名、类型、默认值、读取点、判据都以这里为准。

## 0. 主人的原话与本文件的口径

- 主人 2026-10-28 01:4x 原话：「完善设置菜单，参考安卓版，让长按空格，或者回车键，调出设置页面，
  里面的功能参考安卓里的，键盘调节啊，字体设置啊，什么什么的」＋「和 codearts 配合，两个一块分工干」。
- 「参考安卓」的**实测参照**（不是我的想象，来源 `F:\dshdesktopwork\sansheng-ime-android\_emulator_runs\apktool\main\`
  的 `strings.xml` 与 `smali/org/fcitx/fcitx5/android/data/prefs/AppPrefs$*.smali`，逐屏文案见
  `F:\qoderwork\sansheng-ime-harmony\tmp-androidwalk\walk2\1-fcitx.xml`／`2-global.xml`）：
  安卓**没有**「键盘调节」「字体设置」这两个字面名字，对应物是 **「虚拟键盘」页＋「候选窗口」页＋「主题」页**；
  本页分类标题按安卓那两个页名，**不发明安卓没有的分类**。
- **安卓也没有「长按空格/长按回车打开设置」**（`SpaceLongPressBehavior` 枚举只有 无/轮换/切换语言/选择框，
  回车没有同类设置项）。⇒ 这条入口是**主人的设计**，不是安卓口径；照他这句话做，台账里如实写清「安卓无此入口」，
  以后别有人拿「参考安卓」把它当成抄来的东西去改回去。
- 安卓**有**的入口我们也一并做：工具栏「···」里加一枚「设置」（对应安卓 `StatusAreaWindow` 的
  `RUN`＋`EXTRA_SETTINGS_ROUTE` 深链）。

## 1. 架构决定（含两处「为什么不那么做」，写给以后的人）

**① 设置 UI 画在键盘面板内的顶层覆盖层**（复用 H-213/H-215 已真机验过的通路：
`KeyboardIndex.ets` `build()` 顶层 `Stack` ＋ scrim，`FuncMenu` 就是这个形态）。

- **不走 `startAbility` 拉起 App 的 `SettingsPage.ets`**：官方文档写明输入法扩展受「**输入法安全模式**」管制
  ——「基础模式下，输入法扩展（InputMethodExtensionAbility）进程无法拉起其他 UIAbility 或 ExtensionAbility」
  （[IME 安全模式](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ime-kit-security)），
  只有「完整体验模式」可以（`InputMethodExtensionContext.startAbility` 是 API 12+ 的正解）。
  默认落在基础模式 ⇒ **拿它当唯一通路＝给主人留一个「点了没反应」的按钮**（H-207/H-224 同类的假承诺）。
- **不走 `window.createWindow` 子窗口**：官方明确「输入法面板不支持创建子窗口……不支持 `window.createWindow`」
  （[inputMethodEngine](https://developer.huawei.com/consumer/cn/doc/harmonyos-references/js-apis-inputmethodengine)）⇒
  浮层只能画在面板自己那棵树里。**H-213 的死线仍然有效：内容超出 IME 窗口会被静默裁掉**
  （面板高＝`PORTRAIT_BAR_VP(44) + ROW_COUNT(4)×PORTRAIT_ROW_VP(48) = 236vp`，`KeyboardController.ets:19-23`），
  所以设置页**必须自带滚动**、且首屏条目要在 236vp 内点得到。

**② 存储＝输入法进程内的 `@ohos.data.preferences`**（新建 `entry/src/main/ets/common/SettingsStore.ets`）。

- 依据：[进程模型](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/process-model-overview)
  「输入法组件是运行在独立进程中的」＋安全模式文档「输入法扩展使用独立沙箱，与应用主入口不可互相访问对方的独立沙箱」
  ⇒ **App 侧那份 `sansheng_prefs` 键盘根本看不见**。想让两侧共享，官方只给一条路：申请 `dataGroupId`
  （首选项 `Options.dataGroupId` 原文「只支持三方应用中输入法和输入法的扩展场景使用」），
  需要改 `module.json5`＋重出 profile＋重签 ⇒ **登记成 H-243 等主人点头（要动 AGC 控制台，我替他做不了）**。
- 现有 `SettingsModels.ets` 那 71 个 `prefKey` 声明**不删**（H-129「证明、记录、留着」），但**一个都不许出现在页面上**，
  除非它进了本文件的契约表。

**③ 生效判定＝当场读、当场重绘**：键盘侧读取点统一走 `SettingsStore` 的同步缓存
（`onCreate`／`panel.on('show')` 时 reload，写侧立刻 `flush()`＋`@StorageLink` 驱动重绘），
**不要求重启输入法**（依据：`Panel` 有 `setUiContent`／`on('show')`，`InputMethodAbility` 有 `on('inputStart')`，
`inputStart` 不是进程重启）。

## 2. 分工（谁写哪个文件，写了就别人碰）

| 半区 | 文件 | 内容 |
|---|---|---|
| **Qoder** | `entry/src/main/ets/pages/KeyboardIndex.ets`（只动「入口＋读取点」两类行） | 长按空格／长按回车开设置；「···」菜单加「设置」；键高/字号/每页条数/震动/长按延迟/气泡/网格条数/划动步长的**读取点** |
| **Qoder** | `entry/src/main/ets/inputmethod/KeyboardController.ets` | `computePanelSize()` 读键盘高度百分比；撤销栈上限；横屏系数 |
| **Qoder** | `entry/src/main/ets/engine/RealRimeEngine.ets` | `setPageSize` 按每页候选数 |
| **Qoder** | `scripts/settings_effective_check.py`（新建守卫） | 三条齐全判据：prefKey 注册＋读取点＋真机可量；含已知坏样本自测 |
| **Qoder** | 真机取证＋构建＋自签＋装机（无密码，我自己装） | 每项改前/改后像素与 hilog |
| **CodeArts** | `entry/src/main/ets/common/SettingsStore.ets` | 存储层（**我 02:0x 先落一版可编译的**，接口签名见 §4，你接手时**只许加方法、不许改签名**） |
| **CodeArts** | `entry/src/main/ets/pages/SettingsPanel.ets`（新建） | 设置页 UI：分类＝「虚拟键盘」「候选窗口」两页签（照安卓页名），控件照 §3 表；**不许新增表外条目** |
| **CodeArts** | `entry/src/main/ets/common/SettingsModels.ets` | 把表内 12 项的文案/范围/默认对齐本契约；表外项标 `enabledInPanel: false`（不删） |
| **CodeArts** | `docs/HANDOFF.md`、`docs/ISSUES.md` 追加 | 他名下的台账 |

> 交界面只有一个＝§4 的 `SettingsStore` 签名 ＋ §3 的键名。**双方都不许改键名**；
> 要改先在本文件「变更记录」里写一行并通知对方。

## 3. 条目契约（第一批 12 项；「读取点」全部是当场读代码量出来的行号）

> **⚠ 2026-10-28 03:4x（Qoder）判据 r3**：下表 §3-1/2/4/6/7/8/9/10/12 那几格的「生效判据」列
> 是 02:3x 写的，**真机跑出来有 6 处量不到/量错**（原因与实测数见 §3.1 和
> `docs/evidence/2026-10-28/h239-settings-*/verdict-r*.txt`）。**两处不一致时以 §3.1 为准**；
> 旧文案不删，是为了让接手的人知道为什么改过，不要照旧文案实现。

| # | prefKey | 页面文案 | 控件与范围 | 默认 | 现值出处（读取点） | 生效判据（我能量的那条） |
|---|---|---|---|---|---|---|
| 1 | `kbd_height_pct` | 键盘高度百分比 | 滑条 80–120（%） | 100 | `KeyboardController.computePanelSize()`：行高 = `PORTRAIT_ROW_VP(48)`／`LANDSCAPE_ROW_VP(34)` × pct ÷ 100（**顶栏 44vp 不乘**，否则 H-096 横屏判据会漂） | hilog `H-241 applySettingsChanged: row=…vp` ＋ `relayout resize WxHpx`；WMS `SCBKeyboardPanel` 矩形高度变化 ≥ ±6%，末行键不被裁（H-213 死线） |
| 2 | `cand_font_size` | 候选词字号 | 滑条 14–22（vp） | 18 | `KeyboardIndex.ets` `candFontSize()`：`candFsUser>0 ? candFsUser : candFs`（**用户没定过 ⇒ 沿用 H-077 宽度自适应档**，否则今天这版会把没进过设置页的人的键盘也改了） | 候选行**字形高度 px** 变。**行高故意不跟着长**（`candRowHeight()` 仍吃自适应档 `candFs`）：面板窗高恒 236vp（H-208），字号一涨行高就涨 ⇒ 末行键被静默裁（H-213 那一类事故）。**接手的人别把它改回「行高跟字号」** |
| 3 | `key_font_size` | 键面字母字号 | 滑条 16–26（vp） | 20 | `KeyboardIndex.ets:3031 LetterKey()` 内 `:3035 .fontSize(20)`；九键 `T9Key` 的 `:3474` **同一个值**（两处都要走读取点，漏一处＝那半键盘不变） | 字母字形高度 px 变、键帽不溢出、九键与全键盘同步 |
| 4 | `page_size` | 每页候选词数 | 单选 3/5/7/9 | 竖 5 · 横 9 | `RealRimeEngine.ets:9,11` 常量＋`applyOrientation()` 里 `isUserSet('page_size')` 分流；`KeyboardIndex.recomputePageSize()` 同一来源 | **三处必须同一个值**：① hilog `setPageSize=n`／`UI pinned`；② 候选条数＝n 才续页（H-096 判据现成）；③ 展开网格每竖排行数。用户没定过时横屏仍拿 H-035 的 9 |
| 5 | `kbd_haptic` | 按键时振动 | 开关 | 开 | `KeyboardIndex.ets:1356-1365`（20ms＋50ms 节流） | 关掉后 hilog 里 0 条 vibrate 调用（读取点加一条日志），屏上不抖 |
| 6 | `key_long_press_delay` | 长按触发时长 | 滑条 300–700（ms） | 450 | `KeyboardIndex.ets` 出泡 `setTimeout(..., this.longPressDelayMs)` ＋兜底 `LongPressGesture({duration: this.longPressDelayMs})` **两处同一个镜像值** | 现成时间戳钩子＝hilog `H-215 timer open bubble <ch>`：它的时刻减 Down 的时刻≈设定值。定值 300 ⇒ 注入长点**出泡**；定值 700 ⇒ 同一次注入**不出泡**（注入工具松手早于阈值）——差分成立即证明阈值真被读 |
| 7 | `popup_on_key_press` | 按键时弹出字符 | 开关 | 开 | 出泡两处（`KeyboardIndex.ets:3100` 计时器／`:3209` 手势兜底，H-215 定稿） | 关掉后长按不渲染气泡（复用 `scripts/h216_bubble_order_check.py` 的判据） |
| 8 | `undo_stack_limit` | 可撤销步数 | 数字 5–30 | 10 | `KeyboardController.ets:70` `UNDO_STACK_LIMIT=10` | 连打 12 段候选 ⇒ 只能撤销到第 N 段（N＝设定值），hilog `pushUndo size=` 封顶 |
| 9 | `grid_page_size` | 展开网格每页条数 | 滑条 20–80 | 50 | `KeyboardIndex.ets:212` 全量网格 50 | 屏上网格条数＝值；末屏不空转（H-168 判据） |
| 10 | `space_swipe_step` | 空格划动移光标步长 | 滑条 5–20（**vp 手指位移 / 一格光标**） | 10 | `KeyboardIndex.ets` `spaceSwipeConsume()` 里 `this.spaceStepN`（常量 `SPACE_CURSOR_STEP=10vp` 只作兜底） | 同一段划动，hilog `H-180 space swipe ... step=N` 的**条数**按 `10/N` 成反比变。**单位是 vp 不是「字符」**：安卓同项也是「滑多少距离挪一格」 |
| 11 | `expand_toolbar_by_default` | 默认展开工具栏 | 开关 | 关（＝现状） | `KeyboardIndex.ets` `syncFromSettings()` 单次读＋`expandDefaultOn` 镜像；**只在真的翻转时**动工具栏 | 当场生效：hilog `H-241 expand_toolbar_by_default flipped -> true` ＋顶栏图标行像素；重新调起键盘后仍按值 |
| 12 | `show_preedit` | 显示编码行 | 开关 | 开 | `KeyboardIndex.ets` L1 渲染分支（竖屏/横屏两处都判 `preeditShown`） | 关掉后编码文字**消失**（屏上量：编码行区域像素无字）；**那 16vp 不会被候选行拿回**——面板窗高恒 236vp，改的是「画编码」还是画一条同高占位行。写成「拿回」是错的，会诱使接手的人去动高度预算（H-208/H-213） |

### 3.1 判据 r3 更正（2026-10-28 03:4x，Qoder，全部来自 Mate 80 真机实测）

量具：`scripts/h241_settings_items.py`（逐项改前/改后）＋ `scripts/h241_diag_bubble.py`（出泡诊断）。

**先记一条几何事实**（这条把三项判据带崩过，别再按旧口径算）：打字态屏上从上到下是
`L1 编码行(实测 y≈1836..1857) → 候选行(≈1888..1948) → 四行键(键帽顶≈1990)`，
**那 44vp 是候选栏容器本身**（L1 16vp ＋ 候选 28vp），它上面**没有**一排 44vp 顶栏；
工具栏展开时（§3-11）整排图标把这一块**整个占掉**（实测 `02-bar-after-flip` 那一帧候选消失）。
⇒ 任何「窗顶 + 44vp 才是候选行」的算法量到的都是空白。r3 起 **候选带/L1 带一律从截图自动检出**
（`_bands()`，两帧用同一带才可比）。

**再记一条同量级的硬事实（r4，抓到的是我自己的回归）**：面板顶层那棵树的内容区实测就是 **236vp**
（hilog `SSKeyboardIndex H-215 root area win? x=0 y=0 w=365.7142857142857 h=236`），
`···` 功能菜单在 6 行时代是 234vp（＝H-213 把行高从 36 收到 32 换来的，刚好贴着上限）。
我在 H-241 里给它加了第 7 行「设置（键盘与候选）」⇒ 268vp，**超窗 32vp**，Stack 居中就是上下各裁 ~16vp，
末行只剩半截、点不到。**任何往这个菜单里加行的改动（含 H-227 计划补的 5 个开关）都必须自带滚动**，
现行修法＝外壳定高（92%≈217vp）＋内层 Scroll，圆角/背景/阴影留在外壳，照 `SettingsPanel.ets:213` 那条已真机验过的通路。

| 项 | r3 判据（替换 §3 表里那格） | 为什么要换（实测） |
|---|---|---|
| §3-1 `kbd_height_pct` | hilog `H-241 applySettingsChanged: row=57.6vp`（**必须等于 48×pct÷100**）＋ WMS 面板窗高随之变 ＋ 末行键仍可量到暗像素。改前**不需要** row 日志：run-all 开跑前先点「恢复默认」，默认即 48vp/窗高 983px=236vp | 旧写法只说「row=…vp」，没钉住 57.6 这个期望值 ⇒ 值没进去也可能「有日志就算对」 |
| §3-2 `cand_font_size` | 在**同一自动检出带**里比 18vp/22vp 两帧：暗像素、字高、字宽至少一项涨且 ink ≥1.1×；第二帧自己检出的带与第一帧起终点差 ≤8px（＝行高没跟字号涨） | 旧判据只要「字高变大」，而带算错时两帧都是 0 ⇒ 永远未达判据（假阴性） |
| §3-4 `page_size` | hilog 取数用 `setPageSize[=(](\d+)`，**UI 侧是 `setPageSize(9)`**（`KeyboardIndex.ets:1165`）、引擎侧才是 `setPageSize=50`；判据＝设到 9 后序列里真出现 9 | 旧判据写死 `setPageSize=` ⇒ UI 侧那条永远匹配不上，报「没有 setPageSize 行」 |
| §3-6 `key_long_press_delay` | **同一支注入笔下比「出泡 → 松手」的时长差**：阈值 300 比 700 应长 ~400ms（两个时间戳同一时钟，不受偏移影响）。出泡口径＝`LetterKey longpress <ch> -> bubble` ∪ `H-215 v7 bubble` ∪（保留）`H-215 timer open bubble` | ① 旧判据盯的 `H-215 timer open bubble` **历史上一次都没出现过**（注入走的是兜底 `LongPressGesture` 那条，日志串不同）；② 「700ms 不出泡」注入根本做不出来——`uitest longClick` 实测持按 ≈**1.4s**（出泡→松手 950ms ＋ 阈值 450ms），比阈值上限 700 还长，700 也必出泡 |
| §3-7 `popup_on_key_press` | 阈值固定 300ms 下：关 ⇒ 出泡日志 0 条；开 ⇒ ≥1 条。**像素侧不作判据** | 注入是同步的：`longClick` 返回时手指已抬起、泡当场散（实测 `H-215 cancel q` 在出泡后 950ms），截图量到的是松手之后 ⇒ 「按住看得见泡」这一条只能主人真手（§5-5） |
| §3-8 `undo_stack_limit` | hilog `applySettingsChanged: … undoLimit=6`（默认 10）＝值进了控制器；行为侧（连打 N+2 段只撤 N 段）注入量不出 ⇒ 本项**最多记 PART**，不算全绿 | 旧判据写 `pushUndo size=` 封顶，那条日志在 `KeyboardController` 里并不存在 |
| §3-9 `grid_page_size` | 展开网格时 `setPageSize` 序列**默认不含 20、设后含 20** | 上一版只要求「两次 hilog 文本不同」，两条都是 50 也算 PASS ⇒ **假阳性**，比未达判据更坏 |
| §3-10 `space_swipe_step` | 条数按 10/step 成反比 **且日志里 `step=` 自己从 10 变 5** | 光比条数会把「划动没注入成功」也判成生效/不生效；`step=` 才是设置进去的铁证 |
| §3-12 `show_preedit` | 用**自动检出的 L1 带**比三帧（开/关/再开）暗像素：关掉后 <1/3、再开恢复；**候选带起终点三帧差 ≤8px**（＝那 16vp 画的是同高占位行，没被候选拿回）。**r4 补：量带内暗像素的阈值必须等于检带阈值 170** | 同 §3-2：旧带是硬算的，三帧全是 0。r4 又栽一次——带检到了（`[8,1870,630,1891]`）却量到 `开=0 关=0 再开=0`：**L1 编码行的字是浅灰**（背景 243、笔画均值落在 120..170 之间），而 `ink_stats` 默认阈值 120 把笔画全当背景。改回 170 后**同一批已落盘帧**实测 **585 / 0 / 585** ＝产品一直是好的（候选行的字是深灰，<120 有 7570 个，所以 §3-2 沿用 120 无碍） |

**这轮明确不做的（照 D-021，别有人去补空壳）**：
- **按键音**（`sound_on_keypress`）：包里没有任何音频资源，做了就是空开关 ⇒ 不上页面，登记 H-244。
- **主题/皮肤**（安卓「主题」页＝24 个颜色字段的 JSON）：我们键面颜色是 `KeyboardIndex.ets` 里的一族常量，
  换成可调＝整轮 UI 回归 ⇒ 单独开单（H-245），不进今晚。
- **剪贴板历史上限／表情肤色／横屏独立系数／滑行输符号**：安卓有、我们**当前没有对应的真实实现或入口** ⇒ 不做假开关。
- **App 侧那份 `SettingsPage.ets`/`SettingsCategoryPage.ets`**：本轮不复活、不注册路由（路由文件 `main_pages.json` 归 CodeArts，
  等 H-243 的 `dataGroupId` 有结论再动，避免又造一个「改了键盘不读」的第二真相源）。

### 3.2 真机收口 r5/r6（2026-10-28 05:1x，Qoder，Mate 80 `7GL0226408083897`，装机版）

**装机**：`build.ps1` → `sign.ps1` → `install.ps1` 一轮。unsigned `28,468,870 B`／signed
**`28,592,326 B`**（上一版 02:2x 是 `28,593,375 B`，差 −1,049 B ＝ `FuncMenu` 改定高壳＋Scroll、
`onFuncIcon('more')` 加一条日志）。装机一次过（无密码）。**收口后设备已「恢复默认」回 100%／48vp。**

**12 项终局**（每项改前/改后各量一次，目录带键名、同名不覆盖）：

| # | prefKey | 终局 | 最新取证 | 钉住的那个数 |
|---|---|---|---|---|
| 1 | `kbd_height_pct` | **PASS** | `h239-settings-kbd_height_pct/verdict-r6.txt` | 设 120 ⇒ `row=57.6vp`（＝48×120÷100）、WMS 窗高 983→1117px（+13.6%） |
| 2 | `cand_font_size` | **PASS** | `…cand_font_size/verdict-r3.txt` | 同一检出带 ink +3103（行高不动） |
| 3 | `key_font_size` | **PASS** | `…key_font_size/verdict-r7.txt` | 键面字形 ink +314、字高 +10px |
| 4 | `page_size` | **PASS** | `…page_size/verdict-r3.txt` | `setPageSize` 序列出现 9 |
| 5 | `kbd_haptic` | **PASS** | `…kbd_haptic/verdict-r3.txt` | 关掉后只报 skip、0 次 vibrate |
| 6 | `key_long_press_delay` | **PASS** | `…key_long_press_delay/verdict-r3.txt` | 300 比 700 晚松手 405ms |
| 7 | `popup_on_key_press` | **PASS** | `…popup_on_key_press/verdict-r3.txt` | 关 ⇒ 出泡 0 条／开 ⇒ ≥1 条 |
| 8 | `undo_stack_limit` | **PART** | `…undo_stack_limit/verdict-r4.txt` | `applySettingsChanged: undoLimit=6` 已进控制器；**撤回步数只能主人真手**（§5-5） |
| 9 | `grid_page_size` | **PASS** | `…grid_page_size/verdict-r3.txt` | 引擎侧 [50]→[20]（正控：不设时序列不含 20） |
| 10 | `space_swipe_step` | **PASS** | `…space_swipe_step/verdict-r2.txt` | 日志 `step` [10.0]→[5.0]、同段划动条数 5→11 |
| 11 | `expand_toolbar_by_default` | **PASS** | `…expand_toolbar_by_default/verdict-r3.txt` | `flipped -> true` ＋顶栏图标行像素 |
| 12 | `show_preedit` | **PASS** | `…show_preedit/verdict-r4.txt` | L1 带 ink 开/关/再开 = 585/0/585，候选带三帧不动 |

⇒ **11 PASS ＋ 1 PART（PART 的成因是注入量不出行为，不是没生效）**。§5-4 这条验收项到此闭环。

**这轮量具本身栽的 5 个坑（判据写错，不是产品缺陷；改的都是脚本）**：

1. **卡片锚点把被测项锁死**（`kbd_height_pct`）：`card_anchor()` 的前提是「卡片高＝236vp ⇔ 键高 100%」，
   而这一项**唯一要改的就是键高** ⇒ `CARD ANCHOR-ABORT 卡片高 802px/894px 与 236vp(826px)` 死锁。
   锚点是**防点错行的安全闸**，不能为了跑通就放宽它 ⇒ 另开一条**纯像素**通路：`row0_press()`
   （现量 `panel_rect`→`find_card_bbox`→`is_card`→`find_step_buttons`，只按第一行的 ＋/－，任一步量不到就返回
   None，**绝不盲点**）＋ `set_to_row0()` ＋ `row0_home()`（按像素回到 983px 窗高）。行点击仍必须过锚点。
2. **「读不到现值 ⇒ 按契约默认起步」这个兜底会说谎**：`open_settings()` 会先清 hilog，之后 `set_to()`
   读不到现值就当作 100，于是中途放弃的运行把设备留在 110%/120%，收尾还打印「现值已是 100 ⇒ 不按」。
   ⇒ 通用修法：开页前 `snapshot_settings()` 存一份 `PRE_OPEN`（12 个键＋`h=NN%`＋`undoLimit`），
   `current_value()` 读不到时回落到这份**真值**并写明原因。`undo_stack_limit`、`reset` 那两次「失败」
   其实都是这个级联，不是产品 bug。
3. **`···` 认错簇 ⇒ 拿别人的浮层当证据**（04:33）：旧写法取「最左簇+200..最右簇−60」求均值，实测九簇
   x=69/260/448/639/**829**/994/1019/1043/1209，把 829（剪贴板）吞进去 ⇒ 均值 828＝点了剪贴板说明条。
   ⇒ 簇间距 ≤60px 且 ≥3 簇才是 `···`（三个点间距 ≈25px，图标间距 ≈190px）；**并**在 app 侧补可观测
   `H-241r2 func menu opened|closed`，日志缺失且文字带 <5 条 ⇒ 判据作废重认，不许出 PASS。
4. **卡片内的文字带必须限定 x 段、还要剔掉滚动条列**：整宽扫会把身后 ≈150 灰的遮罩当墨（822px 假带）；
   限定 x 段后，滚到底那一屏又被 `Scroll` 的**自动滚动条**（实测 x=[791,804]，14px，占卡片高 76%）
   把 6 行粘成 1 条 577px 假带 ⇒ 「末行中心」落在行间空白，点下去没反应，**把修好的菜单误判成还在被裁**。
   ⇒ `vert_strips()` 按「列覆盖率」挑竖条（阈值 0.55；实测滚动条 ≥0.76、文字列最高 0.26，两档都打进日志），
   剔完再交给 `_bands(..., skip_x=)`。**教训同款**：第一版阈值我拍脑袋写 0.85，一列都没挑中——
   滚动条是滑块不是轨道。
5. **判据跟着修法动过就要留痕**：`···` 菜单「末行点得动」原来写成「首屏最底一条带」，那只在对**坏布局**
   （8 行硬塞 236vp）成立；改成定高壳＋Scroll 后首屏按设计只有 6 条带 ⇒ 旧口径会把「可滚」判成「仍被裁」。
   ⇒ 现口径＝**先滚到底再点末行**，变更写在 `scripts/h241_funcmenu_check.py` 文件头「判据变更记录」里。

**H-241r2 `···` 菜单裁切：改前/改后各一份**（目录 `docs/evidence/2026-10-28/h241-funcmenu/`）：

- **改前**（02:2x 装机版，无 Scroll）`verdict-r4.txt`：卡片 y=[1849,2674] 高 **825px**（＝235.7vp，
  上下沿正好贴着窗口 ⇒ 内容 268vp 被居中裁掉两头），检出 **7** 条带（标题＋6 开关），
  第 8 行「设置」**整行在窗外**；点末带 (409,2604) ⇒ `settings panel opened` 没命中
  （那一下命中的是「中文/英文」行＝我当场把主人键盘切成英文后立刻点回来了，见 `zoom-lastrow.png`）。
- **改后**（本轮装机版）`verdict-r8.txt`：卡片 y=[1915,2674] 高 **759px＝216.9vp**（＝92%×236vp，
  整块在窗内，底 2674 ≤ 内容底 2675），首屏 6 条带，**上滚 1 次**（末带 2572→2619）后
  「设置」行出现在 (2574,2619)，点 (409,2596) ⇒ `H-241 settings panel opened` **命中**，
  且 `H-241r2 func menu opened` 命中 1 条（证明弹的确实是 `···` 菜单）。肉眼证据
  `zoom-end-r3.png`（末行「设置（键盘与候选）›」完整可见）。
  ⇒ **§3.1 那条「任何往这个菜单里加行的改动都必须自带滚动」现在有改前/改后两组数撑着。**

## 4. `SettingsStore` 接口（CodeArts 实现，Qoder 按这个调用；签名不许改）

```ets
// entry/src/main/ets/common/SettingsStore.ets
export const SETTINGS_STORE_NAME: string = 'sansheng_kb_prefs';   // 输入法进程独立沙箱
export class SettingsStore {
  static inst(): SettingsStore;                                    // 单例
  load(ctx: common.Context): Promise<void>;                        // onCreate / panel.on('show') 调
  num(key: string): number;                                        // 同步读缓存（渲染期唯一读取方式）
  on(key: string, d: number): number;                              // 带默认值
  sw(key: string): boolean;                                        // 开关
  set(key: string, v: number | boolean): void;                     // 写缓存＋flush＋AppStorage 通知
  keys(): string[];                                                // 已注册键（守卫用来对账）
}
```
渲染期**只允许** `num()/sw()` 这类同步读；写侧必须 `flush()`，并 `AppStorage.setOrCreate('settingsRev', rev)` 让
`@StorageLink` 的键面立刻重绘。**不许**在 `.fontSize()` 里 `await`。

## 5. 验收（今晚收口标准）

1. `python scripts/settings_effective_check.py` 绿：12 项每项都能在 store 里找到 key、在键盘侧找到读取点、
   并且**读取点不在注释里**（用已知坏样本自测：给一个「只声明不读」的空壳项，判据必须报红——
   这正是 H-090 那 71 项的形态）。
2. `python scripts/h220_keymap_check.py` 仍全绿（键位不许被入口改动带歪：长按空格/回车**不得**吃掉 s/d/f/g/h/j/k/l/m/n 的长按表）。
3. 内容闸门 **17/17** 阻断 0（2026-10-28 07:1x 起含 H-242 的第 16b 条「设置契约 12 项三项齐全」，此前 16 项）；
   不新增任何权限（`module.json5` 里除 `dataGroupId` 那条待议外零改动）。
4. 真机：每项**改前/改后各量一次**（像素或 hilog），取证落 `docs/evidence/2026-10-28/h239-settings-<key>/`
   （**带 key 名、不许同名覆盖**——H-238 刚踩过）。
5. 主人真手：他长按空格进设置、拖一根滑条、看键盘当场变。

## 6. 变更记录

- 2026-10-28 08:2x Qoder：**`···` 菜单按 H-227 补了 5 枚「滤镜在包里、只是没入口」的开关（commit `aa80025`）**——
  `中英对照 encnDic`／`拼音注音 pinyin`／`英文缩写 abbrEn`／`短语扩展 phraseExt`／`敏感词替换 phraseReplace`；
  文案取各开关自己在 `wubi_pinyin.custom.yaml:6-27` 的 `states` 名（不自造＝H-119），走原有
  `toggleFuncOption→setOption` 一条链（不造第二套），**当前态一律从引擎回读**（前三个 `reset: 1`，写死默认会把「开」显示成「关」）。
  **菜单内容 268vp→约 438vp**，仍在 §3.1 r4 那条「定高壳（92%×236vp）＋内层 Scroll」里滚——`any 加行必须自带滚动`那句没被破。
  **九键下这五枚置灰**（`KeyboardIndex.ets` 的 `WUBI_ONLY_OPTIONS`：`sansheng_t9.schema.yaml:33` 只声明四枚，
  点了没反应＝假按钮＝D-021）。守卫 `scripts/h227_menu_option_check.py`（六环链＋置灰＋壳/Scroll，真树 5/5、`--selftest` 4 坏形状判红）。
  真机判据：hilog 一行 `H-227 toggle option: <name>=<bool>`。unsigned `28,493,174 B`、包模式闸门 17/17；
  **本包尚未装机**（08:2x 抓到他正在真手测气泡，按 `feedback-real-hand` 那条不叠装）。
- 2026-10-28 06:5x Qoder：**本机时钟回跳更正**——上一条写的「07:5x」是按当时读数落的，现在 `date` 实测
  **06:5x**（这机器今天已跳过两次，H-134 记过）。**先后顺序以 commit 号为准**：
  `87f92fe`（两节）→ `1aca163`（滑条）→ `6cbf6e8`（Toggle）→ `ff5961c`/`3b886c6`（值守+WIP）→ `7962f37`（本条前身）。
  另：`settings_effective_check.py` 已挂进内容闸门离线套（`check_app_content.py` 第 16b 条，blocking=True，
  子进程 rc!=0 即拦在构建前）——坏样本双向验证过：删守卫文件 ⇒ 16b FAIL 且闸门 rc=1；恢复 ⇒ 17/17 且 rc=0。

- 2026-10-28 07:5x Qoder：**SettingsPanel.ets 三件套已落地（Qoder 先行；CodeArts 接手前先读本条）**——
  ①按安卓口径分两节渲染（虚拟键盘 8 项 / 候选窗口 4 项，按 key 名归属，commit `87f92fe`）；
  ②§3 表 7 个连续项从「－/＋」改为 **Slider 滑条**（双行布局：标签+数值行 20vp、滑条 24vp；
  只在 `SliderChangeMode.End/Click` 提交、钳到 `[min,max]` 取整，commit `1aca163`）；
  ③4 个 bool 项从文字开关改为 **Toggle(Switch)**（安卓形态，`setBool` 直接写目标值、同值不重复
  reload，commit `6cbf6e8`）；`page_size` 保留离散加减（白名单 [3,5,7,9] 不适用滑条）。
  键名/§4 签名/读取点**一字未动** ⇒ 交界面不变。离线守卫 12/12、键位 86/86 全绿；
  **unsigned 产物 `28,485,496 B` 仅构建验证，未签名未装机**（装机等 CodeArts 整页重做或主人点头，
  避免 H-238 式重复装机）。

- 2026-10-28 05:2x Qoder：**新增 §3.2（真机收口 r5/r6）＝§5-4 那条验收闭环**。
  12 项 **11 PASS ＋ 1 PART**（PART＝`undo_stack_limit`，生效点 `undoLimit=6` 已证，撤回步数只能真手）。
  一轮 build→sign→install（signed `28,592,326 B`）只做了**一次**，因为 `···` 菜单的 H-241r2 裁切修复
  跟这批取证共用同一个构建；改前/改后各一份取证（`h241-funcmenu/verdict-r4.txt` vs `verdict-r8.txt`）。
  **§3.1 的 r3 更正表有 5 格被 r5/r6 再更正**（键高项的锚点豁免、`···` 簇识别、卡片内带扫描的 x 段与滚动条列、
  「末行点得动」改成「滚到底后点得动」），全部写在 §3.2 的「5 个坑」里，**接手的人按 §3.2 实现**。
  键名/范围/默认**一个没动** ⇒ 与 CodeArts 的交界面不变。

- 2026-10-28 02:3x Qoder：**§3 改了 5 行（都是「按旧文案做会做错」那种，不是修辞）**——
  ②候选词字号只改字形不改行高（护 236vp 死线）、④`page_size` 三处同一个值、
  ⑥长按时长的判据换成现成时间戳钩子 `H-215 timer open bubble`（原来那句「按 400ms 不出泡」把极性写反了）、
  ⑩空格划动步长单位是 **vp 手指位移**不是「字符」、⑫关编码行**不还**那 16vp（画同高占位行）。
  同时 §3-1/§3-3/§3-5/§3-7/§3-8/§3-9/§3-11 的「读取点」行号会随本轮改动漂移 ⇒ 以
  `python scripts/settings_effective_check.py` 打出来的**文件＋键名**为准（那才是守卫真正核过的东西）。
  **已装机**：signed `28,593,375 B` 于 02:2x 装进 Mate 80 `7GL0226408083897`（无密码一次过），
  离线三闸先绿——守卫 12/12、键位 86/86、内容闸门 16/16。真机逐项取证见 §5-4 目录。
  **已通知 CodeArts**（M-285）：`SettingsPanel.ets` 我先落「能用」版、整页重做仍归他、五行口径以本封为准。

- 2026-10-28 02:0x Qoder 起草；§1 的两条「不能那么做」是今天查官方文档得到的，别当口口相传。
- 2026-10-28 02:2x Qoder：**`common/SettingsStore.ets` 第一版已落盘**（§4 的 7 个签名一个没动），
  按「只许加方法」的同一规矩，我这边追加了 6 个：`has(key)` / `isBoolKey(key)` / `isUserSet(key)` /
  `defOf(key)` / `minOf(key)`＋`maxOf(key)` / `allowOf(key)`——设置页画滑条与「恢复默认」要用，
  `isUserSet` 是给第 4 项 `page_size` 的横屏口径留的（用户没动过＝横屏仍按 9）。
  **取值范围/离散白名单已在 store 里钳制**（`page_size` 吸附到 3/5/7/9），页面侧不必再判；
  表外键名 `set()` 直接忽略并打 WARN ⇒ **拼错键名不会静默生效**。
  **§2 补一行归属实况**：`entry/src/main/ets/common/**` 在 `docs/HANDOFF.md` 的「文件归属」表里**从未列过**
  （那目录现有的 `SettingsModels.ets`/`PrivacyConsent.ets` 历史上都归 CodeArts）⇒ 本轮我先落第一版、
  接手权仍给 CodeArts，已在 **M-284** 写明，别互相以为对方在改。

## 7. 接手区（CodeArts 在这里追加，一行一条：时间／你改了哪节／键名有没有动）

- 2026-10-28 09:3x CodeArts：**H-240 SettingsModels.ets 文案对齐**——12 项契约条目的 prefKey/文案/范围/默认值全部按 §3 表对齐；表外项（原 71 项中的 ~59 项）全部标 `enabledInPanel: false`（不删，H-129 口径）。**键名改动**：`kbd_height`→`kbd_height_pct`、`kbd_long_press_delay`→`key_long_press_delay`、`kbd_popup`→`popup_on_key_press`、`kbd_expand_toolbar`→`expand_toolbar_by_default`、`global_show_preedit`→`show_preedit`（旧键名保留但 disabled）、`global_default_page_size`→`page_size`（旧键名保留但 disabled）。**新增条目**：`key_font_size`(§3-3)、`space_swipe_step`(§3-10)、`undo_stack_limit`(§3-8)、`grid_page_size`(§3-9)。**分组调整**：`show_preedit` 归虚拟键盘节（KBD_KEYS），`undo_stack_limit` 归候选窗口节（CAND_KEYS），与 SettingsPanel.ets 的 KBD_KEYS/CAND_KEYS 一致。
