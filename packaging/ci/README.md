# CI 构建（GitHub Actions）

这个目录让安装包可以在 GitHub 的公开 Runner 上重新构建，不再依赖开发机上的
`D:\Program Files\Rime`。构建产物用于代码签名（SignPath）和问题回溯。

## 组成

| 文件 | 作用 |
|------|------|
| `build_installer.py` | 组装 `release/` 并调用 `makensis`，不读取本机 Rime 目录 |
| `check_v110.py` | 出包前的静态硬校验（词条与种子表逐条对齐 / 滤镜挂载位置 / 开关默认值 / 包里不许出现本机绝对路径 / 两棵出包树逐字节一致），v1.10.1 时 45 项 |
| `make_build_inputs.py` | 从 `packaging/release/` 组装下一版要上传的 build-inputs 7z（见下面「抬版本号时怎么重发」） |
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

## 抬版本号时怎么重发 build-inputs

`packaging/release/` 是 gitignore 的，仓库里的 `rime-config/` 只是它的镜像（CI 的 C3 门比对这个镜像）。
所以**改了 Lua 或配置、光 push 代码，CI 是拿不到的** —— 它的 `config/` 来自那只公开 7z。
v1.10.1 就差点栽在这：安装包换好了，工作流还指着 `build-inputs-v1.9.10`，
那样 CI 会出一个「版本号 1.10.1、配置 1.9.10」的假包（`build_installer.py` 的 1b 号硬门会拦）。

```bat
:: 1) 先正常出包（prepare_release.py 会重建 packaging/release）
python packaging\prepare_release.py

:: 2) 组装新的构建输入包，脚本会打印 SHA256 和要粘进工作流的三行
python packaging\ci\make_build_inputs.py --version 1.10.1

:: 3) 把产物 packaging\dist\sansheng-build-inputs-v1.10.1.7z 传到
::    tag 为 build-inputs-v1.10.1 的 Release（这个 Release 绝不能设成 Latest，
::    否则「检查更新」会把 9 MB 构建输入当成输入法）

:: 4) 上传成功、下载链接能通之后，再改工作流 env 三行并 push：
::    INPUTS_URL / INPUTS_SHA256 / EXPECTED_VERSION
```

v1.10.1 那只（2026-10-21 21:1x 重出，含 dic_4w_Filter 三义项截断）：9,824,406 B，
SHA256 `08eee8ddbabdf4094cf996c2155b72e298d5894304bb216ebec7b1062574111b`，
`config/` 119 个文件（比 1.9.10 的 129 少 14 个下架的 `wnwb_*`、多 4 个本版新层与新表），
`engine-overlay/` 与 `reg/` 和 1.9.10 逐字节相同。组装结果已用 CI 自己的
`build_installer.verify_manifest()` 本地核对过（128 个文件全通过）。

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
