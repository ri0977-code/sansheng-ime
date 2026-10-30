# Qoder 对 CodeArts 09:13–09:2x 三份交付的核验

> 核验人：Qoder（只读核验 + 文档更正；未碰 `entry/src/**`、未构建、未签名、未装机、未注入）
> 时间：2026-10-25 09:2x（本机时钟；CodeArts 文档头的 `01:0x/01:1x/01:2x` 是 UTC，换算成本机＝09:0x/09:1x/09:2x）
> 被核验：`docs/reviews/h164-e712863-review.md`（09:13）、`docs/h165-android-toolbar-inventory.md`（09:17）、`docs/h154-p2-1-patch-proposal.md`（09:19）
> 方法：逐条回到**当前工作树**（`KeyboardIndex.ets` 自 `0b199eb` 后未再改，他审的 `be51619` 是该提交的后代 docs 提交，代码同一棵）、两个 schema、SDK `.d.ts`、安卓原始 yaml——不以他的转述为依据。

## 一、总判

| 交付 | 结论 | 可用性 |
|---|---|---|
| H-164 对抗复核 | **主体可信**：代码事实全对、三处判断与我逐行复核一致；**3 处表述失准**（见 §三），不改结论 | 可并入 H-164 验收依据；框架行为类结论仍标注「待真机日志」 |
| H-165 安卓交叉核对 | **有真发现**：`ascii_punct` 是我 §七 的漏项（已按两 schema 复验并补进 spec）；`phraseComment` 更正与我一致 | 已采纳 |
| H-154 P2-1 提案 | **成立**：P2-1 已在 `0d8c1e4` 落地，不需要补丁 | 关闭，不再出补丁 |

⇒ M-178 四件里，①③④ 由他交付（②闸门我早前已自跑 16/16 并让他停），**M-181 三问据此可收口**（§四）。

## 二、逐条核验（他写的 → 我实测的）

### 2.1 H-164 复核（`h164-e712863-review.md`）

| # | 他的断言 | 实测 | 结论 |
|---|---|---|---|
| 1 | `candScrollToStart()` 767-775 统一入口，未挂载直接 return，异常只记日志 | `:767-776` 原文一致；`scrollToIndex` 只在 `:772`，`catch` 打 `H-164 scrollToIndex skipped` | ✅ |
| 2 | 4 个外部调用点 824/850/950/970 全走守卫、无裸调用 | `grep "candScrollToStart()"` ＝ 定义 767 + 调用 **824/850/950/970**，候选 scroller 无第二处裸 `scrollToIndex` | ✅ |
| 3 | `candTryContinue()` 781 起；翻页前查 `baseIndex/len` | 函数在 `:781`、`flipPage(1)` 在 `:792`、**检查在 `:794-797`**——顺序是「先翻、后核对」，不是「先核对、后翻」 | ⚠️ **表述反了**（见 §三-1）；靠 `flipPage` 内 `notify()` **同步**回调（`KeyboardController.ets:387-390` → `notify` `:666-683` 直调 listener）使核对时数据已更新，行为无差 |
| 4 | 0b199eb 在 `preeditChanged`/`baseChanged` 两分支都清 `candDragArmed/candDragMoved/candLastVisible` | `:944-948`、`:953-956` 原文一致；`baseChanged` 还消费 `pendingForwardAbs`（`:957-969`） | ✅ |
| 5 | ForEach key＝`cand_${uiPageStart+index}_${cand.text}`，跨页复用不错节点 | `:1211-1212` 一致；续片 `uiPageStart 0→20` 时 item20 的 key 两边同为 `cand_20_<text>` ⇒ 复用正确 | ✅ |
| 6 | `.gesture` 取代 `priorityGesture`；非 List 区仍一滑一页、500ms 防抖 | `:1303-1304` 是普通 `.gesture(SwipeGesture(speed:20))`，注释写明「priorityGesture 会抢在 List 之前」 | ✅（非 List 区是否真能抢到手势属框架行为，见 §三-3） |
| 7 | List 属性：横向、lanes(1)、layoutWeight(1)、scrollBar Off、edgeEffect None、onAppear/onDisAppear、onTouch、onScrollIndex、onScrollStop | `:1214-1257` 逐项对上；`.onTouch` Up 仅在 `!candDragMoved` 时撤许可（`:1237-1238`） | ✅ |
| 8 | `CandidateBar` 恒渲染 ⇒ List 不因展开/收起 `onDisAppear` | `:2824` 无条件调 `CandidateBar()`；`:2827` 才条件渲染 `ExpandedPanel()` | ✅ |
| 9 | `onScrollStop` 后兜底 `candTryContinue(candLastVisible)` 再清两态 | `:1252-1257` 一致 | ✅ |
| 10 | 框架行为：`onScrollIndex` 初始布局/整表替换会回调；`onScrollStop` 每次惯性结束必回调 | 代码侧只能证明「回调进入后有两道守卫」；**回调时机本身 SDK 文档未给保证**，只能在真机看 `H-164 scroll …,` / `scroll-continue` 日志序列 | ⚠️ **待真机**（判据①③⑦） |

### 2.2 H-165 交叉核对（`h165-android-toolbar-inventory.md`）

| # | 他的断言 | 实测 | 结论 |
|---|---|---|---|
| 1 | wubi 六个 switch：`ascii_mode`/`full_shape`/`extended_charset`/`ascii_punct`/`zh_trad`/`phraseComment` | 行号 16/19/21/23/25/28，states 全对；`tradition.option_name: zh_trad`（`:157`） | ✅ |
| 2 | 九键四个 switch，缺 `extended_charset`/`phraseComment` | 行号 34/37/39/41；`tradition.option_name: zh_trad`（`:108`） | ✅ |
| 3 | 我 §七 漏了 `ascii_punct`（安卓 `Punct_switch` 有、两个 schema 都声明） | 安卓 `trime.yaml` `Punct_switch: {toggle: ascii_punct …}`；鸿蒙 23/39 行都在 | ✅ **真漏项，已补 §七 并加进「按方案可用性」表** |
| 4 | 安卓 `Henkan: {toggle: simplification}` 与 schema `zh_trad` 不匹配 ⇒ 按键可能不生效 | 安卓 `trime.yaml:964` 确为 `toggle: simplification`；安卓 schema `tradition.option_name: zh_trad`（`:165-167`）⇒ **静态配置确实对不上**。但 Trime 是否在别处把 `simplification` 映射到 `zh_trad`，未实测 | ✅ 事实成立；⚠️ 「按键失效」是**推断**，给主人的话要按推断写 |
| 5 | 撤销/重做 API 在、`undoLastAction()` 零调用点 | `KeyboardController.ets:533` 定义；全仓 `entry/src/main/ets` 无调用 | ✅ |
| 6 | 移动光标 API 齐（`KeyboardIndex.ets:1336/1371/1428`） | **行号挂错文件**：`KeyboardIndex.ets` 这三行分别是空行/`preedit=''`/`setExpanded`。真实出处是 SDK `@ohos.inputMethodEngine.d.ts` 的 `moveCursor` `:1336`、`moveCursorSync` `:1371`、`selectByMovement` `:1428`（我 §十 原文写的就是 SDK） | ⚠️ **出处错**（见 §三-2）；「API 够、项目 0 调用」的结论不变 |
| 7 | Reload 无 napi 导出 | 与我 §七/§十 一致（`fanxing_napi.cpp:1070-1083` 无 reload） | ✅ |

### 2.3 H-154 P2-1 提案（`h154-p2-1-patch-proposal.md`）

`grep "Text('空格')"` ＝ **0**；`Text('三生')` ＝ `:2439`（主键盘）、`:2644`（符号页）；`Text('空')` ＝ `:1998`（数字键盘，按判据保留）。
⇒ P2-1 **已落地**，不需要 diff，不需要再出包；**关闭**。

## 三、三处表述失准（不改他的结论，但必须在共享区留档，免得下一个人照着改错）

1. **「检查在 `flipPage()` 之前」**：实际在之后（`:792` 翻、`:794` 查）。它能成立只因为 `KeyboardController.flipPage` 是**同步 notify**；若将来有人把 notify 改成异步（post 到 UI 线程），这一查就会在「还没换页」时判成 `refused` 并撤 `pendingForwardAbs`——**日志会撒谎，续页记账失效**。这条要写进代码注释或验收判据的备注里。
2. **「所有 `scrollToIndex` 调用点」**：候选 scroller 只有 `:772` 一处；`symbolScroller` 另有 4 处（`:2177/2218/2354/2586`，符号页自己的滚动），与 H-164 无关。表述应限定为「候选 List 的 scrollToIndex」。
3. **「非 List 区手势仍生效」**：属 ArkUI 命中测试行为（是否被父级 `.gesture` 吃到、`speed:20` 与 List 阈值如何互相让路），代码读不出来，只能真机看判据①。库存文档里应标「推断」。

## 四、M-181 三问：我的收口答复（结合纯模拟 T8/T9）

| 问题 | 答复 | 依据 |
|---|---|---|
| (a) `scrollToIndex(0,false)` 会不会触发 `onScrollStop`，会不会把 `candTryContinue` 带进错误路径 | **两种情形都安全**：所有程序复位都发生在 `candDragArmed=false` 之后（续页 `:791` 先撤许可；`preeditChanged`/`baseChanged` `:944-956` 先清两态再复位），`candTryContinue` 首行就因 `!candDragArmed` 返回 false | 代码 + `sim-output.txt` T8a/T8b |
| (b) 甩动时 `onScrollStop` 与最后一次 `onScrollIndex` 谁先到 | **两种顺序都只续一次**：若 `onScrollIndex` 先到尾部 → 就地续页并撤许可，`onScrollStop` 再调时已无许可；若 `onScrollStop` 先到且 `candLastVisible` 还是旧值 → 只返回 false，随后 `onScrollIndex(last=末尾)` 带着仍有效的许可续页 | 同上 T8a/T9a/T9b |
| (c) `baseChanged` 清许可会不会误伤「按住连拖第二屏」 | **不会「误伤」，是按设计只续一次**：续页时许可已在 `:791` 撤销，`baseChanged` 的清只是把「陈旧许可」也扫掉；同一手势要再续必须抬手重拖 | 代码 `:944-956`、`:791` |

## 五、核验后的改动

- `docs/h165-top-function-bar-spec.md` §七：补 `ascii_punct` 一行（第六枚），结论「五枚」→「六枚」，按方案可用性表加一行。
- 其余三份交付**原样入库**（不改他的文字），失准处只在本文件记录。
- **仍未解决、也不该由复核解决的**：H-164 九条真机判据（设备 09:19 仍锁屏，守候脚本 pid 48168 在跑）、横屏三条、`onScrollStop` 真实回调可靠性。
