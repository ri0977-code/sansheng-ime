# H-279 自造词真机复验（Mate 80）——造得出、记得住、点一次就升第一位

> 整理：Qoder　时间：2026-10-30 07:54–08:15　设备：华为 Mate 80（序列号 `7GL0226408083897`，1280×2832）

## 0. 这一份记录只回答一个问题

主人 10-29 夜里报的原文是「手机鸿蒙，行不行 tgtf，这个词，他造不出来」「行不 gi 行，造不出啊，安卓是造出来了」。
06:2x 我已经在**离线**用同机同 librime、只换词典的 A/B 证明了根因是鸿蒙那份 `wubi86.dict.yaml` 丢了第 4 列（stem 列），
并把三处改动打进包（详见 `../h279-dict/H-279-encoder-root-cause-offline-ab.md`）。
但按硬规则 11「读到配置不等于读到实机行为」，**离线通过不等于真机通过**——所以这一轮只做一件事：
把修好的那份装机候选装到主人这台真机上，按他报的那条编码原样走一遍，看**造得出／记得住**这两件事在真机上到底成不成。

结论先给：**两件事都成，而且自调频也成**（判读见 §4，图在 `docs/evidence/2026-10-30/h279-device/`）。

## 1. 装的是哪一份（可追溯到字节）

| 项 | 值 |
|---|---|
| 包 | `F:/qoderwork/sansheng-release-artifacts/2026-10-30/070923/entry-default-signed.hap` |
| 字节 | 45,003,213 |
| md5 | `b9142560c26f8dda66526b1691fbb3c8`（装机前先本地校验，与台账登记值一致后才装） |
| 装机命令 | `hdc install -r entry-default-signed.hap`（在包所在目录用相对路径跑；绝对路径带 `F:/` 会被 hdc 当相对路径拼到 cwd 后面，报 `no such file`） |
| 装机结果 | `msg:install bundle successfully.` |
| 新词库**真的**重铺的日志行 | `SSRimeData data h279-stems-redeploy released: 29 files + lua tree, 36526180 B, 129 ms -> .../files/rime \| .../files/rime_user` |

最后那行是这一轮**唯一**能证明「装进去的词典被引擎重新铺过」的证据：`RimeDataInstaller.ensure()` 比的是
`<shared>/.data-version` 与常量 `DATA_VERSION`，只有 `h279-stems-redeploy` 这个号打出来才说明补了第 4 列的那份
`wubi86.dict.yaml` 铺到了设备上、旧 `rime_user/build` 被删掉重编。没有这行，后面所有截图都不作数。

## 2. 键位坐标怎么来的（以及为什么不能用现成的 `panel_keys`）

`uitest dumpLayout` 取不到输入法面板窗口的子节点（H-116 老结论），键位只能从截图量。
仓库里已有的 `scripts/panel_keys.py` 用的是**纯白键帽**判据，这一轮在真机上只量到第一行 10 个键，
第二/三行（`asdfghjkl` / `zxcvbnm`）全丢——因为**那两行是灰键帽 `RGB(201,206,218)`**，
面板底是 `RGB(229,231,237)`（键帽上带「全选/行首/文首…」角标，H-220 那套选择模式）。
所以本轮在驱动器里另写了一个 `measure2()`：判据换成「离面板底色 >3 就是键帽」，
26 个字母键＋空格一次量全（每行键数 `[10, 9, 9, 6]`，空格中心 `(711, 2587)`）。

`panel_keys.py` 本身**没动**（它是别的脚本的已验证依赖），这个差异记在这里，等以后统一收。

驱动器：`scripts/h279_ab_drive_qoder.py`（单步执行，每步之间停下来看图）；
一次性跑全套的 `scripts/h279_zaozici_device_check.py` 这一轮**没有**用，原因写在 §3 第 1 条。

## 3. 为什么不照旧脚本「打 tgtf → 按空格 → 读输入框正文」判

离线 A/B 已经量出：造出来的「行不行」在候选里是**第 6 位**（`../h279-dict/` 的 B 组），
而第 1 位是「称王称霸」。也就是说**按空格上屏的一定不是新词**，
用「输入框正文里有没有行不行」当判据会把**通过**误判成**失败**。
⇒ 判词必须看候选列表本身。本轮全部用面板的**展开列表**（候选条右端 `⌄`，实测中心 `(1200, 1950)`；
展开后底栏 `下一页 (665,2610)`／`取消 (895,2610)`／`收起 (1105,2610)`，坐标都从截图逐行量出来，不猜）。

同理，逐字上屏要按**字根整段编码**打：`tf`+空格＝行、`gi`+空格＝不（旧脚本默认 `--codes t g t f` 是逐字母，
上屏出来的是四个不相干的字，等于没做实验）。

## 4. 步骤与判读

| 步 | 动作 | 截图 | 看到什么 |
|---|---|---|---|
| ① 基线 | 空输入框、新进程，直接打 `t g t f` | `h279-ab-10-baseline-tgtf.png` | 预编辑 `tgtf`，候选条＝称王称霸 / first of all / to co(in) …，**没有行不行** |
| ② 基线展开 | 点 `⌄` 展开 | `h279-ab-11-baseline-expanded.png` | 第 1 页 4 条：称王称霸`chenwangchenba`、first of all、to coin、wait a moment；底栏 `1/10` |
| ③ 清场 | 点 `取消` | `h279-ab-12-after-cancel.png` | 预编辑清空、输入框仍空 ⇒ 基线阶段一个字都没上屏，后面造的词不可能是这里污染的 |
| ④ 逐字上屏 | `tf`+空格 → `gi`+空格 → `tf`+空格 | 逐步读输入框 | 正文依次变 `行` → `行不` → `行不行`（`dumpLayout` 直接读到的，不是我推的） |
| ⑤ 同会话再打 | 打 `t g t f` → 展开 → 逐页翻到底 | `h279-ab-21-session-tgtf-expanded.png` + `h279-ab-22-page1..9.png`（拼在 `tmp/h279-ab-pagesA.png`） | **第 2 页第 1 条＝`行不行  xingbuxing  ☯`** ⇒ 引擎当场就把这三个字造成了一个词 |
| ⑥ 杀进程 | `aa force-stop com.sansheng.ime`（**位置参数**，写成 `-b` 会假报 10104002「应用未安装」） | `ps` 复查：`pidof` 无输出 ⇒ App 与 `:inputMethod` 两个进程都没了 | hdc 连接没断（M-368 那次断过，这次不断） |
| ⑦ 重开再打 | 起 App、点输入框、打 `t g t f`、展开、翻到第 2 页 | `h279-ab-31-restart-expanded.png`、`h279-ab-32-restart-page2.png` | 第 2 页仍是 `行不行  xingbuxing  ☯`，底栏 `2/10` ⇒ **跨进程还在＝userdb 真落盘了** |
| ⑧ 点一次 | 点中「行不行」那一格（中心 `(640, 2240)`） | 读输入框＝`行不行` | 新词能正常选词上屏 |
| ⑨ 再打（同会话） | 再打 `t g t f` | `h279-ab-34-after-select-page1.png` | **「行不行」升到第 1 位**（后面才是称王称霸），comment 变 `xingbuxing`、`☯` 标记不见了 |
| ⑩ 第二次杀进程＋重开 | 再 `force-stop`、再起、再打 `t g t f` | `h279-ab-40-restart2-tgtf.png`（候选条裁切 `tmp/crop-restart2-bar.png`） | 候选条第 1 格就是 **行不行**`xingbux...` ⇒ **调过频也跨进程保住了** |
| ⑪ 收尾 | 展开 → `取消` | `h279-ab-49-clean-state.png` | 预编辑清空、输入框空 ⇒ 设备留给主人一个干净状态 |

## 5. 判词

1. **造得出**：④→⑤ 之间没有任何人工加词动作，`tgtf` 的第 6 位凭空多出 `行不行`，且带 `☯`
   （`☯` 在本仓 lua 里就是「自动造词」的标记：`Upper_Filter.lua:24` 用它数 `idxSelf`，
   `pinyinAdding_Filter.lua:36` 注释写「或者这是一个自造词，为了不影响自造词功能…」）。
   同时**四份五笔词典里都没有「行不行」这个词条**（`wubi86` / `wubi86_jidian` / `zh2en_wubi` / `zh2en_wubi_wp` 逐个 grep，
   只有两份拼音词典 `cn_pinyin_wp` / `pinyin_simp` 有，而 `tgtf` 不是拼音输入），
   ⇒ 这一条候选**只能**来自引擎造词，不可能是词库里现成的。
2. **记得住**：⑥⑦ 把 App 与输入法进程全杀掉重开，词还在原位 ⇒ 落在 userdb 磁盘上，不是内存里的临时状态。
3. **会调频**：⑨⑩ 选过一次就升到第 1 位，并且这个位次在第二次重启后仍然保持。
4. 与离线 A/B **完全对上**：同一位置（第 6 位）、同一 comment（`xingbuxing ☯`）。
   离线那套（`scripts/h279_encoder_ab_test.py`）和真机这条链互相独立，两边读数一致，
   说明根因判断（词典第 4 列）抓对了，而不是碰巧。

## 6. 主人会立刻撞上的一个手感问题（必须说）

新造出来的词**第一次不会排在第一位**——第 1 位是「称王称霸」。
所以「打完 行／不／行 之后立刻打 `tgtf` 按空格」拿到的是「称王称霸」，**看起来仍然像"造不出"**。
正确用法是：展开候选（点候选条右端 `⌄`）或翻页到第 2 页，**点它一次**；此后它就是第一位（⑨⑩ 实测）。
这条不是本轮新引入的毛病，是 rime 造词的默认频次行为；要不要给它加一条「新造词临时置顶」，
属于产品口径，等主人点头再动（不在本轮范围内）。

## 7. 这一轮没覆盖到的（不藏着）

- **修复前的阴性对照没在真机上重做**：①②③ 那份基线是**修复后**的包打的，修复前「打 tgtf 第 2 页也没有行不行」
  这句依据是 ① 主人自己 10-29 夜里的亲测（已记在 H-279 现象栏）＋ ② 离线 A/B 的 A 组（旧词典把「行不行」造进 29 个乱码键、
  打 `tgtf` 50 条候选未命中）。要把真机阴性对照补成闭环，得回装一份旧包——那会让主人手机上装的不是发布候选，本轮没做。
- **只验了 `tgtf` 这一条词**：M-371 里给主人列的第 ② 条「换一条全新词验造得出＋记得住」本轮没做
  （没预先把三个字的编码算准，且 `tgtf` 正是主人报的那条，优先对齐他的复现路径）。
- **`☯` 在第二次上屏后从 comment 消失**（⑨）：现象记录在案，机制没查（不影响判定，因为⑦已经证明词是 userdb 里的）。
- **手感仍需主人亲验**：本轮全部是注入点键（`uitest uiInput click`），不是真拇指；
  H-278 单手模式四条的真人手感也还等主人打分。

## 8. 复现

```bash
python scripts/h279_ab_drive_qoder.py open      # 起 App
python scripts/h279_ab_drive_qoder.py focus     # 点「试一试」输入框，弹键盘
python scripts/h279_ab_drive_qoder.py panel     # 量键位（measure2，灰帽也能量）并缓存
python scripts/h279_ab_drive_qoder.py keys t f   # 行
python scripts/h279_ab_drive_qoder.py space
python scripts/h279_ab_drive_qoder.py keys g i   # 不
python scripts/h279_ab_drive_qoder.py space
python scripts/h279_ab_drive_qoder.py keys t f   # 行
python scripts/h279_ab_drive_qoder.py space
python scripts/h279_ab_drive_qoder.py keys t g t f   # 再打合并编码
python scripts/h279_ab_drive_qoder.py tap 1200 1950  # 展开候选列表
python scripts/h279_ab_drive_qoder.py shot 50-check
python scripts/h279_ab_drive_qoder.py kill      # aa force-stop <bundle>（位置参数）
```
