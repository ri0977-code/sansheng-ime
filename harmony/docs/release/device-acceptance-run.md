# 真机验收一次做完（第 3 站执行单）

> 用途：布局（H-096）定稿、最终包装上之后，**在一轮里把 9 条复测（`/szd` 已由 D-023 解冻）+ 5 张商店截图全部做完**，
> 不要零散拍几张就宣布收口。这份单子把每条的「动作 / 命令 / 期望 / 证据文件名 / 失败意味着什么」写死，
> 主会话和值守 agent 走同一套，避免两边口径不同。
> 依据：`docs/ROADMAP.md` 第 3 站、`docs/ISSUES.md` H-086/H-096/H-093/H-095、
> `docs/release/store/listing.md` §介绍截图。

## 0. 开工前置（四条不齐就不要开始）

1. **H-096 已定稿**：主人看过竖/横屏截图并点头。定稿前拍的任何一张都作废。
2. **装的是最终包**：`scripts/build.ps1` 由我独立跑出的 unsigned HAP **字节数与 CodeArts 报的那个数完全相等**
   （判据是「数」不是 hash —— HAP 每条 ZIP 时间戳取构建时刻，两次构建不可能逐字节相同，见 `docs/BUILD.md` §2.1），
   然后 `scripts/sign.ps1` → `scripts/install.ps1`；记下 `entry-default-signed.hap` 的字节数与 sha256（**sha256 只用于「装机的那一份就是验收的那一份」这台机器内自证，不跨构建比**），
   和 `python scripts/check_app_content.py <该包>` 的输出（要求 **16 项里阻断 0**）。**04:5x 实测现状写清楚，别照抄旧数字**：
   对 00:05 那份 unsigned HAP（28,199,141 B）跑 ⇒ **15/16 通过、阻断 0**，唯一的红是 ⑪：包内 `notice.html` 77,148 B 早于我 00:1x 改的 77,255 B（「源已改、页面旧」，下一包重生成即转绿；证据 `docs/evidence/2026-10-24/h149-probe-page-package-check-0012.md`）；
   ⑩ 探针页已从路由摘除（裸 HAP 与手工 zip 的 `.app` 两种口径都 PASS），⑨b／⑩ 在**裸 HAP** 下以 WARN 呈现但判据 PASS（喂 `.app` 时 ⑩ 升为阻断，同样 PASS）。⇒ **最终包的正确期望是 16/16 通过、阻断 0**；若 ⑪ 仍红，先跑 `python scripts/build_notice_html.py` 再构建（源侧 00:18 实测已是 16/16）。
   **05:0x 复核：上面那句「重建后转 PASS」已经从推断升成实测，而且没构建** —— 把 `scripts/build_notice_html.py`／`scripts/build_legal_html.py` 的输出重定向到**仓库外**临时目录，再与磁盘上 `entry/src/main/resources/rawfile/legal/` 的应用内法律页逐字节比：`notice.html` 75,564 B、`privacy.html` 8,862 B、`terms.html` 7,712 B **三份完全相同** ⇒ 许可页／法律页的源侧已经同步好了，新包 ⑪ 与 ⑦ 都会 PASS。⇒ 装机后如果 ⑪ 还红，那是**新包**与源不同源，就得查谁改了 `NOTICE`／`LICENSES/**`／`rawfile/legal/*`；旧包（01:17）红是判据变严，不作为返工依据。
3. **主人两步**（只有本人能做，见 H-086）：① 解锁 Mate 80（7GL0226408083897）；
   ② 设置 → 系统和更新 → 语言和输入法 → 默认输入法 → **三生输入法**。
   另外把**自动旋转打开**（第 1 条横屏要用，`hdc` 没有旋转命令：见 `docs/HANDOFF.md` 476 行的实测结论，
   只能物理转）。
   **05:2x 只读实测补一句**：`hidumper -s InputMethodService` 显示 `com.sansheng.ime` 已是 `isCurrentIme`＝true
   ⇒ 默认输入法**不用你切**，早上瞄一眼确认即可（详见 §0.1）。
4. **闸门自检**：先跑一次

   ```
   python scripts/tap_keys.py --check
   ```

   必须输出 `[闸门] 三生键盘面板: 可测`。**输出「不可测」就停手** —— 说明屏上的键盘不是三生的，
   这时候点出来的字、拍到的图全都不是我们的（上一轮就是因为这个打出了 `jihao`）。

### 0.1 只读取证已在 05:2x 做过（早上不必重复，也别按 Android 口径找命令）

夜里**只做只读命令**（没点屏、没装包、没碰 `power-shell`），四条实测事实：

- `hdc list targets` ⇒ 只有 `7GL0226408083897` 一台在线 ⇒ 本轮没有「装错机器」的风险窗口。
- `hidumper -s InputMethodService -a '-a'` ⇒ `com.sansheng.ime/InputMethodService` 的 **`isCurrentIme`＝true**（同机还列着码圈／百度／繁星不语／小艺／微信 5 个，全为 false）。⇒ **默认输入法已经是三生**，上面第 3 条里的②不用再操作。
- `bm dump -n com.sansheng.ime` ⇒ versionCode 1000000／versionName 1.0.0／installTime 2026-10-22 22:19:40／**updateTime 2026-10-23 01:17:41** ⇒ 手机上现在跑的**就是 01:17 那份 signed HAP**（28,288,696 B，01:17:39 落盘）——也就是说它当天 01:17:41 被覆盖安装过一次（早于主人 01:2x 的夜间指令，不是夜间值守装的）。⇒ 「同一个包不重复装」有了**设备侧证据**（装机前后各读一次 `updateTime`），不用靠记忆。
  **判「装没装过」只能看 `updateTime`**：`installTime` 是**首次安装**时间，覆盖安装（`install -r`）不动它，所以只看 `installTime` 会把「装过」读成「没装过」（夜里 01:5x 那条「installTime 仍是 22:19:40 ⇒ 没装机」的推断就是这么错的，已在值守 prompt 里改判据）。
- `hidumper -s DisplayManagerService -a '-a'` ⇒ Rotation 0（竖屏）、`ScreenPowerState` 2（夜里熄屏，正常）。**自动旋转开没开这项量不出来**：dump 里没有 rotation-lock 字段，而 `-rotationlock`／`-motion` 是**写**命令（夜里一律不碰）。日志里 10-22 08:58 有过 270° 旋转事件，只能证明「那时转得动」，证明不了现在开着 ⇒ **这一条仍要主人肉眼确认**。

**踩过的坑（钉在这里，下次别照 Android 习惯写）**：本机 HarmonyOS shell **没有 `settings` 命令** —— `settings get secure default_input_method` 直接返回 `/bin/sh: settings: inaccessible or not found`。查默认输入法一律用 `hidumper -s InputMethodService -a '-a'`。

设备侧通用变量（PowerShell）：

```powershell
$Hdc = "D:\DevTools\DevEco\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"
$Dev = "7GL0226408083897"
$EV  = "docs/evidence/2026-10-22"     # 证据目录，文件名一律 acc-<条号>-<说明>.jpeg
```

打字**一律用 `python scripts/tap_keys.py dump.json <字母…>`**（从 `uitest dumpLayout` 反查真实坐标）。
**不要用 `scripts/type.sh` 的写死坐标** —— 那套是 H-054 之前的键位，布局重做后必然点偏。

截一张图的标准动作（收进函数，避免每次手写错路径；Git Bash 下必须带 `MSYS2_ARG_CONV_EXCL=*`）：

```bash
shot() {  # 用法：shot acc-01-landscape
  MSYS2_ARG_CONV_EXCL="*" "$HDC" shell snapshot_display -f "/data/local/tmp/$1.jpeg" >/dev/null
  MSYS2_ARG_CONV_EXCL="*" "$HDC" file recv "/data/local/tmp/$1.jpeg" "$EV/$1.jpeg" >/dev/null
  ls -la "$EV/$1.jpeg"
}
```

## 0.5 每轮小回归（每装一次包都量这 6 条；00:26 已按当前布局改写 ①②③）

> 依据 H-109：不靠 CodeArts 自报、不靠主人眼睛；每项只记「通过 / 失败 / 未验」，失败记下现象与截图名。
> 顺序：①② 是 H-106 交付判据；③ 图标（H-108→H-147 已闭，仅防回归）；④⑤ 防回归；⑥ 上滑符号（H-154 手势层已交付，新包若缺就记失败并回 H-154）。**三项都按当前布局写**——底栏已无独立「收起」「九键」键。

| # | 可见行为 | 怎么做 | 通过判据 | 证据 | 失败意味着 |
|---|---|---|---|---|---|
| ① | 候选栏右端 **⌄ 三角**：空闲单击＝折叠键盘；有候选单击＝展开/收起候选网格；**长按＝始终折叠** | 26 键空闲态截图 → 点 ⌄ → 截图 → **点刚才那个输入框** → 截图 → 打 `nihao` → 点 ⌄（应展开网格）→ 截图 → 长按 ⌄ → 截图 | ① 空闲单击后键盘消失、输入框仍在；② 点输入框键盘回来；③ 有候选时单击变 ⌃ 且候选网格展开、再点收起；④ 长按后键盘消失（`KeyboardIndex.ets:1060-1090`） | `acc-rNN-01a..e.jpeg` | H-106 未完成（收起后无 show 路径，或长按不出折叠口） |
| ② | **长按 `?123`（九键态长按 `ABC`）弹「26键／九键」菜单**，点选换布局 | 26 键态长按 `?123` → 截图 → 点「九键」→ 截图；九键态长按 `ABC` → 点「26键」→ 截图 | 菜单两项、当前项带 ✓；26→九宫格严格 3×3；九宫格→26 键回来；**底栏没有独立「九键」键**（D-009 撤销后的口径，说明书 §3.2/§3.3 同） | `acc-rNN-02a..d.jpeg` | 与说明书不一致（图文不符是华为驳回项） |
| ③ | 桌面图标是 **「黑底金环」** 品牌图（D-022／W-209，H-147 已闭） | 回桌面拍照；再用 `python scripts/check_icon_ring.py --fail-on-stale` 量源文件与包内图 | 图标可见、非灰方块、非 DevEco 四宫格模板；金占比 0.20~0.40、图形顶到四边 ≥0.97、环厚 ≥0.018；包内两层与源同几何 | `acc-rNN-03.jpeg`（+可选 `03b-splash`） | 商店图标与包内不一致（华为驳回 TOP6）；跑 `check_icon_ring.py` 会直接给出原因 |
| ④ | 打 `nihao` 出候选，候选条左右滑翻页 | 26 键打 `nihao`，候选条左滑一次 | 候选含「你好」；滑后候选组变化、不崩 | `acc-rNN-04a/b.jpeg` | 候选栏回归，先查是不是又变成滚动容器 |
| ⑤ | 横屏预编辑可见 | 物理转横屏，打 `nihao` | 预编辑行 `nihao · [wqvb]` 完整可见、未被候选栏遮住 | `acc-rNN-05.jpeg` | 横屏预编辑回归（H-096 不能算定稿） |
| ⑥ | 上滑 `a` 只出一个 `@` | 在 `a` 键上滑 | 上屏恰好一个 `@`，不是两个、不是 `a` | `acc-rNN-06.jpeg` | 上滑手势回归，回 H-154/H-155 手势层 |

## 0.6 H-154 三条（新包必验：代码改对 ≠ 屏上对）

> H-154 是提审唯一代码阻断（P1-1／P1-2／P2-1）。出包后**先 `git show <最终包对应提交>` 核源码三处**：① `clearAllAndRecord()` 的 `saved` 分支有 `deleteEditor(saved.length)` 且置 `lastCommitText=''`；② `pushUndo`／`lastCommitText=text` 在 `client.insertText(text).then()` 成功回调里、失败不入栈；③ `KeyboardIndex.ets:2213/2414` 两处均为 `Text('三生')`。**再在真机做下面三条**——W-211／W-212／W-213 三次都栽在「代码说改了、屏上没改」。

| # | 要验的 | 动作 | 期望 | 证据 | 不过意味着 |
|---|---|---|---|---|---|
| 0.6-1 | **P1-1 无编码态「上滑清除」删得掉正文** | 输入框打 `nihao` 选「你好」上屏（此时无编码、预编辑为空）→ 在退格键上**上滑** | 屏上「你好」两字被删掉，不残留预编辑/下划线 | `acc-h154-01-{before,after}.jpeg` | `clearAllAndRecord()` 仍没走 `deleteEditor(saved.length)`（TC-3 判失败） |
| 0.6-2 | **P1-2 下滑撤销只删该删的** | ① 打 `nihao` 选「你好」上屏 → **下滑**退格（撤销）→ 只删「你好」；② 再上屏一个词 → 下滑 → 只删该词，前面的正文不动 | 每次撤销删掉的字数＝最近一次上屏的字数；不清空、不多删 | `acc-h154-02a/b.jpeg` | 入栈时机仍错，用户正文可能被平白删除（TC-4）。**「insertText 失败不入栈」真机难诱发**，以源码判据为准；若 `uitest uiInput text` 能绕过输入法往框里写正文，补做「外部写入后下滑，正文必须还在」 |
| 0.6-3 | **P2-1 空格键面是「三生」且仍上屏空格** | 26 键底栏与符号页底栏各截一张；点空格键；进数字键盘再截一张 | 键面为 **三生**（不是「空格」）；点一下上屏一个空格；数字键盘的「空」键保持原样 | `acc-h154-03-{qwerty,symbol,numpad}.jpeg` | P2-1 未改（仍 `Text('空格')`）；说明书键面称呼要随 H-152 一起改 |

## 1. 复测清单（9 条；H-095 已由 D-023 定 A1，`/szd` 解冻为第 9 条）

> 功能覆盖的对照表在 `docs/evidence/2026-10-23/final-package-device-regression.md` §2（八条铁律 + 2.9 自造词）；**两边冲突时以本执行单为准**（含截图 SOP、H-154 三条、`/szd`）。

> 口径对账：`docs/ROADMAP.md` 第 3 站列的 7 条里，`/szd` 那条原等 **H-095** 拍板——**D-023（2026-10-23）已定 A1 保留 9 组**，预期可写死（包内 `default.yaml:125`：`/szd` → ⒈⒉⒊…⒛），故**解冻为第 9 条**；「设置入口摘掉后无残骸」保留在第 8 条；本轮 H-096 复核**新增**第 2、3 两条（预编辑上限与候选条数对账）。
> 所以这张表 = 原 7 条 + 新增 2 条 = **9 条**。

| # | 测什么 | 动作 | 期望（屏上必须看到的） | 证据 | 不过意味着 |
|---|---|---|---|---|---|
| 1 | **横屏翻页**（H-035/H-081） | 手机转横 → 26 键打 `nihao` → 候选行**左滑一次**、再**右滑一次** | 左滑画面整页变（词全换、页码/位置有反馈），右滑回第 1 页；**一滑一页**不跳条 | `acc-01-landscape-*.jpeg`（滑动前/后各一张）+ `hilog` 里 `setPageSize` 行 | 横屏候选体系没跟上布局重做；H-096 不能算定稿 |
| 2 | **横屏预编辑**（H-096 新，本轮必测） | 横屏连打长编码：26 键 `zhonghuarenming`（15 字母）或五笔打满 4 码带反查注释 | 预编辑**始终可见**；预编辑变长时右侧**仍 ≥2 条候选可见**；超长时预编辑以省略号截断而不是吃掉整行 | `acc-02-landscape-preedit-{short,long}.jpeg` | H-096-3 未修（预编辑无宽度上限） |
| 3 | **横屏候选条数与 setPageSize 对账**（H-096-4） | 横屏打一个候选多的音节，同时抓日志：`hdc shell hilog \| findstr setPageSize` | 日志里最后一次 `setPageSize=n` 的 **n == 屏上实际可见条数**（带长预编辑时也要相等） | `acc-03-pagesize.txt`（日志摘录）+ `acc-03-visible.jpeg` | availW 没扣预编辑宽度，多要的条被 clip 裁掉点不到 |
| 4 | **26 键打 `nihao` 的候选条数**（H-093/拼音翻译器） | 竖屏 26 键 `tap_keys.py n i h a o` | 出候选，且条数与 `n` 一致（同上一条对账口径） | `acc-04-nihao.jpeg` | 包内 `script_translator@pinyin` 没生效（⑤ 项虽 PASS 也要真机确认） |
| 5 | **重复按键换标点**（H-093） | 竖屏连按 `'` 键 4 次（`tap_keys.py "'" "'" "'" "'"`），每次一张或末张 + 日志 | 依次出现 `‘` → `’` → `「` → `」`（包内 `half_shape["'"]` 实测就是这四个） | `acc-05-quote-{1..4}.jpeg` | 标点轮换链路上屏丢失 |
| 6 | **自定义短语**（说明书承诺过，从未在鸿蒙取证） | 打 `at`，看候选里有没有那条短语（`Custom_phrase.txt` 只有 4 条，`at` 是唯一可用编码；`@`/`$$` 是 commit 语法不是编码） | 候选里出现自定义短语内容 | `acc-06-custom-phrase.jpeg` | 说明书该项要改口径（H-152 重打时一起改） |
| 7 | **中英/简繁模式重启后是否保持** | 切到英文/繁体 → `aa force-stop com.sansheng.ime` → 重新拉起 → 再打一次 | **保持**或**不保持**都要如实记下 | `acc-07-mode-{before,after}.jpeg` | 决定隐私政策那句「运行期状态、不另行保存」是否要改回去（有证据才改） |
| 8 | **设置入口摘掉后首页/关于页无残骸**（H-090、D-021「只留生效的」） | 冷启动进首页 → 关于页 → 逐屏截图；`python scripts/check_app_content.py` 第 ⑦⑫ 项已过但界面侧要亲眼看 | 首页与关于页**没有**失效的设置项、灰掉的按钮、「保存在沙箱」一类过期文案 | `acc-08-{home,about}.jpeg` | 提审时「图文与实际不一致」；隐私政策口径要跟着改 |
| 9 | **`/szd` 斜杠符号**（H-095／D-023 A1：保留 9 组） | 26 键态依次点 `/` `s` `z` `d`（`tap_keys.py "/" s z d`；`/` 若不在字母区就先进符号页找，以屏上为准并记录路径） | 候选出现带圈数字 **⒈ ⒉ ⒊ …**（`default.yaml:125` 实测 20 项）；点第 1 条上屏 `⒈` | `acc-09-szd-{keys,cand}.jpeg` | 保留的 9 组没进包/没接通 ⇒ 商店文案承诺落空，删或补 |

### 1.1 商店文案兑现项（H-151，必测）

> 商店长描述写了「自造词与自动调频」，源码只有 `enable_user_dict: true`／`user_dict: user` 的配置证据。**这条不过就删词**（「功能与描述不一致」是华为驳回项）。

| # | 项 | 怎么测 | 判据 | 证据 |
|---|---|---|---|---|
| 2.9 | **自造词/调频真的生效**（H-151） | 打一个词库里没有的自造词（如 `sanshengceshi` 选「三生测试」）上屏 → 清空 → 再打同一串 | 第二次该词**排到候选第 1 或明显前移** ⇒ 文案保留；两次完全一样 ⇒ 删「自造词」只留「自动调频」（改 `listing.md` 后重出商店文案） | `acc-29-selfdict-{1,2}.jpeg` |

补测前已经判过的两条顺带看一眼，不另立判据：**九键仍严格 3×3**、**26 键数字行可直出**、
**Shift 有可见态**、**候选栏左右滑翻页**（四条铁律，任一条回归 = H-096 直接退回）。

另外 2 条待 H-095 拍板后才能定预期：**打一次 `/szd`**（留 9 组就该出带圈数字；不做就不出）。
主人拍板前不要拿它当缺陷。

## 2. 五张商店截图（H-085）

原图直接 `snapshot_display` 收原始分辨率（1280×2832），存 `docs/evidence/<日期>/m6-store-raw-0{1..5}.png`，
**不许手裁**，统一走脚本（按目标比例取最大内切、居中、`--bias` 微调、LANCZOS 缩放，并打印裁切框/字节/sha256；`--size WxH` 换目标尺寸，裁切比例随之改变）：

```
python scripts/make_store_shots.py <新截图目录> --out docs/release/store/screenshots \
    --map 01:01-pinyin-26,02:02-t9,05:03-grid,06:04-symbol,07:05-home --bias 0.5 --size 720x1280
```

| 张 | 内容 | 拍法 |
|---|---|---|
| 1 | 26 键拼音 + 候选 | 竖屏 26 键打 `nihao`，候选栏有词 |
| 2 | 九宫格（T9） | 切九键，键面严格 3×3 |
| 3 | 候选展开网格 | 点 ▼，两行网格带「码上词下」 |
| 4 | 符号面板 | 打开符号面板，数字行 + 两行符号 + 页码 `1/2` 可见 |
| 5 | 首页（应用主界面） | 冷启动后的首页，无调试残骸、无探针入口字样 |

硬性要求：五张同尺寸、内容互不相同、**都来自同一个最终包**；拍到百度/小艺键盘的作废
（这就是前置第 4 步闸门存在的原因）。裁完把 5 张的 sha256 追加进 `docs/release/store/listing.md` 的截图行。

## 3. 做完之后的收口动作（按顺序）

1. 逐条（含未测的 `/szd` 注明「待 H-095」）写进 `docs/ISSUES.md`（对应 H 项状态）与 `docs/PROGRESS.md`，
   VERIFIED 的判据必须是**证据文件名 + 屏上观察**，不接受「构建绿」。
2. 给 CodeArts 的结论走 `docs/MAILBOX.md` 一行（哪几条过、哪几条退回、退回到哪一条判据）。
3. 商店截图裁好后更新 `docs/release/store/listing.md` §介绍截图（H-085 状态）。
4. 全部 VERIFIED + 主人点头 ⇒ 才跑 `scripts/release_build.ps1` 出提审 `.app`
   （内嵌 16 项硬闸门，阻断不为 0 就 throw，不会出件；闸门本身的两处可绕过点见 H-113）。
5. 真机用完只做 `hdc shell power-shell suspend`（熄屏），**绝不 shutdown**。
