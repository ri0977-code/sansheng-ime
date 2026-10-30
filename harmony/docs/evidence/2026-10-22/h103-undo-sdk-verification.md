# H-103 · 撤回（S5）所需 API 的 SDK 核实 —— 结论：可行，且有比原设想更安全的做法

- 记录人：Qoder（只读核实，**未改任何 `entry/src/**`**）
- 时间：2026-10-22 21:2x
- 起因：M-096 派单时把 S5（退格下滑 = 撤回）写成「删掉上一次的输入」，当时**没有核实鸿蒙的 IME Kit 到底能不能删一段已提交文本**。这是 make-or-break：不能删，S5 的设计就得整个换掉。
- 结论：**能删**。而且 SDK 还提供了一个「读回校验」的接口，可以让撤回在光标漂移时**不动手**，避免删掉无关的字。

---

## 一、事实：本应用手上已经握着一个能删文本的句柄

`entry/src/main/ets/inputmethod/KeyboardController.ets:134-140`

```ts
const ability = inputMethodEngine.getInputMethodAbility();
ability.on('inputStart', (kbController: inputMethodEngine.KeyboardController,
  inputClient: inputMethodEngine.InputClient) => {
  this.kbController = kbController;
  this.inputClient = inputClient;   // ← 这个就是句柄
```

`inputClient` 的类型是 `inputMethodEngine.InputClient`，来自 `@kit.IMEKit`。`inputStop` 时置空（`:148`），符合「一个输入框一个句柄」的会话模型。

**已有的两个调用就是证据**（`KeyboardController.ets:442-466`）：

```ts
private insertText(text: string): void {
  const client = this.inputClient;
  client.insertText(text)...
}
private deleteEditor(length: number): void {
  const client = this.inputClient;
  client.deleteForward(length)...   // 退格删 1 个
}
```

⇒ **上屏（insertText）和退格（deleteForward）都已经在用了**，删除一段已提交文本用的是同一个接口族，不需要新权限、不需要新依赖。

---

## 二、SDK 原文（可复核）

文件：`D:\DevTools\DevEco\DevEco Studio\sdk\default\openharmony\ets\api\@ohos.inputMethodEngine.d.ts`
接口：`interface InputClient`（声明在 `:1003`，方法在 `:1020-1290`；另有同源的 `TextInputClient` 在 `:825`）

| 方法 | SDK 声明行 | SDK 文档原文 | 对撤回的意义 |
|---|---|---|---|
| `insertText(text): Promise<boolean>` | `:1169` | "Inserts text." | 上屏（已在用） |
| `deleteForward(length): Promise<boolean>` | `:1071` | "**Deletes the fixed-length text before the cursor.**"（`:1056`） | **删除光标前的 N 个字符** ← 撤回要用它 |
| `deleteBackward(length): Promise<boolean>` | `:1120` | "Deletes the fixed-length text **after** the cursor."（`:1088`） | 删除光标后的 N 个字符（撤回用不到） |
| `getForward(length): Promise<string>` | `:1217` | "**Obtains the specific-length text before the cursor.**"（`:1201` 附近） | **读回光标前的 N 个字符** ← 撤回前的校验用 |
| `getBackward(length): Promise<string>` | `:1266` | "Obtains the specific-length text **after** the cursor." | 本次用不到 |
| `insertTextSync` / `deleteForwardSync` / `getForwardSync` | `:1184` / `:1086` / `:1233` | 同义同步版 | 手势回调是同步上下文，同步版更省事 |

### ⚠ 命名陷阱（务必照抄，**不要"顺手修正"**）

`deleteForward` 删的是**光标前**，`deleteBackward` 删的是**光标后** —— 与英文直觉相反。

本应用**已经踩过并写对了**：`KeyboardController.ets:454-456` 的注释写着「IME Kit 的 deleteBackward/deleteForward 语义与直觉相反，退格方向要用 deleteForward（参考壳实测结论）」。现在 SDK 原文证实了这个注释。**这条不要改、不要"优化"**，它是被真机验证过的。

---

## 三、一个容易走错的地方：不在 ArkTS 的 `inputMethod` 模块里

我第一次 grep 的是 `@ohos.inputMethod.d.ts`，结果 `deleteBackward` / `insertText` **一个都没有**——那是 ArkTS 侧 `@ohos.inputMethod` 模块的 `InputMethodController` 接口（`:478`），它只有：

```
attach / detach / showTextInput / hideTextInput / updateCursor /
changeSelection / updateAttribute / stopInputSession / sendMessage / recvMessage
```

**没有**任何插入/删除文本的方法。如果按那个接口去实现撤回，会误以为「鸿蒙输入法删不了字」，进而改用 `changeSelection` 绕路——那是**错的方向**。

正确的句柄是 `inputMethodEngine.InputClient`，本应用**已经在用**。

---

## 四、应用侧前提：输入框里只有「已上屏文本」

预编辑（preedit）是**本应用自己画在候选栏里**的（`KeyboardIndex.ets:974` `Text(this.preedit)`），不是写进编辑框的；写进编辑框的只有 `insertText(ctx.commitText)` 那一类**已提交文本**。

⇒ 光标前 N 个字符 **==** 最后上屏的 N 个字符，**长度账目是精确的**，不需要去猜 preedit 占了几格。

---

## 五、由此定下的撤回机制（比原设想多一道保险）

原设想（M-096 §四）：「把栈顶那段文本从输入框里删掉（删 N 个字符）」。现在能写死了，并补上一条**读回校验**：

```
撤回 = ① 弹栈顶条目 { text, len }
        ② getForward(len) 读回光标前 len 个字符
        ③ 若读回的内容 !== 条目.text ⇒ 放弃，不删（记一条日志）
        ④ 若一致 ⇒ deleteForward(len)
        ⑤ 引擎侧一起清（engine.clear()：preedit + 候选）
```

**为什么加 ③**：光标可能被用户点了别处、可能被别的 App 改过内容、可能输入框被清空过。此时若照着栈里的旧记录盲删，删掉的是**用户的别的字**——这正是主人最烦的「改一处错一处」型的坑。有了 ③，最坏情况是「没撤动」，而不是「撤错了」。

**入栈点只有一个**：`KeyboardController.insertText()`（`:442`）。全库的上屏路径都经过它——`onKey()` `:314`、`chooseCandidate()` `:323`、`chooseCandidateAbs()` `:336`，S1 的符号路径 `onKey(alt)` 也最终落到这里。**在 `insertText()` 里入栈，就不会漏掉任何一条上屏路径。**

**退格会改编辑器**：因此**除撤回以外的任何编辑器写操作，都要把栈顶条目丢弃**（退格后栈顶那条已经对不上了）。这是最省事且最安全的规则；想要更精细（退 1 个字就修剪栈顶）可以后续再说，本单不做。

**S3/S4「清除全部」怎么做**：需要知道光标前总共有多少字符 ⇒ 用 `getForward` 阶梯探测（64 → 256 → 1024 → 4096）：返回长度 < 请求长度 ⇒ 那就是总量 ⇒ 一次 `deleteForward(总量)`；同时 `engine.clear()` 清引擎侧。

---

## 六、对 M-096 的影响

- S5 **不需要换设计**，也不需要新增依赖或权限——机制见上。
- 要给 CodeArts 补的信息有三条：① 用 `InputClient.deleteForward`（不是 `deleteBackward`）；② 撤回前**必须** `getForward` 读回校验；③ 「清除全部」用 `getForward` 阶梯探测总长。
- 已写进 `docs/MAILBOX.md` 的 `M-096-re` 行。
- 同步修订 `docs/evidence/2026-10-22/h103-gesture-spec.md` §四。
