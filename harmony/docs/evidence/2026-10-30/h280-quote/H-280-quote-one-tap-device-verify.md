# H-280：中文引号的「一键」入口在符号面板，不在 `punctuator` —— 闸门第 ④ 项换判据 + 真机复验

整理：Qoder　　日期：2026-10-30（设备运行 06:48–06:53，Mate 80 `7GL0226408083897`）
决策依据：`docs/DECISIONS.md` **D-033**　　工单：`docs/ISSUES.md` **H-280**
探针脚本：`scripts/h279_symbol_quote_probe.py`　　原始产物：本目录（8 张 PNG + `h280-cells.json`）

---

## 1. 冲突是怎么来的（一句话）

闸门第 ④ 项的原判据是「`default.yaml` 的 `punctuator.half_shape["'"]` 里含中文弯引号」；
CodeArts 在 M-368 为满足主人「一键直出、不要弹菜单」的口径，把 9 个符号全部压成**标量单值**
（`"'": "'"`），于是第 ④ 项在最新包上变红 —— 而**同一时刻真机上引号是能一键打出来的**，
只是入口不是 `half_shape`。也就是说：**判据与用户可见属性绑错了对象**，红的那一项不代表功能缺失，
代表「我用旧路径去找一个已经换到新路径的功能」。

不修这里的两种错法都试过了，写下来防止再犯：
- 把 `half_shape["'"]` 改回四元数组 ⇒ 功能「判据绿」，但一点弹候选菜单、不直出，**退回主人已经否过的行为**（M-369 他亲手验过 `menu=0 num=0`）。
- 直接把第 ④ 项删掉 ⇒ 从此没人守中文引号，「1.0.0 必须能打中文引号」（H-093 属性）失去自动核。

## 2. 判定性事实：多字节面板字**根本不进 librime**

字节级证据链（源码锚点，非推测）：

`entry/src/main/ets/pages/KeyboardIndex.ets:4358` 符号格 `onClick(() => this.typeChar(ch))`
→ `KeyboardIndex.ets:1951` `typeChar` → `KeyboardController.ets:475` `onKey(ch)`
→ `entry/src/main/cpp/fanxing_napi.cpp:696` `ProcessKey`，其中的决定性分支在 **763–766 行**（H-061 注释）：

```cpp
if (key.size() > 1) {                       // 多字节（中文标点/引号）
  ResetPaging();
  return ContextToNapi(env, BuildContext(0, 0, key));   // 直接上屏，不喂给 librime
}
```

⇒ 「符号面板格子里的 “ ” ‘ ’ 「 」 能不能一键出来」与 `punctuator` 小节**在机制上无关**；
`half_shape` 只在**单字节 ASCII 键**（按 `'` 那个物理键）那条路上起作用。
这就是为什么判据必须换成面板口径。

## 3. 真机复验（06:48–06:53，符号面板第 0 页六个格子）

输入框基线文本（`h280-cells.json` 的 `baseline`，逐字）：

```
rigid demand稍等称王称霸行不行称王称霸行不不行行不行
```

先按 `?123`（64, 2587）进符号页，再逐格单击；每格一次点击，**不按空格、不滑动、不清空**：

| # | 符号 | 实点坐标 | 本次新增 | 菜单是否弹出 |
|---|---|---|---|
| 0 | “ | (103, 2298) | `“` | 否 |
| 1 | ” | (322, 2298) | `”` | 否 |
| 2 | ‘ | (533, 2298) | `‘` | 否 |
| 3 | ’ | (746, 2298) | `’` | 否 |
| 4 | 「 | (842, 2438) | `「` | 否 |
| 5 | 」 | (984, 2438) | `」` | 否 |

最终文本 = 基线 + `“”‘’「」`，每步 `before/after` 只差一个对应字形 ⇒ **六格全部一键直出**。

坐标不是目测：`panel_keys.measure()` 在符号页把整行读成一个 1280 px 的连续带（三行分别在
y≈2157/2298/2438），且忽略灰底功能行，格子中心不可用；改为对本目录 PNG 做逐条 PIL 扫描、
按暗色字形列聚类得出六个中心，再点。这一点记下来，避免下次又拿合并带去当坐标。

数据文件：`h280-cells.json`；截图：`h280-00-panel.png`（面板）、
`h280-01-after-tap-64-2587.png`（进符号页后）、`h280-10-00..05-*.png`（每格点击后各一张）。

## 4. 配置侧现状（脚本实测，统计口径写清）

文件 `entry/src/main/resources/rawfile/symbols/symbols.json`，`groups` 里 `id=="common"`／
`label=="常用"` 一组共 **38** 项；面板按每页 **19** 格分屏（`KeyboardIndex.symbolRowItems`，
7+6+6 三行）⇒ 第 0 页 = `items[0..18]`，顺序为：

```
， 。 ？ ！ 、 ； ： “ ” ‘ ’ （ ） 【 】 《 》 「 」
```

六个中文引号的下标：**“=7、”=8、‘=9、’=10、「=17、」=18 ⇒ 全在第 0 页**，无需翻页；
『 』 在 19/20，需左滑一页（本工单不改动这一口径，仅记录）。

文件 `entry/src/main/resources/rawfile/rime/default.yaml`：
`punctuator.symbols` 组数 = **9**（第 ② 项仍守）；
`punctuator.half_shape` 里面板那 9 个符号 `' " ` _ # $ ^ [ ]` 的取值类型**全部是 `str`（标量）**，
没有一个回到 list —— 这是 M-368/M-369 建立的口径，现在由新增的第 4b 项反向守住。

## 5. 闸门改动（`scripts/check_app_content.py`）

**第 ④ 项**（改为面板口径，阻断）：
- 包内/源码树里存在 `rawfile/symbols/symbols.json`，且「常用」组第 0 页（前 19 项）含 “ ” ‘ ’ 「 」 六个字；
- 且 `ui_blob()`（包 = `ets/modules.abc`；`--source` = `.ets` + `string.json` 拼接）里能搜到六个字 ⇒ 回落路径也在。

**第 4b 项**（新增，阻断，D-033 反向守卫）：
- `default.yaml` 的 9 个面板符号仍是标量（变回 list ⇒ FAIL：点一下弹菜单、不出字）；
- 两条直出链锚点仍在位：`fanxing_napi.cpp` 的 `key.size() > 1`、`KeyboardIndex.ets` 的 `this.typeChar(ch)`（文件被挪走/锚点消失 ⇒ FAIL）。

模块与 `SrcCtx` 文档字符串的项数从 16/17 统一改成 **18**（①~⑮ ＋派生 9b/4b/16b）。

## 6. 改完后的实测结果

内容闸门（底包 = `entry/build/default/outputs/default/entry-default-unsigned.hap`，
44,887,059 B，2026-10-30 06:27，sha256 `28beab20fb198cc11517a7c70c77496a4c1e639a8ca67e8056ed0d06b7d58eb6`）：

```
结果: 18/18 通过；阻断项未过 0 个
结论: 阻断项全部通过。
```

同一份表跑源码级 `--source` 亦 18/18。改动前该包唯一红项就是旧第 ④ 项（17 项里 1 项阻断未过）。

自测（`scripts/check_app_content_selftest.py`，已知坏样本双向验证）：

```
自测用例 26 个（含 3 个 .app 包装用例；16b 的 3 条 env/退出码断言不计入包用例，实报 30 条），未按预期触发 0 个
```

新增/改动的坏样本用例：`04-quote-offpage`（六格移出第 0 页 ⇒ ④ FAIL、4b PASS）、
`04b-nosymbolsjson`（删 `symbols.json` ⇒ ④ FAIL）、`04c-punct-back-to-list`
（`"'": ["‘","’"]` ⇒ 4b FAIL、④ 仍 PASS、③ 仍 PASS）、`04c-exit-code`（4b FAIL 时闸门 rc 必须=1，验阻断通路）。
基线 `00-baseline` 与 `16-good` 同步锁 ④/4b 双 PASS，防「新判据对真包误报」。

## 7. 数字口径连带核对（同一批必须一起改，否则闸门项数自相矛盾）

`scripts/owner_surfaces_agreement.py` 现算 `GATE=18`，本次同步改了 4 处活区文字：
`docs/release/app-content-checklist.md`（清单仍 16 项、脚本 18 条断言的口径句 + 第 ④ 行改写 + 新增 4b 行 + 「第 ④ 项为什么换判据」段）、
`docs/ROADMAP.md`（两处「17 项检查」→ 18）、`docs/OWNER-ACTIONS.md`（两处，含增长链 16→17→18）、
`scripts/check_closure_items.py`（OK 文案「`.app` 可达 16/16」→「18/18，D-033 起」）、
`scripts/h165_bar_height_check.py`（文档字符串「现有 16 项内容闸门」→ 18）。
附注：第 16b 条这次自测输出为 **12/12 项三项齐全**（此前一轮是 11/12），即 H-242 守卫当前无缺项。

**未验/不在范围内**：复跑 `owner_surfaces_agreement.py` 仍报 5 处不一致，全部落在
`docs/HANDOFF.md` 活区锚点（`」(\d+) 行表`、`旧编号 ①–⑧ 的原文已于 10-25 09:14 整段移入附 (\d+)`、
`顶部 (\d+) 行表`、`--selfcheck` (\d+) 例 exit 0`、`--selfcheck` (\d+) 例含 3 个已知坏样本`）。
这些漂移**早于本次改动**且该文件归 CodeArts（AGENTS.md §3），我没有动它们，只在 M-372 里点名请他核数；
「为了绿而改别人的锚点」不算修好。

## 8. 没做什么 / 下一步

- 没改 `default.yaml`、没改 `symbols.json`、没改任何 `.ets`/`.cpp` —— 本工单只改判据与其文档，功能侧一行未动。
- 没出 `.app`：**这一条在本文写完几分钟后被推翻了**（07:10 `release_build.ps1` 全绿跑通，
  `.app` 18,249,521 B／sha256 `0d3b3a4a…`、闸门 18/18，见
  `docs/evidence/2026-10-30/release-app/H-280-app-1.0.0-release-build.md`）。
  当时我判「出 `.app` 需要主人手上的 `SS_RELEASE_PWD`/`SS_RELEASE_KEY_PWD`/`SS_RELEASE_STORE_PWD`」是**读漏了
  `sign/release/README.local.md:8`**——那句写明发布私钥库口令与调试库相同、就在 `sign/keys.local.json`（gitignored）。
  原文保留在此，因为它正是「绿闸门 ≠ 我查全了」的又一例：**同一条结论我先给了「做不到」，实际是能做到**，
  差别只在我没把那三个 env 变量的来源查到底。连带登记 **H-281**（发布私钥＋口令同盘、机外副本未办）。

- 真机这六格是**注入点击**（uitest），验的是「一键直出、不弹菜单」这条机制属性；
  拇指手感与「主人会不会去按物理 `'` 键打引号」不在本工单结论里 —— 若主人要求物理 `'` 键也直出中文引号，
  那是另一条需求（与 M-368 的标量口径冲突），需新开 D-0xx 拍板。
- 与本工单同批装机候选：`entry-default-signed.hap` 45,003,213 B / md5 `b9142560c26f8dda66526b1691fbb3c8`
  （含 H-279 自造词修复 + H-278 单手模式），待主人装一次，把自造词与单手手感一起复验（M-371 已请）。
