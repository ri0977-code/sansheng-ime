# 随包 `.so` 的对外声明缺口与修复（H-128/H-129/H-130，2026-10-23 04:0x，Qoder）

本轮全程只读量测 + 改我这侧的法律文档与自测脚本：**没构建、没签名、没装机、没碰手机，`entry/src/**` 的 `ets`／`pages` 一行没动**（改的 `entry/src/main/resources/rawfile/legal/notice.html` 是我这侧脚本 `build_notice_html.py` 的产物，与既往 `d7e7672` 同一口径）。

## 一、为什么去查这个

上架被拒最常见的不是功能，是「对外声明与实际随包内容不一致」。上一轮（H-126）我给内容闸门补了「包内文本必须与源文件逐字节同源」，但那解决的是**新旧**，没解决**覆盖**：包里放了一个没声明的第三方二进制，任何关键词判据都看不出来。于是做一次双向覆盖量测。

## 二、量测方法与实际数字

脚本（仓库外，一次性）：`F:/qoderwork/_audit_tmp/2026-10-23/notice_coverage.py`，输出 `cov_out.txt`。
做法：解包 `entry-default-unsigned.hap` 取全部 83 条条目的 basename 集合；再把根 `NOTICE`（20,988 B）与 `docs/release/legal/` 下 15 个 md 里出现的所有「文件名样式」字符串取 basename 并集（133 个）；两个方向做差集。

- **A（包里有／声明里没点名）＝ 11 条**：`libc++_shared.so`、`libfanxing_rime.so`、`app_icon.png`、`layered_image.json`、`input_method_config.json`、`main_pages.json`、`module.json`、`pack.info`、`pkgContextInfo.json`、`resources.index`、`sourceMaps.map`。后 9 条是构建器产物或本项目的配置／索引，无第三方许可义务；**前 2 条是真缺口**。
- **B（声明里点名／包里没）＝ 61 条**，其中绝大多数是正当的：文档之间的交叉引用（`SIGNING.md`、`DECISIONS.md`…）、`LICENSES/*.txt` 原文（它们不是独立条目，已被合成进 `notice.html`）、以及 `symbols.yaml`／`symbols.custom.yaml` 这类 **D-020 明确「1.0.0 不打包」** 的条目。另有一批带前导空格的名字（如 `␣dateTime_filter.lua`）是正则把中文顿号后的空格一起吃进去的产物，属**误报**，人工核对后不算缺口。

## 三、真缺口：`libc++_shared.so` 全文 0 命中

对 `NOTICE` 逐词实测：`libc++` 0 次、`c++_shared` 0 次、`.so` 仅 1 次（「随同一个 .so/.a 一并进包」这句泛指）。而第二节那张表列的是 `librime.a`／`libleveldb.a`／`libglog.a`／`libmarisa.a`／`libyaml-cpp.a`／`liblua.a`／`libopencc.a` —— **这 7 个 `.a` 都不单独进包**，真正进包的两个 `.so` 一个都没被点名。

入包 `.so` 的来源逐字节核实（比对 HAP 内条目与仓库里 8 个同名文件）：

| 条目 | 入包字节 | sha256 前缀 | 与仓库哪一份相同 |
|---|---|---|---|
| `libs/arm64-v8a/libc++_shared.so` | 1,262,504 | `965803c3fe53e024` | `intermediates/cmake/…`、`intermediates/libs/…`、`stripped_native_libs/…` 三处同值；**源码树里没有** |
| `libs/arm64-v8a/libfanxing_rime.so` | 5,549,616 | `ac47e80ccdc6f8f8` | 仅 `stripped_native_libs/…` 同值（未剥离那份 13,190,344 B） |
| — 对照：`entry/src/main/cpp/lib/libfanxing_rime.so` | 4,870,448 | `385cbef5e988532f` | **不等于入包那一份**；`fanxing_rime_har/src/main/cpp/lib/` 下是同一个文件 |

结论与许可判断：

1. `libfanxing_rime.so` 是**本项目构建产物** —— `entry/src/main/cpp/CMakeLists.txt` 实测：`add_library(fanxing_rime SHARED fanxing_napi.cpp)`，把 7 个 `.a` 用 `--whole-archive`（librime/liblua）＋普通链接（opencc/marisa/leveldb/yaml-cpp/glog）缝进去，另链系统库 `libace_napi.z.so`／`libhilog_ndk.z.so`／`libc++.a`。所以 NOTICE 把随包二进制成「预编译静态库/动态库」是**表述失真**：`.a` 是预编译的，`.so` 是现场链出来的。
2. `libc++_shared.so` ＝ LLVM libc++ C++ 标准库运行时，由 DevEco / OHOS NDK 工具链在原生构建时注入（依据就是它不在源码树、只在构建中间产物里，且三处中间产物与入包逐字节相同）。适用许可 **Apache-2.0 WITH LLVM-exception**；该例外明确允许分发「与 LLVM 库链接得到的编译产物」时不附许可文本 ⇒ **不往 `LICENSES/` 里塞一份我并没有核可来源的抄本**，只在 NOTICE 如实点名上游与许可。这是新增声明，不是新增义务。
3. 顺带（H-129）：`cpp/lib/` 与 `fanxing_rime_har/src/main/cpp/lib/` 里那份 4,870,448 B 的 `libfanxing_rime.so` 是 CMake 从未引用的预编译件，与入包那份不同源 ⇒ 仓库死重，且会让人误判「随包 `.so` 就是预编译的」。**本轮不删**：删二进制要在下一次成功构建后复验字节数，夜里不该动构建输入。

## 四、已改的内容

- 根 `NOTICE`：第二节「说明：librime 上游…」之后插入 25 行「随包动态库的实际清单」，含两个 `.so` 的字节数／sha256 前缀／构建链证据／许可结论，并写明 `.a` 不单独进包与静态链接的许可义务。文件 20,988 → **23,164 B**。备份 `F:/qoderwork/_audit_tmp/2026-10-23/bak_notice_0405/NOTICE.bak`。
- `python scripts/build_notice_html.py` 重跑：应用内 `notice.html` **73,388 → 75,564 B**；`build_legal_html.py` 重跑后 privacy／terms 未变（它们的源 md 这次没动，说明生成器只把该动的动了）。
- `docs/release/legal/third-party-declarations.md`（应用内「第三方声明」页的唯一文案源）：补 libc++ 行 ＋ 「实际入包的是两个 `.so`」的说明；顺带修 **两处上游署名错误** —— `s-yamasaki / marisa` → `s-yata/marisa-trie`、`biomimic/yaml-cpp` → `jbeder/yaml-cpp`（与 NOTICE 一致），`harmonyos-next-rime` → `chuanis/harmonyos-next-rime-har`。该文件不是任何 HTML 的输入，无需重生成。

## 五、闸门现在抓到了一次**真实**过期（不是合成样本）

改完 NOTICE 后跑 `python scripts/check_app_content.py entry-default-unsigned.hap`：

```
[FAIL] 11. 包内能读到 NOTICE 与全部许可全文，且与当前 NOTICE/LICENSES 逐字节同源
       包内 notice.html 与当前 NOTICE/LICENSES 不同源（源文件已改、页面是旧的）⇒ 先跑 python scripts/build_notice_html.py 再构建（现 73388 B）
结果: 13/16 通过；阻断项未过 1 个
```

这正是 H-126 那条判据该有的反应：磁盘上 01:17 那份包**确实**带着旧版许可页面，而新版还没被构建进去。这份包本来就不提审、不装机，所以阻断不影响今晚链路；**下一次构建会自动带上 75,564 B 的 `notice.html`**，⑪ 随之回到 PASS。这条判据由「合成坏样本能拦」升级到「真实过期事件能拦」，是本轮额外拿到的一层证据。

## 六、自测把期望绑在了过期产物上（H-130，我自己的坑）

`check_app_content_selftest.py` 以磁盘上「最新 unsigned HAP」为底包。我改 NOTICE 而还没重新构建 ⇒ `00-baseline`／`16-good` 期望的 ⑦/⑪ PASS 立刻变 FAIL，22 例里 **2 例 MISMATCH、exit 1**。这不是判据坏，是自测的基准选错：它拿一份必然滞后于源文件的产物当「已知良好」。

修法：底包的三个 `resources/rawfile/legal/*.html` 一律注入**工作区当前的生成产物**（脚本会打印 `底包 legal 已换成工作区当前产物: notice.html 73388→75564 B`），语义变成「现在构建会得到什么」，与 ⑪/⑦ 的同源基准同一条。改后 **22 例全 ok、exit 0**，并第一次把「满级可达」钉死：

```
00-baseline  14/16（⑨b/⑩ WARN，阻断 0）
16-good      结果: 16/16 通过；阻断项未过 0 个        ok
19-notice-stale 13/16 阻断 1                          ok
20-privacy-stale 13/16 阻断 1                         ok
17-app-baseline 14/16 阻断 2（.app 下 9b/⑩ 升阻断）   ok
18-app-good     结果: 16/16 通过；阻断项未过 0 个      ok
```

`18-app-good` 16/16 说明**提审包的满分状态是可达的**（补好图标 ＋ 去掉探针页 ＋ 三层同源），不再只是纸面推断。

## 七、遗留

- H-129（OPEN，我这侧）：清 `cpp/lib/**` 与 `fanxing_rime_har/src/main/cpp/lib/**` 里那份未被引用的 `libfanxing_rime.so`，要等一次成功构建后按字节复验再动。
- M-04 应用内「关于/第三方声明」页由 CodeArts 渲染时，libc++ 那行**不要**指向不存在的 `LICENSES/` 文件（第四节已写明写法）。
- 今晚仍不构建：`h106_precheck.py` exit 2／阻断 5 未变，等 CodeArts 的交付行。

## 八、换行符护栏到底修了什么 —— 我先前那句结论说得太满，这里用实测改正（H-131）

第四节里我给 `.gitattributes` 写的注释，理由是推断而不是实测。04:2x 我用一次性克隆做 A/B，
**第一次得出的结论是「`.lua`／`.txt`／包内 HTML 其实不翻，只有 `NOTICE` 和 `notice.html` 翻」**，
并准备据此认错。那个结论本身也是错的，错在测量方法：

- 坑①（列号）：`git ls-files --eol` 每行是 `i/xxx w/xxx attr/xxx <TAB> 路径`，
  **制表符前 split 的第 0 列是索引、第 1 列才是工作区**。我第一遍取错列，报出过「w/crlf 总数＝0」。
- 坑②（stat-clean，更要命）：`git checkout <旧 commit>` 只重写两个 commit 之间**有差异**的文件；
  没被重写的文件保持它上次检出时的行尾 —— 改了 `.gitattributes` 也不会回头重写。
  所以那个克隆里我只看到「差异文件翻了、其他没翻」，这是假象。

正确的做法（`scripts/eol_clean_test.sh` 的思路）：`git clone --shared --no-checkout` → 先检出
`.gitattributes` → 把待测文件**从磁盘删掉** → `git checkout -- <这些文件>` 重新落盘，再数字节。
结果（本机 `core.autocrlf=true`）：

| 文件 | 护栏前 690ab2b 全新检出 | 护栏后 c19c54a 全新检出 | 是否进包 |
|---|---|---|---|
| `NOTICE` | 21,255 B（CRLF=267） | 23,164 B（CRLF=0） | 生成器输入 |
| `rawfile/legal/notice.html` | 74,433 B（CRLF=1045） | 75,564 B（CRLF=0） | 进包 |
| `rawfile/legal/privacy.html` | 9,026 B（CRLF=164） | 8,862 B（CRLF=0） | 进包＋AGC 托管 |
| `rawfile/legal/terms.html` | 7,863 B（CRLF=151） | 7,712 B（CRLF=0） | 进包＋AGC 托管 |
| `rawfile/rime/lua/GUID.lua` | 1,542 B（CRLF=74） | 1,468 B（CRLF=0） | 进包 |
| `rawfile/rime/Custom_phrase.txt` | 1,657 B（CRLF=46） | 1,611 B（CRLF=0） | 进包 |
| `rawfile/rime/*.dict.yaml`／`symbols.json`／`*.md`／`*.ets` | 不翻 | 不翻 | 进包 |
| `scripts/*.py` | 翻（19,221→19,589 B） | **仍翻（CRLF=368）** | 不进包 |

也就是说：`.yaml`／`.json`／`.md`／`.ets` 不翻是因为它们**早就有 `eol=lf` 规则**，
其余无规则的文本（`NOTICE`、`.html`、`.lua`、`.txt`、`.py`、无扩展名文件）在全新检出里全都会翻。
我原先「包内字节数整体变化」的推断**成立**，只是当时没证据；`*.py` 缺规则是这次唯一补上的真实缺口
（它不进包，只影响跨机器 diff，注释里也照实这么写了）。

## 九、护栏之外还有一件事：本机工作区已经和全新检出不同源（H-131，OPEN）

护栏管的是**未来的检出**，不会回头改本机磁盘上的字节 —— 而本机工作区里已经有一批 CRLF 文本，
来源是脚本在 Windows 下用文本模式写文件（`open(...,'w')` 把 `\n` 写成 `\r\n`），
提交时 clean 过滤器又把它们转回 LF，于是 `git status` 一路显示干净，没人看得见。

`python scripts/eol_audit.py`（本轮新增，比较工作区字节与索引 blob，不依赖克隆）实测：

- 全仓 eol 漂移 **78 个文件／299,111 个多余 CR 字节**；
- 其中**进包 rawfile 18 个文件／271,533 B**（最大三笔：`zh2en_wubi.dict.yaml` 89,850、
  `zh2en_pinyin.dict.yaml` 89,747、`lua/dic_4w_en.txt` 39,814）；另有 8 个 `LICENSES/*.txt`（348 B，
  是 `notice.html` 生成器的输入）和 5 个 `ets` 应用代码文件（771 B，**归属 CodeArts，我没碰**）。
- 01:17 那份 `entry-default-unsigned.hap`（28,179,829 B）里，rawfile 条目是 **ZIP_STORED 不压缩**
  （`compress_size == 未压缩大小`，逐条已核对），所以这些 CR 字节 1:1 进了包；
  包内 `rime/lua-files.txt` 1,092 B／CRLF=44 与工作区逐字节相同，证实「磁盘字节＝包内字节」。
- 结论：**同一份 commit，一次全新检出后构建的 HAP 会比现在这台机器构建的小约 271.5 KB**，
  我和 CodeArts 的「unsigned 逐字节比对」只要有一方换了检出目录就会当场对不上，
  而且看起来会像是对方改错了代码。

处置（不在今晚做）：归一化会改变包内字节，属于「会影响比对基准」的动作，必须
① 等 H-106 交付并完成一次成功构建，拿到当前基准字节；② 单独一轮只做 `rawfile/**`＋`LICENSES/**`
的删文件重检出（`git rm --cached` 不动，纯工作区重写，`entry/src/main/ets/**` 一律不碰，那是 CodeArts 的）；
③ 立刻重跑 `eol_audit.py` 到进包漂移＝0，再重建、重新约定基准数；④ MAILBOX 里先把这件事通知 CodeArts，
免得他换目录后以为是构建不稳定。已确认可控的旁证：`.ocd2` 里那 5 个 CR 是二进制内容巧合，
`.gitattributes` 已把 `*.ocd2` 标成 binary，不会被转换，归一化时也不能算进「待修」清单。

**04:4x 补：上面那句「来源是脚本用文本模式写文件」由推断变成实查，并且再犯路径已关（commit `d400d8d`）。**
逐个 grep `scripts/**` 里 `open(..., 'w')`／`io.open(..., 'a')` 未带 `newline` 的调用，命中 11 处，分布在
`port_rime_data.py` 1、`wip.py` 3、`license_gap.py` 2、`third_party_audit.py` 1、`apk_parity.py` 1、
`h106_precheck.py` 2、`check_app_content_selftest.py` 1、`legal_state.py` 1，全部补上 `newline="\n"`
（只改写模式参数，逻辑零改动）。`wip.py` 那 3 处最要紧：它整份重写 `docs/WIP.md`，也就是闸门要解析的台账 ——
这解释了为什么台账文件也在漂移清单里。排除掉的两条：`build_notice_html.py:100` 与 `write_default_yaml.py:162`
本来就写了 `newline="\n"`；PowerShell 侧只有 `release_build.ps1`／`release_csr.ps1` 两个写入器，
用的是 ``($lines -join "`n")`` ＋ `UTF8Encoding($false)`（无 BOM），不产 CRLF。
改后复扫＝0，8 个文件 `py_compile` 全过且 CRLF=0，`eol_audit.py` 的三个数字与改前完全一致
（78／299,111、进包 18／271,533）⇒ **本轮没有归一化任何仓库文件**，存量漂移仍按上面的四步走。

顺带自纠一条操作失误：04:2x 我一条 `git clone` 参数写错，把 **292 MB 的克隆落在仓库根目录**
（`eol_verify/`，`git status` 里是未跟踪目录）。嵌套仓库被 `git add -A` 收进去会变成 gitlink
（假 submodule），比之前那 88 个根目录草稿严重。已删除，并在 `.gitignore` 加了 `/eol_*/`、`/*clone*/`
兜底 —— 但规矩仍然是：克隆只放 `F:/qoderwork/_audit_tmp/<date>/`。
