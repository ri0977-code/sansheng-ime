"""
把 Mate 80 原始截图（1280×2832）裁成商店用的竖向图（默认 720×1280，9:16）。

用法：
    python scripts/make_store_shots.py <raw_dir> [--out docs/release/store/screenshots] [--size 720x1280]

规则（与 docs/release/store/listing.md §5 一致）：
  - 默认输出 720×1280 PNG，竖向 9:16；`--size WxH` 可换目标尺寸（如 AGC 现场若要 1080×1920），
    裁切比例自动跟着 `--size` 走，原始 1280×2832 截图不动，随时重出；
  - 先按目标比例从原图里取最大内接区域（居中），再 LANCZOS 缩放到目标尺寸；
  - 不叠加文字、不加水印、不裁掉键盘主体（取景框居中，若主体偏下用 --bias 调整）。

每张图输出后会打印：源尺寸、裁切框、输出尺寸、字节数、sha256 前 12 位。
"""
import argparse
import hashlib
import os
import re
import sys

from PIL import Image

OUT_W, OUT_H = 720, 1280
TARGET_RATIO = OUT_W / OUT_H          # 0.5625


def crop_box(w, h, bias=0.5, ratio=TARGET_RATIO):
    """按目标比例取最大内接矩形；bias=0 贴顶、1 贴底。"""
    if w / h > ratio:                 # 太宽：裁左右
        cw = int(round(h * ratio))
        ch = h
        x0 = (w - cw) // 2
        y0 = 0
    else:                             # 太高：裁上下
        cw = w
        ch = int(round(w / ratio))
        x0 = 0
        y0 = int(round((h - ch) * bias))
    return (x0, y0, x0 + cw, y0 + ch)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw_dir")
    ap.add_argument("--out", default="docs/release/store/screenshots")
    ap.add_argument("--size", default="%dx%d" % (OUT_W, OUT_H),
                    help="目标尺寸 WxH，默认 720x1280；裁切比例随之改变")
    ap.add_argument("--bias", type=float, default=0.5,
                    help="0=贴顶, 1=贴底；键盘主体偏下时调大")
    ap.add_argument("--map", default="",
                    help="可选：raw 文件名里的编号到输出名的映射，如 01:01-pinyin-26。"
                         "编号按「独立数字块」匹配，所以 m6-store-raw-01-xxx.png 也能被 01 命中")
    args = ap.parse_args()

    try:
        out_w, out_h = (int(v) for v in args.size.lower().split("x"))
    except ValueError:
        print("--size 要写成 WxH（如 720x1280），收到:", args.size)
        return 2
    if out_w <= 0 or out_h <= 0:
        print("--size 必须是正整数:", args.size)
        return 2
    ratio = out_w / out_h

    mapping = {}
    for pair in filter(None, args.map.split(",")):
        k, v = pair.split(":")
        mapping[k] = v

    def map_hit(key, fname):
        """编号命中：前缀（01-xxx.png）或文件名里独立的数字块（m6-store-raw-01-xxx.png）。"""
        return fname.startswith(key) or bool(re.search(r"(?<!\d)%s(?!\d)" % re.escape(key), fname))

    os.makedirs(args.out, exist_ok=True)
    files = sorted(f for f in os.listdir(args.raw_dir)
                   if f.lower().endswith((".png", ".jpg", ".jpeg")))
    if not files:
        print("no images in", args.raw_dir)
        return 1

    hits = {}
    for f in files:
        src = os.path.join(args.raw_dir, f)
        im = Image.open(src).convert("RGB")
        w, h = im.size
        box = crop_box(w, h, args.bias, ratio)
        out = im.crop(box).resize((out_w, out_h), Image.LANCZOS)

        # 输出名：优先用 --map 编号，否则沿用原名
        name = f
        matched = [k for k in mapping if map_hit(k, f)]
        if len(matched) > 1:
            print("!! %s 同时命中多个 --map 编号 %s，按 %s 处理"
                  % (f, matched, sorted(matched)[0]))
        if matched:
            name = mapping[sorted(matched)[0]] + ".png"
            hits[sorted(matched)[0]] = hits.get(sorted(matched)[0], 0) + 1
        dst = os.path.join(args.out, name)
        out.save(dst, "PNG", optimize=True)
        data = open(dst, "rb").read()
        print("%-34s %dx%d -> crop%s -> %dx%d  %7d B  sha %s"
              % (f, w, h, box, out_w, out_h, len(data),
                 hashlib.sha256(data).hexdigest()[:12]))

    missed = [k for k in mapping if k not in hits]
    if missed:
        print("!! --map 里这些编号在 %s 没有任何文件命中: %s" % (args.raw_dir, ",".join(missed)))
        print("   （说明映射写错了或原始图换了名字——别把没生成的成品当已生成）")

    print("\n输出目录:", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
