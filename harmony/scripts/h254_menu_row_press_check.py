#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-254 真机取证：`···` 菜单行点完之后**底色必须回到常态**（Qoder 2026-10-28 09:0x）。

背景（为什么要有这支）：
  H-227 五枚开关 08:5x 逐个点时，每点一行，那一行的底色就停在 #DCE2EC（实测 (219,226,236)），
  直到把菜单关掉重开才恢复——与主人报的 H-238（顶栏 ⇆ 折叠后灰底不恢复）同一根因：
  框架 `stateStyles({pressed})` 抬手不复位。已在 FuncMenu/FuncMenuItem 改成显式 @State
  （Down 上色 / Up·Cancel 清色 / onClick 兜底），并加进 h227_menu_option_check 守卫 ⑩。
  这支脚本证明的是**装机那版真的不复位**——代码看着对不算（H-090 的教训）。

判据（像素，不靠肉眼）：
  每行取「行带内最常见颜色」当底色（文字/开关是少数像素，取众数能剔掉）。
    常态 ≈ (242,243,245) 或卡片底；按压 = (219,226,236)。
  点一下 → 等 1.0s（等动画走完）→ 再取同一条带同一行的众数：
    与按压色差 ≤8 ⇒ FAIL（H-254 没修好）
    与点前色差 ≤8 ⇒ PASS
  同一条带再点一次＝把开关拨回原值（不把主人的开关留在反面）。

安全口径（沿用 h231 双闸）：
  ① 只在三生自己的 App 里点（bring_up 自家 App ＋ 它自带的「试一试」框）；
  ② 每次注入前 guard() 重判解锁与前台；
  ③ 只点菜单行，不输入文字、不碰退格/清空。

用法：
  PYTHONIOENCODING=utf-8 python scripts/h254_menu_row_press_check.py open
  PYTHONIOENCODING=utf-8 python scripts/h254_menu_row_press_check.py row 2001
"""
import os
import sys
import time

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h231_panel_check as h231            # noqa: E402  双闸、点按、截图
import h241_settings_device_check as drv   # noqa: E402  hilog
import h241_settings_items as it           # noqa: E402  面板几何
import h241_funcmenu_check as fm           # noqa: E402  认 `···`、量卡片/文字带
import h227_menu_device_check as h227      # noqa: E402  复用 open/bottom 与取证目录

ROOT = os.path.dirname(HERE)
DIR = os.path.join(ROOT, "docs", "evidence", "2026-10-28", "h254-device")
TAG_RE = r"H-227 toggle option"
PRESSED = (219, 226, 236)


def log(m):
    drv.log(m)


def shot(name):
    p = h231.screenshot("tmp-h254-%s" % name)
    os.makedirs(DIR, exist_ok=True)
    dst = os.path.join(DIR, "%s-%s.jpeg" % (name, time.strftime("%H%M%S")))
    import shutil
    shutil.copyfile(p, dst)
    log("SHOT -> %s" % dst)
    return dst


def row_bg(path, y0, y1, xa, xb):
    """行带内「最常见颜色」＝底色（文字/开关是少数像素）。返回 (rgb, 占比)。"""
    im = Image.open(path).convert("RGB")
    px = im.load()
    W, H = im.size
    xa = max(0, min(W - 1, int(xa)))
    xb = max(xa + 1, min(W - 1, int(xb)))
    y0 = max(0, min(H - 1, int(y0)))
    y1 = max(y0 + 1, min(H - 1, int(y1)))
    cnt = {}
    tot = 0
    for y in range(y0, y1, 2):
        for x in range(xa, xb, 2):
            c = px[x, y]
            cnt[c] = cnt.get(c, 0) + 1
            tot += 1
    if not tot:
        return None, 0.0
    rgb, n = max(cnt.items(), key=lambda kv: kv[1])
    return rgb, n / float(tot)


def dist(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))


def card_geom():
    """现截一帧 → 卡片可见范围 + 横向范围。"""
    p = shot("geom")
    top, bottom, _cb = fm.card_span(p)
    if top is None:
        return p, None, None
    xr = fm.card_xrun(p, (top + bottom) // 2, top=top, bottom=bottom)
    return p, (top, bottom), xr


def cmd_open():
    if h231.keyboard_panel_visible() is not True:
        log("键盘不在 ⇒ bring_up 自家 App")
        h231.bring_up()
    if not h231.guard("h254-open"):
        log("GUARD 不过（没解锁或前台不是自家 App）⇒ 不点")
        return 1
    it.refresh()
    more = fm.find_more_tile()
    if not more:
        log("没挑出 `···` ⇒ 本轮作废（不猜坐标）")
        return 1
    it.hl(r"H-241r2 func menu opened", clear=True, wait=0.2)
    log("点 `···` (%d,%d)" % more)
    h231.tap(more[0], more[1])
    time.sleep(1.5)
    opened = it.hl(r"H-241r2 func menu opened", wait=0.3)
    p, card, xr = card_geom()
    log("菜单开启日志 %d 条；卡片 y=%s x=%s" % (len(opened), card, xr))
    return 0 if opened and card else 1


def cmd_row(y):
    """在指定 y 的菜单行上做「采样→点→采样→再点(复原)→采样」。"""
    y = int(y)
    if not h231.guard("h254-row-%d" % y):
        log("GUARD 不过 ⇒ 不点")
        return 1
    p, card, xr = card_geom()
    if not card or not xr:
        log("没量到卡片 ⇒ 先跑 open")
        return 1
    xa, xb = xr[0] + 10, xr[1] - 10
    y0, y1 = y - 22, y + 22                      # 行距 32vp×3.5=112px，±22 只取本行
    before, share = row_bg(p, y0, y1, xa, xb)
    log("行 y=%d 点前底色=%s（众数占比 %.2f，x=[%d,%d]）" % (y, before, share, xa, xb))

    it.hl(TAG_RE, clear=True, wait=0.2)
    log("点 (540,%d)" % y)
    h231.tap(540, y)
    time.sleep(1.0)
    hits = it.hl(TAG_RE, wait=0.4)
    log("hilog 命中 %d 条：%s" % (len(hits), [h.split("H-227")[-1][:60] for h in hits]))
    time.sleep(0.5)
    p2 = shot("after-y%d" % y)
    after, share2 = row_bg(p2, y0, y1, xa, xb)
    log("行 y=%d 点后底色=%s（众数占比 %.2f）" % (y, after, share2))

    ok = True
    if after is None:
        log("VERDICT y=%d：点后量不到底色 ⇒ 作废" % y)
        return 1
    if dist(after, PRESSED) <= 8:
        log("VERDICT y=%d：FAIL —— 点后停在按压色 %s（H-254 未修好）" % (y, after))
        ok = False
    elif dist(after, before) <= 8:
        log("VERDICT y=%d：PASS —— 点后回到点前底色 %s（不是按压色 %s）" % (y, after, PRESSED))
    else:
        log("VERDICT y=%d：注意 —— 点后底色 %s 既不是点前 %s 也不是按压色，人工看一眼截图"
            % (y, after, before))
        ok = False

    # 复原：再点一次把开关拨回原值；顺便拿第二个数据点
    time.sleep(0.6)
    it.hl(TAG_RE, clear=True, wait=0.2)
    log("复原：再点 (540,%d)" % y)
    h231.tap(540, y)
    time.sleep(1.0)
    hits2 = it.hl(TAG_RE, wait=0.4)
    log("复原 hilog 命中 %d 条" % len(hits2))
    time.sleep(0.5)
    p3 = shot("restored-y%d" % y)
    back, share3 = row_bg(p3, y0, y1, xa, xb)
    log("行 y=%d 复原后底色=%s（众数占比 %.2f）" % (y, back, share3))
    if back is not None and dist(back, PRESSED) <= 8:
        log("VERDICT y=%d 复原点：FAIL —— 又停在按压色" % y)
        ok = False
    if not hits2:
        log("注意：复原那一下没抓到 hilog（可能点到行间空白），开关状态要人眼核一眼")
    return 0 if ok else 1


def cmd_scan():
    """现截一帧 → 列出每条文字带的 [上,下] 与「行中心那一带的底色」。
    用来在点之前确认「要点的这一行」在哪、底色是多少（点错行/点进空白都算白跑）。"""
    p, card, xr = card_geom()
    if not card or not xr:
        log("没量到卡片 ⇒ 先跑 open")
        return 1
    bands = fm.row_bands(p, card[0], card[1], xr)
    xa, xb = xr[0] + 10, xr[1] - 10
    for i, b in enumerate(bands):
        cy = (b[0] + b[1]) // 2
        rgb, share = row_bg(p, cy - 22, cy + 22, xa, xb)
        log("行 %d：y=[%d,%d] 中心 %d 底色=%s（%.2f）" % (i, b[0], b[1], cy, rgb, share))
    return 0


def cmd_bottom():
    return h227.cmd_bottom()


def main():
    drv.setup()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "open"
    if cmd == "open":
        return cmd_open()
    if cmd == "bottom":
        return cmd_bottom()
    if cmd == "scan":
        return cmd_scan()
    if cmd == "row":
        return cmd_row(int(sys.argv[2]))
    log("未知子命令：%s" % cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main())
