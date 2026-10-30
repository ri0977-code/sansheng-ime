# 三生输入法 · 鸿蒙版 第三方许可与来源审计（2026-10-22 12:2x，Qoder）

范围：打进 HAP 的**全部随包数据**（`entry/src/main/resources/rawfile/**`，70 个文件）与
`NOTICE` / `LICENSES/` / `rawfile/rime/README.md` 的声明是否对得上；
判定基准 = 主人自己的安卓产品（D-015）与上游仓库的实际 LICENSE 文本。

只读审计，未改任何数据文件。复现命令（都是本仓库里的只读脚本）：

```
python scripts/license_gap.py 2026-10-22      # 随包文件 vs 声明清单
python scripts/apk_parity.py 2026-10-22       # 鸿蒙数据 vs 安卓发布 APK rime-data
python scripts/third_party_audit.py 2026-10-22 # 逐文件来源命中（安卓根 / dyy / LGPL / Apache / GPL）
```

摘要统一用 **md5 前 16 位**。今天之前散在记录里的 `6d089695…`、`ea929515…`、`f12ee3a6…`
是 **sha256** 前 16 位，两套值不能互比——这是我在核对 `symbols.yaml` 时踩到的坑，已在
`third-party-audit-data.md` 开头写明，后续记录请统一按 md5。

---

## 一、结论摘要

| # | 级别 | 结论 |
|---|---|---|
| F1 | **P0** | 随包 70 个文件里 **48 个在 `NOTICE` 和 `rime/README.md` 里都查不到**（41 个 `rime/lua/**` + `symbols.yaml` + `symbols.custom.yaml` + `symbols/symbols.json` + `lua-files.txt` + `legal/*.html` + README 自身）。上架包对外声明「Apache-2.0」，而包里近一半内容没交代来源。 |
| F2 | **P0** | 其中 **29 个文件与 `happyDom/dyyRime` 字节一致（仅行尾差异），共 3,197,403 B；另有 12 个是 dyy 同名改写（**此数已作废，见文末 2026-10-24 补记**）**。dyyRime 仓库**没有 LICENSE 文件 = 保留所有权利**，授权至今未取得——安卓侧 `LICENSE` 第 4 行白纸黑字写着「另有 54 个文件来自未附许可证的 happyDom/dyyRime，授权尚未取得」。鸿蒙 `NOTICE` 对 dyy **一字未提**。 |
| F3 | **P1** | `NOTICE` 把 `wubi86.dict.yaml` 记成「KyleBing/rime-wubi86-jidian，Apache-2.0」，**错的**：与上游字节比对，我们的 2,289,631 B 版本最接近 `rime/rime-wubi`（其仓库 LICENSE = **LGPL-3.0**，本机实测 `D:/IDM/rime-wubi-master/rime-wubi-master/LICENSE`），jidian 只提供极点权重与词条补充（Apache-2.0，其码表源头 wubi-jidan-dict 本身无许可证）。安卓 `THIRD_PARTY_NOTICES.md` 第 30 行也是按 **LGPL-3.0** 记的。 |
| F4 | **P1** | `symbols.custom.yaml`（11,696 B）行级相似 **89%** 命中 dyy 的同名文件，即「dyy 斜杠符号表的改版」——安卓 `THIRD_PARTY_NOTICES.md` 第 41/96 行自己就是这么写的。它 12:00 刚随 M-059 进包（H-079），所以 F2 敞口在 12:00 之后**变大了**，不是变小了。 |
| F5 | 说明 | `symbols.yaml`（28,473 B，md5 `b4fe9b1fb5419b6c`）与安卓 1.10.1 发布插件 APK 里 `assets/usr/share/rime-data/symbols.yaml` **字节相同**，`/xx` 组数 201 = 201，`/jg` `/bh` 成员逐字符一致。**这一项判 PASS**：CodeArts 的「从 APK rime-data 取」是对的，我此前拿桌面 weasel 那份（28,729 B）当基准造成的「部首不一致」疑虑撤销（详见 `symbols-parity` 复测：`/kx` `/pp` 的差异是 PC weasel 与手机 APK 两份不同的部署副本，不是鸿蒙的缺陷）。它的来源仍需按 F1 补声明。 |
| F6 | P2 | `wubi86.dict.yaml` 的署名头两边不一致：鸿蒙这份文件头带 changelog 署名（Gong Chen / Yu Yuwei / Chen Xing / Wozy），安卓仓库那份（2,426,091 B，md5 `acc9ce3f5b55adae`）前 200 行**没有任何署名/许可注释**，而安卓 `THIRD_PARTY_NOTICES.md` 第 83 行却把「补署名头」划成了已完成。两份文件大小也不同（差 136 KB）。要么安卓文档过期，要么 seed 与仓库文件不是同一份——需要确认，别照抄对方的结论。 |

---

## 二、dyyRime 敞口有多大（可复核的数字）

`third-party-audit-data.md` §2 的口径：字节命中（含 CRLF→LF 归一）= 原样复制；同名不同字节 = 改写衍生。

- 原样复制 **29 个 / 3,197,403 B**：`lua/` 下的 `GUID.lua`、`dateTime*.lua`、`dic_4w*`、
  `dynamicPhrase_Filter.lua`、`eventsList*`、`help.lua`、`laneChangeAndSpace_Filter.lua`、
  `lunar*`、`phraseComment*`、`phraseExt*`、`phraseReplace*`、`pinyinAdding*`、`utf8String.lua`
  与配套 `.txt` 数据表。
- 同名改写 **12 个**（剔除两个同名噪声：`README.md` 相似 7% 是我方自写文档、`Custom_phrase.txt` 是 rime 通用文件名/用户数据）：
  `rime.lua`、`symbols.custom.yaml`、`wubi_pinyin.custom.yaml`、`Upper_Filter.lua`、
  `dic_4w_Filter.lua`、`inputShow.lua`、`inputShow_Filter.lua`、`runLog.lua`、`socket.lua`、
  `sysInfo.lua`、`phraseComment personal.txt`、`phraseExt personal.txt`。
- 与 dyy 无关 **24 个**（本项目自写或另有上游）：`default.yaml`、`sansheng_t9.schema.yaml`、
  `wubi86.dict.yaml`、`pinyin_simp.*`、`zh2en_*` / `en2zh_*` / `cn_pinyin_wp`、`opencc/*`、
  `symbols.yaml`、我方自写的 `abbrGloss_Filter.lua` / `codeLookup_Filter.lua` /
  `phoneComment_Filter.lua` / `rawEcho_translator.lua` 等。

也就是说：**随包数据里体积最大的一块 Lua 逻辑与数据表，来自一个没有授权的上游**。
这不是鸿蒙版新引入的问题——安卓版已经这么发了一版——但它是**上架前必须处理**的问题：
华为审核不会因为声明缺失而一定拒审，拒审风险在合规文件缺失，而**民事风险在未经许可复制他人作品**。
软著登记与「应用版权承诺」也要求权利来源清楚。

## 三、许可传染与处置边界（我的判断，不是法律意见）

1. **CC BY-SA 4.0（`zh2en_*`）**：义务 = 署名 + 这些数据继续以 CC BY-SA 4.0 分发。
   已在 NOTICE 第三节声明并随包 `LICENSES/CC-BY-SA-4.0.txt`，**代码不受影响**。现状 OK。
   （2026-10-22 14:2x 更正：`cn_pinyin_wp` 原先被记进本组，实测不成立，见 §八。）
2. **LGPL-3.0（`wubi86.dict.yaml` 码表）**：LGPL 用于**数据**时，义务基本是「保留许可与署名、
   提供许可文本」，不要求开源 ArkTS。改 NOTICE 即可，但必须**改对**。
3. **GPL-3.0 风险线**：`oh-my-rime` 仓库 LICENSE = GPL-3.0，本机 `D:/IDM/oh-my-rime-main/symbols.yaml`
   与我们那份字节不同（`bc6519a5…` 28,647 B vs `b4fe9b1f…` 28,473 B，行级相似 0.74），
   我们走的是 rime/weasel 数据血脉，**不构成 GPL 派生**。结论：不要为了「看起来更完整」把 oh-my-rime
   的文件搬进来，那才会把 GPL-3 拉进包里。
4. **dyyRime（无 LICENSE = 保留所有权利）**：上面三条的例外。没有授权就**没有**「改个声明就能用」的解法，
   只有 ① 取得授权 ② 换成有许可的等价实现 ③ 移除 三种。这是主人的决定，不是我能靠改文档消掉的。

## 四、我这轮能自己收口的（已在做/待做）

- 改 `NOTICE`：F3 的 wubi86 条目、新增 `[未授权上游] happyDom/dyyRime` 条目、新增 `symbols.yaml` /
  `symbols.custom.yaml` / `symbols/symbols.json` / `rime/lua/**` 条目，并把 F1 的 48 个文件按上面三档归好。
- 补 `LICENSES/LGPL-3.0.txt`（安卓仓库 `LICENSES/` 已有同源文本）。
- `rime/README.md` 的来源表补 `symbols.*` 与 `lua/` 两行，指向本审计（该目录允许改动的唯一例外就是许可/署名注释）。
- 提审前需要有一份「第三方声明」页的**内容源**：我把上面结论整理成可直接渲染的清单，交给
  CodeArts 填进 M-043 的应用内页面（不是让他判断许可，他只负责渲染）。

## 五、必须主人做的（集中列出，一次问清）

| 编号 | 事项 | 为什么只能你做 | 我建议 |
|---|---|---|---|
| O-1 | **对 `happyDom/dyyRime` 取得书面授权**：重开 issue（我 2026-10-20 22:37 用你的账号误关的那条 #9，0 回复）或直接邮件上游作者 `yaoyuan.dou`，请求 MIT/Apache 双许可或至少「允许商用并保留署名」的书面同意 | GitHub 登录态在你的账号上，且这是以著作权人身份对外发出的请求 | **优先做这一步**。拿到书面同意 + 在 NOTICE 里如实署名，F2 就能闭环；发不出去就先按 O-3 处理 |
| O-2 | 若 O-1 拿到**有条件**许可（例如要求署名/非商用），把原文贴给我，我据此改声明 | 许可条款的解释责任在著作权人 | 等 O-1 |
| O-3 | 若 3 日内拿不到回复，决定走哪条：**A 保留（承担风险并在 NOTICE 标注「授权申请中」）** / **B 剥离**（去掉 29 个原样文件 + 2~3 个 dyy 衍生滤镜，功能上会丢 4 字词典、节日/节气注释、phraseExt 等）/ **C 自研替换**（用我们自己已有的 `abbrGloss`/`codeLookup` 链路补齐，工作量给 CodeArts 评估） | 这是产品功能与法律风险的取舍 | 上架不等人：**先 B 的「最小可发版集」做备胎，同时推进 A**；C 作为 M7 之后的正式方案 |
| O-4 | 确认 F6：安卓 1.10.1 实际下发的 `wubi86.dict.yaml` 是不是仓库那份（2,426,091 B），署名头到底加在哪 | 只有你有安卓发布链路与 seed 目录 | 我把两边 md5 都记在 `third-party-audit-data.md`，你对一下 seed/asset 即可 |
| O-5 | AGC 提审时如果问到「第三方库/数据许可」，回答口径以本文件 + `NOTICE` 为准 | 提交动作在你的账号 | 我准备一段可直接粘贴的中英文说明 |

## 六、与 M6 的关系

不阻塞签名链路（证书已核验，`docs/release/SIGNING.md` §7），但**阻塞「合规收口」这一条**：
F1/F2 不收口，第三方声明页与 `NOTICE` 就是不实；提审材料里的权利承诺也无从签。
本轮我把能自己收口的声明部分全部改完，剩下的按 O-1~O-5 等你一句话。

## 七、补记（2026-10-22 14:0x，Qoder）：F1 附表里两处「待确认」收掉一处，并更正我方一处错记

**结论：`lua/abbr_en.txt`、`lua/abbr_num.txt` 判定为本项目自有整理数据，不再是许可敞口。**

复测证据（全部本机可复核）：

| 文件 | 大小 | md5 | 判定依据 |
|---|---|---|---|
| `rawfile/rime/lua/abbr_en.txt` | 17,146 B | `2500936430cdd59636340766e301a116` | 与 `F:/dshdesktopwork/sansheng-ime-android/rime/lua/abbr_en.txt` **逐字节相同** |
| `rawfile/rime/lua/abbr_num.txt` | 3,636 B | `6adbdfb79c3c48051ac698330bc53b0a` | 同上，与安卓数据根同名文件逐字节相同 |

两组 md5 与本文档所附数据表第 44–45 行记录的「安卓:lua/abbr_en.txt」「安卓:lua/abbr_num.txt」命中一致；
在 `D:/IDM/dyyRime-master`、`D:/IDM/oh-my-rime-main`、`F:/dshdesktopwork/rime-zh-en-dict` 三组参照里
按文件名（depth ≤3）查找**均无同名文件**。整理尺子见安卓仓自留记录
`F:/dshdesktopwork/sansheng-ime-android/_probe/abbr_candidates_20261021.md`（现状 422 条，四条收录尺子）。

**我方错记更正**：`NOTICE` 第三节原写「`abbr_en.txt`、`abbr_num.txt` 在本机四组参照与 dyyRime 里均无同名命中」，
与本文档自己的数据表（已记为安卓命中）相互矛盾。已按上表改为「与安卓数据根逐字节相同 ⇒ 本项目自有」。
教训：**同一轮审计里，摘要文档必须回读数据表，不能凭印象写「未命中」**。

**未闭环、如实保留**：该记录里提到的种子表 `rime-config/dicts/abbr-en-seed.txt`（14,012 B / 422 条）
与 `packaging/release/config/lua/abbr_en.txt` 在当前安卓工作副本内**未定位到**（已按路径直接检查），
因此只作为整理过程佐证，不作为许可依据；若日后需要对外自证生成链，请主人口头确认该 seed 表现在在哪台机器。
`rawfile/symbols/symbols.json`（34,984 B，md5 `4bb32817c8d4b65b611a25f06b843cfa`）在安卓仓内也**无同名文件**，
维持「本项目整理、未在本机参照命中」的原标注不变，仍属低风险（仅 UI 取数，不进引擎）。


## 八、补记二（2026-10-22 14:2x，Qoder）：`cn_pinyin_wp.dict.yaml` 不属于 CC-CEDICT 派生

**触发**：复核 NOTICE 第三节时发现该文件头部只有 `# Generated by DSH · 2026-10-13`，
**没有** CC-CEDICT 署名行，而同组另外四个 `zh2en_*` 文件都带 CEDICT / ECDICT / 极点五笔署名。
NOTICE 却写着「署名同时写在每个文件的头部注释里」——这句话与文件实际内容不符。

**实测**（脚本比对（词, 拼音）集合，原始输出 `docs/evidence/2026-10-22/cn-pinyin-wp-provenance.json`）：

| 比对 | 行数 | 去重（词,拼音）对 | 与 `cn_pinyin_wp` 的交集 | 覆盖率 |
|---|---|---|---|---|
| `cn_pinyin_wp.dict.yaml` | 65,114 | 65,114 | — | — |
| `pinyin_simp.dict.yaml` | 65,114 | 65,114 | **65,114** | **100.0%** |
| `zh2en_pinyin.dict.yaml`（CC-CEDICT 派生） | 89,737 | 88,553 | **0** | **0.0%** |

行数与对数完全相等、交集为全集 ⇒ `cn_pinyin_wp` 是 `pinyin_simp` 的**重新切片/改名**，
不含任何 CC-CEDICT 内容；与 CEDICT 派生表交集为 0，排除了「两边都掺」的可能。
这也与主人自己的生成脚本一致（`regen-cn-dsh.py` 从 `D:\Program Files\Rime\pinyin_simp.dict.yaml` 重生成 `cn_pinyin_py`）。

**处置**：

1. NOTICE 第三节：`cn_pinyin_wp.dict.yaml` 从 `[CC BY-SA 4.0]` 组移出，新增
   `[Apache-2.0（派生）]` 条目并附上述数据；「署名写在每个文件头部」改为「这四个文件」。
2. `third-party-declarations.md` §三：同上拆行（这页会被 CodeArts 渲染进应用内声明页，
   所以措辞保持用户可读，不写过程）。
3. **不动 `rawfile/**`**：文件本身一个字没改，只是我们的许可记账改了归属，
   因此**不需要**升 `DATA_VERSION`、不需要重新出词库、不影响路线 A（D-016）对 dyy 文件的冻结约定。

**为什么这个方向是安全的**：把数据从 CC BY-SA 改记成 Apache-2.0 是**减少**我们对外施加的传染性主张，
不会低估任何人的义务；反过来如果哪天发现它确实含 CEDICT 内容，正确做法是加回 CC BY-SA 并补署名，
而不是继续把一个 Apache-2.0 表按 CC BY-SA 对外声明——那会让下游使用者误以为必须整体 SA 兼容。

**教训（与 §七 同一条）**：分组时按文件名后缀（`_wp`）归类，没有回读文件头与数据本体。
许可归属只能由「文件头 + 数据比对」决定，不能由命名决定。


---

## 补记（2026-10-24）：F2 的「12 个改写」已作废，改按行级实测两级披露

随包数据变动后重跑审计：**65 文件 = 安卓同源 17 / dyy 原样 29 / 与 dyy 同名 13 / 四组均无 16**，
29 个原样合计 3,197,403 B 不变；`symbols.custom.yaml` 已不在包内。
原 F2 的「另有 12 个是 dyy 同名改写」是**按文件名**判的：13 个同名文件里 `rime.lua`、`README.md`
与上游命中 **0 行**（本项目自写），照抄会错记成上游衍生。
按 `difflib` 行级相似度改为两级：**改写 7 个**（inputShow 98.4% / Upper_Filter 97.3% /
inputShow_Filter 94.8% / dic_4w_Filter 78.8% / Custom_phrase 46.4% / wubi_pinyin.custom 41.6% /
sysInfo 38.2%）、**同名独立重写 6 个**（Apache-2.0 归本项目，列出仅为对照）。
逐行表与命令见 `docs/evidence/2026-10-24/dyy-same-name-recheck.md`；裁决见 `DECISIONS.md` D-025。
本报告其余结论（F1、F3、F4、§五 O-1~O-3）不变。
