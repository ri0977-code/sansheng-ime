# H-144 · 唯一的 release 提审件被我自己的一次 clean 删掉了 · 2026-10-23 08:4x · Qoder

## 0. 一句话

2026-10-22 13:25 那份**已经通过全链路签名验证**的 release `.app`（11,791,326 B，sha256 `8dad9f3f…b5b6ef1`）和它里面的 release-signed HAP（27,822,532 B，sha256 `64dfcc2e…3ebd5c`），在 2026-10-23 00:08 被我本人执行的一条 `hvigorw clean` 删掉了；机器上**没有任何第三处副本**。文档里有 5 处现状表面还在用现在时说它们存在。物证为零，只剩抄在文档里的哈希能证明「曾经构建成功过」。

## 1. 谁做的、哪条命令、什么时候

- 执行者：**Qoder（我）**，不是 CodeArts，不是主人。
- 命令：`node hvigorw.js clean --no-daemon`（00:08–00:09）。
- 我自己在 `docs/evidence/2026-10-23/0009-clean-build-and-gate.md` 里写下了这条后果：**clean 会清空 `entry/build`**。也就是说做这件事的当时，我已经知道它清哪棵树，只是没把「那棵树里住着我唯一一份提审件」和它连起来。
- 动机是正当的：为了验证 H-113/H-123 内容闸门的「脏树也能重建」路径。代价记在这里。

## 2. 为什么闸门设计没能保住它（这条是真正的教训）

H-113 / H-123 的做法是：内容闸门判不合格时，**就地**把 `.app` 和 `.sha256` 改名成 `.rejected-<时间戳>`，然后 throw。它防的是「被当成合格件发出去」，它没防「整棵树被删」——改名后的文件仍然住在 `entry/build/default/outputs/default/` 里，和 clean 的作用域是同一棵树。

⇒ **凡是曾经落到提审路径上的东西，必须搬出构建树。** 就地改名 = 只是加了个后缀，不叫保留。

## 3. 08:4x 实测（全部只读命令，逐条可复现）

```
$ ls entry/build/default/outputs/default/
entry-default-signed.hap      28,288,696 B   10-23 01:17
entry-default-unsigned.hap    28,179,829 B   10-23 01:17
pack.info                          591 B     10-23 01:15
mapping/                                        10-23 00:09

$ find . \( -name '*.app' -o -name '*release-signed*' -o -name '*.rejected-*' \) | wc -l
0                       # 整个仓库：没有 .app、没有 release-signed HAP、没有隔离改名件

$ find /e/sansheng-sign-backup -type f \( -name '*.app' -o -name '*.hap' \) | wc -l
0                       # 13:26 那次机外备份只备份了签名材料，没有包

$ ls %TEMP%\ss-hap-archive\
prev-2348-codearts.hap  28,178,736 B   10-23 00:08   # 唯一留下的历史件，是 CodeArts 23:48 的调试包

$ ls -d /f/codeartswork/sansheng-ime-harmony/entry/build/default/outputs/default
（不存在）              # CodeArts 那侧工作区也没有可对照的 release 件
```

盘上现存两个包都是 **debug 签名**（01:17 那一对），按硬约束和商店规则**不能用来提审**，也不能当「上一版提审件」来比对内容。

## 4. 哪些表面在说现在时（需要补现状，不是改写历史）

需要加「文件已不在盘上，留档哈希仅作历史证明」的是**现状类**表面，分布在 5 个文件、共 7 处：

| # | 文件：行 | 现在的写法 |
|---|---|---|
| 1 | `docs/RELEASE-READINESS.md:23` | 「已跑通…`.app` 11,791,326 B」 |
| 2 | `docs/RELEASE-READINESS.md:127` | 「已出链路验证件 11,791,326 B」 |
| 3 | `docs/RELEASE-READINESS.md:158` | 「构建 + 二次校验：…11,791,326 B」 |
| 4 | `docs/release/SIGNING.md` §8（131-132 行那块产物清单） | 列在 `entry/build/…` 路径下，读起来像还在 |
| 5 | `docs/release/app-content-checklist.md:4` | 「对象：…／外层 11,791,326 B」——这份拆解本身是历史审计，保留 |
| 6 | `docs/release/AGC-release-profile.md:13` | 「出件：… 11,791,326 B」 |
| 7 | `docs/release/legal/third-party-declarations.md:87` | 「已到位」 |

**不动的历史行**：`docs/PROGRESS.md:232/271`、`docs/MAILBOX.md:192`、`docs/evidence/2026-10-22/*`。它们记录的是 10-22 当时发生的事，那句话在那个时点是真的，涂掉就等于改历史。

## 5. 机械侧修复（都在 `scripts/`，归我，不给 CodeArts 派单）

改前备份：`F:\qoderwork\_audit_tmp\2026-10-23\bak_0840_release_build.ps1`（11,696 B，与原文件逐字节相同）。

`scripts/release_build.ps1` 四处：

1. 新参数 `[string]$ArchiveDir`，默认 `F:\qoderwork\sansheng-release-artifacts` —— **`entry/build` 之外**，clean 打不到。
2. `Stop-AsRejected`：从「就地改名」改成「**移动**进 `$ArchiveDir\quarantine-<时间戳>`」。
3. 时间戳改成**一次运行一个**（`$script:QuarantineStamp`）——之前逐次调用取当前秒，实测会把一个 `.app` 和它的 `.sha256` 分进两个目录，等于又制造一次「找不到配对」。
4. 新 `Save-AcceptedSet`：内容闸门 16/16 PASS 之后，把 `.app` + `.sha256` + release-signed HAP + `MANIFEST.txt`（记 app/hap 的 sha256 与字节数、版本、`content_gate=PASS(16/16)`、保存时间、以及「durable copy outside entry/build; survives hvigor clean (H-144)」）复制进 `$ArchiveDir\accepted-<时间戳>`。
5. sweep 里旧的 `*release-signed.hap` 走 `superseded` 同样进归档，不再直接覆盖。

## 6. 自测（沙箱，不跑构建、不签名、不装机）

`F:\qoderwork\_audit_tmp\2026-10-23\test_h144_archive.ps1` —— 把 helper 段落切出来 dot-source 后在 `%TEMP%` 沙箱里演一遍。08:45 实跑输出：

```
CHECK ascii: non-ascii chars = 0
CHECK tokenize: errors = 0
CHECK grouping: quarantine dirs for one run = 1
CHECK grouping: files in that dir = 3
CHECK quarantine: moved out of build tree, kept in archive
CHECK accepted set: files = 4
CHECK accepted set: copies + MANIFEST fields present
CHECK survives clean: archive files after outputs wiped = 7
HARNESS PASS
```

最后一条就是这个 bug 的反证：**删掉整个 `outputs/` 之后归档仍有 7 个文件**（3 个隔离件 + 4 个已收件），且按名逐个核过。

跑过的三轮都是真问题，不是格式化失败：① `& $scriptblock` 不把函数发布到调用者作用域 ⇒ 改成写临时 `.ps1` 再 dot-source；② 我的 `-Filter '*.release-signed.hap.superseded'` 少算了实际叶名（真实是 `entry-default-release-signed.hap.superseded`）⇒ 改成 `*release-signed.hap.superseded`，这条当时让我误判「产品没搬走」；③ 断言写成「≥8」是我自己数错（3＋4＝7），改成按名精确核对 7 件。

## 7. 现在的实际影响与下一步

- 对进度的**净影响 = 0**：那份 `.app` 在 10-22 18:5x 的内容审计里已经判「不能提审」（10 项里 5 ❌），提审件本来就要等工作树干净后重建；这次丢的是「重建之后还要再丢一次」的可能性。
- 真正受影响的是一条**证据链**：如果有人问「10-22 有没有真出过一个 release 件」，现在只有文档哈希、没有实物。所以 §4 的现状说明必须写，且**不能写成「已备份」或「仍在」**。
- 重建动作按夜间约束推迟：`release_build.ps1` 夜里不跑。下一次跑它时，`Save-AcceptedSet` 会第一次真实落盘，届时用 `$ArchiveDir` 里的实物复核，而不是用哈希回忆。
- 与 H-106 闸门无关，不改变「一次一项」的顺序，**没构建、没签名、没装机、没碰手机**。
