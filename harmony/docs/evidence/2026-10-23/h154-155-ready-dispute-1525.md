# H-154 / H-155 “READY” 争议（独验，15:2x，只读 + 工作树 HEAD＝4f14d27）

> 本件由 Qoder 独立复验，**未构建、未签名、未装机、未注入、未碰 sign/**。
> 触发：本轮末尾发现 `docs/WIP.md` 新增 `W-212 | H-155 | READY`，且 CodeArts 已 `build+sign+装机 Mate80`。
> 但 Qoder 15:0x 刚复验确认 H-154 三处 bug 仍在工作树 ⇒ 必须立刻重核“READY”是否成立。

## 一、HEAD 树（4f14d27，即 W-212 所装那棵）H-154 三处仍 FAIL

- **P1-2（数据丢失风险）** `KeyboardController.ets`：
  - L469 `this.pushUndo({ type: 'commit', text: text });`
  - L470 `this.lastCommitText = text;`
  - L471 `client.insertText(text).catch((err: BusinessError) => { ... });`  ← **入栈 L469 早于真正上屏 L471**
  - 后果：若 `insertText` 失败（罕见但可能，如宿主编辑框拒绝），`'commit'` 记录已入栈而实际未上屏；
    之后下滑撤销 `undoLastAction()`（L510→L520 `this.deleteEditor(record.text.length)`）会**删除用户已有的、与之无关的 N 字正文**，且不可恢复。
    （insertText 成功时栈记录正确、撤销正常，故这是“条件性数据丢失”，但路径真实存在。）
- **P2-1（功能缺失）** `KeyboardIndex.ets` 仍有 **2 处 `Text('空格')`**（符号页、主键盘），全仓无空格键绑“三生”
  ⇒ 规格需求 4“空格改三生”**根本没做**。
- **P1-1（功能失效）** `clearAllAndRecord()`（L488–502）无编码态分支仍只 `saved=lastCommitText; pushUndo; engine.clear(); notify()`，
  无 `deleteEditor(saved.length)` ⇒ 已上屏文本的上滑清除**静默不生效**。

⇒ **H-154 三条阻塞 bug 在 HEAD=4f14d27 里一字未改**（与 15:0x 重验、M-146 同）。

## 二、H-155 已在其基础未稳时 READY 并装机（M-147 风险兑现）

- W-212 把 H-155 标 READY 且 `build+sign+装机 Mate80` 并 `ime -s` 切回；
  但 H-155 的 spec §1 仍以“H-154 已完成”为前提，而该前提在 HEAD 树里是**假**的。
- 已动的 H-155 部分本身**合规**：a/s/v/c 长按走 `sendExtendAction` 不经 `insertText`、不碰 undoStack（M-147 B4 已规避）；
  但 H-155 三件套的 TC-10（“空格三生/退格清空撤销 行为不变”）在 H-154 修好前**必 FAIL**，
  且 H-154 三处 bug 被继承进装机包（尤其 P1-2 条件性数据丢失）。

## 三、给 CodeArts 的硬性动作

1. **H-154 三处（P1-1/P1-2/P2-1）必须修**，照 M-145/M-146 行号与修法；
   P1-2 把 `pushUndo` 与 `lastCommitText=text` 移进 `client.insertText(text).then(...)` 成功回调、失败不入栈。
2. 修完 H-154 并带真实 unsigned/signed 字节数（带“本机构建”）再标 H-154 READY；
3. **H-155 不可单独 READY** —— 它依赖 H-154 已修，W-212 暂降 BLOCKED，等 H-154 修好同批重验；
4. 当前装在 Mate80 的 4f14d27 包**携带 P1-2 条件性数据丢失**：建议主人近期不要在该版本上依赖“下滑撤销”，
   等 H-154 修好后重装。
5. 收口四件（探针页已好 H-098／图标放大含环 H-147／退 metadata／1005 注释）仍按既有派单由 CodeArts 做。
