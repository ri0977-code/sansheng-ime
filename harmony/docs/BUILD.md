# 构建 / 签名 / 装机

> 所有命令在 **PowerShell** 下执行。bash 下 java spawn 会失败，这是旧环境实测过的坑。

## 1. 环境

| 项 | 路径 |
|---|---|
| DevEco Studio | `D:\DevTools\DevEco\DevEco Studio` |
| SDK | `D:\DevTools\DevEco\DevEco Studio\sdk` |
| JDK | `D:\DevTools\DevEco\DevEco Studio\jbr` |
| node | `D:\DevTools\DevEco\DevEco Studio\tools\node\node.exe` |
| hvigor | `D:\DevTools\DevEco\DevEco Studio\tools\hvigor\bin\hvigorw.js` |
| hdc | `D:\DevTools\DevEco\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe` |
| 签名工具 | `D:\DevTools\DevEco\DevEco Studio\sdk\default\openharmony\toolchains\lib\hap-sign-tool.jar` |

DevEco 版本：`DS-261.23567.138.36.2600851`；hvigor：`6.26.8`。

## 2. 构建

```powershell
cd F:\qoderwork\sansheng-ime-harmony
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1
```

脚本会设置 `DEVECO_SDK_HOME`、`JAVA_HOME`，然后执行：

```text
assembleHap --mode module -p product=default -p buildMode=debug --no-daemon
```

产物：

```text
entry\build\default\outputs\default\entry-default-unsigned.hap
```

首次构建/清缓存后会慢（F 盘是机械盘），不要中途杀进程。增量构建通常几十秒到几分钟。

### 2.1 验收时**只比字节数，不要比 hash**（2026-10-23 实测）

HAP 是 ZIP，**每条条目的 DOS 时间戳取的是构建时刻**：01:17 那份 `entry-default-unsigned.hap`
（28,179,829 B）里 **83 条条目的时间戳全部＝2026-10-23 01:17:18**，即同一个构建时刻。
⇒ 同一份代码、同一个 commit，**两次构建（尤其两台机器/两个检出目录）产出的文件不会逐字节相同，
但长度相同**。所以「我和 CodeArts 对齐产物」这条闸门，比的对象是 **unsigned 文件的字节数**
（`Get-Item .Length`／`os.path.getsize`），**不是** sha256/md5。
`release_build.ps1` 顺手写的 `.sha256` 只是给上传/留档用的单文件指纹，不能拿来跨构建比。
谁哪天把闸门改成「两份 HAP hash 相同才装机」，会 100% 误判成「对方构建坏了」。

同一节里另外两个会让「字节数」对不上的已知因素（都归我这侧，H-131／H-129）：

1. **换检出目录构建会少 271,533 B** —— 本机工作区有 18 个进包 rawfile 是 CRLF，而 `.gitattributes`
   已钉成 LF，全新检出拿到的是 LF 版；rawfile 进包是 ZIP_STORED 不压缩，所以 CR 是 1:1 进包。
   判据：`python scripts/eol_audit.py`（进包漂移应归 0，现在 271,533）。归一化要单独一轮做，
   因为会改基准数；做之前在 MAILBOX 报数。
2. **别在 `entry/src/main/resources/rawfile/**` 里用文本模式写文件而不钉 `newline`** ——
   本机 `core.autocrlf=true`，那样写出来的磁盘文件带 CR 而 git 里是 LF，`git status` 一路干净，
   等到构建才发现包变大。我这侧的 11 处已在 commit `d400d8d` 钉死。

## 3. 签名

新构建产物默认 **unsigned**，用脚本签名：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sign.ps1
```

产物：

```text
entry\build\default\outputs\default\entry-default-signed.hap
```

脚本自动读 `sign/keys.local.json`（别名 + 口令，**已 gitignore，绝不提交**），
也可用 `-Hap` / `-Out` / `-KeysFile` 覆盖路径。

签名资产在 `sign/`（**已 gitignore，绝不提交**）：

```text
sign/sansheng.p12          ← 私钥库，别名 [本地密钥已脱敏]
sign/sansheng.cer          ← 应用证书
sign/sanshengDebug.p7b     ← 调试 Profile
sign/sansheng.csr
sign/agconnect-services.json
sign/keys.local.json       ← 别名与口令，只在本机
sign/PROGRESS.local.md     ← 本机备注（不含口令）
```

> 口令只放 `sign/keys.local.json`；不要写进 `docs/`、聊天、git。
> 已验证：2026-10-20 用脚本成功签出 `entry-default-signed.hap`（6,992,543 字节）。

## 4. 装机

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install.ps1
```

默认安装 `entry-default-signed.hap`；也可以指定：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install.ps1 -Hap "路径\xxx.hap"
```

## 5. 设备

| 项 | 值 |
|---|---|
| 机型 | Mate 80（VYG-AL30） |
| 系统 | HarmonyOS 7.0.0.105 |
| API | 26 |
| 引擎库 | arm64-v8a（仅此 ABI） |
| 连接 | USB 调试，或无线调试 |

检查设备：

```powershell
& "D:\DevTools\DevEco\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe" list targets
```

返回 `[Empty]` 就是没连上。

## 6. M1 真机验收清单

- [ ] `hdc list targets` 能看到设备
- [ ] HAP 安装成功，桌面出现「三生输入法」
- [ ] 设置 → 系统 → 语言与输入法 → 输入法，列表里能添加「三生输入法」
- [ ] 切换到三生输入法，键盘面板能弹出
- [ ] 在备忘录里能输入字母、数字、空格、回车、退格
- [ ] 候选栏显示 mock 候选（你/尼/泥/呢/你好）
- [ ] 点候选能把词上屏
- [ ] 键盘不遮住输入框，横竖屏不崩
- [ ] 失败时抓 `hdc shell hilog` 或截图，记入 `ISSUES.md`

## 7. 常见问题

| 现象 | 处理 |
|---|---|
| hvigor 报 java/进程错误 | 用 PowerShell，不要用 Git Bash；确认 `JAVA_HOME` 指向 DevEco 的 `jbr` |
| 构建找不到 SDK | 确认 `DEVECO_SDK_HOME` 指向 `D:\DevTools\DevEco\DevEco Studio\sdk` |
| hdc 看不到设备 | 开发者模式 + USB 调试 + 设备上点「允许」；换线/换口 |
| 安装报签名错误 | HAP 未签名或 profile 不匹配；用 `sign/` 里的资产重签 |
| 安装报版本降级 | 先卸载旧 `com.sansheng.ime`（会清数据，先确认） |
| 输入法不在系统列表 | 这是闸门①；旧基线已验证通过，新包若失败先查 `module.json5` 的 `inputMethod` 扩展和 `input_method_config.json` |
| 面板尺寸不对 | 先 `setUiContent` 再 `Panel.resize`；单位用 vp；参考官方 InputMethod Sample 或 hMixedKeyboard |

## 8. 证据留存

每次构建/装机至少留：

- 构建命令与最后 30 行日志（或脚本输出）
- HAP 路径 + 大小
- `hdc list targets` 输出
- 真机现象（截图/录屏/文字）
- 失败时的 `hilog` 片段

写进 `VERSION_LOG.md` 和 `ISSUES.md`，不要只发聊天。
