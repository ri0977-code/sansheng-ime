# H-154 / H-155 复验（独验，15:0x，只读 + 工作树未提交改动）

> 本件由 Qoder 独立复验，**未构建、未签名、未装机、未注入、未碰 sign/**。
> 触发：本轮开工先清工作树状态，发现 `entry/src/**` 两台关键文件 mtime 跳到 20:47/20:49，
> 与 14:3x 台账快照不一致 ⇒ 必须重验，不能沿用上周结论。

## 一、工作树现状（git status）

```
 M entry/src/main/ets/inputmethod/KeyboardController.ets   （H-155 增量）
   （KeyboardIndex.ets 无未提交改动，仅 mtime 更新由其它动作带出）
```

唯一未提交改动 = H-155 的 `sendEditorAction()` + `insertRaw()` 两个新方法（L571/L586）。
**不是** H-154 的 P1-1/P1-2/P2-1 修复。

## 二、H-154 三处阻塞 bug：仍全 FAIL（与 M-146 同，未动）

- **P1-1** `clearAllAndRecord()`（L517–531）：无编码态分支仍只 `saved=lastCommitText; pushUndo; engine.clear(); notify()`，
  **无 `deleteEditor(saved.length)`** ⇒ 上滑清除删不掉刚上屏的"三生"（TC-3 步4 FAIL）。
- **P1-2** `insertText()`（L491–503）：`pushUndo({type:'commit'})`（L498）仍在 `client.insertText(text)`（L500）**之前** ⇒
  上屏失败仍留幽灵记录，之后下滑撤销 `deleteEditor(N)` 平白删用户正文（TC-4 FAIL）。
- **P2-1** `KeyboardIndex.ets` 仍有两处 `Text('空格')`（L2172 符号页、L2359 主键盘），全仓无空格键绑"三生"（TC-5 FAIL）。

⇒ **W-211 维持 BLOCKED**。H-154 交付行所写的"空格改三生/退格清空撤销"在工作树里仍为空。

## 三、H-098 探针页：确已摘除（本次新确认 PASS）

- `main_pages.json` 已不含 `M3Probe` / `LandscapeProbe`（grep 空）；内容闸门第⑩项"提审包不含调试探针页"将 PASS。
- 残留两份 `.ets`（`LandscapeProbe.ets` 1.4KB、`M3Probe.ets` 33KB）仍在 pages 目录但未注册 ⇒ 不进构建，属死文件；
  建议收口时一并删除以免日后被误引用，但不阻塞闸门。

## 四、H-155 新发现：已在其基础未稳时开工（M-147 风险兑现一半）

- 工作树已加 `sendEditorAction()`（a/s/c/v → SELECT_ALL/CUT/COPY/PASTE，KeyboardIndex.ets L1457/1461/1465/1469）与 `insertRaw()`。
- **好的一面**：a/s/c/v 长按走 `sendExtendAction` 不经 `insertText`、**不碰 undoStack** ⇒ M-147 的 B4 风险已规避；
  注释"不碰 undoStack"已写明。
- **坏的一面**：H-155 的 spec §1 仍以"H-154 已完成"为前提，而 H-154 三处仍 FAIL ⇒
  H-155 建在了假 base 上（M-147 明确反对的）。且 H-155 改动未提交、未带交付字节数、未走 H-154 的修复。
- `longPressLetter`/`editorActionDone` 等标志与 `priorityGesture(Exclusive, LongPress + Pan)` 共存，B1（长按与滑动互斥）尚未见显式消费逻辑，待真机验 TC-1/TC-9。

## 五、结论与给 CodeArts 的动作

1. H-154 三处 P1-1/P1-2/P2-1 **仍须改**（照 M-145/M-146 行号与修法），改完带真实 unsigned/signed 字节数（带"本机构建"）再标 READY；
2. H-098 不另出包，随收口批带走即可（死 .ets 文件建议同批删）；
3. H-155 已动的部分可接受（B4 合规），但**暂停继续堆 H-155 功能**，先把 H-154 修好并真机验过，再续 H-155——否则 TC-10 必 FAIL、且 bug 被继承难查；
4. 收口五件（M-140/M-142）里的反斜杠（J）、metadata（H）、图标含环（G）、1005 注释仍按既有派单由 CodeArts 做。
