#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""三生输入法 · 应用图标生成器（Qoder 归属，M6 ⑤）

为什么自己画而不用 AI 出图：ImageGen 产物右下角带「Qoder AI生成」水印，
上架图标不能带水印，去掉别人水印也不是我们该做的事。本脚本用纯几何绘制，
产物归本项目所有，可随 Apache-2.0 分发。

设计：蓝色渐变底 + 三条白色圆角「键帽」横条（读作「三」，也读作键盘的一排排键），
最下一条右端留一段蓝色高亮（呼应输入法里被选中的那个键）。

用法：
  python scripts/make_icon.py                     # 输出到 docs/release/store/icon/
  python scripts/make_icon.py --out-dir some/dir
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFilter

SIZE = 1024
TOP = (30, 79, 191)      # #1E4FBF
BOTTOM = (47, 123, 232)  # #2F7BE8
KEY_WHITE = (255, 255, 255)
ACCENT = (122, 176, 245)  # 高亮段的浅蓝


def gradient(size=SIZE):
    im = Image.new('RGB', (size, size), TOP)
    px = im.load()
    for y in range(size):
        t = y / float(size - 1)
        r = int(TOP[0] + (BOTTOM[0] - TOP[0]) * t)
        g = int(TOP[1] + (BOTTOM[1] - TOP[1]) * t)
        b = int(TOP[2] + (BOTTOM[2] - TOP[2]) * t)
        for x in range(size):
            px[x, y] = (r, g, b)
    return im


def bars():
    """返回 [(x0,y0,x1,y1,radius, kind)]，kind: white / accent。"""
    cx = SIZE / 2.0
    h = 104.0
    gap = 118.0
    widths = [600.0, 648.0, 600.0]
    total = 3 * h + 2 * gap
    y0 = (SIZE - total) / 2.0 + 8
    out = []
    for i, w in enumerate(widths):
        y = y0 + i * (h + gap)
        out.append((cx - w / 2.0, y, cx + w / 2.0, y + h, h / 2.0, 'white'))
    return out


def draw_icon(size=SIZE):
    img = gradient(size).convert('RGBA')
    scale = size / float(SIZE)
    # 阴影层
    shadow = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for (x0, y0, x1, y1, r, _kind) in bars():
        box = [x0 * scale + 6 * scale, y0 * scale + 14 * scale,
               x1 * scale + 6 * scale, y1 * scale + 14 * scale]
        sd.rounded_rectangle(box, radius=r * scale, fill=(10, 26, 60, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10 * scale))
    img = Image.alpha_composite(img, shadow)

    d = ImageDraw.Draw(img)
    for (x0, y0, x1, y1, r, kind) in bars():
        box = [x0 * scale, y0 * scale, x1 * scale, y1 * scale]
        d.rounded_rectangle(box, radius=r * scale, fill=KEY_WHITE + (255,))
    # 最下一条右端的蓝色高亮段（画成一个小圆角块，压在白条上）
    x0, y0, x1, y1, r, _ = bars()[-1]
    seg_w = 150.0
    inset = 26.0
    box = [(x1 - seg_w) * scale + inset * scale, y0 * scale + inset * scale,
           (x1 - inset) * scale, y1 * scale - inset * scale]
    d.rounded_rectangle(box, radius=((y1 - y0) / 2.0 - inset) * scale,
                        fill=ACCENT + (255,))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', default='docs/release/store/icon')
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    big = draw_icon(SIZE)
    for s, name in [(1024, 'gen-appicon-1024'), (512, 'gen-appicon-512'),
                    (216, 'gen-appicon-216'), (192, 'gen-preview-192')]:
        im = big if s == 1024 else big.resize((s, s), Image.LANCZOS)
        p = os.path.join(args.out_dir, name + '.png')
        im.convert('RGB').save(p, optimize=True)
        print('%s  %dx%d  %d B' % (p, s, s, os.path.getsize(p)))


main()
