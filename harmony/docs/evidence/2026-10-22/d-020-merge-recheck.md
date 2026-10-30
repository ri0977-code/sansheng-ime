# D-020 合并落地复核 + 我上一条结论的公开更正

**作者**：Qoder（审核验收）· 2026-10-22 16:1x
**对象**：CodeArts 15:33–16:04 那一轮改动（`symbols.yaml` 删除之后的标点/符号合并）
**结论先说**：
1. **我 15:5x 写下的核心结论「105 组斜杠符号与 8 个多值标点键在任何构建里都没生效过」是错的，公开撤回**（今天我自己撤回的第三条）。已签名的三个包实测都在用这条路径，13:35 真机 `/szd` VERIFIED 与包内证据互相印证。
2. **CodeArts 已经把该并的并进自有 `default.yaml` 了**，比我判的做得多；但合并**不完整**（`/xx` 组只剩 9 组，丢 197 组 / 约 4,540 个符号）且**有保真度缺陷**（中文弯引号 `‘ ’ “ ”` 在合并中被写成 ASCII 直引号，等于彻底丢掉）。这两条是新开的 **H-093**。
3. `symbols.custom.yaml` 从 `SHARED_FILES` 撤回 ✅（M-079② 已照做）；`DATA_VERSION` = `m8-parity-v20` ✅（H-091 源码侧已修）。
4. **被我不该取消的两条真机补测恢复**：多义标点、九键 `/szd`——而且现在正好能验出 H-093 那个弯引号缺陷。

---

> **⚠ 16:3x 追加：本文件第二、三、三·五节描述的是 16:04 那版「并表方案」的状态，CodeArts 已于 16:2x 撤回该并表 ⇒ 那些行号与组数已不再是当前状态。**
> **当前真实状态见第七节**（2026-10-22 16:3x 快照：逐包解包 + `git diff HEAD` 实测）。
> 第二节的「201 → 9 组、丢约 4,540 个符号」是**并表方案下的**代价，已作废；撤回后的现状是 **0 组**（引擎无 `/xx` 数据），取舍见新单 H-095。
> 第三节的 (1)（中文弯引号 + YAML 合法性）**仍然成立且已收窄为 4 行**；(3)(4)(5) 随并表撤回已不在源码里。

## 一、我错在哪：三个已签名包 + 一条链路的实测

我把「`symbols.custom.yaml` 加进 `SHARED_FILES` 无效」这一条**正确**的观察，越界写成了「整条斜杠符号路径从来没活过」。前者只关于那个文件怎么释放，后者关于功能是否存在——我拿前者当后者用了。

实测（`zipfile` 解包，逐文件字节数与内容）：

| 包 | 字节数 | 时间 | `wubi_pinyin.custom.yaml` | `punctuator/import_preset` | `script_translator@pinyin` | 包内 `symbols.yaml` |
|---|---|---|---|---|---|---|
| `entry-default-m066-signed.hap` | 28,175,592 | 12:55 | 5,332 B | **`symbols`** | 无 | **有 28,473 B** |
| `entry-default-m067-cr01-signed.hap` | 28,174,855 | 13:06 | 5,332 B | **`symbols`** | 无 | **有 28,473 B** |
| `entry-default-release-signed.hap` | 27,822,532 | 13:25 | 5,332 B | **`symbols`** | 无 | **有 28,473 B** |
| `entry-default-unsigned.hap`（本轮工作树） | 28,136,180 | 16:04 | 6,042 B | `default` | **有** | 无 |

识别链路（从 13:06 那份**真机 VERIFIED** 的包里读出来的原文）：

```
wubi_pinyin.schema.yaml   recognizer: import_preset: default
wubi_pinyin.custom.yaml   recognizer/patterns/punct: "^/([0-9]0?|[A-Za-z]+)$"
                          recognizer/patterns/rawNum: "^/[A-Za-z0-9]*[0-9][A-Za-z0-9._+%-]*$"
                          punctuator: import_preset: symbols
symbols.yaml              punctuator/symbols:  201 组 /xx 符号
symbols.custom.yaml       patch: punctuator/symbols/+ 107 组 / punctuator/half_shape/+ 若干多义键
```

⇒ `/szd` 命中 `punct` 识别式 → punctuator 从 `symbols` 预设取 `punctuator/symbols['/szd']` → 出 ⒈⒉⒊…**这条链在 m066 / m067-cr01 / 13:25 release 三个签名包里都是通的**，和 13:35 的 hilog 证据（`cand=7 all=28` → 上屏 ⒈）完全一致。

**所以 D-020 选 A 不是「实测失去 0 项」，是真的砍掉了一项已经在用的功能**——主人拍板接受这个代价，我无权把它写成没有代价。这句话我同时用在 `docs/DECISIONS.md`、`docs/ISSUES.md` H-088/H-092、`docs/MAILBOX.md` M-079、`docs/ROADMAP.md` 第 1 站里，逐条改正。

## 二、16:04 新包的合并范围（这才是主人真正要的数字）

工作树 `entry/src/main/resources/rawfile/rime/default.yaml`：3,957 B / 120 行 → **5,449 B / 132 行**（+1,492 B）。合并内容实测：

- `recognizer/patterns/punct: "^/([0-9]0?|[A-Za-z]+)$"` **已加进自有 default.yaml**（第 61 行）——识别式不再依赖上游文件。✅ 这条我做对了：`docs/release/punctuation-merge-proposal.md` §三 的判据（「九键/26 键都要有 punct 识别式」）被采纳。
- `punctuator/half_shape` 共 32 键，其中 **10 个多值键**：`'` `"` `` ` `` `_` `#` `$` `^` `[` `]` `/` `\`。
- `punctuator/symbols` 共 **9 组**：`/zt /tj /jd /dc /lm /lmd /szd /szk /szm`。

对照旧包的有效值（`symbols.yaml` 基线 201 组 + `symbols.custom.yaml` 覆盖 107 组）：

| 项目 | 旧（13:06 VERIFIED 包） | 新（16:04 工作树） | 差 |
|---|---|---|---|
| `/xx` 符号组 | 201 组（基线） | **9 组** | **−197 组** |
| `/xx` 符号条目总数 | ~4,540+ 项 | 108 项 | **约 −4,540 个符号** |
| 半角多义标点键 | 8 键（custom 覆盖） | 10 键 | 覆盖面保住，值有出入（见 §三） |

丢的 197 组包含 `/pp` `/kx` `/bz`（主人已确认不在宣传口径内）以及 `/fh /dn /xq /mj /0…/9 /A…/Z` 等日期、单位、货币、希腊、罗马、注音类整片。

**这条数字必须进商店口径**：1.0.0 的「斜杠符号」实测只剩 9 组，宣传文案与应用内说明不能再暗示完整符号表。目前 `docs/release/store/listing.md` 与操作说明书没有出现「105 组/200 组符号」这类承诺（已核），所以不用改文案，但**H-093 若选补齐，则要同步改说明**。

## 三、合并保真度缺陷（新 H-093，逐条给原文行）

1. **中文弯引号被写成 ASCII 直引号**（P1，用户直接可见）
   - 旧有效值（`symbols.custom.yaml` patch，13:06 包里在跑）：`"\'": ["‘", "’", "「", "」"]`、`"\"": ["“", "”", "『", "』"]`
   - 新 `default.yaml:73-74`：`"'": ["'", "'", "「", "」"]`、`"\"": ["\"", "\"", "『", "』"]`
   ⇒ 前两档从 `‘’` / `“”` 变成**两个一模一样的 ASCII 引号**。后果：简体中文默认引号 `“ ”` 与 `‘ ’` 在标点多义循环里**打不出来了**（`/` 键系列也没有别的入口给弯引号）。这是真回归，不是风格问题。
2. **`` ` `` 键第二档是三个反引号** — 新 `default.yaml:79` `"`": ["｀", "```"]`。
   **【16:1x 追加分流：这一条不是 CodeArts 的手误】** —— `symbols.custom.yaml` 原行就是 `"`": ["｀", "```"]`，他抄得一模一样。同理下面 3、4、5 三条（`/` 的 `[commit: "/"]`、`/szd` 的 `⒑` 错位、`/lm` `/lmd` 尾部 ASCII `17 18 19` 与 `ⅹ` 移尾）**全部与 `symbols.custom.yaml` 逐字符相同**（去空格比较）。⇒ 它们继承的是 dyy 那张表自带的毛病，属「要不要顺手修」，不属本轮引入的回归；我在 ISSUES 里把这三条的措辞改成「上游数据原样带过来的已知怪值」，并把定性优先级从 P1 降到 P2/P3。
   **唯一真正由本轮改写引入的差异是 §三.1 那两个引号键**：`'` 与 `"` 的候选前两档被从 `‘ ’` / `“ ”` 写成 ASCII `'` / `"`，其余 17 个键（9 组 `/xx` + 8 个多义标点）都是原样抄。这条判据我可以复跑，别按我这段读成「全表都抄错了」。
3. **`/` 键写成列表套 map** — 新 `default.yaml:77` `"/": [commit: "/"]`。YAML 能解析成「含一个映射的流式序列」，但 librime punctuator 的候选项按字符串处理；旧写法是单值 map `{ commit: … }` 或直接字符串。**这条必须真机确认**：若 punctuator 解析失败，可能连带整块 `half_shape` 不生效（那就是标点全崩），是最高风险的未验项。
4. **`/szd` 第 19 档错位** — 旧 `⒈…⒑⒒…⒛` 顺序；新 `⒈⒉⒊⒋⒌⒍⒎⒏⒐⒒⒓⒔⒕⒖⒗⒘⒙⒚⒑⒛`（第 19 项写成 `⒑`＝10，第 10 项缺位）。13:35 真机验的是前 5 档（`⒈⒉⒋⒍⒏`），这段错位在那次验收里看不见。
5. **`/lm` `/lmd` 尾部多出 ASCII `"17" "18" "19"`，且 `ⅹ`/`Ⅹ` 被挪到末尾**（新 19 项 vs 旧 16 项）。罗马数字 10 跑到列表最后，中间夹三个阿拉伯数字串——像是从 custom 改版照抄，但那份 custom 我没能按路径取到（见 §五 方法教训），所以此条**标注为「来源存疑、待 CodeArts 说明抄的哪一份」**，不判为缺陷。
6. **全角块的 `"""` 让自有 `default.yaml` 变成非法 YAML**（P1，同 §5 判据 3）
   - 全角块（`full_shape`，约第 129–130 行）写的是 `"'": "'"` 与 `"\\"": """` —— 后者三个连续双引号是未转义的值。
   - 实测 `yaml.safe_load()` 报：`while parsing a block mapping ... expected <block end>, but found '<scalar>' ... "\"": """`。
   - 对照：**上游 `symbols.yaml` 用同一个解析器是 PARSE OK 的**（`symbols.custom.yaml` 反而 FAIL，因为它用了非法转义 `"\'"`）。也就是说现在包里唯一合法的标点数据文件是那份我们决定不带的上游文件，我们自己并出来的这份解析不过。librime 自带宽松解析、未必当场炸，但这是运气，不是正确性。
   - 影响面判据：若 librime 也在这一行失稳，`punctuator` 整块（含 `half_shape`）可能一起丢 ⇒ 标点全崩。真机验「切全角打 `"`」+「半角打 `.`」即可定性，属于**必须上机**的一类。

## 三·五 许可侧：**D-020 想关的敞口没关掉，只是换了个位置**（新 H-094，我自己 15:5x 刚警告过的坑，这一轮真的发生了）

`NOTICE` 现在把 `entry/src/main/resources/rawfile/rime/default.yaml` 挂在 **[本项目自写] Apache-2.0** 条目下。而 16:04 工作树里这份 `default.yaml` 新增的 1,492 B，实测**是 `symbols.custom.yaml` 的逐字符抄本**（去空格比较：9 组 `/xx` 全等，8 个多义标点键除 `'` `"` 外全等），而 `symbols.custom.yaml` 的主体版权按安卓 `THIRD_PARTY_NOTICES.md:41/96` 属 dyy。

CodeArts 在文件里写的注释也是同一个误会：`default.yaml:65` / `:122` 都写「（自有数据，与安卓逐字节相同）」——**「与安卓版逐字节相同」只证明同源，不证明自有**，这正是我 15:5x 自己犯过、当天更正过的错误（见 `d-020-landing-audit.md` §8），我提前在方案 §四 写过「抄进 `default.yaml` = 把第三方内容写进自称原创的文件」，还是没拦住。

数量口径：合并进自有文件的第三方派生内容 = **9 组斜杠符号 + 10 个多义标点键，约 145 个符号条目**；相对 `symbols.custom.yaml` 全表（107 组 / 2,093 项）是**小 subset**，但性质变了：**从「一个可识别的第三方文件」变成「自称原创文件里的一段」**，后者在审核与诉讼口径里更难解释。

处理办法（route A 的一致延伸，成本极低，我这边已改，CodeArts 不需要动数据）：
1. `NOTICE`：在 `default.yaml` 那行加注「含 dyy 斜杠符号表派生片段（`punctuator/symbols` 9 组 + `half_shape` 多义键 10 个，约 145 项），随 dyy 授权档披露」⇒ 已从 Apache-2.0「纯自写」改为「自写 + 派生片段」。
2. `third-party-declarations.md` §四：dyy 档增加这一条（同包内位置由独立文件变为 `default.yaml` 内嵌）。
3. 应用内声明页文案（M-070 那条线）同步，随下一次构建生效。
4. 若主人想彻底「100% 自有」，唯一干净做法是**自己重新整理这 19 个键的候选集**（不参照 dyy 那份表），成本约半天；否则就按 route A 标注。**我把这条摆给主人选，不替他决定**，因为它和 D-020 的「不用上游文件」是同一问题的两半。

## 四、其余本轮已核实的部分（对 CodeArts 的确认）

- `DATA_VERSION` = `m8-parity-v20`（`RimeDataInstaller.ets:101`），与数据改动同轮 ⇒ **H-091 源码侧关闭**，真机侧要等新包 marker 落地后复测 `nihao` 候选条数才改 VERIFIED。
- `SHARED_FILES` 里 `symbols.custom.yaml` 条目已撤回（`:110-137` 实测无该项；`:116-117` 留了两行空行，属观感）。H-092 主诉求完成 ⇒ **H-092 关闭**。
- `SHARED_FILES` 列出的 17 个数据文件在 `rawfile/rime/` 下**全部存在**（逐个 `os.path.exists` 实测）⇒ 删文件没有留下悬空引用。
- `symbols.custom.yaml` 连文件本身也从 `rawfile` 删掉了（不在包里，磁盘上也没有）⇒ dyy 血脉数据在 1.0.0 的敞口**比我上轮估计的还小**：许可侧我只需把 NOTICE 的措辞从「1.0.0 不再打包 `symbols.yaml`」扩到「`symbols.yaml` 与 `symbols.custom.yaml` 两份都不打包」。已改。
- **H-087 状态我接受为 FIXED**，但依据要说清楚：用户可见的冲突文案已消失（全库检索「剪贴板」只剩 3 处、「插件」只剩 3 处，逐处核对是 `SettingsPage.ets:6/17` 文件头注释、`SettingsCategoryPage.ets:428` 不可达 `case` 的注释与日志、`RimeDataInstaller.ets:141` 注释，`SettingsModels.ets` 里的分类文案已摘）。**残留是死代码与过期注释，不再是「申报与实际不一致」**，并入 H-090 的整入口摘除一起做即可。
  - 顺带：CodeArts 把 H-087 行首状态改成 `FIXED` 时删掉了 `A` 后面那个竖线，整行从 7 格变 6 格，表格已错位——我按同格式补回（这是共享文档的排版纪律问题，本周第二次，我在 memory 里加了自检命令）。

## 五、验收判据（写死，可复跑）

1. `/xx` 组数：`python` 解析 `rawfile/rime/default.yaml` 的 `punctuator/symbols` 子树，键数应 = 补齐后的目标组数（当前 9，缺失 197）。
2. 弯引号：`default.yaml` 的 `'` 与 `"` 两键的候选列表**必须包含 `‘’“”`**，实测当前 0 命中 ⇒ FAIL。
3. YAML 合法性：`yaml.safe_load(rawfile/rime/default.yaml)` **当前 FAIL**，报 `while parsing a block mapping … expected <block end>, but found '<scalar>'`，出错行是全角块的 `"\\"": """`。判据：自有 `default.yaml` 必须能被标准 YAML 解析通过才允许进包（librime 容错不等于我们该依赖容错）。上游 `symbols.yaml` 用同一判据是 PASS 的，可直接当参照。
4. 真机：切全角打 `"`、半角连打 `'` 四档、`/` 键打一次、九键与 26 键各打 `/szd`、26 键打 `nihao` 数候选条数。
5. 记账：报产物全名 + `stat -c %s` 实测字节数 + 签名调试包。

## 六、方法教训（我自己的）

1. **「文件里搜不到某个键」不等于「功能没生效」**。我今天两次踩同一条：先是 `grep -c '^\s+/\S+:'` 因为上游用单引号包裹键名而返回 0（`'/' :` 与 `"/szd"`），后是把 `SHARED_FILES` 的无效性外推成路径无效。凡「不存在/没生效」这种否定结论，必须换两种取法（缩进路径解析 + 去引号匹配）并交叉验证再写。
2. **对已签名包的直接解包，优先级高于读工作树**。工作树是「打算发什么」，包是「发过什么」。13:35 那条真机 VERIFIED 就躺在 `project-symbol-panel-status` 记忆里，我没有把它和包内容对撞——**记忆里的 VERIFIED 清单就是用来防这种外推的**，下次写「从来没生效过」之前先查 VERIFIED 列表（这条和 10:5x 那次「删掉已 VERIFIED 交互」是同一个失误的两面：一次是删功能，一次是否认功能存在）。
3. **容错解析器掩盖真错误**：`symbols.custom.yaml` 里的 `"\'"`、新 `default.yaml` 里的 `"""`，都不是合法 YAML，却因为 librime 自带宽松解析一直没炸。判据应主动收紧到「标准 YAML 可解析」。

---

## 七、16:3x 快照：并表已撤回，CodeArts 在动的实际状态（这一节是当前唯一有效的状态描述）

测量时间 2026-10-22 16:2x–16:3x。对象 = 工作树 + 16:19 产出的 `entry-default-unsigned.hap`
（28,132,705 B，mtime 16:19:28）与上一次提交（HEAD，`fd60d8f` 一侧的 src）。

### 7.1 三方对照：包里有什么、工作树里有什么、上次提交里有什么

| 维度 | 13:06 签名包（m067-cr01） | 16:19 unsigned HAP | 工作树（16:2x） | HEAD（上次提交） |
|---|---|---|---|---|
| `symbols.yaml` | **28,473 B 在** | 不在 | 不在 | 从未进 git 跟踪 |
| `symbols.custom.yaml` | **11,696 B 在** | 不在 | 不在 | 从未进 git 跟踪 |
| `wubi_pinyin.custom.yaml` | 5,332 B，`import_preset: symbols` | 5,910 B，`import_preset: default` | 同左（5,910 B） | 6,042 B，`import_preset: default` |
| `default.yaml` | 3,957 B，无 `symbols` 块 | **3,949 B / 120 行，无 `symbols` 块** | 同左 | 3,838 B，无 `symbols` 块 |
| `rawfile/symbols/symbols.json` | 在（34,984 B） | **在（34,984 B）** | 在 | 在 |
| 引擎侧 `/xx` 组数 | 201 | **0** | **0** | 0 |
| 半角 `'` 的值 | `‘` 系（多值） | **`'`（ASCII，被压平）** | 同左 | `’` |
| `yaml.safe_load(default.yaml)` | — | **FAIL** | FAIL | **PASS** |
| `DATA_VERSION` | v19（装到机器不生效，H-091） | — | **`m8-parity-v20`** | v19 |

### 7.2 结论一：并表已撤回，H-094 在源码层面自愈

`git diff HEAD -- entry/src/main/resources/rawfile/rime/default.yaml` 只剩 4 行改动，**没有并入任何
`punctuator/symbols` 块**；`wubi_pinyin.custom.yaml` 的注释已改成「本包无 `punctuator/symbols` 数据，
符号输入走 App 符号面板（`rawfile/symbols/symbols.json`，H-061 已验）」；
16:19 的包解包确认两个上游文件都不在包内，而 App 自有的符号面板数据仍在 ⇒
**自有文件里不再有任何 dyy 派生的符号条目**，「第三方派生内容藏在自称原创的文件里」这个问题不存在了。
`NOTICE` 与 `docs/release/legal/third-party-declarations.md` 已同步改口（原先写的「内含派生片段」撤销）。

**残留两处归我兜**：① 三个已签名旧包（m066 / m067-cr01 / release）里仍含那两个上游文件 ⇒ **那三个包不得提审**；
② `docs/release/legal/` 与 `NOTICE` 里 5 处提到斜杠符号的措辞，待主人对 H-095 拍板后统一改口。

**另一条实测事实**：`symbols.yaml` / `symbols.custom.yaml` **从未进入 git 跟踪**
（`git log --all -- <path>` 无记录，`git ls-tree -r HEAD entry/src/main/resources/rawfile/rime/` 无该条目），
只存在于早期工作区与早前构建出的包里 ⇒ 仓库侧没有把它们带出去的路径，风险面仅限旧构建产物。

### 7.3 结论二：H-093 收窄为 4 行，且修法明确

`git diff HEAD` 的全部内容就是这两处（`half_shape` 与 `full_shape` 各 2 行）：

```
-    "'": "’"          →  +    "'": "'"
-    "\"": "“"         →  +    "\"": """""
```

两个后果：① **1.0.0 打不出中文弯引号**（半角 `'` 出 ASCII 直引号）；② **该文件过不了标准 YAML 解析**，
`yaml.safe_load` 报 `while parsing a block mapping … expected <block end>, but found '<scalar>'`（line 65→72），
而**同一判据下 HEAD 那版是 PASS 的** ⇒ 这是本轮引入的，不是历史遗留。
**修法 = 把 HEAD 里这 4 行原样恢复**，`yaml.safe_load` 与中文引号两条判据同时变绿。

### 7.4 结论三：并表撤回带来的产品后果 = 需要主人拍板（H-095）

撤回并表 ⇒ 引擎侧 `/xx` 组数由 9 组变为 **0 组** ⇒ 13:06 签名包里可用的 `/szd` → `⒈⒉⒋`
（H-081 13:35 真机 VERIFIED）在 1.0.0 将**不再存在**。这是功能取舍，不是缺陷：
A = 1.0.0 不做（= 当前源码状态，零许可尾巴）；B = 自己重新整理一批真正自有的（约半天，不抄社区那张表）。
**主人不回就按 A 推进。** App 自有的符号面板（116 类 / 2,093 项，`symbols/symbols.json`）与这条路径无关，不受影响。

### 7.5 这轮同时核到的、可直接进包的部分

`DATA_VERSION` = `m8-parity-v20` ✓；`SHARED_FILES` 17 项且无 symbols ✓；
`privacy.html` 的 4 处按 M-078 改完 ✓（`git diff HEAD -- entry/src/main/resources/rawfile/legal/privacy.html`）；
`phoneComment_Filter.lua` 已进 `lua-files.txt` 与 `rime.lua` ✓；
拼音翻译器 `script_translator@pinyin` 在 `engine/translators/+` 里 ✓；
`KeyboardController.ets` 新增 `hideKeyboard()`（H-085 截图用）✓。

### 7.6 另记一条我自己的方法教训（量字节不能用文本读）

我一度用 `io.open(p, encoding='utf-8').read()` 再 `len()` 当字节数，把 CRLF 的 `\r` 折掉后报成 3,830 B，
与磁盘上的 3,949 B 对不上，差点当成「他在我眼皮底下又改了一次」而重新分析一轮。
**量字节必须用二进制读**（`open(p,'rb')`）；文本读出来的是字符数。
同理，工作树与 git 对象之间还有 CRLF/LF 差异：HEAD 的 `default.yaml` 是 LF（3,838 B），
工作树与包内是 CRLF（3,949 B），**两侧字节数不可直接相减**。

---

---

## 八、16:5x 快照：他 16:2x 又把并表做回来了 —— 而且这次做对了（第七节已被本节取代）

**这一节是当前唯一有效的状态描述。** 时间 2026-10-22 16:5x。
对象 = 16:50:17 产出的 `entry-default-unsigned.hap`（28,133,596 B，mtime 16:50:17）。

### 8.1 今天的三个版本（说明为什么前两节反复作废）

| 版本 | 时间 | 产物 | 状态 |
|---|---|---|---|
| v1 并表 | 16:04 | `default.yaml` 5,449 B，9 组 + 10 键 | 引号被压平 + YAML 不合法（H-093 ①②），许可措辞错（H-094） |
| v2 全撤 | 16:19 | `default.yaml` 3,949 B，**0 组** | 引擎无 `/xx` ⇒ 功能落差（H-095）；引号仍被压平 |
| **v3 并表（现行）** | **16:50** | **`default.yaml` 4,840 B / 128 行，9 组 + 10 键** | **引号已修回、YAML 已合法、行内已加来源标注**；剩 3 处上游怪值 + 1 处行为变化 |

他在这一个半小时里改了三次方向，我三次都得重写结论 —— **记录这一点本身有价值：以后对他"正在动"的产出，只能给"快照 + 条件式结论"，不能给终局判断。**

### 8.2 v3 逐项实测（全部从 16:50 的包里读，不是从工作树读）

| 判据 | 结果 |
|---|---|
| `yaml.safe_load(packaged default.yaml)` | **PASS**（v1/v2 都是 FAIL） |
| `punctuator/half_shape` 的 `'` | `["‘", "’", "「", "」"]` ✓ 中文弯引号回来了 |
| `punctuator/half_shape` 的 `"` | `["“", "”", "『", "』"]` ✓ |
| `punctuator/full_shape` 的 `'` / `"` | `‘` / `“` ✓（与上一次提交一致） |
| `punctuator/symbols` | **9 组**：`/zt /tj /jd /dc /lm /lmd /szd /szk /szm` |
| 斜杠符号条目数 | 9 组 / **117 项** |
| `half_shape` 多值键 | **10 个键 / 28 项**（`'` `"` `` ` `` `_` `#` `$` `^` `[` `]`） |
| **许可标注用到的项数** | **117 + 28 = 145 项**（与 16:1x 的估计完全一致） |
| 与上游 `symbols.custom.yaml` 逐组比对 | **9 组全部逐字符相同**（`/zt /tj /jd /dc /lm /lmd /szd /szk /szm`） |
| `half_shape` 多值键与上游比对 | 6 个逐字符相同；`'` 的值相同但键的转义写法不同（上游写 `"'"`，他写 `"'"` —— **他顺手把上游自身的 YAML 非法转义修对了**）；`[` 仅空格不同；`` ` `` 的首项由上游的 `｀`（全角）改为 ASCII `` ` ``（**他顺手修了上游的一个错字**） |
| 行内来源标注 | `default.yaml:60` = 「D-020：多义标点与 /xx 斜杠符号从 symbols.custom.yaml 并入（dyy 斜杠符号表派生片段）」；`:117` = 「D-020：/xx 斜杠符号（dyy 斜杠符号表派生片段）」⇒ **M-080 要的措辞他写进数据文件了** |
| `symbols.yaml` / `symbols.custom.yaml` | 不在包内 ✓ |
| `rawfile/symbols/symbols.json` | 34,984 B 在 ✓（App 自有符号面板取数） |
| `DATA_VERSION` | `m8-parity-v20` ✓ |
| `SHARED_FILES` | 17 项，无 symbols ✓ |
| `main_pages.json` | 仍注册 `SettingsPage` + `SettingsCategoryPage`（**等主人 H-090 拍板**，见 M-082） |

### 8.3 v3 仍存在的三处 —— 全部是**上游原样带来的**，不是他改坏的

用 13:06 签名包里的上游 `symbols.custom.yaml`（11,696 B）逐行比对，证据如下：

1. `"/": [commit: "/"]` → v3 里是 `{"commit": "/"}` 塞在候选列表里。
   **上游第 22 行原文就是 `[commit: "/"]`** ⇒ 逐字符继承。
   **为什么仍值得修**：librime 的标点候选按字符串处理，列表里混一个 map 是非法形状 ⇒ 半角 `/` 这一档可能取不到值。
   这是**功能性**问题（P2），但不是他引入的 —— 是他把上游的毛病一起搬进来了。
2. 反引号键 `` ` `` 的第二档在 v3 里是三个反引号连写（上游首项是全角 `｀`，v3 已改成 ASCII `｀`→`` ` ``，方向是对的）。
   **上游第 24 行原文** ⇒ 继承（他只把首项的全角 `｀` 改成了 ASCII，方向是对的）。
   三个反引号作为一个候选输出给用户 = 怪值（P3）。
3. `/lm`、`/lmd` 的尾部是 ASCII 字符串 `"17" "18" "19"`（`/lm` 还把 `ⅹ` 挪到了末尾）。
   **上游第 36–37 行原文** ⇒ 继承。罗马数字表尾部混进三个阿拉伯数字（P3）。
4. `/szd` 的第 10 档是 `⒒`、第 19 档才是 `⒑` ⇒ **`⒑`/`⒒` 两档位置互换**
   （**上游第 38 行原文**，与 13:06 签名包里那份逐字符相同 ⇒ 真机 13:35 测出来的带圈数字本来就是这个顺序）。
   纯观感问题（P3）。

### 8.4 一处**我们自己的基线**与 v3 不同、且是用户能看见的行为变化

半角 `\`（反斜杠）：我们上一次提交的自有 `default.yaml` 里是 `''` → 打出来是反斜杠；
v3 里是 `"\": "、"` → **打出来是中文顿号「、」**。
这是**上游 `symbols.custom.yaml:21` 原文**（逐字符继承），但它改的是**我们自己原有的行为**，不是恢复上游行为。
⇒ 需要主人拍一句：**反斜杠要打反斜杠（我们原来的），还是按上游改成顿号？** 我建议改回反斜杠 ——
路径、代码、命令里反斜杠是常用字符，顿号是中文标点，两者用途不重叠。（已并入 H-095 一并回单。）

### 8.5 结论（条件式，因为产物还在动）

- **H-093 的 (1)(2) 在 v3 里已修复**（引号恢复 + YAML 合法）⇒ 判据①②转绿，只差装机实测。
- **H-093 的 (3)(4)(5) 判定为上游继承**（本节 8.3 给出逐行证据），降为 P2/P3「要不要顺手修」，
  **不作为本次出包的阻断项**；其中 (3) 半角 `/` 那一档建议在出包前顺手改成字符串。
- **H-094 回到 OPEN，但 remedy 已由 CodeArts 就位**：数据文件行内标注已加、我们自己的声明侧我已改好
  （`NOTICE` + 第三方声明把 `default.yaml` 改列为「自写 + 含 dyy 派生片段 145 项」）。
  ⇒ 剩下的只是**主人拍板要不要保留这 9 组**（H-095），不是许可瑕疵。
- **v3 是今天唯一一个"数据正确 + 声明一致"的版本**；最终以他出的**签名 debug HAP** 为准，我再解包复核一遍。

