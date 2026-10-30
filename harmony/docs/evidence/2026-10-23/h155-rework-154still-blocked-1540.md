# H-155 手势重构复核 + H-154 仍阻断（独验，15:4x，只读）

> Qoder 独立复核，**未构建、未签名、未装机、未碰手机、未碰 sign/**。
> 触发：`entry/src` 本轮出现未提交改动，`KeyboardIndex.ets` +103/-48 行。

## 一、本轮改动是什么（未提交 WIP，CodeArts 归属）

- `KeyboardIndex.ets` 把字母键手势从 `GestureGroup(Exclusive, LongPress + Pan)` 拆成：
  - `.priorityGesture(PanGesture Vertical 12)` 管上滑/下滑（H-154 次级字符/大写，仍在）；
  - `.gesture(LongPressGesture 450ms)` 管长按（H-155 气泡 + a/s/c/v 编辑框动作），优先级低于 priority；
  - 新增 `swipeAltDone` 守卫：若本次按下已发生滑动，长按 onAction 直接丢弃，避免"长按 a 既全选又上屏 a"。
- 这正是 M-147 的 **B1（长按与上下滑互斥）** 的正确解法：Exclusive 会让 LongPress 抢走滑动事件，拆开后 Pan(priority) 先吃滑动、纯按住才计时长按。

## 二、H-154 三处阻断 bug 仍全 FAIL（与 15:2x / M-150 同，未动）

- **P1-1** `clearAllAndRecord()`（L488-502）无编码态仍无 `deleteEditor`；
- **P1-2** `insertText()`（L462-475）`pushUndo`(L469) 仍在 `client.insertText`(L471) 之前；
- **P2-1** `KeyboardIndex.ets` 仍 **2 处 `Text('空格')`**（符号页、主键盘）。
- `KeyboardController.ets` 本轮**零改动** ⇒ 三处毫发未改。

## 三、判据

1. 本次 H-155 重构方向对（B1 解决），但属**未提交 WIP**，尚不是可交付态；
2. 更关键：它建在 H-154 假 base 上（M-147/M-150 反对的同一件事）——H-154 三处 bug 仍在工作树，**不可 READY、不可 sign、不可 install**；
3. 等 CodeArts 把 H-154 三处（P1-2 把 pushUndo+lastCommitText 移进 insertText 成功回调）改好、并把本次 H-155 重构一并提交，带真实 unsigned/signed 字节数（带"本机构建"）后，再整体复验并重跑 16/16 闸门。

## 四、给 CodeArts 的动作（重申，未变）

- 先修 H-154 三处，再续 H-155；H-155 不可单独 READY（W-212 仍 BLOCKED）。
- 当前手机上的 4f14d27 包仍携 P1-2，近期别依赖下滑撤销，等 H-154 修好重装。
