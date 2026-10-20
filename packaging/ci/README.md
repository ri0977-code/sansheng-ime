# CI 构建（GitHub Actions）

这个目录让安装包可以在 GitHub 的公开 Runner 上重新构建，不再依赖开发机上的
`D:\Program Files\Rime`。构建产物用于代码签名（SignPath）和问题回溯。

## 组成

| 文件 | 作用 |
|------|------|
| `build_installer.py` | 组装 `release/` 并调用 `makensis`，不读取本机 Rime 目录 |
| `.github/workflows/build-installer.yml` | windows-latest 上的构建流程 |

## 构建输入从哪来

1. **官方 Weasel 0.17.4 安装包**（rime/weasel 的 GitHub Release，SHA256 固定）。
   CI 用 7z 取出 x64 那一份。
2. **公开的 build-inputs 压缩包**，逐字节来自 v1.9.10 实际发布的
   `packaging/release/`：
   - `config/`：装到 Rime 用户目录的 129 个配置文件；
   - `engine-overlay/`：相对官方 x64 引擎只替换了 4 个文件
     （`WeaselServer.exe`、`weasel.ime`、`weaselx64.ime`、`data/default.yaml`）；
   - `reg/`：4 个注册表片段；
   - `MANIFEST.sha256`：包内每个文件的 SHA256，构建前逐个校验。

   下载地址和 SHA256 写在工作流的 `env:` 里。

## 本地跑一遍

```bat
python packaging\ci\build_installer.py ^
  --inputs <解压后的 build-inputs 目录> ^
  --weasel-installer <weasel-0.17.4.0-installer.exe> ^
  --work _work --out dist
```

需要 7-Zip 与 NSIS（`makensis`）。脚本会输出
`dist/sansheng-ime-v<版本>-setup.exe` 和 `SHA256SUMS.txt`。

## 已验证到什么程度

2026-10-20 用本目录的脚本重建 v1.9.10：

- 组装出的 `config/`（129 个文件）与 `weasel-0.17.4/`（107 个文件）
  和实际发布的 `packaging/release/` **逐字节一致**；
- 重建出的 setup.exe 与已发布的 v1.9.10 安装包相比，解包后的
  **282 个内嵌文件全部一致**；
- 两个 setup.exe 的 SHA256 不同，这是 NSIS 的正常现象（时间戳/压缩），
  不是内容差异。

## 签名

SignPath Foundation 通过后，在 “Upload installer” 之前加签名步骤即可。
届时公开的 Actions 日志就是签名所需的构建来源证明。
