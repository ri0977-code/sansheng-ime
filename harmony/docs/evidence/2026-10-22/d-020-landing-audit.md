# D-020 落地复核：删的是哪个文件、留的是哪个文件、引擎到底取不取得到

复核人：Qoder（审核验收侧）　时间：2026-10-22 15:5x　方式：全部为本机静态测量 + 已签名 HAP 解包，未碰设备、未碰 `entry/src/**`（只读）。

> **⚠ 16:1x 公开更正（先读这段，本文件 §0 末段、§4、§7 的否定性结论已作废）**
> 我在本文里写「那 105 组斜杠符号与 8 个多值标点键**在任何构建里都没生效过**」是**错的**，成因是我把「工作区那份 `wubi_pinyin.custom.yaml` 的 `import_preset: default`」当成了「包里的那份」。16:1x 重做解包（三个签名包逐一读包内 `wubi_pinyin.custom.yaml` 原文）实测：m066 / m067-cr01 / 13:25 release 三个包里都是 **5,332 B、`punctuator/import_preset: symbols`、包内确有 `symbols.yaml` 28,473 B**，且 `recognizer/patterns/punct` 在包内 custom 里 ⇒ **斜杠符号与多义标点这条链在每个已签名包里都是活的**，与 13:35 真机 `/szd → ⒈⒉⒋⒍⒏` VERIFIED 互相印证。
> 仍然成立的结论（未受影响）：① 删 `symbols.yaml` 是真实减敞口、必须重出签名包；② CodeArts 把 `symbols.custom.yaml` 加进 `SHARED_FILES` 既反方向又无效（`SHARED_FILES` 只管同步到共享目录，不改引擎取哪份预设；且删了 `symbols.yaml` 之后没有任何东西 import 它）——该条目他 16:04 前已撤回；③ 许可表述的两处更正（`symbols.custom.yaml` = dyy 改版、`symbols.json` 派生 59%）照旧有效。
> 影响：D-020 选 A **确实砍掉了一项已经在用的功能**，由主人拍板接受代价；由我取消的两条真机补测（`[` `'` 多义标点、九键 `/szd`）**恢复**。合并范围与保真度缺陷见 `docs/evidence/2026-10-22/d-020-merge-recheck.md`（H-093）。


## 0. 一句话结论

D-020 选 A 的**删除动作是对的**（`symbols.yaml` 确实随包发出去了 28,473 B，见 §2），但 CodeArts 顺手做的另一半**方向相反**：把 dyy 血脉的 `symbols.custom.yaml` **新加进了 `SHARED_FILES`**（引擎释放清单），而这份文件在我们的包里**引擎根本取不到**（§3）。所以这一改既没减少许可敞口，也没带来任何功能，只是把一个第三方文件从「躺在包里」变成「拷进用户目录」。

同时，我在 `aa1fbf7` 提的「把两块并进自有 `default.yaml`」方案，**前提错了**（我默认那些多连打标点和 `/xx` 组在现网包里是活的），本文件 §4 予以更正并撤掉该方案；`docs/release/punctuation-merge-proposal.md` 已加更正头。

## 1. 当前工作区（CodeArts 未提交的在途改动）测到了什么

`git log --oneline -3` 最新是我的提交 `353797b`；HEAD 之后 **CodeArts 没有新提交**，所以 D-020 目前只存在于工作区：

| 项 | HEAD（已提交） | 工作区（在途） | 判定 |
|---|---|---|---|
| `DATA_VERSION`（`RimeDataInstaller.ets:101`） | `m5-pinyin-v18` | `m8-parity-v20` | 改了但**未提交**；H-091 只有在同一提交里改数据才算闭合 |
| `SHARED_FILES` symbols 条目 | **无**（111–115 行为 5 个 schema/default 文件，无 symbols） | 新增 `symbols.custom.yaml`（117 行，还多带一个空行） | 见 §3，方向错误 |
| `rawfile/rime/symbols.yaml` | 不在 git 里（`git log --all --diff-filter=A -- "*symbols.yaml"` 0 命中） | 磁盘上已删 | 见 §2，删对了，但只能靠重新构建生效 |
| `rawfile/rime/symbols.custom.yaml` | 不在 git 里（同上） | 磁盘上还在（11,696 B，md5 `b1e28d38ede993a7403b8087c55bc194`） | 第三方派生文件，仍未纳入版本控制 = 一次 `git clean` 就丢，**必须让 CodeArts 提交** |
| `wubi_pinyin.custom.yaml` | `:31 script_translator@pinyin`（H-089 已恢复）、`:74 recognizer/patterns/punct`、`:77 punctuator: import_preset: default` | 与 HEAD 相同 | 未改 |
| `default.yaml` | 3,957 B / 120 行，Oct 21 14:48 起未动 | 同 | **我的并表方案没有被执行，也没被需要**（§4） |

## 2. 「删掉 `symbols.yaml`」到底减少了吗 —— 减少了，实测在包里

把当前那个 13:25 产出的已签名发布包解出来列目录（`entry/build/default/outputs/default/entry-default-release-signed.hap`，27,822,532 B）：

```
resources/rawfile/rime/symbols.yaml         28,473 B
resources/rawfile/rime/symbols.custom.yaml  11,696 B
resources/rawfile/symbols/symbols.json      34,984 B
resources/rawfile/rime/default.yaml          3,957 B
resources/rawfile/rime/wubi_pinyin.custom.yaml  5,332 B   ← 旧版（H-089 恢复前）
```

要点三条：

1. `rawfile` 整棵目录树都会进 HAP，**跟 `SHARED_FILES` 有没有列它无关**。所以 `symbols.yaml` 虽从未进释放清单，却一直随包分发 = 真实的许可敞口，删它有意义。
2. 同一个包里 `wubi_pinyin.custom.yaml` 只有 5,332 B（HEAD 是 6,042 B），**证明这个已签名包是陈旧的**：它不含 H-089 的 26 键拼音恢复，也不含 D-020 的删除。旧的 `.app` 不能提审，这条条已在 §6 落成待办。
3. `symbols.custom.yaml` 也一样早就随包发出去了（11,696 B），删不删是另一个决定（§5 给了判据）。

## 3. 为什么「把 `symbols.custom.yaml` 加进 SHARED_FILES」是无效的

这份文件根键是 `patch:`，它给**名字叫 `symbols` 的配置**打补丁。要让它生效，必须有人 `import_preset: symbols`。实测：

- 桌面端 dyy 原配 `dyyRime-master/wubi_pinyin.custom.yaml:49` = `import_preset: symbols`；
- 桌面端主人现行 `D:/Program Files/Rime/wubi_pinyin.custom.yaml:66` = `import_preset: symbols`；
- 我们鸿蒙包里 `wubi_pinyin.custom.yaml:77` = `import_preset: **default**`；
- 把 `rawfile/rime/*.yaml` 全部 grep（`import_preset` / `__import`）：**11 处命中，全部指向 `default`，没有一处指向 `symbols`**；
- `default.yaml` 的 `punctuator:` 只有 `half_shape`（64 行起，32 个键，**每个键都是单值**）和 `full_shape`（96 行），**没有 `symbols:` 子块**。

⇒ 结论：把它拷进引擎用户目录后没有任何 schema 会去读它。`symbols.custom.yaml` 想要的 8 个多值标点键（`[` `]` `'` `"` `#` `^` `` ` `` `$` `_`）和 105 组 `/xx` 符号，在我们的包里**一个都不生效**。而 `wubi_pinyin.custom.yaml:72` 那行注释（「没这一行，`symbols.custom.yaml` 里那 107 组 `/xx` 符号一个都出不来」）是从桌面版抄来的因果说明，**在本项目不成立**，建议一并改掉以免误导下一个接手的人。

对照实验（很便宜，给 CodeArts 自己判）：在设备上打 `[` 连按三次。现网行为 = `default.yaml` 单值 → 出「【【【」；`symbols.custom.yaml` 若真生效应该是「［ / 【 / 〔」轮转。若三次都是「【」，就是本文件的静态结论。

## 4. 更正我自己：标点并表方案的前提是错的（撤掉 `punctuation-merge-proposal.md`）

我在 `aa1fbf7` 写方案时认定「`import_preset` 回 `default` 之后，那 20 个多义标点键和 9 组 `/xx` 会**新失效**，所以必须同一次并进 `default.yaml`」。§2/§3 的解包测量说明：**它们在任何已构建的包里从来没生效过**（包里一直是 `import_preset: default` + 无 symbols 块）。**【16:1x 更正：这句错。解包读的是工作区文件，三个签名包内实际是 `import_preset: symbols` 且带 `symbols.yaml`，这条路径一直活着并被 13:35 真机验过。见文件头更正段。】**所以：

- 不存在「这次删文件导致标点回归」，我提的这条风险作废；
- 相应的「并进自有 `default.yaml`」也不是发布前必做项；
- 顺带一个我之前没意识到的坑：`default.yaml` 在 `NOTICE` 里挂在 **[本项目自写] Apache-2.0** 条目下，若真把 dyy 血脉的符号表抄进它，就等于**把第三方内容写进一个我们自称原创的文件里** —— 那是许可上的降级，不是升级。既然 §3 证明并进来也不生效，就更不该做。

同样作废：D-020 决议文本里「失去的只有 `/pp` `/kx` `/bz`」这句。**实测失去的是 0 项**（那三组本来就不在引擎路径上）**【16:1x 更正：失去的不是 0 项。合并后自有 `default.yaml` 的 `punctuator/symbols` 只剩 9 组，旧包 201 组 ⇒ 丢 197 组 / 约 4,540 个符号，含 `/pp` `/kx` `/bz`；数字见 `d-020-merge-recheck.md` §二】**，而 `/kx` `/pp` 的差异此前已由 `symbols-parity` 复测判为「PC weasel 与手机 APK 两份不同部署副本」，不是鸿蒙缺陷。

## 5. 那 1.0.0 的符号输入靠什么 —— 靠 App 自己的符号面板，而它的数据也是 dyy 血脉

`rawfile/symbols/symbols.json`（34,984 B，116 组 / 2,093 项）是 H-061 已验收的符号面板取数来源，**不经过 Rime 引擎**，所以它是活的。它的生成脚本 `scripts/build_symbol_data.py` 文件头写明输入是 `D:/Program Files/Rime/symbols.custom.yaml`「107 组 /xx 符号表」。我把两边逐组比了：

| 指标 | 实测 |
|---|---|
| `symbols.json` 里 `r_` 前缀组 | 105 组 / 1,236 项（占全部 2,093 项的 59%） |
| 与 `symbols.custom.yaml` 同名的组 | 105 / 105 全命中 |
| **成员集合完全相同**的组 | **104 / 105**（剩 1 组为子集关系） |
| 抽样 `r_szd` vs `/szd` | 前 6 项逐个相同：⒈⒉⒊⒋⒌⒍ |

⇒ 所以「删掉 rime 侧的 symbols 文件」在**功能上**几乎无损（符号面板照常），但在**许可上**没有把 dyy 内容请出包：同一张表的 59% 内容以 JSON 形式随包发着，而且这是我们自己脚本生成的、证据链清清楚楚。

由此，`NOTICE` 现在这句是**低估**：「`rawfile/symbols/symbols.json` —— 本项目整理……上游同名文件在本机四组参照里均未命中，来源标注为待确认」。「无同名文件」只证明没有字节相同的副本，不证明没有派生。已在本次提交里改成如实表述（派生自 dyy 血脉表，许可归入「授权申请中」，随 route A 一起等 dyy 回复）。

## 6. 交给 CodeArts 的三条（已写进 MAILBOX M-079）

1. `SHARED_FILES` 里**去掉** `symbols.custom.yaml`（连同 117 行那个空行）。它取不到、不生效，只会让引擎目录里多一个没人读的第三方文件；`rawfile` 里留不留都行，但**必须把这份文件提交进 git**（现在完全不在版本控制里，一次 clean 就丢，也是许可敞口算不清的根源）。
2. `wubi_pinyin.custom.yaml:70-74` 的注释改成实情：`recognizer/patterns/punct` 这条在本项目**只影响引擎是否把 `/xxx` 认成符号串**，由于 `punctuator: import_preset: default` 且 `default.yaml` 无 `symbols` 块，斜杠符号在鸿蒙版**不出候选**，符号输入走 App 面板；把桌面版那句「107 组一个都出不来」删掉。
3. 把在途改动**提交**（v20 与数据变更必须同一提交，H-091），再出**签名 debug HAP**，报文件名 + `stat -c %s` 实测字节数。不要自己往 Mate 80 上装。

## 7. 对发布路径的影响（好消息）

原「待补测」清单里由我加的两项现在**取消**：`[` `'` 多连打标点、九键 `/szd` 引擎路径。理由 = §3/§4，现网包里从来没有过这条路径，不是这次改动弄坏的，也不是 1.0.0 的承诺功能。**【16:1x 更正：取消决定作废，两条补测恢复。**现网签名包里这条路径一直是活的（见文件头更正段），所以合并后的新包必须重新验一次：多连打 `[` `'` `"` 看弯引号还在不在（H-093 已查出 `‘ ’ “ ”` 被写成 ASCII 直引号 ⇒ 不打出来就是回归）、九键与 26 键各打 `/szd`、再顺带验全角 `"` 能否打出来（`default.yaml` 目前过不了标准 YAML 解析）】**真机上仍要测的符号项只剩一个：**H-061 的符号面板在最终包上照常可用**（一次点击即可，随 5 张商店截图一起做）。

余量：`symbols.yaml` 的删除要重新构建才落到包里 ⇒ 已签名的 `.app` 仍需重出（本来就在计划里）。商店文案未承诺斜杠符号，无需改文案。


## 8. 补测（同一批测量里顺手关掉的两件事）

**① `symbols.custom.yaml` 与安卓版是同一份文件，但那份文件本身是 dyy 改版。**
`md5` 三方对比：鸿蒙包内 `b1e28d38ede993a7403b8087c55bc194` = 主人安卓数据根
`F:/dshdesktopwork/sansheng-ime-android/rime/symbols.custom.yaml` = 桌面现行 `D:/Program Files/Rime/symbols.custom.yaml`；
dyy 原配 `D:/IDM/dyyRime-master/dyyRime-master/symbols.custom.yaml` 是 `04379ef2…`（13,286 B）。
差异 15 行，内容全是删掉上游的 `None` / `None11` 这类空占位项。安卓自己的
`THIRD_PARTY_NOTICES.md` 第 41 行与第 96 行写明「dyy 斜杠符号表的改版 —— 清掉 162 个 `None` 空占位……主体版权仍归 dyy」。
⇒ 我在 15:2x 方案里由「与安卓逐字节相同」推出「自有数据、无第三方许可问题」是**推理错误**：同源性只证明两个端发同一份文件，不证明来源。已按实改成 dyy 档。

**② 本轮第 3 个新入包文件 `phoneComment_Filter.lua` 来源已判：本项目自写。**
2,397 B，md5 `3cd9b776895346b3ea0e2864a7810271`，与安卓数据根同名文件**逐字节相同**（diff 0 行）；
在 `dyyRime-master`、`oh-my-rime-main`、`D:/Program Files/Rime/lua` 三组参照里都**没有同名文件**
⇒ 与 H-083 的 `abbr_en.txt` / `abbr_num.txt` 同一判据（我方数据根命中 + 三组参照无命中），
`NOTICE` 现有的 [本项目自写] 条目正确，`lua-files.txt` + `rime.lua` 两层登记齐全，无需 CodeArts 补说明。

## 9. 给下一个接手的人：这类判断怎么不再错

- 判断一个 rime 数据文件"有没有生效"，不能只看它在不在包里，要追**引用链**：`*.custom.yaml` 根键是 `patch:` 的，必须有人
  `import_preset` 指向同名预设；把 `rawfile/rime/*.yaml` 全 grep 一遍 `import_preset` 就能一次看穿（本次 11 处全指 `default`）。
- 判断"删掉它会不会造成功能回归"，先解包看**已交付的产物**（`zipfile` 列目录即可），别拿工作区文件当发布内容。
- 判断"是不是我们的原创数据"，与自家安卓端逐字节相同 **不是**证据；要找上游同名文件做行级比对，并读**我们自己安卓端的 `THIRD_PARTY_NOTICES.md`** —— 那里已经写过结论。
