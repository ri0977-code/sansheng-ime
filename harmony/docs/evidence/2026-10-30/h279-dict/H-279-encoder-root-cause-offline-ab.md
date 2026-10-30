# H-279 鸿蒙端「自造词」造不出 —— 根因与修复证据

> 整理：Qoder　日期：2026-10-30　工单：H-279　关联：D-0xx 无需（未换路线，属数据缺陷修复）

---

## 1. 主人的现象（原话）

- 「手机鸿蒙，行不行 tgtf，这个词，他造不出来，是不是自造词功能有问题啊」
- 「我知道了，安卓也是一样的，我刚试了，打行不行的不，得用 gi 不，就造出来了，不能用 i 不。」
- 「不对啊，鸿蒙这个不行啊，行不 gi 行，造不出啊，安卓是造出来了」
- 「安卓是 tgtf 行不行和桌面端一样，不是你说的 titf」

即：**同一份词、同一串键，桌面和安卓都能造出 `tgtf → 行不行`，只有鸿蒙造不出。**

---

## 2. 造词链的机制（读的是本仓 librime 头/源，不是推测）

| 环节 | 位置 | 关键行为 |
|---|---|---|
| 提交历史 | `table_translator` / `TranslatorOptions.encode_commit_history` | 上屏的字进 commit history，攒够长度交给 encoder |
| 造词入口 | `entry/src/main/cpp/include/rime/gear/unity_table_encoder.cc:CreateEntry` | `user_dict_->UpdateEntry(entry, commits, kEncodedPrefix)`，`kEncodedPrefix = "\x7f" "enc" "\x1f"`（同文件第 16 行） |
| 推编码 | 同文件 `TranslateWord` → 走 `rev_dict_`（reverse.bin 的 **stems**） | 逐字取该字的**全码**，按规则拼成新词码 |
| stems 来源 | `entry_collector.cc:122` `if (!stem_str.empty() && !code_str.empty())` | **stem 只来自 dict 第 4 列非空的行** |

三字词规则（五笔通行口径）：第一、二字各取首码 + 第三字取前两码。
`行`=tf、`不`=gi、`行`=tf ⇒ **tgtf**。这与主人观察到的码完全一致，说明规则本身三端相同，不需要「另一套编码机制」。

⇒ 推论链：dict 没有第 4 列 stem ⇒ reverse.bin 里 stems 为空 ⇒ `TranslateWord` 对任何非简码字都推不出码 ⇒ 造词只能瞎拼或整条失败。**这是数据缺列，不是引擎没接通、也不是 UI 没触发。**

---

## 3. 三端词库实测（2026-10-30 本机复测，口径写在下面）

统计口径（同一规则跑四份文件）：`utf-8-sig` 读整文件 → 第一个以 `...` 开头的行之后算数据段 → 去空行后 **136,941 行**，其中 25 行是被 `#` 注释掉的简码行（`#子\tb\t1477224451` 这种）→ **真实词条行 136,916** → 再按 `\t` 切，第 4 列去空后非空记为「带 stem」。

| 端 | 文件 | 字节 | md5 | 词条行 | 带 stem 行 |
|---|---|---|---|---|---|
| 桌面 | `D:/Program Files/Rime/wubi86.dict.yaml` | 2,352,069 | `7c486bb7b5f6c9e7a135249962416e4f` | 136,916 | **20,935** |
| 安卓 | `F:/dshdesktopwork/sansheng-ime-android/rime/wubi86.dict.yaml` | 2,352,069 | `7c486bb7b5f6c9e7a135249962416e4f` | 136,916 | **20,935** |
| 鸿蒙（修复前） | `docs/evidence/2026-10-30/h279-dict/wubi86.dict.yaml.before-stems` | 2,290,104 | `e7dfa7a72cffa1501c55e2200959bf25` | 136,916 | **25** |
| 鸿蒙（修复后） | `entry/src/main/resources/rawfile/rime/wubi86.dict.yaml` | 2,352,834 | `8e020b029ad8dab31ccc8a74ad7f17c3` | 136,916 | **20,935** |

两个要点：

1. **词条数三端一直是 136,916，一模一样**；差的是第 4 列 —— 鸿蒙只剩 25 行（25 个一级简码），桌面/安卓有 20,935 行。
2. 修复后鸿蒙与安卓的 **非空数据段 136,941 行逐行完全相同**（脚本比对 `data identical: True`，含那 25 行注释掉的简码）；字节数不同的 765 B 全在表头注释块（鸿蒙这份保留了自身 changelog 与 H-273 补的 `import_tables` 两行）。⇒ 鸿蒙这份不是「整包覆盖成安卓那份」，是**只往目标行追加第 4 列**（`scripts/h279_restore_stems.py` 的口径：逐行按 `(text, code)` 双键校验，任一行对不上就整体中止不写盘；原文件先备份再改并打前后 md5）。

---

## 4. 判定性实验：离线 A/B（同一台机器、同一份 librime、只换词典）

脚本：`scripts/h279_encoder_ab_test.py`
原始结果：`encoder-ab-offline.json`（合并）＋ `encoder-ab-A-old-dict.json` / `encoder-ab-B-fixed-dict.json` ＋ 各自 `.stdout.log` / `.stderr.log`
运行时间：2026-10-30 06:25（见文件 mtime）

实验设计（每变体一个子进程，跑两阶段，中间彻底销毁引擎）：

1. 阶段一：`select_schema(wubi_pinyin)` → **`set_option enable_sentence=0`**（否则 Poet 会当场组句，出现假阳性）→ 依次上屏 `tf`→行、`gi`→不、`tf`→行 → sync → 销毁 session → `RimeFinalize`。
2. 读 `<user>/user.txt`（副本把 `db_class` 从 userdb 改成 tabledb，**只为能读到造出来的码**；发布配置仍是 userdb）。encoder 产生的条目 key 前缀是 `\x7fenc\x1f`，解析时剥掉。
3. 阶段二：**重新 initialize 起一套引擎**（内存里的 commit history / composition 全没了，这才是「下次开机还在不在」）→ `enable_sentence=0` → 打 `tgtf` → 记 preedit、候选数、`行不行` 命中位置、前 6 名。

| | A = 修复前词典（25 条 stem） | B = 修复后词典（20,935 条 stem） |
|---|---|---|
| `select_schema` | 1 | 1 |
| 三次上屏 | tf→行 OK / gi→不 OK / tf→行 OK | 同 |
| `user.txt` 里「行不行」的编码 | **29 个**：`hgha hgok hgpe hgra hgro hgsw hgtf hgwe hgxi ogha … pgxi rgha rgok` | **1 个：`tgtf`** |
| 重开引擎后打 `tgtf` | 50 个候选，**「行不行」未命中**（top：称王称霸 / first of all / to coin …） | 50 个候选，**「行不行」命中第 6 位**，comment=`xingbuxing ☯` |
| 打 A 自己造出来的 `hgha` | 命中第 0 位，comment 里写着 `[tgtf]` | — |
| 判定 | `PART：造出词了但码不是 tgtf` | `PASS：打 tgtf ⇒ 重开引擎后第 6 位出「行不行」` |

⇒ **结论（判定性）**：只有 B 打 `tgtf` 出词，根因成立 —— 丢的确实是第 4 列 stem，补回来造词链就通。
A 那一栏还解释了主人为什么觉得「完全造不出」：词**写进了用户词典**，但挂在 `hgha` 这类乱码下（stem 缺失 ⇒ encoder 退化成拿字面码拼），`tgtf` 上永远找不到它；且那 29 个垃圾码不会遮蔽 `tgtf`（见 §6 真机清单）。

---

## 5. 修复清单（三项必须同时成立，缺一即「装了等于没装」）

| # | 改动 | 文件 | 为什么 |
|---|---|---|---|
| 1 | 补回第 4 列 stem（25 → 20,935 行） | `entry/src/main/resources/rawfile/rime/wubi86.dict.yaml` | 见 §2–§4，造词的唯一必要条件 |
| 2 | `translator/max_phrase_length: 6` | `entry/src/main/resources/rawfile/rime/wubi_pinyin.custom.yaml:96` | custom 里那份 patch 早先把 schema 的 6 压回 4，长词造不出来；与 schema 对齐 |
| 3 | `DATA_VERSION = 'h279-stems-redeploy'` | `entry/src/main/ets/engine/RimeDataInstaller.ets` | `ensure()` 开头拿 `<shared>/.data-version` 与常量比对，**相同就直接 return**：不升号则新词库既不重铺、`rime_user/build` 里的旧 `wubi86.table.bin` 也不重编 ⇒ 已装机用户升级后仍是旧词典。升号后走 H-276 那条路径删 staging 目录并重铺数据 |

---

## 6. 待真机复验（尚未做，不许当作已过）

已做的只有离线引擎实验（§4）+ 包内容审核（§7）。**真机没验，就不能写「已闭环」。** 装机一次（按规矩：整套离线验证绿了才占主人一次输密码的装机）核对四条：

1. 打 `tf`→行、`gi`→不、`tf`→行 上屏 → **退出输入法重开**（或切走再切回）→ 打 `tgtf` → 候选里出现「行不行」。
2. 换一条全新短语（不在词库里、也没被 §4 的脏 user.txt 污染），验「造得出 + 记得住」。
3. 单手模式那四条（H-278，见 `docs/evidence/2026-10-30/h279-device/`）在同一包上再走一遍，别只验造词。
4. 第一次拉起键盘会**明显比平时慢**：`ensure()` 删了 `<user>/build`，`wubi86.table.bin` 要重编。这是预期，不是回归。

装机时的两个硬提醒：

- **不要清用户词典**。旧词典造出的 29 个乱码词挂在 `hgha` 这类键下，不与 `tgtf` 冲突；清了反而把主人自己攒的 Custom_phrase / 词频一起弄丢（H-272 口径）。
- 验收用**新词**，别用「行不行」——离线实验已经在桌面 temp 里造过它，但那是另一套 user 目录；真机上重造一遍才算数。

---

## 7. 安装包内容审核（按字节，不按哈希猜）

`entry/build/default/outputs/default/entry-default-signed.hap`（debug 签名，`scripts/sign.ps1` 产物）：

- 大小 **45,003,213 B**，md5 `b9142560c26f8dda66526b1691fbb3c8`
- 解包后 `resources/rawfile/rime/wubi86.dict.yaml` = 2,352,834 B / md5 `8e020b029ad8dab31ccc8a74ad7f17c3` / 带 stem 行 20,935 —— 与仓库那份一致
- `resources/rawfile/rime/wubi_pinyin.custom.yaml` = 7,284 B，内含 `max_phrase_length: 6`
- `ets/modules.abc` 里能直接搜到字节串 `h279-stems-redeploy`（证明重铺闸门真的进了包）
- 内容闸门：**16/17 通过，阻断项 1 个**（已知的 `default.yaml` 中文引号被压成单值 = goal 第③项）。⇒ 这份可以装机测，**不能提审**。

---

## 8. 脚手架踩过的坑（记下来，下次别再花时间）

1. **`RimeSessionId` 是 `uintptr_t`**（`rime_api.h:57`），ctypes 必须 `c_size_t`。先前写成 `c_uint32`，`select_schema` 一直返回 0 且**日志里没有任何错误**，白查两轮。相关签名还有 `Bool = int`（第 46 行）、`clear_composition(SessionId)` 单参（第 318 行）、`get_current_schema(SessionId, char*, int)`（第 347 行）、`select_candidate_on_current_page(SessionId, size_t)`（第 445 行）。
2. **librime 的 `ConfigDependency` 会扫整份 schema 里所有叫 `dictionary` 的键**，session 加载时逐个 `Dictionary::Require()`。副本里那四个没用到的命名空间（`en_word` / `zh2en_wubi` / `en2zh_v2` / `zh2en_pinyin`）直接把离线加载打死（`Error loading table for dictionary 'en_word'`，随后 `en_word/dictionary not specified in schema`）。⇒ 脚本对副本剥掉这些块 + custom 里对应的 `translator@<ns>` 行。**发布配置不动**：鸿蒙上 `en_word` 是 Lua `enWord_Filter` 在供（H-260(CodeArts) v44）。
3. **userdb 是 LevelDb，键是二进制读不出来**；副本改成 `tabledb` 才有可读的 `user.txt`，且 TextDb 只在 db 析构时落盘 ⇒ 必须 `RimeFinalize` 才读得到。
4. **一个进程只能跑一套完整 librime 生命周期**，第二变体直接 `access violation reading 0x...40`。⇒ 改成 `orchestrator` 每变体 `subprocess.call` 一个子进程，各写 `encoder-ab-<tag>.json`，主进程只做合并与判定。
5. 首次解析 `user.txt` 时把 `\x7fenc\x1fhgha` 整串当码去上屏，preedit 回来成 `en c hg ha`，一度误判「两边都不出」；判定必须以 `tgtf` 这条探针为准。

---

## 9. 主人要的那一句（「三端词库一样、编码机制不一样是吧」）

**不是编码机制不一样。** 三端造词规则是同一套（librime `UnityTableEncoder`，三字词＝一二字首码＋第三字前两码 ⇒ 行不行=tgtf），词条数也一直是 136,916 完全相同；差的是**鸿蒙这份词库文件在移植时掉了第 4 列「末级全码（stem）」**——20,935 行只剩 25 行，引擎推不出编码，所以只有鸿蒙造不出词。现在列补回来了，实测只有补列后的那份打 `tgtf` 能出「行不行」。

---

## 10. 本目录文件

| 文件 | 内容 |
|---|---|
| `wubi86.dict.yaml.before-stems` | 修复前鸿蒙词典原件备份（2,290,104 B / md5 `e7dfa7a7…`） |
| `encoder-ab-offline.json` | A/B 合并结果（含 `verdict_能造出并记住`） |
| `encoder-ab-A-old-dict.json` / `.stdout.log` / `.stderr.log` | A 变体明细与 librime 日志 |
| `encoder-ab-B-fixed-dict.json` / `.stdout.log` / `.stderr.log` | B 变体明细与 librime 日志 |
| `H-279-encoder-root-cause-offline-ab.md` | 本文件 |

复现：`python scripts/h279_restore_stems.py --dry`（只统计不写盘）；`python scripts/h279_encoder_ab_test.py`（离线 A/B，需桌面那份 `rime-backup` 里的 `librime` 与 `weasel-0.17.4` 运行目录）。
