# H-123 — 发布脚本不会再留下「看起来能上传」的包（2026-10-23 03:2x，Qoder）

归属：`scripts/**` = Qoder（`docs/HANDOFF.md` 文件归属）。本轮仍然只有
`scripts/release_build.ps1` 一个文件，`.ps1` 保持纯 ASCII。

## 一、为什么 H-113 修完还不够

H-113 堵的是「内容闸门」那一段（缺 checker / 闸门 exit 非 0）。把脚本从头读完之后，
同一类问题在**闸门之前**还有两处，量级一样，因为它们同样把成品放在提审路径上：

1. **上一轮的包不会被清。** `$OutApp` 的名字只含版本号（`sansheng-ime-1.0.0-release.app`），
   每次跑都是同一个路径。原来脚本在 `sign-app` 之前不检查这里是否已有旧文件；
   一旦这一轮在后面任意一步失败（verify-app、结构检查、内容闸门之前崩），
   `outputs/` 里躺着的仍然是**上一轮那份** `.app` 和它配套的 `.sha256`。
   主人上传时看的是文件名和目录，不会知道它是哪一次构建的产物 —— 这正是 13:25 那份
   「签名有效但内容不合格」能被当成候选品的同一类失误，只是这次连"这一轮构建过"都对不上。
2. **闸门之前的失败点不隔离。** `verify-app on .app`（exit 码判据已有）和 zip 结构检查
   （`entry-default.hap` / `pack.info` 是否在内）失败时直接 `throw`，此时 `$OutApp` 已经
   被 `sign-app` 写在盘上了。原写法把「产物落盘」放在「产物被证明合格」之前，
   只对内容闸门做了补救，没对这两步做。

## 二、改法（一个函数 + 三类调用点）

`Stop-AsRejected(artifact, reason)` 移到脚本顶部（原来定义在内容闸门段里，
所以更早的调用点用不到它 —— 这一点本身就是回归测出来的，见 §四）。
改名而非删除，保留取证：`<name>.stale-<时间戳>` / `<name>.rejected-<时间戳>`。

- **开跑先扫**：`$OutDir` 里所有 `*.app` 连同各自 `.sha256` → `.stale-*`。
  `-Filter '*.app'` 精确匹配后缀，所以已隔离的 `*.app.stale-*` 不会被反复改名。
- **显式 `-OutApp` 目标**在算出最终路径后再清一次（覆盖指到 outputs 之外的情况）。
- **verify-app + 结构检查**整段包进 `try/catch`：任一步失败 ⇒ 先隔离 `.app` 与 `.sha256`，
  再 `throw`（原样重抛，不吞异常、不改退出码语义）。
- **内容闸门**沿用同一个函数，注释改成引 H-113/H-123。

脚本内 `Stop-AsRejected` 现在 1 处定义 + 10 处调用（扫描 2、显式目标 2、catch 2、
闸门两条分支各 2），`PSParser` 解析 errors=0，非 ASCII 字节=0（PowerShell 5.1 会把无
BOM 的 `.ps1` 按 GBK 解码，中文注释会坏）。

## 三、为什么现在能验、端到端仍要留给冻结点

夜间不出包（主人的硬约束），所以这轮用「把真实脚本正文切出来单独跑」的方式取证，
量的是**我改的那几段本身**，不是整条链路：真实 `.app` 是否真能通过这条链，
仍然只有 code freeze 那一轮实跑才算数。

## 四、回归：8 例，含 4 个已知坏样本

`F:/qoderwork/_audit_tmp/2026-10-23/h123_harness.py` —— 按标记从
`scripts/release_build.ps1` 切出四段（函数定义 / 开跑扫描 / verify+结构 / 内容闸门），
拼桩变量与桩产物写成独立 `case.ps1` 用 `powershell.exe -File` 跑，逐例断言退出码、
`REACHED-OK` 哨兵、隔离文件清单、失败后提审路径上是否还留着文件。

| # | 用例 | 输入 | 期望 | 实测 |
|---|---|---|---|---|
| 1 | `gate_missing_checker` | 有 `pkg.app`+`.sha256`，无 checker（H-113 回归） | exit≠0、无 REACHED-OK、隔离 2 份、输出不得含 `NOT verified` | 符合 |
| 2 | `gate_checker_fails` | 桩 checker `sys.exit(1)` | exit≠0、隔离 2 份 | 符合 |
| 3 | `gate_checker_passes` | 桩 checker `sys.exit(0)` | exit=0、REACHED-OK、零隔离 | 符合 |
| 4 | `sweep_clears_previous_package` | `out/` 里放上一轮的 `.app`+`.sha256` | exit=0、两份都变 `.stale-*`、原名不在 | 符合 |
| 5 | `verify_good_package` | 真 zip（含 `entry-default.hap`+`pack.info`）、stub java exit 0 | exit=0、REACHED-OK、零隔离 | 符合 |
| 6 | `verify_missing_pack_info` | 真 zip 但**缺 `pack.info`**（坏样本） | exit≠0、`.app` 被隔离、提审路径不留文件 | 符合 |
| 7 | `verify_not_a_zip` | `.app` 是纯文本（坏样本，`.NET` 异常而非 `throw`） | 同上，证明 `catch` 也接得住非 ErrorAction 异常 | 符合 |
| 8 | `verify_app_verify_fails` | 好 zip 但 stub java `exit /b 1`（坏样本） | exit≠0、`.app` 被隔离 | 符合 |

`RESULT: PASS (8/8 cases)`。

**harness 自己也错过一次**（第 6 节那种「量具坏了还是被测物坏了」的区分）：第一版把函数
定义从闸门段里移出去之后，切片只截了闸门段 ⇒ 六例报 `quarantined=0`，看着像隔离逻辑失效，
实际是 `Stop-AsRejected` 未定义（exit 1 但没改名）。改法是把函数段一并拼进每个用例。
这条正是移动函数位置会踩到的坑，也说明**为什么必须留已知坏样本**：没有坏样本，
「期望隔离的例子里什么都没发生」会被误读成通过。

## 五、与内容检查器的相互作用（量过，不是推理）

我造的隔离文件名会不会被「默认选最新产物」那套逻辑抓回去当本轮的包？不会，而且是
可证的：`check_app_content.py` 的默认目标只有**两个固定路径**
（`DEFAULT_APP` = `entry/build/default/outputs/default/sansheng-ime-1.0.0-release.app`，
`DEFAULT_HAP` = 同目录 `entry-default-unsigned.hap`，`scripts/check_app_content.py:27-28`），
按 mtime 二选一，**不做 glob**；而隔离是改名成 `<名>.app.stale-<时间戳>` /
`.rejected-<时间戳>`，结尾不再是 `.app`，路径也不再等于 `DEFAULT_APP`。

现场实测（03:3x，只读）：`outputs/default/` 目前**没有任何 `.app`**（只有 01:17 的
unsigned / signed HAP 与 `pack.info`）；无参跑检查器 ⇒ 选中
`entry-default-unsigned.hap` **28,179,829 B / sha256 `cc80a989…b82c3a`** / 83 条目，
14/16、阻断 0、exit 0。顺带确认一件事：默认拿的是**未签名** HAP，它正是「构建完立刻
快检内容」该查的对象；发布那一步必须把 `.app` 路径**显式**传给检查器（既定链路里已经
这么写）。

## 六、结论

发布链的产物路径现在是「要么这一轮合格的包，要么什么都没有」：旧包开跑即隔离，
中间任何一步失败成品即隔离，内容闸门失败成品即隔离。CodeArts 侧无动作（M-116 已说明
`scripts/**` 归我、`release_build.ps1` 你别动）。

闸门不变：**H-106 未交付前不构建**。本轮量过：`scripts/h106_precheck.py` 在工作树
exit=2 / 5 项阻断，`KeyboardIndex.ets` mtime 仍 01:17:02 ⇒ 没构建、没签名、没装机、没碰手机。
