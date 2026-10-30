#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""H-147 图标回归量具 —— 包内两层是否「黑底金、含外环、顶四边贴满」。

口径（2026-10-24 00:14 按 W-209 定案，旧 nova6 原版几何作废）
--------------------------------------------------------------
2026-10-23 19:40 CodeArts 按主人要求把图标金环外径放大到顶满画布，主人真机
（dock 行金图标与邻图标同宽 202 px）回「好了」⇒ **通过口径是「顶四边贴满」**：

    gold 覆盖率 ∈ [0.20, 0.40]   环+杠占画面比例（大金环顶满后的实测 0.258 / 0.334）
    内容占比   ≥ 0.97            金像素左右边界几乎等于画布宽（边到边）
    环厚       ≥ 0.018           中心行第一段金的厚度 / 边长（实测 0.0215 / 0.0264）

为什么改：本脚本原来用 nova6 原版 192² 的 fill∈[0.74,0.80]，而主人对上机的最终要求
是「顶四边贴满」。19:40 那版 fill=0.994 在新口径下正确、在旧口径下被判「偏小」，
旧脚本还会打印「要 ×1.25」——照它做会把已经顶满的图继续放大，属**判据方向错误**。
旧基准数字保留在这里只作历史参照，不再参与判定：
    nova6 真源 ic_launcher.png（192²）gold 0.1545｜内容占比 0.771｜环厚 0.0260

判未过时按方向给话：fill 偏小＝顶不到四边；gold 偏少＝缺环/环太细；gold 偏多＝杠或环过粗。
每次交付按 `--fail-on-stale` 跑（退出码 1 = 图标未达口径，`.app` 不许出包）。

用法（只读，不改任何文件）：
  python scripts/check_icon_ring.py                  # 量两张包内图标 + 商店母版（参照）
  python scripts/check_icon_ring.py --fail-on-stale  # 包内两层未达口径就 exit 1
"""
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG_APP_ICON = "entry/src/main/resources/base/media/app_icon.png"
PKG_FOREGROUND = "AppScope/resources/base/media/foreground.png"
STORE_512 = "docs/release/store/icon/gen-appicon-512.png"

# W-209「顶四边贴满」口径
GOLD_LOW, GOLD_HIGH = 0.20, 0.40
FILL_MIN = 0.97
RING_MIN = 0.018


def _open(path):
    p = path if os.path.isabs(path) else os.path.join(ROOT, path.replace("/", os.sep))
    return Image.open(p).convert("RGB")


def gold_ratio(path):
    im = _open(path)
    w, h = im.size
    data = im.getdata()
    c = sum(1 for px in data if px[0] > 150 and px[1] > 120 and px[2] < 140)
    return c / float(w * h)


def fill_and_ring(path):
    """返回 (内容占画面比, 外环厚度/边长)。环厚取中心行第一段金像素长度。"""
    im = _open(path)
    w, h = im.size
    thick = 0
    y = h // 2
    for x in range(w):
        r, g, b = im.getpixel((x, y))
        if r > 140 and g > 100 and b < 140:
            thick += 1
        elif thick:
            break
    xs = []
    for yy in range(0, h, 2):
        for xx in range(0, w, 2):
            r, g, b = im.getpixel((xx, yy))
            if r > 140 and g > 100 and b < 140:
                xs.append(xx)
    fill = ((max(xs) - min(xs)) / float(w)) if xs else 0.0
    return fill, thick / float(w)


def measure(path):
    """按 W-209 口径量一张图，返回 dict（gold/fill/ring/ok/reasons）。"""
    gold = gold_ratio(path)
    fill, ring = fill_and_ring(path)
    reasons = []
    if gold < GOLD_LOW:
        reasons.append(u"gold=%.3f 偏少（缺外环或环太细，口径 ≥%.2f）" % (gold, GOLD_LOW))
    elif gold > GOLD_HIGH:
        reasons.append(u"gold=%.3f 偏多（杠或环过粗，口径 ≤%.2f）" % (gold, GOLD_HIGH))
    if fill < FILL_MIN:
        reasons.append(u"fill=%.3f 顶不到四边（还差 %.1f%% 画布宽，口径 ≥%.2f）"
                       % (fill, (FILL_MIN - fill) * 100, FILL_MIN))
    if ring < RING_MIN:
        reasons.append(u"环厚=%.4f 偏细（口径 ≥%.3f）" % (ring, RING_MIN))
    return {"gold": gold, "fill": fill, "ring": ring,
            "ok": not reasons, "reasons": reasons}


def main(argv):
    fail_on_stale = "--fail-on-stale" in argv
    bad = 0
    for label, path in (("包内 app_icon.png", PKG_APP_ICON),
                        ("包内 foreground.png", PKG_FOREGROUND)):
        try:
            m = measure(path)
        except Exception as e:
            print("  [MISS] %s 读不到（%s）" % (label, e))
            bad += 1
            continue
        print("  %-22s gold=%.4f fill=%.3f ring=%.4f  [%s]"
              % (label, m["gold"], m["fill"], m["ring"], "OK" if m["ok"] else "FAIL"))
        for why in m["reasons"]:
            print("      - %s" % why)
        if not m["ok"]:
            bad += 1
    try:
        m = measure(STORE_512)
        print("  %-22s gold=%.4f fill=%.3f ring=%.4f  [参照，不参与判定]"
              % ("商店母版 512", m["gold"], m["fill"], m["ring"]))
    except Exception as e:
        print("  [MISS] 商店母版 512 读不到（%s）" % e)
    print("口径（W-209 顶四边贴满）：gold ∈ [%.2f, %.2f]｜fill ≥ %.2f｜环厚 ≥ %.3f"
          % (GOLD_LOW, GOLD_HIGH, FILL_MIN, RING_MIN))
    if fail_on_stale:
        print("结论：%s" % ("FAIL，包内图标未达顶四边贴满口径" if bad else "OK，包内两层均达口径"))
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
