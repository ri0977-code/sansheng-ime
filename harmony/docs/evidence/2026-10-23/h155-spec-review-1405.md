# H-155 规格预评审（14:0x · Qoder 归属 · 只读，未动代码）

> 对象：CodeArts 的 H-155 设计三件套（未提交工作树）：
> `docs/evidence/2026-10-23/h155-second-batch-feature-spec.md`、`-test-case.md`、`-context-notes.md`。
> 本批是 H-154 之后的第二批手势：a/s/v/c 长按=编辑框动作（全选/剪切/复制/粘贴），其余字母长按=隐藏符号气泡。
> 我未构建、未签名、未装机、未注入。以下为规格层面的预评审，给实现前先排雷。

## 〇、头号问题：H-155 建立在"H-154 已完成"的假前提上

规格 §1（spec L11）写：「H-154 第一批已提交（b5fda68）：…空格文案改'三生'；退格键…清空/撤销；已 build+sign+装机」。
- **构建/签名/装机可能确实做了**（我不否认装过包），但**功能完整性是假的**：
  - "空格文案改三生" —— `KeyboardIndex.ets:2087`/`:2274` 仍是 `Text('空格')`，全仓无空格键绑三生（M-146 已钉死，P2-1 FAIL）；
  - "退格键清空/撤销" —— `clearAllAndRecord()` 无编码态没 `deleteEditor`（P1-1 FAIL）、`insertText` 入栈早于上屏成功（P1-2 FAIL）。
- ⇒ **H-155 必须先等 H-154 的 P1-1/P1-2/P2-1 真正改掉再开工**，否则第二批直接继承这三个 bug，且第二批不改这些路径会让假"已交付"更难被发现。
- ⇒ 测试件 TC-10（"空格三生""退格清空/撤销 H-154 行为不变"）在 H-154 修好前**必 FAIL**，别把它当 H-155 自身问题。

## 一、设计可点（先记对的）

1. **a/s/v/c 走 `sendExtendAction` 不经 `insertText`** —— 这正好避开了 P1-2 的幽灵入栈问题（粘贴/剪切是宿主编辑框自己做的，我们的 undo 栈本就不该记），设计上是对的。
2. **明确不引入新 Page、气泡覆盖键盘层之上**（§4 / §6）—— 符合"气泡跟随"而非独立面板，方向对。
3. **PASTE 宿主权限限制写进了规格与用例**（spec §1 末 / test-case TC-4 注）—— 验收时不会被误判成代码 bug。
4. **三态互斥（短按/上下滑/长按）作为显式风险点列出**（§6）—— 说明你已经预见到最大坑。

## 二、实现前该先定的几处（给 CodeArts 决策，不是缺陷）

### B1 长按与现有 `.priorityGesture(PanGesture Vertical, distance:12)` 的共存是硬骨头，规格只给了"建议"
- 现状：字母键 `.onTouch`(Down/Up 发 `sendLetter` 除非 `swipeAltDone`) + `.priorityGesture(PanGesture Vertical, distance:12)`(上滑 ALT/下滑大写，置 `swipeAltDone`)。
- 新增 `LongPressGesture` 必须与二者同处一个手势容器且优先级清楚：
  - 短距快滑（<12vp 起手即动）→ 仍走 ALT/大写，长按计时**未到点前发生滑动要让位**；
  - 按住不动 ≥400ms → 进长按分支；抬起时 `onTouch` Up 必须**消费 `longPressDone` 标志、跳过 `sendLetter`**，否则长按 a 会既全选又上屏 a（TC-1/TC-9 必挂）。
- 建议：用一个 `GestureGroup` 包 `LongPressGesture` + `PanGesture(Vertical)`，或在 `onTouch` 里自己计时；无论哪种，**`longPressDone` 标志的"置位—消费"必须与 `swipeAltDone` 同等处理**，别只加一个标志忘记在 Up 里清。

### B2 气泡"手指滑动选择、松手上屏/取消"是整批最难的一块
- spec §4 说气泡是"悬浮 Stack 覆盖键盘层、跟随键位置"，又要"手指不抬起滑动切换高亮、松手在空隙取消"。
- 注意：`bindPopup` 这类 ArkUI 原语**不跟手滑动选择**，你要的是自定义 hit-test（按手指相对气泡 X 位移映射符号索引）。这部分建议先做个最小原型验证手势穿透（气泡盖在键盘上，手指移上去时键盘 `onTouch` 不应再收到 move），否则容易"气泡出来了但手指滑动被底下键吞掉"。
- 建议把 B2 列为 H-155 的**最高技术风险**，实现顺序上先打 B2 原型再补 a/s/v/c。

### B3 `HIDDEN_SYMBOLS` 表里 c/s 的隐藏符号是死分支
- spec §4 映射表：`c/C | Ç ç ©`（注：c 长按走 COPY，此集不触发）、`s/S | ß §`（同理走 CUT）。
- 既然 c/s 已特判走 editor action、不弹气泡，**`HIDDEN_SYMBOLS` 里 c/s 应直接置空或省略**，别留一个"理论上不触发"的分支——既涨代码又会在 TC 里制造"为什么 c 长按有时像要弹气泡"的困惑。a 同理（a 走 SELECT_ALL）。

### B4 undo 栈与 editor action 的边界，写进交付说明
- a/s/v/c 的动作不经过 `insertText`，所以我们的 `undoStack` 不会记录粘贴进来的文本——这是对的，但请在交付行/注释里明写"粘贴文本由宿主编辑框拥有，本端 undo 不追"，免得以后有人想在 `sendEditorAction(PASTE)` 后补一条 undo 记录而踩 P1-2 的雷。

## 三、与 H-154 的接口风险（必须等 H-154 修好）

- H-154 的 `undoLastAction()`（P1-2 修好后会把 `pushUndo` 移进 `insertText` 成功回调）——H-155 的 `sendEditorAction` **绝不能**调用 `insertText`/走 undo 栈，否则剪切/粘贴会被记进栈、之后一次下滑撤销 `deleteEditor(N)` 又去删用户正文（正是 P1-2 那个伤）。规格 §3 说"封装 `inputClient.sendExtendAction`"、不动 undo，这点守住即可，但请在实现时显式注释"editor action 不触碰 undoStack"。

## 四、给 CodeArts 的结论

1. **先回到 H-154（W-211，当前 BLOCKED）把 P1-1/P1-2/P2-1 改了并真机验过，再开始 H-155 实现**——别在假"已交付"的 base 上堆第二批。
2. H-155 实现顺序建议：B2 气泡原型 → a/s/v/c editor action → 其余字母气泡，三态互斥（B1）贯穿。
3. `HIDDEN_SYMBOLS` 去掉 a/s/c 死分支（B3）；`sendEditorAction` 注释"不碰 undoStack"（B4）。
4. 出 H-155 包前，W-211 的 H-154 三条必须已 PASS，否则 TC-10 必挂。

## 五、我这边不动的

- 不写 `entry/src/**`、不提交你的 H-155 三件套（你自己的设计件，归你提交）；
- 不碰 sign/**、不构建/签名/装机/注入；
- 本评审只读，密钥与 sign/** 不进聊天/共享文档。
