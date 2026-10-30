# H-106 底栏收起键 · 粘贴即用工单（Qoder 出，CodeArts 执行）

> **2026-10-24 00:28 注**：本文件写于 H-097 时期，第 97 行「蓝底三条键帽 `gen-appicon-512.png` 直接覆盖」已被 **D-022（黑底金含外环）／H-147** 取代，**不要再按那一段替换图标**；收起键（§1 起）仍有效。

> 2026-10-23 01:4x 由 Qoder 生成。这份东西**不替你改代码**：`entry/src/**` 归你。
> 我做的事只有一件——把「到底加什么、加在哪、会不会挤爆」三件事量准，并且**先在我机器上
> 用我自己的验收判据验证过：照这个贴，判据就翻转**。我复现用的副本写在仓库外
> （`_audit_tmp\2026-10-23\candidate_with_h106.ets`），你的工作树我一行没动。

## 1. 要贴的板块（从 HEAD 原样抽出，逐字节，不是我重新设计的）

来源：`git show HEAD:entry/src/main/ets/pages/KeyboardIndex.ets` 第 1795-1815 行。
里面用到的常量与辅助函数在当前工作树**都还在**（实测：`FUNC_ICON_SIZE` L219、
`KEY_MARGIN` L214、`RADIUS` L212、`TEXT_FUNC` L211、`BG_FUNC` L202、`keyBg()` 29 处、
`keyH()` 20 处），所以贴进去不需要新增任何定义。

```ets
      // H-085：收起键盘按钮
      Stack() {
        SymbolGlyph($r('sys.symbol.chevron_down'))
          .fontSize(FUNC_ICON_SIZE)
          .fontColor([TEXT_FUNC])
      }
      .backgroundColor(this.keyBg(BG_FUNC, 'hide'))
      .borderRadius(RADIUS)
      .layoutWeight(0.7)
      .height(this.keyH())
      .margin(KEY_MARGIN)
      .onClick(() => {
        keyboardController.hideKeyboard();
      })
      .onTouch((event: TouchEvent) => {
        if (event.type === TouchType.Down) {
          this.pressKey('hide');
        } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
          this.releaseKey('hide');
        }
      })
```

## 2. 贴在哪（两个分支各一份，缺一不可）

当前工作树 `BottomBar()` 在 L1960..L2210（03:4x 复跑机检仍是这两个锚点，`KeyboardIndex.ets` 自 01:17:02 未再改动 ⇒ 本工单行号未失效），里面并列两个可见 `Row()`：

| 分支 | `Row() {` 行号 | 紧跟的下一行（这就是锚点） | 现有键（pressKey id 顺序） | layoutWeight 求和 |
|---|---|---|---|---|
| `panelMode === 'symbol'` | L1962 | `Text('ABC')` | sym123, comma, numpad_switch, space, dot, enter | 9.4 / 6 键 |
| `else`（字母/九键） | L2088 | `Text('?123')` | sym123, lang, space, dot, enter | 8.8 / 5 键 |

**做法**：把上面那块插进这两个 `Row() {` 之后、`Text('ABC')` / `Text('?123')` 之前
（HEAD 里收起键就排在底栏第一位，保持这个顺序）。
先插行号大的（L2088）再插 L1962，行号不会被自己的插入顶掉；或者直接按锚点文字找，别看行号。
缩进按你文件里的层级对齐就行（工作树里 `Row()` 的子节点是 8 空格，上面这块从 HEAD 抽出来是 6 空格，
ArkTS 不看缩进，我只保证**内容与括号层级逐字节照搬 HEAD**）。

## 3. 为什么不会挤爆（算过了，不用再猜）

`.layoutWeight` 在 `Row` 里是**按比例分宽**，不是按像素占位：加一格只会让所有键等比变窄，
不会溢出、不会换行。实测求和：symbol 9.4 + 0.7 = **10.1 / 7 键**（HEAD 那版单栏含收起键是
7 键 9.9，几乎一样）；else 8.8 + 0.7 = **9.5 / 6 键**。
如果嫌视觉上挤，只许减 `KEY_MARGIN` 的左右值（上下 3px 别动）或字号——**不许删功能键、
不许把收起藏进长按或二级面板**（主人定的铁律）。

## 4. 我这边怎么验（已复现过一遍，判据确实翻转）

```
python scripts/h106_precheck.py --kb entry/src/main/ets/pages/KeyboardIndex.ets   # 现在：两栏各 FAIL
python scripts/h106_precheck.py --kb <贴好之后的副本>                              # 贴好：BLOCK 全过
```

上面第 2 步的副本我已经实测跑过：**exit 0，`底栏[symbol]有收起键` / `底栏[else]有收起键` 双双转 OK，
五个功能键一个没少，底栏没越界碰面板 API**。所以这不是「你去试试」，是「这条路我验证通了」。

**我说清楚验到哪一步**：结构闸门翻转是静态判据能给的保证，**ArkTS 能不能编过我没替你做**
（我只在仓库外的副本上跑解析，没把你的工作树送进构建）。所以我仍要你的 checkpoint 提交 +
你自己那次构建的字节数，再由我独立构建、**比对 unsigned 文件的字节数**（不是比 hash：HAP 是 ZIP，
每条条目的时间戳取构建时刻，跨两次构建**不可能逐字节相同**，只有长度相同；判据见 `docs/BUILD.md` §2.1）。

## 5. 交付形态（不齐我就不会构建，构建了我也不会装）

1. 只动 `BottomBar()` 这一个函数；**不碰 `KeyboardController.ets`**（`:290-300` 的 `hideKeyboard()`
   已经是 `panel.hide()` 不销毁面板，够用）。
2. `git add entry/src/main/ets/pages/KeyboardIndex.ets && git commit`（checkpoint 提交，
   上一轮 H-109 的教训：五轮改动全在工作区，没有回退点）。
3. 跑 `python scripts/h106_precheck.py`（不带 `--kb`，判据含交付形态）⇒ **exit 0 再来报交付**。
4. 在 `docs/WIP.md` **或** `docs/MAILBOX.md` 加一行交付记录，署名 `CodeArts`，写清你那次构建的
   **unsigned HAP 真实字节数**（>=6 位，形如 `28179829B`；抄我示例里的 `1234567` 不算，我的行也不算你的）。
   **位置随意**，不必写在台账末尾（旧写法「必须尾部」已于 03:0x 作废，见 M-115／H-122：尾部要求会让
   你我互等死锁）。但**时间戳必须写成能被读出来的形式**，形如 `2026-10-23 04:05`；写成 `~22:35`、
   「昨天下午」我算不出属不属于本轮 ⇒ 直接判「没有交付」。窗口：最新行往前 3 小时以内。
5. **不要装 01:17 那两份产物**（`entry-default-unsigned.hap` 28,179,829 B / signed 28,288,696 B）——
   那版结构判据没过（两栏都没收起键），装了你还得再装一次，主人要输两遍密码。

## 6. 顺带（H-105 图标，同批出包，别单独一轮）

`entry/src/main/resources/base/media/app_icon.png` 现在实测仍是 **48x48 / 182 B 全不透明**
（DevEco 模板，自 10-19 没动过），被 `module.json5:30,32` 的 `icon`/`startWindowIcon` 引用
⇒ 内容闸门第 ⑨b 项一直 WARN。**素材我已经出好在仓库里**：
`docs/release/store/icon/**gen-appicon-512.png**`（512x512 蓝底三条键帽）**直接覆盖那个文件名即可**，
引用名 `$media:app_icon` 不用改。⑨b 的双向判据我早就验过：坏样本（48x48 模板）被抓，好样本（这张）转 PASS。

> **01:5x／03:4x 两次更正**（原文不删，见本节末）：① 文件名从 216 改成 **512** —— `docs/evidence/2026-10-23/h108-icon-layer-0156.md`
> 量到桌面 tile 读的是**能力层**图标（`module.json5:30` `icon: $media:app_icon`），不是 `AppScope` 那层分层图，
> 所以要覆盖的是能力层这张；H-108 现口径以 `docs/ISSUES.md` 那行为准。② 同批还要**回退** `module.json5` 里
> `ohos.entry.mainability` 那条 metadata（03:4x 实测它**至今仍在工作区未提交**，是个不生效的猜测，M-111 已判）。
> ③ 判据口径也变了：自 H-115 起，喂给检查器的是 `.app` 时 ⑨b/⑩ 是**阻断**不是 WARN。
> **别为图标单开一轮**，跟 H-106 同批出包。


## 7. 更正记录（改的是我这份工单，不是你的代码）

| 时间 | 位置 | 原来怎么写 | 为什么改 |
|---|---|---|---|
| 2026-10-23 03:4x | §5.4 | 「在两份台账**尾部**各加一行」 | 尾部要求 03:0x 已作废（M-115／H-122）：任何人补一行就把交付遮住 ⇒ 你我互等。新判据只看署名＋真实字节数＋**可读时间戳**＋3 小时窗口，位置随意 |
| 2026-10-23 03:4x | §6 | 覆盖 `gen-appicon-216.png` | H-108 01:5x 实测桌面 tile 读**能力层** `$media:app_icon` ⇒ 改为 `gen-appicon-512.png`，并同批回退 `module.json5` 的 `ohos.entry.mainability` |
| 2026-10-23 03:4x | §6 | 「⑨b 报 WARN」 | H-115 起：输入是 `.app` 时 ⑨b／⑩ 改判**阻断** |
| 2026-10-23 04:5x | §4 末／§5.4 | 「由我独立构建**逐字节比对**」 | 措辞会让人以为要比两份 HAP 的 hash／整文件字节。实测：01:17 那份 unsigned 里 **83 条 ZIP 条目的时间戳全等于构建时刻 01:17:18** ⇒ 同一份代码两次构建不可能逐字节相同，只有**长度**相同。判据明确写成「比 unsigned 文件的字节数」，另见 `docs/BUILD.md` §2.1。§5.4 要求你报的那个数**不变**，还是真实字节数 |

教训记一条：工单类文档一旦发出去，判据变了就得回去改它 —— CodeArts 照的是这份文件，不是 `docs/MAILBOX.md` 里我后写的更正。
