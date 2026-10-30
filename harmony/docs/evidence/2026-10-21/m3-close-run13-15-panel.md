# M3 结案证据 · 引擎侧（run13–run15）+ M-030 真机面板复核

时间：2026-10-21 16:00–16:36 · 执行人：Qoder · 设备：Mate 80 `7GL0226408083897`（全程 `hdc` + `uitest uiInput` 自动注入，未占用主人）
构建：unsigned **24,360,659 B**（16:16）/ signed **24,480,678 B**（16:17）· `DATA_VERSION = m3-sansheng-v12`

---

## A. 引擎侧结案

### A1. run13 —— 13 级 Lua 齿轮链挂回 `wubi_pinyin`，候选与摘链基线逐条一致（H-044 正向结案）

run9/run10 曾得出「鸿蒙这版 rime-lua 把候选列表当 userdata 传进滤镜，桌面滤镜按 table 写，所以 M4 必须先写适配器」的结论。**run11–run13 把这个结论推翻了**：错的不是契约，是我们的诊断桩用了 `return`，而 rime-lua 的滤镜是**协程生成器**，返回值一律作废。

run11 用 `zzd_f8`（`for cand in input:iter() do yield(cand) end` 恒等透传）拿到 **4 条候选，与纯 `table_translator` 的 `zzd_min` 逐条相同**；run12 的 `zzd_f9` 在候选上改 comment（`你好[诊断九g]`）、`zzd_f10` 用 `Candidate("诊断十", ...)` 自建候选插到第 1 位，全部生效。run13 据此把 `DROP_LINE_PREFIXES` 里摘掉的三个互译 `lua_translator` 挂回，`wubi_pinyin` + `wubi_pinyin.custom.yaml` 上共 **13 个齿轮**（2 个 `lua_translator@` + 11 个 `lua_filter@`）真机部署成功，候选与摘链基线一致、无 0 候选、无崩溃。

原始日志：`hilog-m3-run13.txt`、`m3-stderr-run13.txt`（15,279 B，`[EW]` 级告警 0 条）。契约全文记在 `scripts/port_rime_data.py` 文件头。

### A2. run14 —— `ascii_mode` 真机测量：librime 对 printable 字母返回 `handled=0`

`hilog-m3-run14.txt` 里 `[Rime-Napi] ascii probe` 逐键打印：`wubi_pinyin` 与 `pinyin_simp` **两个方案都一样**——`ascii_mode` 打开后按 `x`，`handled=0`、编码串空、commit 空。即这版 librime 的 `ascii_composer` 在「无挂起编码」时不消费西文字母。所以英文直出必须在桥侧补，不能等引擎。

修复（`fanxing_napi.cpp`，H-041 ②）：`ascii_mode && commit 空 && 无候选菜单 && 编码串仍空` → 直接把该键作为 commit 送出，与 H-024 数字直出同一套语义。

### A3. run15 —— 全新安装（先 `hdc uninstall` 再装）全项回归

`hilog-m3-run15.txt` + `m3-stderr-run15.txt`（12,196 B，`[EW]` 0 条）+ `M3Probe` 页自检输出：

- `PASS Lua 齿轮已挂载: 发布件里 lua_filter@/lua_translator@ 共 24 行`（新增的回归探针，替代 run11 的 `zzd_*` 诊断环）
- 引擎初始化 4,120 ms（首次全量编译），`engine ready`，`schema wubi_pinyin selected`
- 五笔/拼音混输、`nihaoma`→你好吗、`dog`→狗、`haoma`→号码[kgdc]、T9 `64426`→你好[ni hao]、`zh_trad`→中國、`ascii_mode` 单键 `x`/大写 `X`/连打 `hi` —— **全部 PASS**
- 数据清单：`m3-data-manifest.json`（本次重新生成）

诊断脚手架 `zzd_*.schema.yaml`（4 个文件）与 `fanxing_napi.cpp` 里的逐个部署循环已一并删除。

---

## B. M-030（H-042 弹性候选栏 + H-043 简繁收进中英）真机面板复核 → 通过

### B1. 弹性 pageSize 真的在跟着宽度走

`hilog` 里 `SSRealRimeEngine setPageSize=N (UI pinned)` 在同一次会话内出现 **4 / 5 / 9 / 10 / 11** 五个值（16:23:11 → 16:34:42），完全由 `CandidateBar` 外层 `Row.onSizeChange` 实测宽度算出，代码里没有 5/9 常量。这是主人「定死数肯定不满足两个屏，弹性才行」那条要求落地后的第一次真机读数。

### B2. 竖屏（备忘录，真实输入框）

`m3-panel-01-notepad.png` → `m3-panel-03-tap.png`（点 `n`：嗯/民/already/唔，preedit `n`）→ **`m3-panel-04-nihaoma.png`**：preedit `nihaoma`，候选第 1 条 **「你好吗」整词完整**、第 2 条「你好吗」带 comment `nihaoma`，**没有任何「你…」或整条只剩「…」**。H-042 的原始复现（`v0.3.1-engine` 上第 2 条整条只剩「…」）消失。

**翻页回归（H-034 在弹性栏上不破）**：竖屏点 `j` → `m3-panel-10-portrait-j-p1.png` 第 1 页 `是 / sun / to be / 就(jiu yi yidn)`，一次左滑 → `m3-panel-11-portrait-j-p2.png` 第 2 页 `将(jiang shall uqf uqfy will would) / 及(ey eyi ji) / 叫…`。**一滑一页、内容整页替换、没有自动续翻**。这一页同时是「中英互译 + 三向反查」的竖屏证据（`是→sun / to be`、`将→uqf uqfy / shall / will would`）。竖屏 `setPageSize` 在打 `j` 后从 5 自动降到 **4**（因为带 comment 的条目变宽），弹性算法在竖屏也在动。

### B3. 横屏（`LandscapeProbe` 页 + 真实输入法面板）

- `m3-panel-05-landscape-blank.png`：横屏首帧四行 + 功能行完整（H-037 回归）
- `m3-panel-06-landscape-nihaoma.png`：preedit `nihaoma`，一页 **9 条**，第 1 条「你好吗」完整，后面几条带 **三向反查 comment**（`你号吗` / `你耗磨` / `你泥`），无截断
- **`m3-panel-08-landscape-trad-zhongguo.png`（本轮最强的一张）**：长按中英键后键面显示 **「繁」**（H-043），preedit `zhongguo`，候选 `中國` / `China` / `中國`，第 3 条 comment `china khlq zhongguo` —— 一次按键同时验到 **简繁转换（OpenCC 真出繁体）+ 中英互译候选 + 五笔码反查 + 拼音反查 + 弹性候选栏不截断**

### B4. H-043 三态键

点击中英键 → 键面 `中`→`英`（`m3-panel-09-landscape-ascii-hi.png`，灰色「英」）；长按 → `中`→`繁`（`m3-panel-08` 蓝色「繁」）。三态可见、互不冲突，空格键吸收了腾出的一格。

### B5. 复核过程中踩到的自动化坑（写给 CodeArts 也写给自己）

`uitest dumpLayout` **看不到输入法面板窗口**，键位坐标只能从截图量。横屏面板存在「首帧窄布局 → 之后铺满 2832px」的变化（`panel created 1280x812px` → `relayout resize 2832x588px`），期间键位坐标整体平移。本轮第一组坐标（按首帧量的）在铺满后全部失效，导致一串误触。**结论：每轮注入前必须重新截屏量一次键位**，可复用脚本 `docs/evidence/2026-10-21/tmp/` 里的白色键帽扫描法（键帽 `#FFFFFF`、面板底 `#E5E7ED`、面板外 `#E3E4E6`，横排扫描取游程中点）。

---

## C. 本轮新开的问题

- **H-045（P2，归 CodeArts）**：**中英切换不清码** —— 编码串 `zhongguo` 挂着时点「中」切到英文，日志显示 `ascii probe key=h handled=1 input="zhongguo"->"zhongguoh"`，字母被并进了拼音编码，候选栏 0 条、无法上屏，用户只能退格删干净。修法：`setOption('ascii_mode', true)` 时先发一次 Escape 清码（桥侧或控制器侧都行，别动 `module.json5`）。
- **H-046（P3，归 CodeArts）**：**预编辑区自身被省略号截断** —— `m3-panel-09` 里 10 个字符的 `zhongguohi` 只显示成 `zhongg…`。H-042 修的是候选词，preedit 的 `constraintSize({maxWidth:80})` 把编码区限死了；长编码（五笔 4 码 + 拼音串）会看不见尾巴。建议 preedit 改为**尾部对齐 + 可弹性加宽**（候选栏已经弹了，编码区也该弹）。
- **H-047（P1，A/Q 共担）**：**九宫格面板没接到 T9 引擎** —— 见下面 D 节。
- **H-040 更新（观察）**：横屏面板首帧按 1280 宽排版、随后 `relayout` 到 2832，中间会出现一次「键盘只占左 62%」的可见跳变。不是本轮验收项，但值得 CodeArts 在 M5 适配时一并看。

---

## D. 九宫格（T9）真机面板实测 —— 引擎侧绿、面板侧未接通

按主人的验收铁律（「构建绿不算过」「别把这轮没测到当已完成」），M3 目标里那句「真机验证九宫格按 T9 出你好类候选」必须分两层看：

**引擎侧 —— 已 VERIFIED**（`hilog-m3-run15.txt:930-932`，全新安装）：

```
PASS 九宫格 T9: 输入"64426" 预编辑"64 426" 含"你好"=true ｜ 你好[ni hao] / 你敢[ni gan] / 米高[mi gao] / 你[ni] / 嗯[ng]
PASS 九宫格 T9 数字直入: 输入"986" ... ｜ 做[zuo] / 晕[yun] / 作[zuo] / 坐[zuo] / 云[yun]
INFO T9 "746"(=p?o?i?): 预编辑"746" 亲[qin] / 品[pin] / 秦[qin] / 琴[qin] / 拼[pin]
```

顺带纠正一处：目标里写的 `6-6-8-2` 不是「你好」的 T9 码，**`你好` 是 `64426`**（n=6 i=4 h=4 a=2 o=6）。

**面板侧 —— 未接通（新开 H-047）**：真机竖屏备忘录里走 `?123` → 「九宫格」标签，3×3 面板正常出现（`tmp/panel-t9.png`，`2 ABC / 3 DEF / 4 GHI / 5 JKL / 6 MNO / 7 PQRS / 8 TUV / 9 WXYZ`），但**点 `6` 之后备忘录正文从 `"""@&)` 变成 `"""@6&)`** —— 数字被 H-024 的直出语义送进了编辑器，preedit 没有任何变化，hilog 里也**没有一次 `selectSchema(sansheng_t9)`**，会话仍是 `wubi_pinyin`。`KeyboardIndex.ets:359-361` 的 `T9Key.onClick` 只调 `keyboardController.onKey(num)`，缺「进九宫格换方案 + T9 模式下数字进编码」这两步。

另有一个连带观察：点完九宫格数字后再截图，面板已经退回 26 键（`m3-panel-12-t9-64426-panel.png`，preedit 变成 `yishu`、候选 艺术中柯/艺术/depend），疑似一次上屏触发 `onStartInput` → 面板重建 → `panelMode` 这个 `@State` 丢了。与 H-043 建议（三态也应回读引擎）同源，M5 前建议把面板状态提到控制器里。

**修法分工**：~~Qoder 侧在接口 v0.1.9 加对外的 `selectSchema(id)`（`RealRimeEngine` 已实现，只是没通过 `KeyboardController` 暴露）~~ **本行 16:55 勘误**：核对代码后确认 `selectSchema(id)` 在**接口 v0.1.7 已全链路落地**——`RimeEngine.ets:50`、`RealRimeEngine.ets:116`、`MockRimeEngine.ets:156`、`KeyboardController.ets:322`，M3Probe 正是用它切的方案。**Qoder 侧没有剩余工作**，H-047 是纯 CodeArts 接通；CodeArts 侧进/出九宫格时换方案，并让 T9 模式下的数字走编码而不是直出。

**给主人的说明**：本轮测试在他的备忘录测试稿（标题「你好」）正文里留下了一个多余的 `6`，尝试回滚时因游标位置不确定没有强删，避免误删别的内容。
