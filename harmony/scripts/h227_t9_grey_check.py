#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-227 九键置灰真机取证（Qoder 2026-10-28 09:2x）。

要证的事：切到九键后，`···` 菜单里那五枚 H-227 开关**是灰的、点了不起作用**
（`funcTileEnabled` 把点击闸门关掉）。离线守卫 ⑨ 只证「代码里接了闸门」，
证不了「装机这版屏幕上真是灰的、真点不动」。

安全口径（照 h231 双闸）：
  ① 只在三生自己的 App 里操作（bring_up 自家 App ＋ 它自带「试一试」框）；
  ② 每次注入前 guard() 重判解锁与前台；
  ③ 只点布局键/菜单行/切回键，不输入任何文字。

子命令：
  lp        长按左下角 `?123`（500ms）弹布局菜单，落一帧（我人眼定「九键」那一行坐标）
  tap X Y   在图示坐标点一下（guard 后），落一帧
  menu      开 `···` 菜单并滚到末屏（复用 h227 的 open/bottom）
  grey      量末屏五行的文字墨色（灰 vs 黑）并落一帧
  try Y     点第 Y 这一行，抓 `H-227 toggle option`；抓不到＝置灰生效（这一行被闸门挡住）
  back      点左下角 `ABC` 切回 26 键，落一帧
"""
import os
import sys
import time

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h231_panel_check as h231            # noqa: E402
import h241_settings_device_check as drv   # noqa: E402
import h241_settings_items as it           # noqa: E402
import h241_funcmenu_check as fm           # noqa: E402
import h227_menu_device_check as h227      # noqa: E402

ROOT = os.path.dirname(HERE)
DIR = os.path.join(ROOT, "docs", "evidence", "2026-10-28", "h227-t9")
TAG_RE = r"H-227 toggle option"
SYM = (100, 2590)          # 左下角 `?123`／`ABC`（底行 y=2590，见 h241 驱动器实测）
ROWS = [(2001, "中英对照"), (2119, "拼音注音"), (2239, "英文缩写"),
        (2358, "短语扩展"), (2476, "敏感词替换")]


def log(m):
    drv.log(m)


def shot(name):
    p = h231.screenshot("tmp-t9-%s" % name)
    os.makedirs(DIR, exist_ok=True)
    dst = os.path.join(DIR, "%s-%s.jpeg" % (name, time.strftime("%H%M%S")))
    import shutil
    shutil.copyfile(p, dst)
    log("SHOT -> %s" % dst)
    return dst


def ink(path, y, xa=30, xb=760):
    """行带 ±22px 内**文字墨色**：返回 (最暗灰度, 暗像素占比(灰度<120), 中位灰度(灰度<200 的像素))。"""
    im = Image.open(path).convert("RGB")
    px = im.load()
    W, H = im.size
    darkest = 255
    dark_n = 0
    tot = 0
    vals = []
    for yy in range(max(0, y - 22), min(H, y + 22), 2):
        for xx in range(xa, min(W, xb), 2):
            r, g, b = px[xx, yy]
            v = (r + g + b) // 3
            tot += 1
            if v < darkest:
                darkest = v
            if v < 120:
                dark_n += 1
            if v < 200:
                vals.append(v)
    vals.sort()
    med = vals[len(vals) // 2] if vals else None
    return darkest, dark_n / float(max(1, tot)), med


def cmd_lp():
    if h231.keyboard_panel_visible() is not True:
        h231.bring_up()
    if not h231.guard("t9-lp"):
        return 1
    shot("before-lp")
    log("长按左下角 `?123` (%d,%d)" % SYM)
    drv.long_press(*SYM)
    time.sleep(1.2)
    shot("layout-menu")
    return 0


def cmd_tap(x, y):
    if not h231.guard("t9-tap-%d-%d" % (x, y)):
        return 1
    log("点 (%d,%d)" % (x, y))
    h231.tap(x, y)
    time.sleep(1.2)
    shot("after-tap-%d-%d" % (x, y))
    return 0


def cmd_menu():
    rc = h227.cmd_open()
    if rc:
        return rc
    rc = h227.cmd_bottom()
    if rc:
        return rc
    shot("menu-t9")
    return 0


def cmd_grey():
    p = shot("grey")
    top, bottom, _cb = fm.card_span(p)
    xr = fm.card_xrun(p, (top + bottom) // 2, top=top, bottom=bottom) if top else None
    log("卡片 y=%s x=%s" % ((top, bottom), xr))
    for y, name in ROWS:
        d, frac, med = ink(p, y)
        log("行 %-6s y=%d 最暗=%d 暗像素占比=%.4f 中位=%s" % (name, y, d, frac, med))
    return 0


def cmd_try(y):
    y = int(y)
    if not h231.guard("t9-try-%d" % y):
        return 1
    it.hl(TAG_RE, clear=True, wait=0.2)
    log("点被置灰的行 (540,%d)" % y)
    h231.tap(540, y)
    time.sleep(1.0)
    hits = it.hl(TAG_RE, wait=0.5)
    log("hilog 命中 %d 条%s" % (len(hits), [" | " + h.split("H-227")[-1][:50] for h in hits]))
    shot("try-y%d" % y)
    if hits:
        log("VERDICT y=%d：FAIL —— 九键下这行还能点（闸门没关）" % y)
        return 1
    log("VERDICT y=%d：PASS —— 九键下点了没有引擎事件（置灰生效）" % y)
    return 0


def cmd_back():
    if not h231.guard("t9-back"):
        return 1
    log("点左下角 `ABC` 回 26 键 (%d,%d)" % SYM)
    h231.tap(*SYM)
    time.sleep(1.2)
    shot("back-qwerty")
    return 0


def main():
    drv.setup()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "grey"
    if cmd == "lp":
        return cmd_lp()
    if cmd == "tap":
        return cmd_tap(int(sys.argv[2]), int(sys.argv[3]))
    if cmd == "menu":
        return cmd_menu()
    if cmd == "grey":
        return cmd_grey()
    if cmd == "try":
        return cmd_try(int(sys.argv[2]))
    if cmd == "back":
        return cmd_back()
    log("未知子命令：%s" % cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main())
