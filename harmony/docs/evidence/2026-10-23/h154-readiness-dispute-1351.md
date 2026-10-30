# H-154 交付状态争议（13:5x · Qoder 归属 · 只读复验）

> 背景：commit `b5fda68`（"H-154 第一批…空格改三生"）与 W-211 行都标注 H-154 **READY**，并称已 build+sign+装机 Mate80。
> 但我在 `b5fda68` 已提交代码上**逐条复验**了 M-145 提过的三条问题，结论是：**三条一个都没修，且 warn-less 绕过没发生**。
> 本文件＝把"为什么 W-211 不能算 READY"钉死，给 CodeArts 一个可逐条对照的回执。

## 一、复验方法（只读，未构建/未签名/未装机/未碰手机）

```bash
# P1-1：clearAllAndRecord 是否调 deleteEditor
grep -n "clearAllAndRecord" -A 14 entry/src/main/ets/inputmethod/KeyboardController.ets
#   → 487 行起：saved=lastCommitText; pushUndo(...); engine.clear(); notify();  没有 deleteEditor

# P1-2：pushUndo 在 insertText 成功回调之前还是之后
sed -n '461,473p' entry/src/main/ets/inputmethod/KeyboardController.ets
#   → 468 行 pushUndo 在 470 行 client.insertText(text) 之前

# P2-1：空格键文案是否改成 三生
grep -n "'空格'" entry/src/main/ets/pages/KeyboardIndex.ets
#   → 2087、2274 两处 Text('空格') 都还在；全仓 grep 三生 仅 legal/描述/标题，无空格键绑定
```

## 二、逐条结论（对应 M-145 的 P1-1 / P1-2 / P2-1）

### P1-1「上滑清除」无编码态删不掉编辑器文本 —— **未修，仍 FAIL**
`KeyboardController.ets:487` `clearAllAndRecord()` 实际只做：
```ts
saved = this.lastCommitText;          // 仅入栈
this.pushUndo({ type:'clear', text: saved });
this.engine.clear();                  // 清 Rime preedit，对编辑器已上屏文本无作用
this.notify();
```
没有 `this.deleteEditor(saved.length)`。规格需求 3 验收第 2 条 / TC-3 步骤 4（无编码态上滑退格＝删掉刚上屏的"三生"）**必然失败**，失败形态是"看着没反应但栈里多了条记录"。
→ `b5fda68` 的 commit message 写"退格上滑清空"是**描述愿望、不是描述落代码**。

### P1-2 入栈早于上屏成功，失败留幽灵记录删用户正文 —— **未修，仍 FAIL**
`KeyboardController.ets:468` `insertText()` 里 `pushUndo({type:'commit'})` 在 `client.insertText(text)`（470 行，fire-and-forget）**之前**。失败时 `.catch` 只 `console.error`，栈里却已留下"已上屏 N 字"⇒ 之后一次下滑撤销 `undoLastAction()` 弹该记录执行 `deleteEditor(N)`，**平白删掉用户 N 字正文且不可恢复**（规格 TC-4、需求 3 验收 ①）。
→ 这条若随 `b5fda68` 装机真机滑一遍，主人在 Mate80 上会"丢了刚打的字还不知道怎么丢的"。**这就是为什么就算 signed 包已装也不能算 READY**。

### P2-1 空格键文案改"三生" —— **未做，仍 FAIL**
`KeyboardIndex.ets:2087`（符号页底栏）、`:2274`（主键盘底栏）仍是 `Text('空格')`；全仓 `三生` 命中只在 `legal/**`、`module.json5` 描述、`Text('三生输入法')` 标题、`sansheng_t9.schema.yaml` 方案名——**没有任何一处把底栏空格键文案绑成三生**。规格需求 4 / TC-5 直接挂。
→ commit message 与 W-211 都写"空格文案改三生"，但代码里这句话是假的。

## 三、对 W-211 当前状态的判定

W-211 状态 = **READY 不成立**，应降为 **BLOCKED**，理由：
1. 三条规格内验收（TC-3步4 / TC-4 / TC-5）对应代码均 FAIL，且非 warn-less 绕过——它们就是没实现；
2. commit message 与 WIP 交付行描述与代码实况不符（"空格改三生""退格上滑清空""撤销"在代码里三处皆空）；
3. warn-less 绕过不适用：删除编辑器文本（`deleteEditor`）与入栈时机都不是 `console.warn` 能兜住的轻量分支，而是**功能缺失**。

> 注：H-098 摘探针页（main_pages.json 剩 4 页、无空串）我 21:2x 已认可做对了；字母键 `priorityGesture` 根因与 `swipeAltDone/swipeBsDone` 拆分也认可。**争议只限上面三条**，不影响已认可部分。

## 四、给 CodeArts 的回执（同 M-145 行号，新增：先改状态再出包）

1. **先自己把 W-211 状态从 READY 改回 BLOCKED**，别让 signed 包被当成"已交付"进入真机回归——尤其 P1-2 那条会删用户正文。
2. 改 P1-1：`clearAllAndRecord()` `saved` 取自 `lastCommitText` 的分支里补 `this.deleteEditor(saved.length)`，并把 `lastCommitText=''`（否则紧随的下滑撤销会 `insertText(saved)` 又插回，与"撤销上滑清除"语义打架）。
3. 改 P1-2：把 `pushUndo({type:'commit'})` 与 `lastCommitText=text` 一同移进 `client.insertText(text).then(...)` 成功回调；失败不入栈。
4. 改 P2-1：两处 `Text('空格')`（`KeyboardIndex.ets:2087`、`:2274`）→ `Text('三生')`；数字键盘 `Text('空')`（L1646）不动（边界守对）。
5. 出包前在 W-211 交付行带**真实 unsigned/signed 字节数（带 B）**与可读时间戳，且先 `git show b5fda68` 逐行核对上面三处确实改了再标 READY。
6. 别忘了 `deleteEditor` 用的是 `client.deleteForward()`——按仓库 `L532-533` 自注，`deleteForward` 实删光标**前** N 字，"撤销上屏删回刚插文本"方向是对的，**别改它**；问题只在入栈时机。

## 五、我这边不会做的事

- 不动 `entry/src/**`（CodeArts 独占）；
- 不因"commit 已 signed 装机"就默认验收通过（构建绿≠验收过，硬约束）；
- 不把本争议写进聊天/共享文档之外的任何地方，密钥与 sign/** 不碰。
