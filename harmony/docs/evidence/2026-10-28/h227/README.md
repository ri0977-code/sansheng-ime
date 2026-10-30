# H-227 `···` 菜单补 5 枚滤镜开关 —— 本轮取证

日期 2026-10-28 08:2x 构建 / 08:34 签名装机（Qoder）。**全程零注入**。截图三张：`h227_screen.jpeg`(08:28)、`h227_s2.jpeg`(08:32) 装机前；`h227_s4.jpeg`(08:34) 装机后。

## 1. 构建与闸门（都是当场跑的，不是引用旧数）

| 项 | 结果 |
|---|---|
| `scripts/build.ps1` | BUILD SUCCESSFUL，unsigned **28,493,175 B**（首建 28,493,174 B；补守卫 ⑧⑨ 两条判据后重建 28,493,175 B。上一包 `1aca163`＝28,483,892 B，差 **+9,283 B**＝5 枚 @State 镜像＋5 行菜单＋5 条切换分支的量级） |
| 内容闸门（包模式，显式传 HAP 路径） | **17/17 通过**，阻断未过 0，rc=0 |
| `check_closure_items.py --strict` | rc=0（五件全过） |
| `check_icon_ring.py --fail-on-stale` | rc=0 |
| `scripts/h220_keymap_check.py` | 86/86 |
| `scripts/rime_harmony_overrides_check.py` | 9/9 |
| `scripts/h216_bubble_order_check.py` | 54/54 |
| `scripts/h227_menu_option_check.py`（本轮新） | 5/5；`--selftest` **6** 个坏形状全判红、rc=0（第 5 个＝菜单行开关名拼错，第 6 个＝置灰没接线） |
| `scripts/issue_id_reference_check.py`（本轮新，H-252） | 真树缺行 1→0；`--selftest` 3 条全判红 |
| `scripts/doc_table_shape_check.py` | 新增违规 0（基线 49 条不动） |
| `git diff --stat`（代码范围） | 只 `KeyboardIndex.ets` 一个文件，**73 增 3 删**，无 peer 改动混入 |
| `scripts/sign.ps1` | `SIGN OK`，signed **28,616,635 B**（08:34:07），比 unsigned 多 **123,460 B**（签名块＋权限块，与历史包同量级） |
| `scripts/install.ps1` | `install bundle successfully`，updateTime **08:34:11**，不早于 HAP 的 mtime ⇒ 装的是这一包 |
| 装机后进程 | `ps -ef` 见 `com.sansheng.ime:inputMethod` **08:34:10 新起**，升级没把输入法卡死 |
| 包内实证（解 `ets/modules.abc`，593,544 B） | 五条文案 `中英对照`／`拼音注音`／`英文缩写`／`短语扩展`／`敏感词替换` 与 `H-227 toggle option`、`WUBI_ONLY_OPTIONS` **都在字节码里命中** ⇒ 不是「源码里有、包里没有」 |

## 2. 08:2x 为什么先没装（留痕，**这一段已被 08:34 的签装取代**）

08:23 的 hilog 里出现了**真手**：`LetterKey longpress y -> bubble` → `H-215 move y wx=…idx=3/2` →
`H-215 commit y -> ұ` / `-> \` → `H-215 cancel y`；08:28 截屏（`h227_screen.jpeg`）看到屏幕亮着、
输入法就在前台，输入框里是 `ұ、`。

按 `feedback-real-hand-not-synthetic-keys` 那条硬规矩（hilog 显示他在手上时**不叠装、不抢注入**），
08:2x 那一轮没签没装。

**08:34 判他放手了，当场签装**：最后一次真手是 08:23:39 `H-215 cancel y`；08:28、08:32、08:33 三张截图
（`h227_screen.jpeg` / `h227_s2.jpeg` / `h227_s3.jpeg`）内容一模一样——屏幕亮着、输入框还是 `ұ、`、
十分钟没有任何新 `SSKeyboard` 日志 ⇒ 判定为空闲窗口。装机前置条件也已满足：`settings_effective_check.py --head`
在 commit `c4c6894` 上 rc=0（工作树与已提交树判定一致），全套离线判据在同一份产物上全绿。

装机前的前台是我们自己的「试一试」页（不是他的文档），安装只把 `com.sansheng.ime` 的 UI 能力重启，
系统回落到栈里的备忘录（`h227_s4.jpeg`，文字是他自己早前真手测出来的 `ұêë…` 那串），
**本轮一次注入都没有，正文一个字没动**。

## 3. 真机验收判据（装机后）

1. 长按空格或回车进设置页 → 返回 → 点 `···`；
2. 菜单应能看到新增五行：中英对照／拼音注音／英文缩写／短语扩展／敏感词替换，且**能滚到底**（H-241r2）；
3. 逐枚点一下，hilog 抓 `SSKeyboardIndex H-227 toggle option: <name>=<bool>`；
4. 引擎没吃进去的开关，标签会在紧随其后的 `syncEngineOptions()` 回填里**自己跳回原样**——这是故意的不假亮；
5. 九键方案下这五枚应为灰（不可点）：`sansheng_t9.schema.yaml` 只声明四枚开关；
6. 装机后这张屏（`h227_s4.jpeg`）只是「IME 进程被重启、系统回落到备忘录」的证据，**不是**菜单截图——
   菜单要看主人点开 `···` 才算数。

## 4. 同轮的第二件事：形状守卫假绿（H-253）

CodeArts 08:3x 回执（M-298）之后我复跑离线套，顺手撞见守卫自己的盲区：
`scripts/doc_table_shape_check.py` 的 `check_mailbox` 只在 `## 消息表` 这一节内生效，
而 M-270～M-298 这 28 条**全被追加在文件末尾**（`## 当前看板` 之后）⇒ 它们从未被扫过。

同一份真树上：

| 步骤 | 结果 |
|---|---|
| 修之前跑 `doc_table_shape_check.py` | **18 条 FAIL**，头一条 `MAILBOX:M-298:列12`（正文里 `abs(...)` 原来的写法是两条裸竖线，把一行拆成 12 格） |
| 修之后（按表格块自校准＋补「行必须竖线收尾」「续行」两条判据） | **0 条新增**，基线 49→**66**（17 条是旧违规第一次被看见，逐条留档、不追改＝H-129） |
| `--selftest` | 8→**10** 条断言全过：新增「消息追在别的章节后面」「正文裸竖线拆格」两个**真形状**，另有端到端（复制真树→插坏行→必须 rc=1） |
| M-298 那行 | 两处**纯形状**修复：绝对值竖线写成 `abs(wx - letterTouchDownX)`、删掉行尾 3 格（逐字等于 M-297 的正文/文件/状态＝粘贴残留）⇒ 12 格回到 7 格、3263→1477 字符，**语义一字未改** |

这一条与本目录的 H-227 没有代码关系，只是同一轮里必须记下来的事：**「新增 0 条」如果来自一个看不见半张表的守卫，
它就等于没查**（H-130/H-238 口径）。
