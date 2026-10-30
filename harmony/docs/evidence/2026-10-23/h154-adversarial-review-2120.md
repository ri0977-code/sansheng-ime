# H-154 对抗审查（21:2x · Qoder 归属 · 只读，未改任何 entry/src）

> 对象：CodeArts 工作树里**未提交**的 H-154 改动（`KeyboardIndex.ets` +63/-?、`KeyboardController.ets` +78、`main_pages.json` -2 行）。
> 交付行：**无**（WIP 里没有 H-154 行、没有 unsigned/signed 字节数）⇒ 按回路这只是「做完了待审」，不是「已交付」。
> 我未构建、未签名、未装机、未碰手机。以下全部是只读代码审查 + 逻辑推演。

## 一、先记做对的部分（别只挑刺）

1. **需求 1 的根因找对了**。原 `.gesture(PanGesture)` 与 `.onTouch()` 同挂 Text，onTouch 在 Up 阶段消费触摸序列，PanGesture 拿不到完整滑动 ⇒ `onActionEnd` 不触发。改挂 `priorityGesture` 是对的（候选栏 L1050 同款已验证过的写法）。distance 20→12 也合理。
2. **`swipeAltDone` 语义扩展成「滑键完成」并把字母键/退格键分开两个标志**（`swipeAltDone` / `swipeBsDone`）—— 比共用一个标志安全，两个键各按各的时序复位。
3. **`main_pages.json` 摘除两个探针页**（H-098 存量项）：删得干净，只剩 4 个页面、无空串残留（我用 `json.loads` 验过），内容闸门第 ⑩ 项这条过了。
4. **撤销栈不持久化、会话边界清空**（`inputStart`/`inputStop` 各清一次）—— 与规格里「避免与宿主编辑器状态不一致」的要求一致。
5. **下滑出大写绕过 `sendLetter()` 直接 `onKey(ch.toUpperCase())`**，不碰 shift 状态 —— 符合规格「不开 shift 锁定、不点亮 shift」。

## 二、发现的问题（按严重度）

### P1-1「上滑清除」在**无编码态根本没删东西**（需求 3 验收第 2 条必挂）

规格要求：无编码态（刚上屏"三生"）上滑退格 = 编辑器里"三生"被删掉。
代码 `clearAllAndRecord()`（`KeyboardController.ets:487`）实际做的事：

```ts
saved = this.lastCommitText;   // 只把文本存进撤销栈
...
this.engine.clear();           // 只清引擎编码（此时本来就没编码）
this.notify();
```

**没有调用 `deleteEditor(...)`** ⇒ 编辑器里的"三生"一个字都没删。`engine.clear()` 清的是 Rime 的 preedit，对已经 `insertText` 进宿主编辑器的文本没有任何作用。

⇒ 真机验收 TC「无编码态上滑退格 = 删掉刚上屏的文本」**必然失败**，而且失败形态很误导人：屏上看着"没反应"，但栈里其实压了一条记录。

**修法**（CodeArts 侧，两行）：`clearAllAndRecord()` 在 `saved` 取自 `lastCommitText` 的分支里补一次 `this.deleteEditor(saved.length)`，并且删完把 `lastCommitText = ''`（否则紧接着一次下滑撤销会 `insertText(saved)` 又插回来一份，与"撤销上滑清除"语义打架）。

### P1-2 入栈先于「上屏成功」，失败也会留记录 ⇒ 之后一次撤销平白删掉用户正文

`insertText()`（`KeyboardController.ets:461`）把 `pushUndo({type:'commit'})` 放在 `client.insertText(text)` **之前**：

```ts
this.pushUndo({ type: 'commit', text: text });   // ← 先入栈
this.lastCommitText = text;
client.insertText(text).catch((err) => { ... 只打 error 日志 ... });  // ← 后执行，失败不入栈不回滚
```

`insertText` 失败时（宿主编辑器异常、client 已失效等，`.catch` 里只 `console.error`），**栈里已经留下一条"已上屏 N 字"的记录，但编辑器里并没有这段文本**。此时用户下滑撤销 ⇒ `undoLastAction()` 弹出该记录 ⇒ `deleteEditor(record.text.length)` 删掉光标前 N 个字符 —— 删的是用户**原本就在那里的正文**，不可恢复。

**附带一条时序问题**（同一函数族）：`deleteEditor()` 是 fire-and-forget（`.catch()` 只打日志，不 await），`undoLastAction()` 在它之后立刻 `engine.clear(); notify();`。删除异步、UI 同步复位，用户若在下滑后立刻继续打字，删除落在新打字之前的位置。这条无法从代码完全消除，但要在交付行里写明"待真机验"，别当没问题。

**修法**（CodeArts 侧）：把 `pushUndo({type:'commit'})` 与 `lastCommitText = text` 一起移进 `client.insertText(text).then(...)` 的成功回调；失败不入栈。

> 顺带纠正一个容易搞混的点（**不是缺陷**）：`deleteEditor()` 用的是 `client.deleteForward()`，而仓库 `L532-533` 自己写着「IME Kit 的 deleteBackward/deleteForward 语义与直觉相反，退格方向要用 deleteForward」⇒ `deleteForward` 实际删的是光标**前** N 个字符。所以"撤销上屏删回刚插的文本"这个**方向是对的**，别去改它；问题只在"入栈时机"。

### P2-1 需求 4（空格键文案改"三生"）**没做**

规格第 4 项明写 `Text('空格')` → `Text('三生')`。实测工作树里两处 `Text('空格')` 都还在：

- `KeyboardIndex.ets:2087`（**符号页**底栏）
- `KeyboardIndex.ets:2274`（**主键盘/九宫格**底栏，规格说的就是这处）

规格自己划了边界「数字键盘 `Text('空')`（L1601→现 L1646）不在本次范围」—— 这条它守住了，确实没动。但主键盘那处没改。主人原话「空格两个字，能不能换成三生」，这条漏了主人会再提一次。

### P2-2 缺交付行与字节数

WIP 里没有 H-154 行。按 H-145/M-143 口径，我要收到「unsigned XX B（本机构建）/ signed XX B」才谈得上独立复现。另外注意规格里说「本批无资源改动，字节数仍只比 unsigned」—— 但 `main_pages.json` 是**进包资源**（profile 里注册页面数变了，HAP 内该文件字节数会变），所以这句"无资源改动"不准确；不影响"只比字节数"的口径，但别在交付行里写错理由。

## 三、规格与代码对不上的一处（给 CodeArts 确认，不是缺陷）

规格需求 1 写「距离 20」，代码改成了 12。这是**有意的改进**（Mate80 上 40vp 太难滑），我认为该保留，但请在他的 WIP 交付行里显式写一句「distance 20→12，依据：规格未定死，按真机可达性调整」，否则下次有人拿规格对代码会以为漏做。

## 四、我这次没验的（边界）

- **没构建、没签名、没装机、没做任何 uiInput 注入**（夜间约束）；以上都是静态审查。
- `priorityGesture(PanGesture Vertical)` 与候选栏 `priorityGesture(SwipeGesture Horizontal)`、符号面板 Swiper 的真实抢占关系，只能真机测——规格里"无冲突"这条我**无法**从代码证实，列为待真机项。
- `undoStack` 上限 10 的内存行为、`inputStop` 后栈是否真的空，需真机+hilog 复核。

## 五、给 CodeArts 的一句话结论

P1-1 / P1-2 是**会让主人生气**的两条（一个"没反应"、一个"删我正文"），P2-1 是漏做的需求，P2-2 是交付流程。改完这四条再出包，别带着上真机——主人现在正一遍遍提键盘毛病，返工成本比我们高。

## 六、复现方式（只读，不动代码）

```bash
# P1-1：看 clearAllAndRecord 有没有 deleteEditor 调用
grep -n "clearAllAndRecord" -A 16 entry/src/main/ets/inputmethod/KeyboardController.ets

# P1-2：看 pushUndo 在 insertText 成功回调之前还是之后
sed -n '461,474p' entry/src/main/ets/inputmethod/KeyboardController.ets

# P2-1：需求 4 漏做 —— 两处 '空格' 都还在（符号页 L2087 + 主键盘 L2274）
grep -n "'空格'" entry/src/main/ets/pages/KeyboardIndex.ets

# P2-2：交付行缺失
grep -n "H-154" docs/WIP.md      # 无输出 = 没写交付行
```

