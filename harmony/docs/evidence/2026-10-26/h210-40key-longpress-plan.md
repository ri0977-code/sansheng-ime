# 40 键长按编辑键位 · 实施方案

> ⚠️ **本文已部分作废（2026-10-26 21:xx 主人当场纠正）**：我写这份方案时**只比了「哪个键长按是什么」，没比键盘排布**。主人原话「trime那个预设键盘是5排的，平时的4排的，你没比较差异，硬搬啊」。
>
> **三条更正**（详见 `h210-40key-layout-facts.md`）：
> 1. **40 键是 5 排**（顶上一排数字 `1-0`），我们是 3 排字母；中排要补 `;`、下排要补 `,` `.` `/`、底栏要补 `'`。**排布不同，键位就不同，长按映射不能照搬。**
> 2. **f/g 判错了**：`Page_Up`/`Page_Down` 的 label 是「上頁/下頁」，指**候选翻页**，我们 `KeyboardController.flipPage(±1)` **早就有** ⇒ 能做，不是做不到。
> 3. **C 类「做不到」只剩 n（Insert）一项**，且措辞应为「未找到 API」而非「平台做不到」。
>
> 另外 s/d 的角标不该写成「到头/到尾」——Trime 键面原文就是「行首」「行尾」。
>
> **基于本文错误前提写的代码已全部撤销**（`git diff` 已干净）。

> 整理：CodeArts
> 发起：主人 2026-10-26 20:xx 直接问「40键长按键位，如果你做，打算怎么做，具体方案有没有」
> 依据：三生 Trime 部署产物 `rime/build/trime.yaml`（74,549 B，2026-10-26 16:32）中 `preset_keyboards/qwerty`（預設40鍵）逐键实测
> 归口：业务交互归 Qoder 出变更包（D-030）；本文是**方案与可行性证据**，不是变更包

---

## 一、先纠正我自己的一个错

我在 `nova6-ime-research.md` §4.2 里写过「**s/d 的 Home/End 无 IME Kit API**」——**这条是错的**。

我本轮逐行查 SDK，鸿蒙有现成 API：

| API | 位置 | 签名 | 用途 |
|---|---|---|:-:|
| `getTextIndexAtCursorSync()` | `@ohos.inputMethodEngine.d.ts:1496` | `(): number` | 取光标在全文中的下标 |
| `selectByRangeSync(range)` | `:1413` | `(range: Range): void` | 按 `{start, end}` 选中一段 |
| `moveCursorSync(direction)` | `:1371` | `(direction: number): void` | 1 上 2 下 3 左 4 右 |
| `getForwardSync(len)` | `:1233` | `(len: number): string` | 取光标**之前** len 字 |
| `deleteForwardSync(len)` | `@ohos.inputMethodEngine.d.ts` | `(len: number): void` | 删光标前 len 字 |
| `sendExtendAction(action)` | `:1554` | `(action: ExtendAction): Promise<void>` | SELECT_ALL=0 / CUT=3 / COPY=4 / PASTE=5 |
| `insertText(text)` | 已在用 | `(text: string): Promise<void>` | 上屏 |

**Home 怎么实现**（不是逐字符左移猜位置）：

```
idx = getTextIndexAtCursorSync()        // 光标下标
selectByRangeSync({ start: 0, end: idx })  // 选中 [0, 光标) 整段
moveCursorSync(3)                       // 左移一格 ⇒ 撤销选中、光标落到选区左端 = 行首
```

**End 怎么实现**：先用 `getForwardSync` 阶梯探测（64→256→1024→4096）拿到光标前总长 `totalLen`：

```
idx = getTextIndexAtCursorSync()
selectByRangeSync({ start: idx, end: totalLen })   // 选中 [光标, 末尾)
moveCursorSync(4)                                  // 右移一格 ⇒ 光标落到末尾 = 行尾
```

> 注意：`end` 用 `totalLen` 会选中到「全文末尾」而不是「本行末尾」。**行首行尾还是全文首尾，必须真机定**——Trime 的 `Home`/`End` 在 Android 编辑框里是「本行首/本行尾」语义，鸿蒙 `selectByRange` 没有按行 API，所以**第一版做「全文首尾」**，行内语义标为**已知差异**，不假装等同。这条是本方案唯一需要主人/ Qoder 拍板的语义点。

---

## 二、40 键要做的东西，逐项落法

三生 40 键里 **44 处长按**，按我们能不能做分三类：

### A 类：直接做（API 齐、已验证或一行可通）

| # | 键 | 长按 = | 鸿蒙实现 | 现状 | 工作量 |
|--:|---|---|---|---|:-:|
| 1 | `a` | 全选 | `sendExtendAction(SELECT_ALL)` | **已做**（`KeyboardIndex.ets:2706`） | 0 |
| 2 | `x` | 剪切 | `sendExtendAction(CUT)` | **已做**（`:2711`） | 0 |
| 3 | `c` | 复制 | `copyThenCollapse()` | **已做**（H-204） | 0 |
| 4 | `v` | 粘贴 | 剪贴板面板 + PasteButton | **已做**（H-204/H-207） | 0 |
| 5 | `h` | ← | `moveEditorCursor(3)` | **未接**（长按现在只弹符号气泡） | 低 |
| 6 | `j` | ↓ | `moveEditorCursor(2)` | 未接 | 低 |
| 7 | `k` | ↑ | `moveEditorCursor(1)` | 未接 | 低 |
| 8 | `l` | → | `moveEditorCursor(4)` | 未接 | 低 |
| 9 | `m` | Delete | `deleteForwardSync(1)` | 未接（`deleteEditor` 已有私有实现） | 低 |
| 10 | `s` | Home | `getTextIndexAtCursorSync` + `selectByRangeSync({0,idx})` + `moveCursorSync(3)` | 未接 | 中 |
| 11 | `d` | End | 同上 + `getForwardSync` 测总长 + `moveCursorSync(4)` | 未接 | 中 |

### B 类：能做但要么改数据、要么有前提

| # | 键 | 长按 = | 做法 | 前提/风险 |
|--:|---|---|---|---|
| 12 | `q w e r t y u i o p` | `_ - + = \| \ [ ] { }` | 数据侧：把这 10 个符号塞进 `getHiddenSymbols(ch)` 的表，**复用现有气泡选择器**（长按弹气泡→滑到目标→抬手出符号） | 现在这 10 键已有气泡（原有内容），要**换/合并**符号集，属数据变更 |
| 13 | `z b , . / ; '` | `` ` `` `~` `<` `>` `?` `:` `"` | 同上 | 同上 |
| 14 | `Shift_L` | 大写锁定 | 本地三态已有（`shiftOn` 单击/双击锁定），只需补「长按直接锁」 | 无 |
| 15 | `space` | 无长按 | 不动 | — |
| 16 | `BackSpace` | 无长按（`repeatable: true` 连删） | 已有 `startBackspaceRepeat()` | 0 |
| 17 | 回车 | `CommitComment`（编码上屏） | 引擎侧 `commit_composition(session)` 已存在（`fanxing_napi.cpp:846` 区域），napi **未导出** ⇒ 需加一个 `commitComposition` 方法 | 要改 `cpp`（Qoder 区） |
| 18 | 「符號」「數字」副键盘 | 单击/长按各进一个 | 我们已有 `?123` 符号面板，需对齐分类 | 数据 |

### C 类：明确不做（真做不到，不挂账）

| 键 | 长按 = | 为什么做不到 |
|---|---|---|
| `f` | Page_Up | `ExtendAction` 只有 `SELECT_ALL/CUT/COPY/PASTE` 四个（SDK `:2984-3003` 实测），无翻页；`InputClient` 无滚动 API |
| `g` | Page_Down | 同上 |
| `n` | Insert（覆盖模式） | 鸿蒙编辑框没有 Insert 覆盖语义，`ExtendAction` 无此项；无法从输入法侧改宿主编辑模式 |

---

## 三、改动落点（文件级）

| 文件 | 归属 | 改什么 | 谁写 |
|---|---|---|---|
| `entry/src/main/ets/pages/KeyboardIndex.ets` | 共享热点区 | `LetterKey` 的 `LongPressGesture.onAction` 加 `h/j/k/l/m/s/d` 七个分支（现在只有 a/x/c/v 四个） | **Qoder**（业务交互） |
| `entry/src/main/ets/inputmethod/KeyboardController.ets` | 共享热点区 | 新增 `moveCursorBy(intent)` 封装、`goLineStart()` / `goLineEnd()` 两个方法 | **Qoder** |
| `entry/src/main/resources/rawfile/rime/*.yaml` + `KeyboardIndex` 的 `ALT_CHARS` | 数据 | 17 个键的长按符号集对齐 40 键 | **Qoder**（数据变更） |
| `entry/src/main/cpp/fanxing_napi.cpp` | Qoder 独占 | 新增 `commitComposition` 导出（包 `g_rime->commit_composition` + `TakeCommit`） | **Qoder** |

**我（CodeArts）本轮不动任何一行**——按 D-030，这些都属业务逻辑/数据变更，归 Qoder 出包。

---

## 四、分三步走（每步都能独立验收，不一次改 11 个键）

> 理由：H-103 的教训就是「一次改 7 项，改一处错一处」。这次拆成三步，每步真机验完再走下一步。

### 第 1 步：光标与删除（5 个键，纯调用既有 API，不碰数据）——**建议先做这步**

| 键 | 行为 | 验收判据 |
|---|---|---|
| `h` | 长按 → 光标左移一格 | 在「你好世界」中间位置，长按 h 一次，光标左移一位（用可见光标位置或后续输入位置证明） |
| `j` | 长按 → 下移一行 | 多行文本，光标下移一行 |
| `k` | 长按 → 上移一行 | 同上 |
| `l` | 长按 → 右移一格 | 同 h 反向 |
| `m` | 长按 → 删光标后一个字 | 光标在「你好世界」的「你」后，长按 m，「好」消失 |

**这一步 0 风险**：只调 `moveEditorCursor` / `deleteForwardSync`，H-177 真机已验证过 `moveEditorCursor(3)` 可用。

**「按住连续」要不要**：Trime 里这 5 个键是**单次触发**（不是 repeatable），建议**先做单次**，按住连移留到第 3 步再评估——连移需要定时器，H-200 已经踩过「组件消失定时器还活着」的坑。

### 第 2 步：行首行尾（2 个键，语义要定）

| 键 | 行为 | 待定问题 |
|---|---|---|
| `s` | 长按 → 光标到行首 | **行首还是全文首？** 见第一节末的说明。我建议第一版做全文首，UI 上不承诺「行」 |
| `d` | 长按 → 光标到行尾 | 同上 |

**这一步有一个必须先真机验的前提**：`selectByRangeSync` + `moveCursorSync` 的「选中后左移等于取消选中并把光标放到选区左端」这个行为，**我只有 SDK 语义推断，没有真机实测**。所以第 2 步开工前要先做一个 20 行的探针（长按 s 只打日志、打印 `getTextIndexAtCursorSync` 前后值 + 是否有选中），确认真实行为再写正式逻辑。

### 第 3 步：符号四件事（数据 + 引擎）

| 键 | 行为 | 依赖 |
|---|---|---|
| 17 个键长按出符号 | 弹气泡选符号 | 数据：符号集对齐；UI：复用现有气泡 |
| 回车长按编码上屏 | 无候选时把 preedit 上屏 | cpp 新增 `commitComposition` |
| Shift 长按锁定 | 长按 ⇧ 直接锁定大写 | 本地状态 |
| 「符號」「數字」副键盘对齐 | 分类顺序对齐 40 键 | 数据 |

---

## 五、我建议的顺序与理由

**先做第 1 步（h/j/k/l/m 五个键），理由三条**：

1. **零数据变更、零引擎改动**，只加 5 个 `else if` 分支调用已有 API ⇒ 不会牵动 H-202~H-207 那批刚修好的东西；
2. **主人最常感知的就是这个**——「上下左右的方向键也弄到键盘上了」「插入删除」，光标移动和删除是打字时的高频动作；
3. **可独立验收**，失败也不用回滚别的。

**第 2 步（s/d）单独做**，因为语义（行 vs 全文）要主人或 Qoder 定一句话，且要先跑探针。

**第 3 步最后做**，因为它同时碰数据和 cpp，最容易出事。

---

## 六、这套方案的已知不确定点（不藏着）

| # | 不确定点 | 现状 | 怎么解 |
|--:|---|---|---|
| 1 | `selectByRangeSync` 后 `moveCursorSync` 能否把光标准确定位到选区端点 | **只有 SDK 语义推断，无真机实测** | 第 2 步开工前写探针真机跑一次 |
| 2 | `getTextIndexAtCursorSync` 返回的是 UTF-16 下标还是字符下标 | 未知；中文/emoji 可能差 1 倍 | 探针一并量（用含 emoji 的文本） |
| 3 | `End` 的「本行尾」拿不到，只能到全文尾 | 确认做不到行内语义 | 做全文尾，标为已知差异；或先不做 d |
| 4 | 长按 h/j/k/l 与现有「长按弹气泡」冲突 | h/j/k/l 现在有符号气泡吗？**我没核** | 第 1 步开工前先 `grep` 确认 `ALT_CHARS` 里这 4 个键有没有符号集 |
| 5 | 按住连续移动要不要 | Trime 是单次 | 先单次，第 3 步评估 |

---

## 七、如果主人点头，我下一步具体做什么

1. 先跑一个 **30 行探针**（`M3Probe.ets` 里加一页，或临时脚本），把上面 1/2/3/4 四个不确定点一次量完，**真机出日志**；
2. 把探针结果写成本文档 §八，**连同「h/j/k/l 有没有符号气泡」的 grep 结果**；
3. 拿这份实测结果请 Qoder 出第 1 步的变更包；
4. 变更包到后我复核 + 跑离线闸门，真机验收由 Qoder 装机。

**我现在不动任何代码**，等主人对「先做第 1 步」这件事点一句。