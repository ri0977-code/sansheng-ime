#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-279 自造词真机判定——**单步**驱动器（Qoder，2026-10-30 07:5x）

为什么再写一个（`h279_zaozici_device_check.py` 不是已经能跑全套了吗）：
那套是一次性把七步跑完的，中间不给看。但离线 A/B 已经量出「行不行」在修复后的词典里
落在**候选第 6 位**（不是第一位），所以「打 tgtf → 按空格 → 读输入框正文」这条判据根本不成立：
空格上屏的是第一位，正文里没有「行不行」不等于造词失败。**判词必须看着候选列表下**，
而候选列表只有截图里有（H-116：dumpLayout 取不到输入法窗口子节点）。⇒ 每一步之间要停下来看图，
所以需要单步驱动。

同时这里做的键序列也和那套默认值不同：默认 `--codes t g t f` 是逐**字母**上屏，
上屏出来的是 t/g/t/f 各一个候选；主人报的是「打 行(tf) 不(gi) 行(tf)」，
所以逐字上屏要按**字根编码整段**打再空格，即 tf+空格 / gi+空格 / tf+空格。

用法（每条命令做一次动作，然后我读输出/看图）：
    python scripts/h279_ab_drive_qoder.py open            # 起 App
    python scripts/h279_ab_drive_qoder.py focus            # 点「试一试」输入框，弹键盘
    python scripts/h279_ab_drive_qoder.py panel            # 量键位并截图（打印认到的键数）
    python scripts/h279_ab_drive_qoder.py keys t g t f     # 按字母点键（不截图）
    python scripts/h279_ab_drive_qoder.py space            # 点空格＝上屏当前第一位候选
    python scripts/h279_ab_drive_qoder.py shot 12-tag      # 截图并打印输入框正文
    python scripts/h279_ab_drive_qoder.py field            # 只打印输入框正文
    python scripts/h279_ab_drive_qoder.py kill             # aa force-stop（注意：历史上会把 hdc 连接打断）
    python scripts/h279_ab_drive_qoder.py pages            # 打印 dumpLayout 里的文字节点（查页面状态）
键位坐标在 `panel` 之后缓存到本地文件 `.h279-keymap.json`（docs/evidence/.../tmp/，gitignore），
后续 keys/space 直接复用，不必每次重量。

退出码：0＝动作做完了（不代表功能通过）；2＝环境不对（没设备/量不到键）。
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import h279_zaozici_device_check as H  # 复用已验证的 sh/tap/shot/find_field/key_map

KEYMAP = os.path.join(H.EVID, "tmp", "h279-keymap.json")
LETTERS = ["qwertyuiop", "asdfghjkl"]


def load_keymap():
    if not os.path.isfile(KEYMAP):
        return None, None
    with open(KEYMAP, encoding="utf-8") as fp:
        d = json.load(fp)
    return {k: tuple(v) for k, v in d["letters"].items()}, tuple(d["space"])


def field():
    """本驱动自己的输入框定位（不复用 H.find_field）。

    为什么（08:0x 实测踩到）：H.find_field 取「标签下方最高的宽块」，
    这次页面下方还套着一层 Scroll/List 容器（[0,1886][1280,2579]，h=693），
    比真正的输入框（[70,1466][1210,1849]，h=383）高 ⇒ 选中了容器，
    点它等于点到「用户协议」上，页面直接跳走了。
    改成：紧挨标签下方（y1 最小）且高度在 200..560 之间的宽块＝输入框本体。
    """
    nodes = H.walk(H.dump_layout(), [])
    label = None
    for a in nodes:
        if (a.get("text") or "").strip() == "试一试":
            label = H.box_center(a)
            break
    if not label:
        return None
    _, _, _, _, _, ly2 = label
    best = None
    for a in nodes:
        c = H.box_center(a)
        if not c:
            continue
        cx, cy, x1, y1, x2, y2 = c
        if y1 < ly2 - 10 or x2 - x1 < 900:
            continue
        h = y2 - y1
        if not (200 <= h <= 560):
            continue
        if best is None or y1 < best[1][1]:
            best = (c, (a.get("text") or ""))
    if not best:
        return None
    (cx, cy, x1, y1, x2, y2), text = best
    return {"cx": cx, "cy": cy, "box": [x1, y1, x2, y2], "text": text}



def save_keymap(letters, space):
    os.makedirs(os.path.dirname(KEYMAP), exist_ok=True)
    with open(KEYMAP, "w", encoding="utf-8") as fp:
        json.dump({"letters": letters, "space": list(space)}, fp)


def measure2(png):
    """自己量键位：判据改成「与面板底色不同」，而不是 `panel_keys` 的「纯白键帽」。

    为什么（08:0x 实测）：`panel_keys.measure` 只认白色键帽，而我们的键盘
    **第二/三行是灰键帽 (201,206,218)**（H-220 选择模式在角上标了「全选/行首/文首…」，
    底色就不是纯白了），结果 26 键只量到第一行 10 个，`key_map` 报「缺 asdfghjkl」直接退出。
    面板底 (229,231,237) 与键帽（白 255 / 灰 201）每通道都差 ≥26，
    所以「离面板底色 >3」就是键帽；字母与图标颜色更深，会被游程合并阈值并回同一个键。

    返回 ({字母: (cx,cy)}, 空格(cx,cy), 每行键数)。行数/键数对不上就返回空表，
    让调用方去看截图，不猜坐标（硬规则 4）。
    """
    from PIL import Image
    img = Image.open(png).convert("RGB")
    w, h = img.size
    px = img.load()
    bg = px[3, int(h * 0.86)]          # 面板底（键盘区最左，键间隙处）

    def is_bg(x, y):
        return all(abs(a - b) <= 3 for a, b in zip(px[x, y], bg))

    def merged_runs(y):
        rs = []
        x = 0
        while x < w:
            if not is_bg(x, y):
                x0 = x
                while x < w and not is_bg(x, y):
                    x += 1
                if x - x0 >= 40:
                    rs.append([x0, x - 1])
            else:
                x += 1
        out = []
        for a, b in rs:
            if out and a - out[-1][1] <= 24:
                out[-1][1] = b
            else:
                out.append([a, b])
        return [o for o in out if o[1] - o[0] + 1 >= 40]

    def centers(y):
        return [(a + b) // 2 for a, b in merged_runs(y)]

    bands = []
    y = int(h * 0.55)
    while y < h:
        if len(centers(y)) >= 4:
            y0 = y
            while y < h and len(centers(y)) >= 4:
                y += 1
            if y - y0 >= 100:
                bands.append((y0, y))
        else:
            y += 1
    bands = bands[-4:]                  # 键盘恒在画面底部；上方若混进候选条假带一律弃
    if len(bands) != 4:
        return {}, None, [b[1] - b[0] for b in bands]
    rows = [centers((a + b) // 2) for a, b in bands]
    counts = [len(r) for r in rows]
    if counts[:3] != [10, 9, 9]:
        return {}, None, counts
    letters = {}
    for band, pattern, row in ((bands[0], "qwertyuiop", rows[0]),
                               (bands[1], "asdfghjkl", rows[1])):
        my = (band[0] + band[1]) // 2
        for ch, cx in zip(pattern, row):
            letters[ch] = (cx, my)
    # 第三行两端是 ↑(shift) 与 ⌫，中间 7 个才是 zxcvbnm
    my = (bands[2][0] + bands[2][1]) // 2
    for ch, cx in zip("zxcvbnm", rows[2][1:8]):
        letters[ch] = (cx, my)
    y4 = (bands[3][0] + bands[3][1]) // 2
    rs = merged_runs(y4)
    wide = max(rs, key=lambda ab: ab[1] - ab[0]) if rs else None
    space = ((wide[0] + wide[1]) // 2, y4) if wide and wide[1] - wide[0] > 300 else None
    return letters, space, counts


def cmd_panel():
    png = H.shot("h279-ab-panel.png")
    letters, space, counts = measure2(png)
    want = "".join(LETTERS)
    missing = [c for c in want if c not in letters]
    print("png=%s 每行键数=%s 认到字母键=%d 缺=%s 空格=%s"
          % (os.path.basename(png), counts, len(letters), missing or "无", space))
    if letters and not missing and space:
        save_keymap(letters, space)
        print("键位已缓存 ->", os.path.relpath(KEYMAP, ROOT))
        return 0
    return 2



def cmd_keys(seq):
    letters, space = load_keymap()
    if not letters:
        print("先跑 panel 量键位")
        return 2
    for ch in seq:
        xy = letters.get(ch)
        if not xy:
            print("  [warn] 无键 '%s'" % ch)
            continue
        H.tap(*xy)
        print("  tap %s @ %s" % (ch, xy))
    return 0


def cmd_space():
    letters, space = load_keymap()
    if not space:
        print("先跑 panel 量键位")
        return 2
    H.tap(*space)
    print("space @ %s" % (space,))
    return 0


def cmd_shot(tag):
    png = H.shot("h279-ab-%s.png" % tag)
    f = field() or {"text": "?"}
    print("png=%s 输入框正文=%r" % (os.path.basename(png), f.get("text")))
    return 0


def cmd_field():
    f = field()
    print("field=%s" % json.dumps(f, ensure_ascii=False) if f else "没找到输入框")
    return 0 if f else 2


def cmd_pages():
    nodes = H.walk(H.dump_layout(), [])
    for a in nodes:
        t = (a.get("text") or "").strip()
        if t:
            print("%r | %s" % (t[:70], a.get("bounds")))
    return 0


def cmd_open():
    print(H.sh("shell", "aa", "start", "-a", H.ABILITY, "-b", H.BUNDLE).strip())
    return 0


def cmd_kill():
    # 08:0x 实测：`aa force-stop -b <bundle>` 报 10104002「应用未安装」（误导），
    # 正确写法是位置参数 `aa force-stop <bundle>` ⇒ 一次成功，App 与 :inputMethod 两个进程都杀掉。
    out = H.sh("shell", "aa", "force-stop", H.BUNDLE)
    print("force-stop ->", (out or "(空)").strip())
    print("残留进程:", (H.sh("shell", "pidof", H.BUNDLE) or "(无)").strip())
    targets = H.sh("list", "targets").strip()
    print("hdc 连接仍在？targets=%s" % (targets or "(空)"))
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    rest = sys.argv[2:]
    if cmd == "panel":
        return cmd_panel()
    if cmd == "keys":
        return cmd_keys("".join(rest))
    if cmd == "space":
        return cmd_space()
    if cmd == "tap":
        # 任意坐标（如候选条右端的展开箭头 ⌄）；坐标一律从截图量，不猜
        H.tap(int(rest[0]), int(rest[1]))
        print("tap %s %s" % tuple(rest[:2]))
        return 0
    if cmd == "shot":
        return cmd_shot(rest[0] if rest else "x")
    if cmd == "field":
        return cmd_field()
    if cmd == "pages":
        return cmd_pages()
    if cmd == "open":
        return cmd_open()
    if cmd == "focus":
        f = field()
        if not f:
            print("没找到输入框")
            return 2
        H.tap(f["cx"], f["cy"], hold=1.2)
        print("点中 %s" % ([f["cx"], f["cy"]],))
        return 0
    if cmd == "kill":
        return cmd_kill()
    print("未知命令:", cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main())
