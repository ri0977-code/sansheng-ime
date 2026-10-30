# 发布签名与 `.app` 打包（M6）

> 2026-10-22 · Qoder · 状态：**本机链路已用调试证书端到端跑通；只差 AGC 发布证书/Profile**
> 本文只写流程与公开指纹。私钥、口令、证书内容一律不进仓库/聊天/共享文档。

## 1. 当前状态

| 项 | 状态 | 说明 |
|---|---|---|
| 发布密钥对 | **已生成** | `sign/release/sansheng-release.p12`，别名 `sansheng-release`，ECC NIST-P-256 |
| 发布 CSR | **已生成，待上传** | `sign/release/sansheng-release.csr`，SHA-256 `ce1b16f13f6e6a2791a8f6ac6199e59d75cdf5027e8ebd923a8f56f4c17accab` |
| 发布证书 `.cer` | 等主人 AGC | 证书管理 → 发布证书 → 上传上面的 CSR → 下载 |
| 发布 Profile `.p7b` | 等主人 AGC | Profile → 发布类型 → 包名 `com.sansheng.ime` → 绑定该发布证书 |
| `.app` 构建/签名/验签 | **已验证** | 用现有调试证书跑通：最终 `.app` 27,983,039 B，`verify-app success` |
| 发布包真机 | 不适用 | 发布包只交 AGC；Mate 80 回归仍用调试签名 HAP |

本地文件（全部被 `.gitignore` 忽略）：

```text
sign/release/
  sansheng-release.p12          # 发布私钥（绝不出机、绝不入仓）
  sansheng-release.csr          # 只把这个上传 AGC
  sansheng-release.cer          # AGC 签发后放这里（待）
  sansheng-release.p7b          # AGC 发布 Profile（待）
  release-csr.info.txt          # 别名/主题/CSR 与 P12 的 SHA-256（无口令）
```

口令沿用已机外备份的调试密钥库口令，只存在 `sign/keys.local.json`；脚本不落盘、不回显。

## 2. 官方签名顺序（别搞反）

依据 DevEco `hvigor-ohos-plugin/src/tasks/sign-app.js` 与 `sign-packages-from-app.js`：

1. `assembleHap buildMode=release` → `entry-default-unsigned.hap`
2. **签 HAP**（发布证书 + 发布 Profile）→ `entry-default-release-signed.hap`
3. `app_packing_tool --mode app --hap-path <signed.hap> --pack-info-path <pack.info> --out-path <unsigned.app>`
   - 打包器要读 HAP 签名里的校验信息；给**未签 HAP** 会报 `HapVerifyInfos is empty`
   - 打包时会重写 HAP 容器，**内层 HAP 签名块会被去掉**（实测：包内 HAP `verify-app` 报 `No Hap Signing Block`）
4. **签 `.app`**（同一套发布证书/Profile）→ `sansheng-ime-<version>-release.app`
   - `hap-sign-tool sign-app` 接受 `.app` 输入；这一步才是 AGC 校验的签名
5. `verify-app -inFile <final.app>` → 必须 `Verify success`

> 只做到第 3 步就上传 = 交了一个未签名包，必被拒。脚本已按 1–5 全跑通。

## 3. 本机命令

首次生成发布密钥 + CSR（已完成；只有轮换密钥才重跑）：

```powershell
# 交互输入口令；或先设环境变量 SS_RELEASE_PWD
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\release_csr.ps1
```

AGC 证书/Profile 到位后（文件按上表命名）：

```powershell
# 口令默认提示输入；自动化时用 SS_RELEASE_PWD（或分开的 KEY/STORE 两个变量）
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\release_build.ps1
```

产物（`entry/build/default/outputs/default/`）：

```text
entry-default-release-signed.hap      # 给打包器用，不单独上架
sansheng-ime-1.0.0-release.app        # 上传 AGC 的最终包
sansheng-ime-1.0.0-release.app.sha256 # 大小/SHA-256/版本/时间
```

脚本会先 `verify-profile` 检查：签名有效、`type=release`、`bundle-name=com.sansheng.ime`；不符直接停，避免拿调试 Profile 签出“假发布包”。

> **2026-10-30 07:10 实跑记录（Qoder）**：`release_build.ps1` 全绿跑通，`.app` 18,249,521 B／sha256 `0d3b3a4ac70a…`、
> release-signed HAP 44,365,525 B／sha256 `95ce406e6211…`、`verify-profile` 报 `type=release bundle=com.sansheng.ime`、
> 内容闸门 **18/18、阻断 0**，accepted 套已存到树外 `F:\qoderwork\sansheng-release-artifacts\accepted-20261030-071035\`
> （含 `content-gate.txt` 原始输出）。
> **口令从哪来的（更正一条旧口径）**：本文与 `submission-artifacts-index.md` 此前都写「要主人在场输密钥密码」——不成立。
> `sign/release/README.local.md:8` 记录发布私钥库口令**与调试密钥库相同**，调试口令就在 `sign/keys.local.json`
> （键名只有 `keyAlias`/`keyPwd`/`keystorePwd` 三项；`/sign/` 已在 `.gitignore:19`，本次未把任何口令写进文档或日志）。
> 我用它设了 `SS_RELEASE_PWD`/`SS_RELEASE_KEY_PWD`/`SS_RELEASE_STORE_PWD` 三个环境变量后调用脚本，**没改 `release_build.ps1`、没把口令落盘**。
> **代价与要求**：发布私钥 `.p12` ＋口令 ＋ `.cer`/`.p7b` 目前**全在这块盘上**，README:10 那条「整个 `sign/` 拷一份机外」仍未办 ⇒
> 已开 `docs/ISSUES.md` **H-281**（P2，归主人）：异地副本＋一旦泄露是否轮换的判断。
> 复现命令（不含口令，口令自取）：`powershell -NoProfile -ExecutionPolicy Bypass -File <临时脚本>`，
> 临时脚本只做三行 env 赋值再调 `scripts\release_build.ps1 -Product default`；本次用的是
> `C:\Users\Administrator\AppData\Local\Temp\ssrel\run-release.ps1`（temp 目录，仓库里没有它，也不该有）。


## 4. 主人要做的 AGC 步骤（一次 15 分钟）

> **2026-10-22 更新**：`.cer` 已到手（见 §7），现在**只剩 Profile `.p7b` 一步**，
> 逐步点单页（含防点错对照表、落盘文件名、备份要求）见
> **`docs/release/AGC-release-profile.md`**，下面这版留作全流程备份。

1. 登录 AGC → 我的项目 → 证书、APP ID 和 Profile。
2. **证书** → 新增 → **发布证书** → 上传 `sign/release/sansheng-release.csr` → 下载 `.cer`。
3. **Profile** → 新增 → **发布** → 选 `com.sansheng.ime` → 绑定刚建的发布证书 → 下载 `.p7b`。
4. 两个文件改名为 `sansheng-release.cer`、`sansheng-release.p7b`，放进 `sign/release/`。
5. 告诉我「证书到了」。我跑 `release_build.ps1`，把 `.app` 指纹与验签结果写进共享文档。

注意：

- 发布证书每账号最多 3 张，实名开发者有效期约 3 年；**私钥丢失无法补发**，证书/Profile 到位后立刻把整个 `sign/` 再拷一份机外。
- 发布 Profile 不需要 UDID；调试 Profile 才有 `debug-info.device-ids`。
- CSR 主题是 `C=CN,O=Sansheng,OU=IME,CN=Sansheng IME Release`，不含个人姓名；证书身份由 AGC 账号实名决定。
- 不要用发布包 `hdc install` 到手机（发布 Profile 不绑设备）；真机回归继续用 `scripts/sign.ps1` 的调试签名包。

## 5. 实测证据（2026-10-22 04:34，调试证书）

- 流水线：未签 HAP → 调试签 HAP（28,049,331 B）→ 打包 → 签 `.app` → `verify-app`。
- 最终 `.app`：27,983,039 B，SHA-256 `1f278469398bb26dde90a241f02260e9538ab0df743647adf802784e87220de6`（仅证明流程，不是发布产物）。
- 包内结构：`entry-default.hap` + `pack.info`；内层 HAP 无签名块属官方默认（`appWithSignedPkg=false`），签名在 `.app` 层。
- 踩坑记录：`app_packing_tool` 的 HAP 参数是 **`--hap-path`**，不是 `--hap-list`；后者不报参数错，只报 `HapVerifyInfos is empty`。

## 6. 失败对照

| 报错 | 原因 | 处理 |
|---|---|---|
| `profile type is 'debug'` | 下错 Profile | 回 AGC 建「发布」Profile |
| `profile bundle-name is '...'` | Profile 绑错应用 | 重下 `com.sansheng.ime` 的 Profile |
| `HapVerifyInfos is empty` | 给打包器的是未签 HAP | 先 `sign-app` 签 HAP，再打包 |
| `No Hap Signing Block`（对包内 HAP） | 正常：签名在 `.app` 层 | 对最终 `.app` 跑 `verify-app` |
| `keyAlias`/`password` 失败 | 口令或别名不对 | 用 `sign/keys.local.json` 的口令；别名 `sansheng-release` |
| `.app` 上传被拒 | 只打包未签 `.app` | 重跑脚本第 4 步 |

## 7. 发布链路当前状态（2026-10-22 12:02 · Qoder 实测）

| 环节 | 状态 | 证据 |
|---|---|---|
| 发布私钥库 | 已生成 | `sign/release/sansheng-release.p12` 1032 B，别名 `sansheng-release`，ECC NIST-P-256；口令只在 `sign/keys.local.json` |
| 发布 CSR | 已生成并上传 AGC | `sign/release/sansheng-release.csr` 444 B，SHA-256 `ce1b16f1…17accab`，subject `C=CN,O=Sansheng,OU=IME,CN=Sansheng IME Release` |
| **发布证书** | **已取得并核验** | `sign/release/sansheng-release.cer` 2910 B，SHA-256 `19cb3cf0…b9e10734`；链内 3 张：Huawei CBG Root CA G2 → Huawei CBG Developer Relations CA G2 → 叶子 `CN=…(2064840864965865793)\,Release`；有效期 **2026-10-22 → 2029-10-22**；叶子公钥 DER SHA-256 `798c7d60…7116d728` **与 CSR 公钥一致**（证明未绑到调试密钥；调试证书叶子结尾是 `,Development`） |
| 发布 Profile `.p7b` | **已取得并核验（2026-10-22 13:07 主人下载）** | `sign/release/sansheng-release.p7b` 4016 B，SHA-256 `922fe91c8e099c8c98acbe3bf66951ffed13401cc8d695a997b1d998ac820679`；`openssl pkcs7 -print_certs` 链为 Huawei CBG Root CA G2 → CBG Software Signing Service CA → HOS Profile Management；内嵌 JSON（`openssl smime -verify -noverify`，临时文件已删）：`type=release`、`bundle-info.bundle-name=com.sansheng.ime`、`app-distribution-type=app_gallery`、`issuer=app_gallery`、`validity 2026-10-22 11:45 → 2029-10-22 11:45`、`apl=normal`、`app-identifier=6917619501579115120`、**无受限 ACL、无设备清单** ⇒ 点单页要求的三件事全对 |
| `.app` 构建 | **已构建并双重校验（2026-10-22 13:25）** | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/release_build.ps1` → `RELEASE OK`；口令从 `sign/keys.local.json` 读入环境变量，**未落盘、未进聊天** |
| 机外备份 | **本机双盘已齐，机外仍缺** | 13:26 新建 `E:\sansheng-sign-backup\20261022-132646\sign\`（13 文件全量：调试四件套 + `release/` 的 `.p12/.cer/.csr/.p7b` + `keys.local.json` + `agconnect-services.json`），附 `MANIFEST.sha256.txt`（只有文件名+长度+SHA-256，不含密钥内容）。**旧份 `20261022-092803` 的 `sign/release/` 是空目录 ⇒ 发布私钥此前从未进过任何备份**〔更正 (Qoder) 2026-10-30 07:2x：这句两处都不对，`ls -laR` 实测 `20261022-092803\sign\release\` **不是空目录**，里面有 4 件（`README.local.md` 743 B／`release-csr.info.txt` 258 B／`sansheng-release.csr` 444 B／**`sansheng-release.p12` 1,032 B，mtime 10-22 04:36**）⇒ 发布私钥**从 09:28 那一次起就一直在备份里**，两份同机副本都算；那份真正缺的是 12:00／13:07 才到的 `.cer` 与 `.p7b`（`python scripts\verify_sign_backup_match.py "E:\sansheng-sign-backup\20261022-092803\sign"` 实测这两件 NOT-BACKED-UP、exit 1）。结论不变、说法要准：**私钥有两份同机副本，一份完整一份缺证书，机外一份都没有**〕。**E: 与 F: 只是同机两块盘，不算机外**：主人需把 `20261022-132646` 整份拷到 U 盘/网盘各一处 |

坑（本轮实测）：

1. 机器上有**两个** `sign/`：`F:\qoderwork\sansheng-ime-harmony\sign\`（有 `release/`）与 `F:\codeartswork\sansheng-ime-harmony\sign\`（**只有调试四件套，无发布私钥**）。主人 11:58 误从后者选了 `sansheng.csr`（调试 CSR）。**发布私钥不得由 agent 跨工作区搬运**，只由主人复制。
2. AGC 的证书/Profile 页在 iframe 里，`take_snapshot`/`upload_file` 都取不到内部元素；从 iframe 上下文 `fetch('http://127.0.0.1:…')` 被拦（`TypeError: Failed to fetch`，CSP/mixed-content 未定位）。**结论：CSR 上传只能由主人在浏览器里手点**，agent 只提供文件路径。相关临时服务与目录已清理。
3. `openssl pkcs12 -info` 会把加密包内容打到 stdout——**不要带 `-info` 跑**，只用 `-nokeys -pubkey`。

## 8. 发布产物（2026-10-22 13:25 首次跑通，`type=release` 全链路）

```
entry/build/default/outputs/default/
  entry-default-release-signed.hap        27,822,532 B
    sha256 64dfcc2e42fde792f5f5bc22032550751581e2998cc8d3712182d95d713ebd5c
  sansheng-ime-1.0.0-release.app          11,791,326 B
    sha256 8dad9f3f9402969043e54ea5921c0d3d6d0c5e18ff1560ec6d5020c3fb5b6ef1
    （同名 .sha256 侧车文件已随产物生成）
  ../release-verify/                       证书链与内嵌 Profile 解出件
```

> **%s 现状**：上面这两个件已不在盘上——%s。留档哈希只能证明「2026-10-22 曾出过并通过校验」，不再是实物。重建后的新件会同时归档到 `F:\qoderwork\sansheng-release-artifacts\accepted-<时间戳>`（在 `entry/build` 之外，clean 打不到）。

- 构建模式：`build.ps1 -Product default -BuildMode release`（比调试包小：28,061,414 → 27,822,532 B）。
- 校验：`verify-profile` 通过（脚本内建，且 `type != release` 会直接抛错）；`verify-app` 对 HAP 与 `.app` **各跑一次**，均 `verify: Verify success`；`.app` 内确认含 `entry-default.hap` + `pack.info`。
- 复现命令（口令从 `sign/keys.local.json` 读进环境变量，不落盘、不回显）：

```
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { $j = Get-Content -Raw 'sign/keys.local.json' -Encoding UTF8 | ConvertFrom-Json; $env:SS_RELEASE_KEY_PWD = $j.keyPwd; $env:SS_RELEASE_STORE_PWD = $j.keystorePwd; & scripts/release_build.ps1 }"
```

**注意**：`release_build.ps1` 在口令缺失时会 `Read-Host` 静默等待，agent 侧表现为"卡住无输出"。要么按上面注入环境变量，要么主人自己在终端里输。**agent 不得索要也不得记录口令明文。**

- **这个 `.app` 现在还不能提审**：它打的是当前工作区代码（含 CodeArts 未提交的 `KeyboardIndex.ets` 等），且 M6 的 ③④⑤（隐私表单、备案/软著、商店素材）未收口。**用途 = 证明签名链路可用 + 留一份可复现的哈希基线**。真正提审前要在干净 commit 上重打一次并更新本表。
- 发布签名的 HAP **不要 `hdc install`**（发布 Profile 不绑本机设备，装上也起不来）；真机验证一律用调试签名包。
