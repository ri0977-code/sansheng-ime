# H-275b 选区删除「撤销只回 1 字」根因（真机铁证）

- 时间：2026-10-30 00:22（Mate 80，序列号 7GL0226408083897，PID 46160）
- 主人原话：「长按n选几句，退格删掉，下滑退格，只撤销一个字。顶栏撤销一样也是一个字。」
- 抓取方式：`hdc shell "hilog -x"` + 关键字过滤（`-x` 是 dump 到 stdout，不能带文件参数）

## 铁证日志

```
00:21:55.583 SSKeyboardController H-220 toggleSelectionMode -> true anchor=510
00:21:59.002 SSKeyboardController H-220 extendSelection native dir=1 ok
00:22:01.561 SSKeyboardController H-177 moveEditorCursor dir=3 ok
00:22:01.562 SSKeyboardController H-229 walkCursorTo already at 454
00:22:01.594 SSKeyboardController H-275 sel-delete anchor=510 liveCur=454 [454,510]
              textLen=0 deleted=56 afterPos=454
00:22:02.941 SSKeyboardController undo clear restore 0 chars
00:22:04.053 SSKeyboardController undoLastAction: no clear record
00:22:08.725 SSKeyboardController undoCommit: no commit/clear record
```

## 读法

1. `[454,510] deleted=56` ⇒ **删除本身是对的**：一次退格把 56 字整体删掉，光标停在选区起点 454。
2. `textLen=0` ⇒ 撤销记录里的文案是**空串**。上一版在「选区还活着」时用
   `getForwardSync(65536)/getBackwardSync(65536)` 拼选中文案，本机这两种读法在选区激活时回空串
   （也可能是超大 n 不被接受，两种可能都指向同一个结论：这个读法不可用）。
3. 于是 `pushUndo({type:'clear',text:''})` 压进一条 0 字记录 ⇒ 下滑「恢复 0 个字」（主人看到＝没反应），
   顶栏撤销紧接着报「no commit/clear record」⇒ 主人感受就是「撤销一个字都没有 / 完全没用」。

## 修法（H-275b，已装机 00:27）

1. **先收拢选区再读**：`showSelectionMode=false` → `moveCursorSync(左/右)` 收拢 → `walkCursorTo(a)` 回到选区起点。
2. 两级兜底读文本：
   - ① 精确长度读：活动端在右 ⇒ `getForwardSync(b-a)`，活动端在左 ⇒ `getBackwardSync(b-a)`；读满 `b-a` 才采用。
   - ② 读不满 ⇒ **逐字「先读后删」**：删之前先读光标后 1 字，读到的必然就是马上被删掉的那个字，按序拼成撤销文案。
3. 全选路径同样改造：`walkCursorTo(0)` 后逐字「先读后删」，一直删到光标后无字（上限 20 万防死循环），
   读不到就退回常规退格，绝不空转。
4. 撤销记录为空时不再压栈（避免 0 字记录把栈位吃掉、顶栏还误报「没有记录」）。

## 待主人真手复测

长按 n 选几句 → 退格 → 下滑退格（应整段回来）→ 顶栏撤销（应整段回去）→ 重做（应整段回来）；
长按 a 全选 → 退格（应整框删掉）→ 撤销（应整框回来）；长按 m 删选区 → 撤销（应整段回来）。

日志判据（下一轮抓）：
```
H-275 sel-delete ... textLen=56 deleted=56 ...   ← textLen 必须等于 deleted
H-275 select-all delete deleted=N ... head=...
undo clear restore 56 chars                       ← 不再是 0
```

## 真手复测（2026-10-30 00:34，已过）

主人 00:34 真手：「hongmeng xuanqu keyi le」（鸿蒙选区可以了）。同一时刻日志（PID 56094，装机后的新进程）：

```
00:34:25.786 H-275 sel-delete anchor=454 liveCur=405 [405,454] textLen=49 deleted=49 afterPos=405 head=口口品clamor梨，’
00:34:27.046 undo clear restore 49 chars                 ← 下滑退格，整段 49 字回来
00:34:27.046 bs_row swipe down: undoLastAction dy=82.0
00:34:30.202 undoCommit: commit restored 49 chars, redo depth 1   ← 顶栏撤销，整段 49 字回去且重做深度=1
```

三个判据全部对上：`textLen(49) == deleted(49)`（备份不再是空串）、下滑整段恢复、顶栏撤销整段撤回并留下可重做记录。
