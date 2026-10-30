# 00:17 包内分层图标复核：构建降采样到 512，图形一致（「包内逐字节同 md5」的说法不成立）

**对象**：`entry/build/default/outputs/default/entry-default-unsigned.hap`（00:09 clean 构建，28,178,736 B）
**目的**：核实 H-097「包内图标已换成蓝底三条键帽、与 AGC 上传图标同图」到包级，而不是只看源文件。

## 1. 包内条目

| 条目 | 字节 | 尺寸/模式 | md5 |
|---|---|---|---|
| `resources/base/media/background.png` | 6,034 | 512×512 RGBA | `f57d73ab773accb45903de976a5e88fb` |
| `resources/base/media/foreground.png` | 8,884 | 512×512 RGBA | `4780e60287755e60a54c677de552d835` |
| `resources/base/media/layered_image.json` | 81 | — | — |

## 2. 源文件 / 商店母版

| 文件 | 尺寸/模式 | md5 |
|---|---|---|
| `AppScope/resources/base/media/background.png` | 1024×1024 RGB | `2bc823deb4b17b5a87db090bc58aadfc` |
| `AppScope/resources/base/media/foreground.png` | 1024×1024 RGBA | `d14de5e5b332de9a334c8f7f46fa0723` |
| `docs/release/store/icon/layered/background-1024.png` | 1024×1024 | `2bc823deb4b17b5a87db090bc58aadfc` |
| `docs/release/store/icon/layered/foreground-1024.png` | 1024×1024 | `d14de5e5b332de9a334c8f7f46fa0723` |

⇒ **源文件与商店母版逐字节相同**；但**包内不是 1024 原图**，hvigor 打包时降采样成 512，md5 必然不同。此前文档写成「包内与母版逐字节同 md5」是把源文件层与包层混为一谈，已更正。

## 3. 像素比对（证明是同一图形，不是换了图）

把 1024 母版 Lanczos 缩到 512 后与包内图逐通道求差（0–255）：

| 通道 | background 平均差 | foreground 平均差 |
|---|---|---|
| R | 0.13 | 2.09 |
| G | 0.36 | 2.09 |
| B | 0.75 | 2.09 |
| A | 1.00 | 0.31 |

- 前景少数边缘像素 max 255，是 1024→512 重采样 + 抗锯齿的边界差异，不是图形差异。
- 包内 background 的 alpha 恒为 254（源为不透明 RGB）；0.4% 透明，视觉不可辨，属构建转 RGBA 的产物。
- 结论：**蓝底三条键帽，同一图形**；AGC 侧 216×216 上传图由同一母版合成，视觉比对应能过。
- 并排对比图（左=包内 512，右=母版缩放）：`0017-background-leftpkg-rightmaster.png`、`0017-foreground-leftpkg-rightmaster.png`。

## 4. 边界与后续

- 真机桌面可见性仍未拍定（H-108/第 ⑯ 项），本条只证明包内素材正确。
- 发布 `.app` 重出后（代码冻结）再抽一次包内 512 图，防止降采样策略变化。
- 复现命令：

```bash
unzip -o -j entry/build/default/outputs/default/entry-default-unsigned.hap \
  resources/base/media/background.png resources/base/media/foreground.png -d _tmp_iconcheck
md5sum _tmp_iconcheck/*.png
python - <<'PY'
from PIL import Image, ImageChops, ImageStat
for n, src in [('background','AppScope/resources/base/media/background.png'),
               ('foreground','AppScope/resources/base/media/foreground.png')]:
    pkg = Image.open(f'_tmp_iconcheck/{n}.png').convert('RGBA')
    ref = Image.open(src).convert('RGBA').resize(pkg.size, Image.LANCZOS)
    for ch in 'RGBA':
        d = ImageChops.difference(pkg.getchannel(ch), ref.getchannel(ch))
        print(n, ch, round(ImageStat.Stat(d).mean[0], 2), ImageStat.Stat(d).extrema[0][1])
PY
```
