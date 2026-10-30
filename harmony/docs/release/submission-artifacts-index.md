# 提审产物索引（提审当天照着拿 · 2026-10-23 14:3x · Qoder）

> **用途**：AGC 提审那一步，**每一个要上传的文件只从这里拿**。历史上出过「推荐错文件」的事故（listing §7 曾同时推荐 `gen-appicon-216.png` 与 `preview-216.png`，02:1x 才发现两张不同图）。
> **状态是 2026-10-23 14:3x 实测、2026-10-24 00:33 复核过的**；每行都写了 sha256 前 12 位和字节数，拿之前对一眼。

---

## 一、AGC 要上传的（4 件）

| # | 文件 | 规格 | 状态 | 说明 |
|---|---|---|---|---|
| 1 | `docs/release/store/icon/layered/preview-216.png` | 216×216 PNG，**1,374 B**，sha `dff8ef2997b6` | ✅ **可传** | AGC 上架图标唯一指定件。14:34 按 nova6 黑底金含环重出。**不要用 `icon/appicon-216.png`**（旧包四宫格模板） |
| 2 | `docs/release/store/screenshots/01…05-*.png` | 720×1280 PNG 5 张 | ❌ **不能传** | **现为 10-22 08:45 拍的旧界面**（H-085）。必须用最终包重拍，裁切用 `scripts/make_store_shots.py`，步骤见 `screenshot-reshoot-script.md` |
| 3 | 隐私政策 / 用户协议 / 第三方许可声明 | 托管或自定义 URL | ⏳ | 三件在 `docs/release/legal/`，与应用内**逐字节同源**（00:33 实测：`notice.html` 77,255 B / sha `4d5196c35915`、`privacy.html` 8,862 B / `cda802017ce1`、`terms.html` 7,712 B / `45fb95255180`；旧写 notice `1a7d955b…` 是 00:1x 改 NOTICE 前的）。走 AGC 托管则不用上传文件，点「托管」即可 |
| 4 | `.app` 提审包 | `sansheng-ime-1.0.0-release.app` **18,249,521 B**／sha256 `0d3b3a4ac70a`（全串 `0d3b3a4ac70a79925bb8ccd65fb800239998ffaceae47af273e99df615f3ae9e`） | ✅ **已生成，闸门 18/18、阻断 0**（2026-10-30 07:10:35） | **树外永久副本（提审当天就从这里拿）**：`F:\qoderwork\sansheng-release-artifacts\accepted-20261030-071035\`（含 `.sha256` sidecar 与 `content-gate.txt` 原始输出）；仓库内同名件在 `entry/build/...`，一次 `hvigor clean` 就没了（H-144）。**〔2026-10-30 07:1x 更正 (Qoder)：旧写法「要主人在场输密钥密码」作废〕** 实测依据：`sign/release/README.local.md:8` 写明发布私钥库口令**与调试密钥库相同**，而调试口令就在 `sign/keys.local.json`（gitignored，`/sign/` 见 `.gitignore:19`）⇒ `release_build.ps1` 的 env 分支能自取，不需要交互输入。**这同时意味着发布私钥＋口令＋.cer/.p7b 全在这块盘上** ⇒ README:10 那条「证书/Profile 到位后整个 `sign/` 拷一份机外」仍是**未办的事**，私钥丢失无法补发、已上架应用将无法更新（新开 H-281）。 |

---

## 二、软著要交的（3 件）

| # | 文件 | 规格 | 状态 |
|---|---|---|---|
| 1 | `docs/release/copyright/pdf/source-code.pdf` | 60 页，**1,236,139 B**，sha `bb8cb728e564` | ✅ 已按 **6,063 行**重打（14:0x）。**提交当天必须再跑 `build_copyright_source.py --check`**，漂了照新数填申请表 |
| 2 | `docs/release/copyright/pdf/operation-manual.pdf` | 20 页，1,592,670 B，sha `0b5bf717fe2a` | ✅ **已达建议值**：官方底线 10 页、建议 ≥20 页，本版 20 页；补写任务单 `manual-expansion-tasklist.md` 已执行（四段式扩写）。仍待最终包到位后补 **3** 张新截图（26 键主键盘／五笔 wqvb／反查注释行；00:22 实点 `<!-- FIG -->` 占位＝3 处，旧写 4 是笔误）。**重打时同步键面称呼**：若当日代码里 H-154 P2-1 已落地（空格键面「三生」），`operation-manual.md` 的 `:90/:97/:127` 三处一并改；与源程序 PDF 同一次生成（见 `copyright/README.md` §六/§七.5） |
| 3 | 申请表 | 在线填 | ✅ 逐格照抄 `docs/release/copyright/application-draft.md` |
| 4 | **版权证书**（AGC 上传件） | JPG/PNG/BMP，≤10 张、每张 ≤15 MB | ⏳ **三选一**：软著登记证书／APP 电子版权认证证书／软件著作权认证证书。**先办电子版权（约 2 周）**，见 `owner-submission-steps.md` §四（D-024） |

---

## 三、明确**不要**传的（历史事故源）

| 文件 | 为什么不能传 |
|---|---|
| `docs/release/store/icon/appicon-216.png`／`-512.png`／`-1024.png` | **旧包四宫格模板**合成图，不是当前品牌 |
| `docs/release/store/icon/gen-appicon-*.png` | 14:34 起已与 `preview-216` 同图（216 逐字节相同，512/1024 为放大版；512 fill 0.781 不达包内 W-209）。为避免两个来源，**AGC 上传只认 `layered/preview-216.png`** |
| `docs/release/store/icon/candidates/cand-*.png` | **带「Qoder AI生成」水印**，不能上架 |
| `entry/build/**/outputs/**/entry-default-unsigned.hap` | **未签名**，不能装也不能提审 |
| `entry/build/**/outputs/**/entry-default-signed.hap` | debug 签名，**只用于 Mate 80 自测**，不是提审件。**〔2026-10-30 07:1x 实况 (Qoder)〕** 07:10 那次 `release_build.ps1` 重跑了 release 构建 ⇒ 树里这个文件名**已不存在**，现在树里是 `entry-default-unsigned.hap`（release 模式 44,249,132 B）＋ `entry-default-release-signed.hap`（44,365,525 B，**不能 hdc 装**）。主人要装的那一份（自造词＋单手）在**树外只读归档**：`F:\qoderwork\sansheng-release-artifacts\2026-10-30\070923\entry-default-signed.hap` 45,003,213 B／md5 `b9142560c26f8dda66526b1691fbb3c8`／sha256 `88bc7ecdbac05d73…`——装机命令直接指它：`powershell -File scripts\install.ps1 -Hap "F:\qoderwork\sansheng-release-artifacts\2026-10-30\070923\entry-default-signed.hap"`（`install.ps1` 支持 `-Hap`，已核 `scripts/install.ps1:2/12`）。**别重跑 `sign.ps1` 去找它**：那会拿 release 模式的 unsigned 包签出一份**不同的** debug 签名件，把「装机候选」换成没按字节审过的那一份。 |

| 2026-10-22 13:25 那份旧 `.app` | 已被 `hvigor clean` 删掉，且本来就不能提审（H-144） |

---

## 四、提审前的四道自动闸门（全绿才许传）

```bash
python scripts/check_closure_items.py --strict   # ① 收口六件（CodeArts）
python scripts/check_icon_ring.py --fail-on-stale   # ② 包内图标达 W-209（gold 0.20~0.40／fill≥0.97／环≥0.018），不达标退出码 1
python scripts/check_rime_yaml.py               # ③ Rime 数据合法＋反斜杠
python scripts/check_app_content.py <.app 路径>  # ④ 16 项内容闸门，须 16/16
```

外加两条人工项：软著 `build_copyright_source.py --check` 通过；`check_copyright_manual.py --pdf` 全项通过（20 页）。**两份 PDF 必须同一次生成**：源程序与会随代码漂移；说明书里空格键面称呼在 H-154 P2-1 落地后要同步 3 处（见 `copyright/README.md` §六），不许旧 PDF 配新代码（§七.5）。

---

## 五、归档（H-144）

产物一旦生成，立刻跑：

```bash
python scripts/archive_release_artifacts.py --write
```

归档根 `F:/qoderwork/sansheng-release-artifacts/<日期>/<时刻>/`（**构建树之外**，`clean` 删不到），带 `MANIFEST.json`（sha256＋字节数＋git HEAD）。
**异地备份（U 盘/另一台机）仍要主人做** —— 脚本只防 clean。
