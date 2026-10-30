# 分层应用图标交付（H-097）· 2026-10-22 18:3x · Qoder

> **2026-10-24 00:28 作废提示（重要）**：本文件描述的是 H-097 时期的「蓝底三条键帽」。品牌已按 **D-022** 改为**黑底金含外环**，包内两层现在是 `background.png`＝纯黑、`foreground.png`＝金环（W-209，H-147 CLOSED）。同目录 `background-1024.png`／`foreground-1024.png` 在本机 14:34 已被黑底金单张整图覆盖（两者 md5 相同），**不能再按 §三 覆盖进包**；AGC 上传件用 `preview-216.png`（黑底金含环，md5 `dff8ef29…`）。以下蓝底几何与替换步骤仅作历史记录。

**用途**：替换包内 `AppScope/resources/base/media/` 的两层，使**包内图标 = 商店上传图标**，解除 AGC「申报与实际不一致」驳回风险。

## 一、文件

| 文件 | 尺寸 | 用途 |
|---|---|---|
| `docs/release/store/icon/layered/background-1024.png` | 1024×1024 RGB | 替换 `AppScope/resources/base/media/background.png` |
| `docs/release/store/icon/layered/foreground-1024.png` | 1024×1024 RGBA（其余透明） | 替换 `AppScope/resources/base/media/foreground.png` |
| `preview-square-1024.png` | 1024×1024 | 两层合成的方图（供核对，不进包） |
| `preview-launcher-1024.png` | 1024×1024 | **按桌面圆角遮罩裁过的预览**（证明四角不裁键帽） |
| `preview-216.png` | 216×216 | 与 AGC 上传图标同尺寸，可直接比对 |

生成脚本：`scripts/make_layered_icon.py`（纯 Pillow、无第三方素材、可复跑）。

## 二、几何不是估的，是从已批准的商店图标里量出来的

脚本里写死了母版实测值，并在生成后**自检断言**：

| 键帽 | y 范围 | x 范围 |
|---|---|---|
| 第 1 条 | 246–350（高 105） | 212–812（宽 601） |
| 第 2 条 | 468–572（高 105） | 188–836（宽 649，比另两条宽，母版如此） |
| 第 3 条 | 690–794（高 105） | 212–812 |
| 高亮段 | 716–768（高 53） | 688–786（宽 99） | 

底色：竖向渐变 `#1E4FBF` → `#2A6FDC`（取自母版上下边缘实测像素）。
键帽：纯白 `#FFFFFF`；高亮：`#7AB0F5`。
脚本输出 `GEOMETRY MATCH: True` 才写盘 —— 与 `gen-appicon-1024.png` 的三条键帽范围相同。
**注意数法（2026-10-23 02:1x 复核后改准）**：这句话**只指三条键帽的包围盒**，实测在 1024 上逐条一致
（(246,350,212,812)／(468,572,188,836)／(690,794,212,812)）；**整图不是逐像素相同** ——
两层合成与 `gen-appicon-1024.png` 直接比，仍有 26.9% 的像素差 >8/255（最大 66），差在背景渐变插值与抗锯齿。
⇒ 别拿整图 md5 当回归判据（会误报成 bug），要比就比键帽包围盒。
证据：`docs/evidence/2026-10-23/store-copy-intro-audit-0214.md` §四。

## 三、替换方式（两条路，选一条）

**路线 1（推荐，保持分层图标）**：直接覆盖两个同名文件，`layered_image.json` 不用动。
- `background.png` ← `background-1024.png`
- `foreground.png` ← `foreground-1024.png`
- 注意：分层图标的 **foreground 会被系统按掩码裁切**，本套内容已全部落在安全区内（见 `preview-launcher-1024.png`），不要再放大。

**路线 2（改单层）**：`AppScope/app.json5` 的 `"icon": "$media:layered_image"` 改成 `"$media:app_icon"`，
并把 `preview-square-1024.png` 缩放成 216/512/1024 三个尺寸放进 `media/`。**不推荐**，因为失去系统主题下的自适应效果。

## 四、验收（我这边做，不是你看）

1. 解包新包，取 `background.png` + `foreground.png` 用 Pillow 合成；
2. 与 `preview-square-1024.png` 逐像素比对（预期零差异）；
3. 与 `gen-appicon-1024.png` 比三条键帽的 y/x 范围（预期各差 ≤2 px）；
4. 真机桌面/应用列表截图，确认不是四宫格。

## 五、与其它单子的关系

- **H-096 布局重做**仍是主优先级；本项**与布局同批出包**，不要单独出一版。
- `AppScope/app.json5` 的 `versionCode=1000000` / `versionName=1.0.0` **不要动**（改版本号要同步 AGC）。
- 打包后把 `entry-default-unsigned.hap` 的产物全名 + `stat -c %s` 字节数报给我，我按第四节验收。
