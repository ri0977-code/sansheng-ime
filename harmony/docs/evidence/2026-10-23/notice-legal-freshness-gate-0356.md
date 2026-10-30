# 对外声明的「同源」闸门（H-126）—— 改 NOTICE / legal md 忘了重生成，现在机器能抓到

时间：2026-10-23 03:56（夜间值守，Qoder）
范围：`scripts/check_app_content.py`、`scripts/check_app_content_selftest.py`（均归 Qoder）
**没有动 `entry/src/**` 一行代码，没有构建、没有签名、没有装机、没有碰手机。**

## 一、为什么查这个

M6①/③ 的收口口径是「对外声明与实际一致」，而同一份内容今天存在**三个表面**：

1. 根 `NOTICE`（20,988 B）与 `docs/release/legal/privacy-policy.md` / `user-agreement.md` —— 源文件；
2. `docs/release/legal/privacy.html` / `terms.html` —— 给 AGC 上传的**公示版**；
3. 包内 `resources/rawfile/legal/notice.html` / `privacy.html` / `terms.html` —— 用户在应用里**实际读到**的那份。

后两个是 `scripts/build_notice_html.py` 与 `scripts/build_legal_html.py` 生成的。
`NOTICE` 今天 17:57 才改过（D-020 的斜杠符号表敞口口径）。**只要那次改完忘了重跑生成器，应用里就会带着旧的许可声明出包**，而当时没有任何机器判据能发现：

- ⑪ 原来只查「包里有 notice.html」＋「页面里出现 Apache/LGPL/MIT 这几句关键词」；
- ⑦ 原来只查「公示版与应用内版正文一致」—— 两边都旧的时候**完全一致**，恰好放过最危险的那种过期。

## 二、今天的实测：三层确实是同步的（不是已存在的缺陷，是缺保护）

| 判法 | 结果 |
|---|---|
| 现场重跑 `build_notice_html.py`（输出到仓库外临时目录）vs 工作树 `rawfile/legal/notice.html` | **逐字节一致**，都是 73,388 B |
| 上面那份 vs **01:17 那个 unsigned HAP 里**的 `legal/notice.html` | **一致**（同 73,388 B） |
| `NOTICE` 20,988 B（sha256 前缀 `9f3c2300d5b9c26a`）＋ `LICENSES/` 11 份（拼接 sha 前缀 `40853ccb26b5731c`） | git 里干净，无未提交改动 |
| 包内 `privacy.html`(8,862 B)／`terms.html`(7,712 B) vs 工作树同文件 | 一致 |
| 仓库公示版 `docs/release/legal/privacy.html`／`terms.html` vs 用当前 md 现场重生成 | **unified diff 0 行**（8,993 B / 7,843 B） |

所以这一条不是「抓到已发货的错」，而是**把一类会在夜里悄悄发生的错变成机器必拦**。同属 H-113／H-123 那一族：「看起来能上传」。

## 三、改了什么

`check_app_content.py` 新增模块级助手 `_regen(kind)`：用 `importlib` 现场加载那两个生成器，
把它们的输出目录 `OUT` / `INAPP_DIR` / `OUT_DIR` 指到系统临时目录后跑 `main()`，
返回 `{逻辑文件名: 文本}`。标题一类常量不复制进判据（调 `main()` 而不是 `build(...,title)`），
这样以后改标题也不会让判据误报。生成器跑不起来 ⇒ 判不了同源 ⇒ **按阻断处理**，不静默放行。

- **⑪**（阻断）：除原关键词判据外，新增「包内 `notice.html` 必须等于用当前 `NOTICE` + `LICENSES/` 现场重生成的结果」；不一致时报「源文件已改、页面是旧的 ⇒ 先跑 `python scripts/build_notice_html.py` 再构建」。
- **⑦**（阻断）：新增两组比对 —— 应用内 `privacy/terms.html` vs 现场重生成的 `build_inapp` 结果；公示版文件 vs 现场重生成的 `build` 结果。原有「公示版与应用内版正文一致」保留。

项数不变（仍 16 项），只是把两条原有判据做实 —— 不牵动 `OWNER-ACTIONS.md` 的「16 项」口径。

## 四、我自己写错过一次，记下来

第一版 `_regen("legal")` 只返回**应用内**那一组，而 ⑦ 拿它去比**公示版** ⇒ 一跑就把当前真包判成「公示版不同源」，阻断 1、`结论：这份包不能提审`。
公示版与应用内版正文相同但**页面外壳不同**（`build()` 带 nav/footer/草案横幅，`build_inapp()` 不带），混比必然误报。
已改成 `{"inapp": …, "hosted": …}` 两组分别比。

**教训：新加判据必须先拿已知良好的包验它「不误报」，再拿坏样本验它「必拦」。** 这条现在固化进自测：`00-baseline` 与 `16-good` 都显式要求 `7: PASS / 11: PASS`，缺了任何一侧都算自测不通过。

## 五、自测结果（`scripts/check_app_content_selftest.py`，exit 0）

| 用例 | 注入 | 期望 | 实测 |
|---|---|---|---|
| `00-baseline` | 不注入（真包） | 9b/10 WARN、**7/11 PASS** | ok（14/16、阻断 0） |
| `16-good` | 好图标＋去探针页 | 9b/10 PASS、**7/11 PASS** | ok（16/16、阻断 0） |
| `19-notice-stale` | 只在 notice.html 尾部追加一段「旧版残留」，关键词全保留 | **11 FAIL** | ok（13/16、阻断 1） |
| `20-privacy-stale` | 同样只往 privacy.html 尾部追加残留 | **7 FAIL** | ok（13/16、阻断 1） |

22 个用例（含 2 个 `.app` 包装用例）全部按预期触发，未按预期触发 **0** 个。
对当前 unsigned HAP 重跑检查器：**14/16、阻断 0、exit 0**（9b/⑩ 对裸 HAP 仍只是 WARN，符合 H-115 的分级）。

## 六、顺带抓到的一条（属 CodeArts，单开 H-127）

01:17 那个 unsigned HAP 里**已经打进** `resources/rawfile/rime/lua/phoneComment_Filter.lua`（2,397 B），
但这个文件在 git 里至今是 `??`（未跟踪）。⇒ 现在的产物包含一份仓库从没见过的源码：
他做 checkpoint 提交时必须把 4 个未跟踪源码文件一起入库，否则「从提交出来的代码复跑构建」与「他报的字节数」天然对不上，
而我这侧的逐字节比对会把这种不一致判成构建差异去查，白花时间。

## 七、结论

- 今天三层同步，**没有已发货的错误声明**；这条改动的价值在于之后任何人改 `NOTICE`／legal md 忘了重生成时，提审链会在内容闸门处停下并直接给出该跑哪条命令。
- 夜里**没有构建**：这条判据只对「下一次出包」生效，等 H-106 交付后随那一批一起验。
- 闸门未受影响：`scripts/h106_precheck.py` 仍 exit 2／阻断 5；`--selfcheck` 仍 exit 0（11 个已知好／坏样本）。
