# 代码签名政策 / Code Signing Policy

更新日期：2026-10-20

三生输入法（Sansheng IME）的 Windows 安装包可由本仓库公开源码在 GitHub Actions 上复现构建。本项目计划通过 [SignPath Foundation](https://signpath.org/) 提供的免费开源代码签名证书签名，签名版本将直接取自该工作流的构建产物。

## 签名范围 / Scope

只有发布在 GitHub Releases 的 Windows 安装包会被签名：

```text
sansheng-ime-v<版本号>-setup.exe
```

`SHA256SUMS.txt`、源码压缩包及其它辅助文件不单独签名。

## 构建流程 / Build process

签名版本不包含手工放入的二进制产物，全部由 CI 从固定版本的输入构建：

| 输入 | 来源 | 校验 |
|------|------|------|
| 安装器源码 | 本仓库 `packaging/installer-src/` | 随提交固定 |
| 构建脚本 | 本仓库 `packaging/ci/build_installer.py` | 随提交固定 |
| 配置与引擎覆盖层 | Releases 资产 `sansheng-build-inputs-v*.7z` | 工作流内 SHA-256 校验 |
| 上游引擎 | [rime/weasel 0.17.4 官方安装包](https://github.com/rime/weasel/releases/tag/0.17.4) | 工作流内 SHA-256 校验 |

- 构建工作流：<https://github.com/ri0977-code/sansheng-ime/blob/master/.github/workflows/build-installer.yml>
- 工作流会逐个校验构建输入的 SHA-256，检查配置与引擎文件完整性，并由构建脚本校验 TIP 参数、版本号与关键文件，任一不符即拒绝出包。
- 构建产物作为 GitHub Actions artifact 保存，任何人可复跑工作流核对。

## 签名流程 / Signing process

1. 维护者从通过校验的 CI 构建中取安装包。
2. 通过 SignPath.io 提交签名请求，使用 SignPath Foundation 签发的证书做 Authenticode 签名与时间戳。
3. 只有维护者可以批准发布与签名请求；合并后的源码才会进入签名构建。
4. 签名后的安装包与 `SHA256SUMS.txt` 一起发布，Release 说明中给出构建运行链接与 SHA-256。

## 团队与职责 / Team and roles

| 角色 | 人员 | 职责 |
|------|------|------|
| 维护者 / Maintainer | 小台（GitHub [@ri0977-code](https://github.com/ri0977-code)） | 需求取舍、代码审核、发布与签名批准 |
| 贡献者 / Contributors | 社区贡献者与 AI 编程代理 | 提交代码、词库与测试；无发布或签名权限 |

所有改动经维护者审核后合入；AI 编程代理不持有签名权限，也不能批准签名请求。

## 验证 / Verification

```powershell
Get-AuthenticodeSignature .\sansheng-ime-vX.Y.Z-setup.exe
```

签名者为 **SignPath Foundation**。也可右键安装包 → 属性 → 数字签名查看。若签名无效或签名者不符，请不要安装，并通过 GitHub Issues 告知我们。

> 截至 2026-10-20，SignPath Foundation 申请仍在进行中，当前发布的 v1.9.10 尚未签名；获批后的版本会按上述流程签名。

## 归属 / Attribution

Free code signing provided by [SignPath.io](https://signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

代码签名政策遵循 [SignPath Foundation 开源项目条款](https://signpath.org/terms.html)。
