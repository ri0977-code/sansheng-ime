# W-213（H-155 手势修复）READY 争议：动作层三处仍 FAIL（2026-10-24 00:2x · Qoder）

## 交付内容（对 HEAD d3840eb 只读核对）

- `d3840eb` 2026-10-24 00:06:31「H-155 修复：拆开 Pan/LongPress 手势竞争——上滑符号/下滑大写/退格上下滑回归；长按改普通 gesture」
- `docs/WIP.md` 新增 **W-213 | H-155 | READY**（00:06，未提交）
- 本轮**没构建、没签名、没装机、没碰手机**；只读代码与 git 历史。

## 做对的部分（结构与 M-147/M-151 的建议一致）

1. 字母键：`priorityGesture(PanGesture(Vertical, distance 12))` 管上下滑（`KeyboardIndex.ets:1487-1505`），
   `LongPressGesture(450ms)` 改挂普通 `.gesture()`（`1507-1520`），优先级关系正确。
2. `swipeAltDone` 守卫在 LongPress 回调首行（`1513`）丢弃「滑动后长按」⇒ 不会一滑既出次级字符又触发全选/气泡。
3. 退格键：`priorityGesture(PanGesture)` 上滑 `clearAllAndRecord()`、下滑 `undoLastAction()`（`1615-1630`），
   `swipeBsDone` 防与 `onTouch(Up)` 短按删 1 字冲突（`1606-1611`）。
4. `main_pages.json` 仍无探针页（H-098 保持关闭）。

## 仍 FAIL 的三处（H-154 的 M-145/M-146/M-149 三项，一字未改）

| # | 位置（HEAD d3840eb） | 实测 | 后果 |
|---|---|---|---|
| P1-1 | `KeyboardController.ets:488-502` `clearAllAndRecord()` | 无编码分支只 `saved=lastCommitText`（L495）→ `pushUndo({clear})`（L498）→ `engine.clear()`（L500）→ `notify()`；**无 `deleteEditor(saved.length)`、无 `lastCommitText=''`** | 「上滑清除」在已上屏态**看着没反应**（`engine.clear()` 只清 Rime preedit）；栈里却多一条 `clear` 记录，下一次下滑会 `insertText(saved)` 把同一段再插一遍 |
| P1-2 | `KeyboardController.ets:462-475` `insertText()` | `pushUndo({commit})` 在 L469，`client.insertText(text)` 在 L471；`.catch` 只打日志 | 上屏失败时栈里留「已上屏 N 字」幽灵记录 ⇒ 之后一次下滑 `deleteEditor(N)` **平白删掉用户正文且不可恢复** |
| P2-1 | `KeyboardIndex.ets:2414` | 主键盘空格键仍是 `Text('空格')`（符号页 `2213` 那处按 M-145 可不动） | 需求 4「空格键文案改三生」未落地 |

`grep` 复核：`KeyboardController.ets` 全文 `deleteEditor` 只出现在 `undoLastAction()`（L~520）与 `deleteEditor` 定义处，
`clearAllAndRecord()` 内 0 次。

## 为什么这条对 H-155 尤其要紧

W-213 恰好把**退格上下滑**接到了上面两个坏动作上：
上滑 = P1-1（无编码态不清除）⇒ 这条新交互在真机上是空动作；
下滑 = 弹出的栈顶若来自 P1-2 的幽灵 `commit` 记录 ⇒ 删用户正文。
即：**H-155 的手势层修好了，但它驱动的动作层是坏的**，此时标 READY 就是把已知缺陷送到主人手上。

## 结论

- **W-213 → BLOCKED**（与 W-211/W-212 同一原因，非新增问题）。
- H-154 仍 **P0 OPEN**：P1-1/P1-2/P2-1 三项按 M-145 的修法改完，再报 unsigned/signed 字节数（带「本机构建」）。
- 下一轮我复验的顺序：① 先看 `KeyboardController.ets` 三项；② 再看 `KeyboardIndex.ets` 手势是否仍成立；
   ③ 字节数一致后才 sign+install；④ 装机后跑 16 项内容闸门与 8 项真机回归。
