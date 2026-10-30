# H-096 两个静态缺陷的修法复核（针对提交 `3c94d66`）

复核时间：2026-10-22 19:4x（**机器 19:0x 重启过，系统时钟比上一段记录回拨约 1.5 小时**；
文档里出现的 20:9x / 21:0x 与 18:0x / 19:0x 可能是同一批动作。本轮起一律以**文件 mtime** 为准，
不以聊天里的钟点为准。）

复核对象：`entry/src/main/ets/pages/KeyboardIndex.ets` 的 **提交态**（`git show 3c94d66:...`，
86,750 B / 2,154 行），**不是工作区态** —— 见文末 §四。

---

## 一、结论先说

| 项 | 结论 |
|---|---|
| 缺陷①「横屏 preedit 无渲染点」 | **修法方向对，落地不完整**：预编辑确实回到了屏上，但宽度无上限、也没参与候选条数计算 ⇒ 长编码时会吃掉候选行。另开 H-096-3 / H-096-4 两条。 |
| 缺陷②「上滑次级字符双上屏」 | **没有消除不确定性，只是把赌注从 `onClick` 挪到 `onTouch(Up)`**：仍然依赖「`onActionEnd` 与抬手回调谁先到」这个 ArkUI 未文档化的行为。给一个**不依赖顺序**的写法（§三）。 |
| 包内容核验 | 对他 18:40 的 `entry-default-signed.hap`（28,255,548 B，sha256 `cf2e0e5a…f8502`）跑 `scripts/check_app_content.py`：**14/15 通过，阻断项 0**，只剩 ⑩ 探针页 WARN（H-098）。 |
| 装机/签名 | **本轮未做**。工作区 19:35 正在被改（见 §四），不能拿在途文件出包。 |

---

## 二、缺陷① 复核：横屏预编辑

提交态 `CandidateBar()`（:958-968）：

```ts
Row() {                                                  // L2 候选行
  if (this.barHeight < 40 && this.preedit.length > 0) {   // :960
    Text(this.preedit)
      .fontSize(12).fontColor(FG_HINT)
      .maxLines(1).textOverflow({ overflow: TextOverflow.Ellipsis })
      .flexShrink(0)                                     // :966 ← 问题
      .margin({ right: 8 })
  }
  Row({ space: 4 }) { ForEach(this.pagedCandidates(), ...) }
    .layoutWeight(1).height(...).clip(true)               // :979-989
  Stack() { /* ▼ 展开按钮 */ }.width(40)                   // :991-1005
}
```

原来「整行隐藏 L1」确实改成了「并进候选行左侧」，横屏打字能看见编码了 —— 这条我提的意见他照做了，
`commentLine()`/L1 竖屏路径没动，竖屏不回归。**但有两处没算到：**

### H-096-3（新）预编辑宽度无上限，长编码会把候选挤没

`.flexShrink(0)` 且没有 `maxWidth`/`constraintSize` ⇒ 这段灰字按**内容自然宽度**参与测量；
候选行是 `layoutWeight(1)`，拿的是「固定子节点之后剩下的空间」。
横屏可用宽度本来就窄（Mate 80 横屏候选栏约 700vp 级），三生又是「preedit · comment」双字段形态，
五笔连打 5 码 + 反查注释时这串很容易到 20 字符以上。届时：

- 候选行被压到 0～1 条宽 ⇒ **横屏打字越打越看不到候选**，与「看得见变化」还是同一类问题，只是换了触发条件；
- `textOverflow(Ellipsis)` 此时**不保证生效**——省略号只在宽度被约束时才出现，`flexShrink(0)` 恰恰是不允许被压缩。

**建议修法（一句话）**：给这段 Text 加约束，例如 `.constraintSize({ maxWidth: '40%' })`
（或直接按 vp 给死宽度上限），保留 `Ellipsis`。

**真机判据**：横屏连打一串长编码（26 键 ≥10 个字母，或五笔打满 4 码以上带反查注释），
要求 **预编辑变长时右侧仍然至少 2 条候选可见**、预编辑超长时以省略号截断而不是吞掉整行。

### H-096-4（新）候选条数没把预编辑的宽度扣掉，横屏恒比实际能显示的偏多

`recomputePageSize()`（:533-590）里：

```ts
let expandBtnW: number = 40;                                     // :537
let availW: number = this.candBarWidth - expandBtnW - 2 * CAND_PAD_H;  // :538 ← 只扣了 ▼ 与内边距
```

`candBarWidth` 是外层 L2 `Row` 的 `onSizeChange` 实测整宽（:1035 区），**不随预编辑出现而变化**；
`availW` 也没减掉「预编辑宽度 + 8vp 间距」。于是横屏在有预编辑的那一拍，
`setPageSize(n)` 向引擎要的条数 **大于剩余宽度真能放下的条数**：

1. 多出来的候选被内层 `Row` 的 `.clip(true)` 裁掉 ⇒ 看着像「少了一条」，而且裁掉的那条**点不到**（点击热区在裁切外）；
2. 打破 H-060 的记账不变量「屏上渲染条数恒等于最后一次 `setPageSize`」（本文件头注释 :42、:720 都以此为前提），
   `uiPageStart`/`baseIndex` 的翻页对账日志会在横屏出现固定偏差 —— 以后查跳条问题会被这条误导。

好消息是**触发时机不用改**：`preeditChanged` 已经在调 `recomputePageSize()`（:808-811），
只要在 `barHeight < 40 && preedit.length > 0` 时把
`estimateCandWidth(this.preedit, 12) + 8` 从 `availW` 里减掉（并保证 `availW<=0` 早退不变），
每次编码变化会自动收敛，不会引入 H-055 的棘轮（棘轮根因是「用当前页切片估宽」，这里用的是全量）。
展开态走 `gridCols()*2`，不受影响。

**真机判据**：横屏打一个候选较多的音节，`hdc shell hilog | grep setPageSize`，
把日志里的 `n` 与屏上**实际可见**条数对一次；带长预编辑时两者应相等（现在应能观察到 n 偏大）。

---

## 三、缺陷② 复核：上滑次级字符

提交态 `LetterKey()`（:1321-1363）现在只挂 `onTouch` + `PanGesture`：

```ts
.onTouch((e) => {
  if (e.type === TouchType.Down)  { pressKey(); swipeAltDone = false; }
  else if (e.type === TouchType.Up) {                       // :1343
    releaseKey();
    if (!this.swipeAltDone) { this.sendLetter(ch); }         // :1345-1347
    this.swipeAltDone = false;
  }
  else if (e.type === TouchType.Cancel) { releaseKey(); }    // :1349-1351：抬手取消不再发字母，这条对
})
.gesture(PanGesture({ direction: PanDirection.Up, distance: 20 })
  .onActionEnd(() => { if (alt !== '') { onKey(alt); this.swipeAltDone = true; } }))  // :1355-1360
```

`onClick` 删干净了、`Cancel` 分支不再发字母 —— 这两步是实打实的改进。
但**根因没有被消除**：整个防重现在完全押在一句「ArkUI 中 `PanGesture.onActionEnd` 先于 `onTouch(Up)`」上，
而这句仍然是**未文档化行为**。顺序如果相反（抬手回调先到），执行轨迹是
`Up → swipeAltDone=false → sendLetter('a')` → 随后 `onActionEnd → onKey('@')`，
结果就是我最初报的那个 `a@`，**只是从"可能"变成"换了个姿势仍然可能"**。
他说「onActionEnd 在 ArkUI 事件流中先于 onTouch(Up) 触发」，我没有在官方文档里找到这句话，
也没有本机日志证据；这条必须真机验，不能靠断言收口。

### 一个不依赖事件顺序的写法（建议，不是我要求的设计）

把标志改成在 **`onActionStart`** 里置位，而不是在 `onActionEnd` 里：

```ts
// H-096：上滑一旦被识别（阈值 20vp 越过即触发），先立标志；
// PanGesture 的 onActionStart 必然发生在抬手之前（它由移动触发），
// 所以 onTouch(Up) 读到的值与 onActionEnd/onTouch(Up) 的先后无关。
.onTouch((e) => {
  if (e.type === TouchType.Down) { pressKey(); swipeUpActive = false; }
  else if (e.type === TouchType.Up) {
    releaseKey();
    if (!(swipeUpActive && this.getAltChar(ch) !== '')) this.sendLetter(ch);
    swipeUpActive = false;
  } else if (e.type === TouchType.Cancel) { releaseKey(); swipeUpActive = false; }
})
.gesture(PanGesture({ direction: PanDirection.Up, distance: 20 })
  .onActionStart(() => { swipeUpActive = true; })            // ← 关键：Start 不是 End
  .onActionEnd(() => { const alt = this.getAltChar(ch); if (alt !== '') keyboardController.onKey(alt); }))
```

要点：置位放在 `Start`（由移动触发，逻辑上一定早于抬手），消费放在 `Up`，`End` 只负责出次级字符。
`alt` 为空的键（无次级字符的字母）仍按普通点击出字母 —— 与现行为一致。
是否采用由 CodeArts 定，**判据不变**：真机 26 键上滑 `a` 一次，**只出一个 `@`**，
且正常单击 `a` 只出 `a`（抬手才出字母，别把「按下不动」当成没响应）。

### 顺带两个行为变化，建议真机时一并看

1. **字母现在在抬手时上屏**（原来 `onClick` 也是抬手后，但 ArkUI 的 click 还带一次目标命中判定）。
   按下不抬手不再出字 —— 手感上比主流输入法略慢半拍；是否改成 Down 出字属于产品取舍，本轮不派单。
2. **按住键位滑出键盘区再抬手**：`onTouch(Up)` 通常仍会投给按下的组件 ⇒ 会照发字母；
   而旧的 `onClick` 语义下这种「甩出去」不算点击。主流输入法在键区外抬手是**取消**的。
   这是本次改动引入的新差异，值得在真机上明确测一次并让主人判可接受与否。

---

## 四、一次我自己的流程失误（如实记录，不算 CodeArts 的缺陷）

19:34:30 我跑 `scripts/build.ps1` 复算他报的字节数，**BUILD FAILED**，
`default@CompileArkTS` 报 594 个 `arkts-no-standalone-this`（首错 `KeyboardIndex.ets:1617`，
文件里 1584-1585 出现游离的 `})` / `}`，1540 起 `@Builder` 缩进掉到 0 列）。
核对 mtime：`KeyboardIndex.ets` **19:35:05 被写入、102,072 B**，而提交态是 86,750 B / 2,154 行 ——
即**他当时正在改这个文件**（九键/数字键盘那一片），我踩到了半保存状态。

违反了本轮约束第 ④ 条（构建前等 mtime ≥ 120 s）。已把这次失败日志留证：
`docs/evidence/2026-10-22/build-verify-190x.md`（去色码摘录，入库）与本地全量 `build-verify-190x.log`（`.log` 被 .gitignore 忽略，未入库）。**这条不记在他头上**，也不作为任何 H 项的证据。
后续动作：等他本轮报数并停手 ≥120 s 后，我再独立构建、逐字节比对、签名装机。

工作区与提交态的差异（`git diff --stat HEAD`）：KeyboardIndex.ets **+431 行 / −35 行**，
说明他在做新一轮布局改动（本轮 H-096 未收口）。

---

## 五、我这侧做的两处修正（`scripts/` 归属我自己）

1. `scripts/check_app_content.py` 在 PowerShell 管道下 **崩溃**：Python 用本地代码页（这台机器 GBK）打印
   `⇒`/`←` 时抛 `UnicodeEncodeError`，15 项跑到第 9 项就整条闸门异常退出。
   已在导入后统一 `sys.stdout/stderr.reconfigure(encoding="utf-8", errors="replace")`。
   **这条如果漏掉，`release_build.ps1` 里的硬闸门会以"脚本报错"的形式失效** —— 看起来像没通过，实际什么都没核。
2. 文档首行「10 项」改为「15 项」，与实际检查数一致。

复跑结果（对 18:40 那份 signed HAP，非在途源码）：**14/15 通过，阻断 0**，WARN 仅 ⑩ 探针页（H-098）。
