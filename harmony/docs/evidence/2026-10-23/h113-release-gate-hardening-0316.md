# H-113：`release_build.ps1` 内容闸门的两处可绕过点已堵死（03:16）

取证/动手时间：2026-10-23 03:1x（Qoder 主会话，夜里等 H-106 交付的空档）。**只改 `scripts/release_build.ps1`（归属 Qoder），没有运行它** —— 夜间禁止跑发布链（它会签提审用 `.app`）；`entry/src/**` 一行没动，没构建、没签名、没装机、没碰手机。

## 一、这条为什么会留在待办里：是我自己把它派错了人

H-113 是我 00:1x 只读审计时开出来的，缺陷在 `scripts/release_build.ps1`，而 `docs/HANDOFF.md` 的「文件归属」表里 `scripts/**` 明确归 Qoder。当时我却把负责人写成 A（CodeArts），下一步写「CodeArts 在 code freeze 前随任意脚本改动一并收口」⇒ **让写鸿蒙应用代码的人去改我的发布脚本**，既违反分工，也让这条一直没人真动手。本轮按归属把它收回我自己做，并给 CodeArts 发 M-116 说明「这个文件你别动」。

## 二、原来那两个可绕过点（逐字对照旧代码）

旧块（`bak_0315_release_build.ps1:185-198`）长这样：

```powershell
if (Test-Path -LiteralPath $Checker) {
    & $PyExe $Checker $OutApp
    if ($LASTEXITCODE -ne 0) { throw "package content check FAILED ..." }
} else {
    Write-Warning "check_app_content.py not found; package content was NOT verified"
}
```

1. **闸门文件不在 ⇒ 只 `Write-Warning`，随后照常打印 `RELEASE OK`。** 脚本被改名、挪走、或者哪天 checker 挪了目录，出件就完全没有内容核验，而日志最后一行仍是最容易被人当成结论的 `RELEASE OK`。这正是 13:25 那份不合格 `.app` 能一路走通的同一类失效模式（签名有效 ≠ 内容正确，见 `project-app-content-audit`）。
2. **闸门失败时 `throw` 之前，签名后的 `.app` 早已在 `:150` 落盘。** 抛错只让控制台难看，产物仍躺在 `entry/build/default/outputs/default/` 里，`*.app` 和 `*.app.sha256` 成对齐全 ⇒ 谁（包括第二天早上的我自己）按「最新那份产物」去取，就可能把不合格包当合格包传上 AGC。
3. 附带：`:186` 注释还写「14-item checker」，实际早已 16 项（H-115 之后）。注释在这里不是装饰 —— 它是下一个人判断「这个闸门覆盖到什么」的依据。

## 三、改法（三条都落在同一个块里）

- checker 缺失 ⇒ 与闸门失败同等处理：**先隔离产物再 `throw`**，`Write-Warning` 分支删掉。
- 新增 `Stop-AsRejected()`：把 `$OutApp` 与 `$OutApp.sha256` 各改名成 `*.rejected-<yyyyMMdd-HHmmss>`（带时间戳，不覆盖上一次隔离，也不删任何文件）。这样目录里再不会有"看起来能上传"的成对文件；`RELEASE OK` 也到此为止不会打印。
- 注释改为 16 项，并写明「missing checker 与 failing checker 一律阻断」的规则与出处（H-113）。

脚本必须保持**纯 ASCII**：PowerShell 5.1 会把无 BOM 的 `.ps1` 按 GBK 解码，中文注释会直接把脚本改坏（这条坑已在该文件历史上踩过一次），所以新增文案全部用英文。

## 四、怎么验的（判据也要有已知坏样本）

没有运行 `release_build.ps1` 本体（夜间禁跑发布链），改用**从真实文件里逐字抽取被改的那一段**来跑三例：`F:/qoderwork/_audit_tmp/2026-10-23/h113_harness.ps1` —— 它按 `# Content gate` 到 `Write-Host "RELEASE OK"` 之间切片，把这段原样塞进临时目录里的 wrapper 脚本，用桩 `check_app_content.py`（`sys.exit(0)` / `sys.exit(1)`）与"根本不建桩"三种情况驱动。**测的是文件里真正那几行文本，不是我在别处重写的一份等价逻辑。**

| 用例 | 现场结果 | 判读 |
|---|---|---|
| A：checker 缺失 | `exit=1`、无 `REACHED-OK`、`pkg.app` 已不在、隔离文件 2 个（`pkg.app.rejected-20261023-031513`、`pkg.app.sha256.rejected-…`）、**无 `NOT verified` 警告** | 绕过点①关闭：不再"警告后放行"，产物也被隔离 |
| B：checker 判失败（桩 exit 1） | `exit=1`、无 `REACHED-OK`、`pkg.app` 已不在、隔离 2 个 | 绕过点②关闭：`.app` + `.sha256` 成对隔离，不会留在目录里冒充合格包 |
| C：checker 通过（桩 exit 0） | `exit=0`、`REACHED-OK` 出现、`pkg.app` 仍在、隔离 0 个 | 闸门没有被改成"永远过不去"，好样本仍能通过 |

整文件另外两项检查：`PSParser::Tokenize` **语法错误 0**；`NON-ASCII bytes = 0`（纯 ASCII 保住了 GBK 解码这条坑）。harness 汇总行：`RESULT: PASS (3/3 cases behave as designed; script is ASCII and parses)`，exit 0。

我自己写 harness 时也踩了一次：`Get-Child` 拼错 ⇒ PowerShell 报 `CommandNotFoundException`，但**同一轮的其它断言照样在跑**，差点让我以为"quarantined=0 说明没隔离"。真去看 `pkg.app=False` 才发现隔离其实生效了，是统计那一行坏了。教训照旧：断言失败先分清"被测物坏了"还是"量具坏了"，别看一个 0 就下结论。

## 五、还剩什么（不能因为这次 PASS 就宣称发布链已验）

- **端到端仍未跑过**：桩只证明这段控制流对，不证明真实 `.app` 上 `check_app_content.py` 16 项全绿。那要在 code freeze 那天，CodeArts 交付定稿、H-106 装机验收之后，由我跑一次 `release_build.ps1` 才算 —— 而且当夜就得用它产出的那份 `.app` 提审，不能拿旧的。
- 已知 `release_build.ps1` 的其它约束不变：它内部会调 `sign`，`sign/**` 我只让脚本自己用，不读内容、不入仓库、不进聊天。
- 提审 `.app` 必须 16/16 且阻断 0；当前源码线 14/16（裸 HAP 阻断 0），两个缺口是 ⑨b（H-105 模板启动图）与 ⑩（H-098 探针页），二者对 `.app` 输入是阻断级（H-115），随 M-097 收尾批处理。

## 六、本轮结论

H-113 从「我派错人、于是一直 OPEN」变成「我自己做完并有三例回归（含两个已知坏样本）」，发布链的**内容**闸门现在不可静默绕过；归属也顺手改回 Q。改动只在 `scripts/release_build.ps1` 一个文件，`.ps1` 保持纯 ASCII。

**闸门不变：H-106 未交付前不构建。** 03:1x 实跑 `h106_precheck.py` 仍 5 项阻断、exit 2。
