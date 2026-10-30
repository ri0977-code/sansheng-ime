# dyy 层「保留 / 剥离」决策表（备胎方案）

> 2026-10-22 12:5x · Qoder · 对应 H-083 / F2、`third-party-audit-2026-10-22.md` §五 O-1/O-3
> 用途：主人拍板用。**这份文件不改动任何代码**，也不要求 CodeArts 现在动手。
> 依赖关系与文件大小为实测（`scripts/third_party_audit.py` + 逐个 `grep require`），非推测。

---

## 一、先把状态钉死（今天 12:5x GitHub API 实测）

| 事实 | 数值 / 状态 | 说明 |
|---|---|---|
| 正式授权请求 Issue #9 | **open**，`comments=0` | `created=2026-10-20T13:46:16Z`，`updated=2026-10-20T16:21:53Z`（= 北京时间 **10-21 00:21**）。即：**已被重开**，此前 22:37 的误关闭已修复。至今 0 回复。 |
| 误发的占位 Issue #8 | 仍 open，`comments=0`，正文还是 line1/line2 占位 | 「误发空壳，请忽略，正式请求见 #9」这句**从没发出去**；挂着会让上游以为我们在刷 Issue，建议补一句再关 |
| dyyRime 仓库许可 | `license = null` | 依旧是「保留所有权利」 |
| dyyRime 活跃度 | `pushed_at = 2026-01-23`，93 star | 距今 **9 个月无提交**；Issue #1–#7 里作者只在 2024–2025 零星回过几条 |
| 邮件 `douyaoyuan@126.com` | **只有草稿，无发送留痕** | 安卓侧 `给dyy的授权请求.md` §二 是草稿；`开源合规与安卓发布评估.md` 第 83 行写的是「草稿已写好」。**没有记录证明发过** |

结论：**「申请」确实发了、现在是可见状态；「邮件」这一步在记录里并不存在。** 如果主人记得发过邮件，那是好事但没留痕——留痕（截图/发件箱存档）才是软著与合规材料能引用的东西。
上游 9 个月不动 + 0 回复，短期内拿到授权的期望值很低。

---

## 二、三条路怎么选（我的建议）

| 路线 | 做法 | 法律敞口 | 功能损失 | 对 M6 排期 |
|---|---|---|---|---|
| **A 保留 + 标注** | 现状 + NOTICE/应用内页面写「授权申请中，版权归上游」 | 中等（未经许可复制他人作品，民事风险；审核层面通常不看） | 无 | **不阻塞** |
| **B 剥离** | 删 dyy 原样文件 + 摘 schema 齿轮行 | 低（干净） | 见第四节，主要是候选注释类能力 | 需 CodeArts 重跑移植+真机回归，约 1 天 |
| **C 自研替换** | 用我方 `abbrGloss`/`codeLookup` 链路补齐等价能力 | 无 | 逐步追平 | M7 工作量，赶不上本轮上架 |

**建议：维持 A（这也是主人 2026-10-20 已经定过的口径：「不回复不阻塞发版 + 持续标注授权请求中」），同时把 B 当备胎留在这份文件里。** 一旦上游回一句「不允许」，24 小时内按第三节执行即可。C 作为 M7 的正式方案派给 CodeArts 评估。

另外两条**不依赖上游**、今天就能做的：
1. #8 补一句说明并关闭（主人的登录态，我不碰账号）。
2. 邮件真的一封封到 `douyaoyuan@126.com`，正文用草稿 §二，**把发件截图存进仓库外备份目录**——有留痕才谈得上「已尽合理努力取得授权」。

---

## 三、剥离清单（按可独立摘除的功能包分组）

口径：`原样` = 与 dyy 字节一致（审计判定 P0 敞口主体）；`改写` = 同名不同字节；`我方` = 本项目自写/安全桩，**不必剥离**。
每个功能包 = 「删这些文件 + 摘这些 schema/custom.yaml 行」。摘行必须在 `wubi_pinyin.custom.yaml` 的 `engine/filters` 与 `engine/translators` 整表里删，不能只删文件——**齿轮引用了不存在的模块会让整条候选队列打断**（M3 run6 真机教训，`rime.lua` 头注释里记着）。

| 包 | 要删的文件（dyy 原样） | 关联的改写/我方文件处理 | 要摘的引用 |
|---|---|---|---|
| **P1 日期/时间/农历/节气/节日** | `dateTime_filter.lua`、`dateTimeModule.lua`、`lunarModule.lua`、`lunarjieQiModule.lua`、`eventsListModule.lua`、`eventsList.txt`（6 个 / ≈120 KB） | 无 | `custom.yaml: lua_filter@dateTime_Filter`；`rime.lua: dateTime_Filter` |
| **P2 自定义短语扩展（emoji/Unicode）** | `phraseExt_Filter.lua`、`phraseExt_Module.lua`、`phraseExt commonPhrase.txt`、`phraseExt esAppEmoji.txt`、`phraseExt esUnicode.txt`（5 个 / ≈53 KB） | `phraseExt personal.txt`（清空过的用户模板，建议一并删） | `lua_filter@phraseExt_Filter`；`rime.lua: phraseExt_Filter` |
| **P3 候选释义注释** | `phraseComment_Filter.lua`、`phraseComment_Module.lua`、`phraseComment commonPhrase.txt`、`phraseComment chemicalElement.txt`（4 个 / ≈59 KB） | `phraseComment personal.txt`（同上） | `lua_filter@phraseComment_Filter`；`rime.lua: phraseComment_Filter` |
| **P4 关键字替换** | `phraseReplace_Filter.lua`、`phraseReplaceModule.lua`、`phraseReplace.txt`（3 个 / ≈12 KB） | 无 | `lua_filter@phraseReplace_Filter` |
| **P5 候选加注音** | `pinyinAdding_Filter.lua`、`pinyinAddingModule.lua`、`pinyinAdding.txt`（3 个 / ≈10 KB） | 无 | `lua_filter@pinyinAdding_Filter`；注意与**我方** `codeLookup_Filter`（三向反查/多音字注释）功能有重叠，剥 P5 不影响反查 |
| **P6 英中对照注释** | `dic_4w.lua`、`dic_4w_cn.txt`（888 KB）、`dic_4w_en.txt`（2.0 MB）（3 个 / ≈2.9 MB，**占 dyy 敞口 90% 体积**） | `dic_4w_Filter.lua` 是我方改写的挂接层 → 一起摘 | `lua_filter@dic_4w_Filter`。**互译混输主链路不受影响**（那三个 translator 走 `zh2en_*`/`en2zh_*` CC-CEDICT/ECDICT 词库，见 `RimeDataInstaller.ets` 第 124 行） |
| **P7 动态候选（系统/环境信息）** | `dynamicPhrase_Filter.lua`、`GUID.lua`（2 个 / ≈8 KB） | `sysInfo.lua`、`socket.lua`、`runLog.lua` = **我方安全桩/日志，保留**（`socket.lua` 已是 `socketEnable=false` 的鸿蒙桩，本来就是为「不联网」重写的） | `lua_filter@dynamicPhrase_Filter` |
| **P8 场景追加候选** | 无原样文件 | `inputShow.lua`、`inputShow_Filter.lua`（改写衍生，相似度高）→ **降级处理**：保留但标注，或按 P8 摘 | `lua_translator@inputShow_translator` + `lua_filter@inputShow_Filter` |
| **P9 换道与空格 / 帮助** | `laneChangeAndSpace_Filter.lua`(3.9 KB)、`help.lua`(1.9 KB) | 无 | `lua_filter@laneChangeAndSpace_Filter`；`lua_translator@help_translator` |
| **P10 符号表改版** | 无原样文件 | `symbols.custom.yaml`（与 dyy 同名相似 89%）→ 若走 B，**用 `symbols.yaml`（rime/weasel 血脉，已确认可用）整表覆盖**即可摘掉这层衍生 | `schema: punctuator/import_preset: symbols` 保持不变 |
| **P11 通用字符串工具** | `utf8String.lua`(8.1 KB) | ⚠️ **不能单独删**：我方 `codeLookup_Filter.lua`、`abbrGloss` 链路和多个滤镜都 `require` 它 → 走 B 时必须**由我方重写替换**，否则连锁挂掉反查功能 | 无 schema 引用（被 require） |

`rime.lua`（改写）与 `wubi_pinyin.custom.yaml`（改写）在 B 路线下是**整表重写**，不算敞口主体，保留即可（文件头署名注明血脉来源）。

规模合计：P1–P10 删掉 **29 个原样文件 / 3,197,403 B**（约 3.05 MB，其中 2.9 MB 是 P6 词典），改写衍生里再摘 `symbols.custom.yaml`、`inputShow*`，`rime.lua`/`custom.yaml` 重写。

---

## 四、剥离以后用户看到什么（功能影响表）

| 能力 | 属于哪个包 | 剥离后 | 是否影响宣传卖点 |
|---|---|---|---|
| 五笔 / 拼音 / 英文**混输** | 不依赖 dyy（`wubi86` + `pinyin_simp` + 我方 `wubi_pinyin.custom.yaml`） | **完全不变** | ✅ 卖点保住 |
| **三向反查**（拆字/拼音/编码） | 我方 `codeLookup_Filter` + `zh2en_*`/`en2zh_*` | 逻辑保留；仅 `utf8String.lua` 需我方重写（P11） | ✅ 卖点保住 |
| **自造词 / 自调频** | rime 用户词典，与 dyy 无关 | **完全不变** | ✅ 卖点保住 |
| 简繁切换 | OpenCC 数据，Apache-2.0 | 不变 | ✅ |
| 智能九键 T9 | 我方 `sansheng_t9.schema.yaml` | 不变 | ✅ |
| 打「今天/明天/中秋/节气」出日期农历 | P1 | **功能下线** | 属于附加亮点，不是主 slogan |
| 候选右侧 emoji/Unicode 扩展短语 | P2 | 下线 | 次要 |
| 候选释义（化学元素、常用词注释） | P3 | 下线（我方 `abbrGloss_Filter` 还能覆盖英文缩写一类） | 次要 |
| 关键字替换、候选加注音 | P4/P5 | 下线（注音与反查有重叠，用户感知小） | 次要 |
| 英文候选的中文对照注释 | P6 | **注释变薄**；互译上屏本身不受影响 | 需在「关于」页说明口径 |
| 系统信息/时间/`ip` 这类动态候选 | P7 | 下线（`ip` 那条在鸿蒙上本来就是桩，等于无感） | 无 |
| `/v` `/p` 之类斜杠符号大表 | P10 | 换成 rime 官方 `symbols.yaml`，**分组顺序与自定义短语有差异**，需重拍截图 | 无 |

一句话：**四条 slogan（互译混输 / 三向反查 / 自造词 / 自调频）在 B 路线下全保**，丢的是「注释与扩展候选」这一层锦上添花；代价最大的是 P6 的英中对照注释和 P1 的日期农历。

---

## 五、走 B 之前必须先答的两个问题（还是主人的）

1. **P8（`inputShow*`）算不算敞口**：它是「同名改写」，相似度不是字节级；严格讲仍是派生作品。要么留（承担），要么一起摘（丢场景追加候选）。我建议摘——它和 P7 功能重叠。
2. **P11（`utf8String.lua`）由谁重写**：纯 UTF-8 编码/解码工具，工作量约半天。B 路线下**必须由 CodeArts 补我方实现**，否则 `codeLookup_Filter` 直接挂，反查卖点受损。

---

## 六、执行边界（避免误会）

- 本轮我**没有删除、也没有修改任何 rawfile**；只是把决策表写清楚。
- M-063 里已经请 CodeArts **先别动这些文件**，等主人拍板；移植与真机回归的活现在在 H-081/H-082 上。
- 走 B 的改动全部落在 `rawfile/rime/**` + `scripts/port_rime_data.py` 的齿轮完备性检查（摘引用后检查必须同步，否则会以非 0 退出码失败）→ **这是 CodeArts 的实现工作**，我只负责在真机上验收「功能确实下线且候选链路没被打断」。
- 走 A 什么都不用改：`NOTICE` 第三节已经写了 `[授权申请中 · 上游未附许可证] happyDom/dyyRime` + 29+12 文件清单与字节数；应用内页面由 M-043 渲染同一份文案。

