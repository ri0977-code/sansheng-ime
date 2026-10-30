# M6 内容闸门复核（源码级 + 包级）· 2026-10-22 21:4x · Qoder

## 一、为什么要复核这一遍

13:25 那份 release `.app` 是当天上午打的，落后当前源码很多。它跑 15 项内容闸门得到
**4/15、10 项阻断**——但那 10 项里混着两类东西：**「早就改好了，只是包旧」**和**「真的还没改」**。

把这张表原样发给 CodeArts，等于让他去改已经改完的东西。主人原话「一直在让他改键盘，
闹心改一处错一处」——这种活儿正是要多花一轮的来源。本文件的目的是把两拨分开。

**复核对象**：
- 旧包：`entry/build/default/outputs/default/sansheng-ime-1.0.0-release.app`（13:25，11,791,326 B）
- 新包：`entry/build/default/outputs/default/entry-default-unsigned.hap`（21:15，28,184,481 B，83 条目）
- 源码：当前工作区（`KeyboardIndex.ets` 21:29 又改过，比新包还新）

## 二、13:25 那 10 项阻断，逐项归位

| # | 检查项 | 13:25 旧包 | 21:15 新包 | 性质 | 证据 |
|---|---|---|---|---|---|
| ① | 上游符号文件 | FAIL | **PASS** | 旧包特有 | `git log --all -- "*symbols.yaml"` **零命中** ⇒ 这两个文件一直是未跟踪的上游拷贝，13:25 时还在工作区，后被删；新包 `rawfile/rime/` 内无 |
| ② | 斜杠符号 9 组 | FAIL（组数=0） | **PASS（9 组）** | 旧包特有 | `default.yaml` 的 `punctuator/symbols` = /zt /tj /jd /dc /lm /lmd /szd /szk /szm |
| ③ | yaml 可解析 | PASS | PASS | 两版都过 | — |
| ④ | 中文弯引号 | PASS（`'` = 单值 `’`） | **PASS（4 值 `‘ ’ 「 」`）** | 旧包只有一种引号 | 新版更全 |
| ⑤ | `script_translator@pinyin` | FAIL | **PASS** | 旧包特有 | `wubi_pinyin.custom.yaml:31` |
| ⑥ | `import_preset` 指向 default | FAIL（指向 symbols） | **PASS** | 旧包特有 | `wubi_pinyin.custom.yaml:76` |
| ⑦ | 不声称「设置保存在沙箱」 | FAIL | PASS（**但公示版那一侧当时还没同步，见 §四**） | 旧包特有 + 新缺口 | — |
| ⑧ | 仅 VIBRATE 无 INTERNET | PASS | PASS | 两版都过 | `module.json5` |
| ⑨ | 图标非四宫格 | FAIL（20/64 行 ≥2 段） | **PASS（0/64 行）** | 旧包特有 | AppScope 两层 18:09 已换 |
| ⑩ | 不含探针页 | WARN | **WARN（仍在）** | **未解决** | `main_pages.json` 仍注册 M3Probe/LandscapeProbe |
| ⑪ | 包内有 NOTICE 全文 | FAIL | **PASS（73,388 B）** | 旧包特有 | `rawfile/legal/notice.html` 17:57 |
| ⑫ | 不让用户去「安装目录」找许可 | FAIL | **PASS** | 旧包特有 | `AboutPage.ets:370` 改为「可在应用内直接阅读」 |
| ⑬ | About 页标 LGPL-3.0 + 五笔主码表 | FAIL | **PASS** | 旧包特有 | `AboutPage.ets:211-223` |
| ⑭ | 版本号 1.0.0 | PASS | PASS | 两版都过 | — |
| ⑮ | deviceTypes = [phone] | FAIL（phone+tablet） | **PASS（[phone]）** | 旧包特有 | `module.json5:7-10` |

**结论**：那 10 项阻断里，**9 项在当前源码和 21:15 新包里已经不存在**，只剩 ⑩ 探针页这一条 WARN。
⇒ **提审候选 `.app` 必须重打**，13:25 那份不能提审。

## 三、给闸门加了一个「源码级」快检模式（省一轮构建）

`scripts/check_app_content.py` 原来只能查包。问题是：布局/数据改动后的第一道验收往往在**还没构建**
时就想知道内容对不对，等构建完才发现要返工，已经白跑一圈。

新增 `--source`：`SrcCtx` 把包内路径映射回工作区源码（`rawfile/rime/`、`rawfile/legal/`、
`module.json5`+`app.json5` 合并成包内 `module.json`、`main_pages.json`、`AppScope` 两层图标）。
源码里测不出来的项（打包后才有的 `modules.abc`）用 ets 源码字符串近似，并在输出里显式标注
「源码级快检不能替代包上复核」——**不许把测不出来当成通过**。

**一致性验证**（源码级 vs 包级，同一份 21:15 源码）：两边都是 **14/15、阻断 0**，逐项结论一致。
**回归验证**（包模式跑旧 `.app`）：仍是 **4/15、阻断 10**，与改动前完全相同 ⇒ 没把包模式改坏。

## 四、复核时抓到一个**包级闸门看不见**的缺陷

### 现象
`docs/release/legal/privacy.html` 与 `terms.html`（**这一份是要托管给 AGC 的公示版**）与
应用内 `entry/src/main/resources/rawfile/legal/` 那两份**正文不一致**，公示版仍写着：

> 词库、用户词典、自造词与**全部设置**只存在于你的设备上
> 用户词典、自造词、**中英文与简繁等设置，均保存在本应用沙箱内**

### 为什么闸门没抓到
第 7 项只查**包内** `rawfile/legal/terms.html`。公示版不在包里，闸门根本没看过它。
⇒ 这是一个「grep-0 ≠ 不存在」的典型：包内干净，公示版照样错。

### 为什么它要紧
1. **AGC 驳回 TOP6 = 「应用内与提交信息不一致」**（`docs/release/legal/agc-privacy-form.md:15` 自己写的口径）。
   公示版和应用内版说不一样的东西，正是这条。
2. 公示版那句「全部设置保存在沙箱」**正是 H-090 判定为不实的表述**：32 个设置项 0 个被消费
   （`sansheng_prefs` 全库只有隐私弹窗和设置页自己打开），中英文/简繁是引擎运行期状态，
   根本没有代码把它存进沙箱。

### 根因
15:4x 我改了 md 母版（`docs/release/legal/privacy-policy.md` / `user-agreement.md`）并出了 HTML
补丁单 `privacy-html-sync-2026-10-22.md`；CodeArts 按单改了**包内 rawfile 那一份**（16:15 / 17:58），
但 **`docs/release/legal/` 这一份没重新生成**，一直停在 15:26 的旧版本。

### 修法（不碰 `entry/src/**`）
只重生成托管版：`scripts/build_legal_html.py` 的 `build()` 两份 + `build_index()`。
包内那两份**一个字没动**——先在临时目录生成后逐字节比对，确认「新生成 = 现有包内版本」，
证明包内那份确实是生成器产物、没有手改，才敢只改托管版。

### 验证（含已知坏样本）
| 样本 | 第 7 项结果 |
|---|---|
| 托管版还原成修复前那一版（`git show HEAD:...`） | **FAIL**，报出 4 条具体原因：`与全部设置` / `用户词典与设置` / `设置保存在应用沙箱` / `自造词与设置保存在`，并指两份正文不一致；总表 13/15、阻断 1 |
| 修复后 | **PASS**：「两处均无『设置保存在沙箱』表述，且公示版与应用内版正文逐条一致」；总表 14/15、阻断 0 |

### 附带修的一处
托管版页脚原本是给开发者看的话——「本页由 Markdown 源文件生成；修改请编辑
`docs/release/legal/*.md` 后运行 `python scripts/build_legal_html.py`。」——**用户能看到**。
已改成与应用内一致的用户可见文案：「三生输入法 V1.0 · 本页内容随应用版本更新」。

### 防复发
第 7 项已扩成「应用内 + 公示版两处都不许出现该表述，且两份正文逐条一致」，并入闸门。
以后谁改了 md 母版却只重建了一边，闸门立刻报。

## 五、还剩三件事（都不在我这边）

1. **提审候选 `.app` 要重打**。21:15 之后 `KeyboardIndex.ets` 又改过（21:29，H-103 手势在写），
   代码没冻结，重打两遍是浪费。等 H-103 交付 → 我独立构建 → 字节数与他报的逐字节一致 →
   签名打包 → 对 `.app` 再跑一遍 15 项。
2. **`main_pages.json` 里 4 个不该进提审包的页面**：
   `LandscapeProbe`/`M3Probe`（⑩ WARN，H-098）、`SettingsPage`/`SettingsCategoryPage`
   （D-021 已定 1.0.0 摘设置入口；首页那个「设置」按钮已经摘掉了，`Index.ets:79-83` 的
   `openSettings()` 只剩死代码，没有任何地方 pushUrl 过去 ⇒ **用户够不着**，但两个页面
   还在包里、还有 946 行死代码）。
3. **`entry/src/main/resources/base/media/app_icon.png` 还是 DevEco 蓝方块**（48×48，182 B，
   2026-10-19 基线以来没动过）。它是 `EntryAbility.icon` 和 `startWindowIcon` 用的图 ⇒
   **启动窗口显示的是蓝方块**，和桌面图标（三条键帽）不是一个图形。
   素材已备好：`docs/release/store/icon/gen-appicon-216.png`（`make_icon.py` 纯几何自绘，
   与分层母版逐像素一致），直接覆盖即可。

## 六、本轮我改了什么（都在 Qoder 归属范围内）

| 文件 | 改动 |
|---|---|
| `scripts/check_app_content.py` | 加 `--source` 快检模式；第 7 项扩成双份法律页比对；12/13 项改用 `ui_blob()` 统一入口 |
| `scripts/build_legal_html.py` | 托管版页脚改成用户可见文案 |
| `docs/release/legal/privacy.html`、`terms.html` | 由 md 母版重新生成（同步 H-090 口径） |
| 本文件 | 证据 |

**没有改**：`entry/src/**` 一行未动（`git diff --stat` 只显示 `docs/release/legal/` 三处）。
