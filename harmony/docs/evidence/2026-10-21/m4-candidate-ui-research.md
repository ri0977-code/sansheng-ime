# M4 · 候选栏调研：抄哪个成熟实现（2026-10-21）

主人本轮指令原话：**「去找安卓的参考…成熟的布局，成熟的方案…照着改就行了」**。
本文是调研结论 + 选定方案 + 落地拆分。**本轮未动任何生产代码**，M4 的 Lua 移植一行都还没落盘。

## 1. 问题定性（我们自己卡了几天的东西）

现状 `KeyboardIndex.ets:233-307`：候选栏是**非滚动 `Row`**，每个条目 = `词 + comment 同行横排`。
三向反查（五笔码/拼音/英译）全塞在同一行右侧 → 条目固有宽度被 comment 撑大 →

- 竖屏一页只能放下 4~5 条，横屏 9~11 条（H-042 弹性方案已 VERIFIED，但那只是「不截断」，条数依然少）；
- 空间不够时只能整条隐藏 comment（`showComment=false`），**反查能力就看不见了**——为保住五笔反查，等于牺牲条数；
- 为压这个矛盾已经改了 4 轮（H-035 紧凑样式 → H-042 截断 → M-029 固定条数 → M-030 弹性），全是横向一维布局内部的调参，**方向本身就错了**。

主人给的成熟做法有两条，都指向「把 comment 从候选的横向空间里拿出来」：
① 反查另起一行（不占候选宽度，候选能多显示）；② 候选栏右端一个 ▼，点开在键盘区铺出多行候选网格。

## 2. 找到的参考（逐个核实过，许可证已判）

### 2.1 kanonIME —— **本机已 clone 并通读，MIT，代码可直接搬改**（首选）

- 仓库 `https://github.com/ysk0518/kanonIME`，分支 `feat/candidate-presentation-20261017`，
  commit **`f5cfca9110b0793a2d08205f01b78d0e6fafb2b0`**。经 `ghfast.top` 镜像 clone，
  **已用 github.com `git ls-remote` 的 sha 校验一致**（镜像内容可信）。本机路径 `F:/qoderwork/_ref_kanon`。
- LICENSE = **MIT**（`LICENSE:1-3`，Copyright (c) 2026 ysk0518 and kanonIME contributors）；
  `NOTICE` 另注明它**派生自 OpenHarmony KikaInputMethod 官方示例（Apache-2.0）**——也就是说这套候选栏本身就是「鸿蒙官方示例 + MIT 增强」的产物，是我们能拿到的最贴身的成熟实现。
- 它是 HarmonyOS NEXT / ArkTS 原生输入法（日语·英语，Mozc 引擎），**候选栏部分与引擎无关，可以直接改**。

它已经实现了主人要的全部三个机制（关键行）：

| 机制 | 位置 | 做法 |
|---|---|---|
| **候选条占两行** | `components/CandidateBar.ets:129-141` | 横向 `List` + 每个 `ListItem` 是一个 `Column{ 词1, 词2 }`，`DEFAULT_CANDIDATE_ROWS = 2`（`common/CandidateLayout.ets:4`）→ 同样的横向宽度**候选数量翻倍** |
| **行高/降级算法** | `common/CandidateLayout.ets:9-26` | `rowHeight = max(28, ceil(fontSize*1.2*fontScale+6))`；`barHeight = max(toolbar, rowHeight*rows)`；`candidatePanelHeight()`：**剩余键盘高度 < 160vp 时自动退回单行**，不硬撑 |
| **辅助信息不吃候选宽度** | `CandidateBar.ets:107-128` | 预编辑/读音放在**左侧 44vp 窄列**（rows=2 时 12fp）或行首（rows=1 时 `constraintSize({maxWidth:96})`），不进候选条目 |
| **▼ 展开覆盖键盘** | `CandidateBar.ets:142-148` + `151-159` | 右端 40vp 按钮 `cand_expand`，图标 `ic_arrow_down`/`ic_arrow_up` 切换；展开态 = `Scroll(纵向)` 包 `Flex({wrap: FlexWrap.Wrap})`，高度 = `keyboardHeight - toolbarHeight` → **整个键盘区变成候选面板** |
| **网格里长词可换行** | `CandidateBar.ets:90-91` | 展开态 `full=true` → `maxLines(3)` + `maxWidth:'100%'`，普通态 `maxLines(1)` + `maxWidth:280` |
| **选中项自动跟随可见** | `CandidateBar.ets:58-74, 92-97` | 翻页时用 `stripScroller.scrollToIndex(i, true, CENTER)`；展开态用 `onAreaChange` 记录每格 top/height 存 Map，`revealExpandedSelection()` 手动滚进视口 |
| **点选即上屏并收起** | `CandidateBar.ets:75-80` | `tapCandidate()` → 选词 + `this.expanded = false` |
| **展开态底部工具行** | `CandidateBar.ets:160-167` | 「取消」（`cancelCompose`）+「部分上屏」（`partialCommit`）两个文字按钮 |

### 2.2 fcitx5-android —— LGPL-2.1，**只借设计，不搬代码**

本机 `F:/qoderwork/_ref_fcitx5-android/LICENSE` 首行实测 `GNU LESSER GENERAL PUBLIC LICENSE`。
按仓库规矩（GPL 系只借设计），**它的价值是印证主人说的「反查放上面一行」确实是标准做法**：

- `input/preedit/PreeditUi.kt`（经镜像 raw 抓取确认）：`verticalLayout { upView; downView }` 两行独立文本，
  `textSize = 16f`，高亮候选的光标用 `append('|')` + `CursorSpan` 表示 —— **aux 行整宽独立，完全不与候选抢横向空间**，
  插入位置在 `input/InputView.kt` 里 `above(keyboardView)`。
- 展开候选 = 网格 + 右侧窄列翻页键，交互语义与 kanonIME 一致。
- ⚠ 本节的具体数值（列数 6/8、每页 48）来自调研 agent 读上游源码的转述，**本机 sparse-checkout 未成功，未逐行复核**。
  落地不依赖这些数字（我们自己按实测宽度算），如需精确值再补抓。

### 2.3 Trime —— GPL-3.0，**只借设计**

形码（五笔/仓颉）场景里唯一把「词与码的相对位置」做成主题开关的实现：
`ime/candidates/CandidateItemUi.kt` 提供 `CommentPosition { RIGHT, TOP, OVERLAY }`，
`TOP` = comment 在上、约占 cell 高 40%，词在下占 60%；主题键 `comment_position / comment_height / comment_text_size / candidate_view_height` 等。
→ 我们**展开网格**里每格用这个「码上词下」的叠法（语义照抄，代码自己写）。同样未在本机复核，属设计参考。

### 2.4 其余候选（结论：不用）

- `AOSP LatinIME`（Apache-2.0）`MoreSuggestionsView` + `config.xml` 数值可照抄，但它是「长按键弹层」机制、英文联想词场景，双行候选语义不如 kanonIME 贴合，且要自己移植大量 Java。
- `fcitx-contrib/fcitx5-harmony`（GPL-3.0）：键盘是 **ArkWeb 网页**（`pages/VirtualKeyboard.ets` 只有一个 `Web()`），无原生候选栏，不可用。
- `gitee.com/ohos_port/applications_inputmethod`（KikaInput 官方示例，Apache-2.0）：**单行、无展开**，是 kanonIME 的祖先，不如直接用 kanonIME。
- `harmony-pinyin-ime` / `HengIME` 等：**仓库无 LICENSE 文件 → 默认保留所有权利，代码一律不许搬**。

## 3. 选定方案（三生鸿蒙版候选栏 v2）

**骨架抄 kanonIME（MIT，可直接改代码），反查行的语义借 fcitx5，展开格内叠法借 Trime。**
三层，全部在候选层，**不动键盘壳、不动 Rime 桥、不扩接口**：

1. **候选行（第 1 行）**：`List(横向)`，条目只放**词**，不再内联 comment（删掉现在 `KeyboardIndex.ets:258-266` 的内联 comment）。
   `rows` 取 1 或 2 由 `candidatePanelHeight` 式降级规则决定（剩余高度不足 160vp → 1 行）。
   → 同样宽度可显示的候选数**直接翻倍**，且长词不再需要 `showComment=false` 这种「舍反查保条数」的取舍。
2. **反查行（第 2 行）**：整宽一行 12fp 灰字，显示**当前页第一条**（或用户按住的）候选的三向反查全文（`ni hao ma` / 五笔码 / 英译中）。
   数据接口已有（`RimeCandidate.comment`），**不需要新接口**。
3. **▼ 展开面板**：右端 40vp 按钮（照 `cand_expand`），展开 = `Scroll` + `Flex(wrap)` 铺满 `keyboardHeight - 候选行高`，
   每格「码上词下」（Trime `TOP` 语义），点格 → 上屏并自动收起，底部工具行放「取消 / 上一页 / 下一页」。
   展开态调 `keyboardController.setPageSize(n)`（n = 行×列，接口上限 50，已在 v0.1.5/v0.1.6 落地），
   翻页仍走 `flipPage(±1)`；**展开态禁用候选条的左右滑 `priorityGesture`**（避免和纵向 Scroll 双手势打架，H-034 的「一滑一页」只在收起态要求）。
4. **面板高度联动**（我们踩过的坑，必须写进验收）：`KeyboardController.createPanel` 是**先算尺寸再 `setUiContent` 再 `resize`**（H-037 教训，`KeyboardController.ets:214-241`），
   现在候选区高度从常量变成 `rows`×行高，服务侧的 `rowVp`/面板高度必须把新增的第二行算进去，否则横屏首帧会重演「功能行被裁」。

### 为什么不选另外两条路

- 「每格词+码纵向叠、收起态就这么显示」：反查全量可见最彻底，但每格宽度被最长的那条形码决定（我们的 comment 有长有短），条数依然上不去 —— 这是 H-042 的原病根，只是从横排换成竖排。
- 「只做 ▼ 展开、收起态保持现状」：改动最小，但主人第一条抱怨（反查占候选空间）没解决，日常打字还是 4~5 条。

## 4. 落地拆分

| 谁 | 做什么 | 参考文件（本机可读） |
|---|---|---|
| **CodeArts**（`pages/**`+`components/**` 归他） | 候选栏 v2 三层：横向 `List` 双行 + 反查行 + ▼ 展开网格 + 展开态手势互斥 + `setPageSize` 重算 | `F:/qoderwork/_ref_kanon/entry/src/main/ets/components/CandidateBar.ets`（171 行，MIT 可搬）、`.../common/CandidateLayout.ets`（26 行） |
| **CodeArts** | 服务侧面板高度把第二行算进去，保留 160vp 降级 | `.../common/KeyboardLayout.ets:47-63`（`panelHeight`/`toolbarHeight`/`standardKeyHeight`） |
| **Qoder**（我） | ① 真机验 `setPageSize(24/30)` 在展开态返回整页且 `flipPage` 正常；② 若要做「上下滑移动高亮条」再补 `highlightIndex`（潜在接口 v0.1.9，现在不扩）；③ 继续 M4 引擎侧 Lua 去 Windows 依赖 + 自造词/自调频 | `docs/INTERFACE.md` §4 |
| **Qoder** | 装机 + 真机量：竖屏候选条数（基线 4~5）、横屏（基线 9~11）、反查行完整不截断、展开网格点选上屏、转屏不裁行 | `scripts/build.ps1` / `sign.ps1` / `install.ps1` |

## 5. 一句话给主人

主人说的两个做法在安卓上确实是标准方案，而**鸿蒙 ArkTS 生态里已经有一家 MIT 授权的 kanonIME 把它整个做完了**（双行候选条 + ▼ 展开覆盖键盘 + 选中自动跟随 + 高度不够自动降级），
代码已 clone 到 `F:/qoderwork/_ref_kanon` 并核对过 commit sha，**可以直接改**，不用我们自己发明布局。
按这套改，竖屏候选数预计从 4~5 条提到 8~10 条，反查还全看得见。
