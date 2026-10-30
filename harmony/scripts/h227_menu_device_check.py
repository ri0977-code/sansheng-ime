#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-227 五枚滤镜开关的**真机机械验收**（Qoder 2026-10-28 08:5x 起）。

为什么要单开一支量具（不是重复劳动）：
  H-227 的五枚开关（中英对照／拼音注音／英文缩写／短语扩展／敏感词替换）08:34 已装机，
  台账上写的是「待主人真手逐枚勾」。可离线守卫只证明「代码里五环齐全」，**证明不了
  「装机那版点下去引擎真的换了」**——H-090 那轮 71 项 0 项生效就是栽在「代码看着对」。
  这支脚本把「点一下→hilog→标签翻转」这条链在路上跑完，主人的真手只留最后「手感」一项。

安全口径（照 h231 的已验证双闸，不新造）：
  ① 只在**三生自己的 App**里操作：`h231.bring_up()` 启动 com.sansheng.ime、点它自带的
     「试一试」输入框，绝不碰主人的备忘录/聊天；
  ② 每次注入前 `h231.guard()` 重判锁屏与前台归属，不是自家就停手；
  ③ **不输入任何文字**：全程只有「点菜单行」与「在菜单卡片里滚动」，不碰退格/清空。

做法：
  open    → 拉键盘、展开工具栏、挑 `···`、点开、量卡片与文字带（首屏）
  bottom  → 在卡片里往上拖到底（末屏＝设置行那屏），再量文字带
  tap N   → 现截一帧、现量文字带，点第 N 条带中心；抓 `H-227 toggle option: <name>=<bool>`
  crop N  → 把第 N 条带放大 3 倍落盘（我人眼核 文案＋开/关 那列）
  close   → 点遮罩关菜单
  t9      → ?123 → 九宫格，再开 `···` 落一帧（九键下五枚应灰）

产出：docs/evidence/2026-10-28/h227-device/（同名不覆盖，加 -r2/-r3）
用法：PYTHONIOENCODING=utf-8 python scripts/h227_menu_device_check.py open
"""
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h231_panel_check as h231            # noqa: E402  锁屏/前台双闸、点按、截图
import h241_settings_device_check as drv   # noqa: E402  hilog
import h241_settings_items as it           # noqa: E402  面板几何
import h241_funcmenu_check as fm           # noqa: E402  认 `···`、量卡片/文字带

ROOT = os.path.dirname(HERE)
DIR = os.path.join(ROOT, "docs", "evidence", "2026-10-28", "h227-device")
STATE = os.path.join(DIR, "state.json")
TAG_RE = r"H-227 toggle option"


def log(m):
    drv.log(m)


def uniq(name, ext):
    os.makedirs(DIR, exist_ok=True)
    p = os.path.join(DIR, "%s.%s" % (name, ext))
    i = 2
    while os.path.exists(p):
        p = os.path.join(DIR, "%s-r%d.%s" % (name, i, ext))
        i += 1
    return p


def shot(name):
    p = h231.screenshot("tmp-%s" % name)
    dst = uniq(name, "jpeg")
    import shutil
    shutil.copyfile(p, dst)
    log("SHOT -> %s" % dst)
    return dst


def load():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save(d):
    os.makedirs(DIR, exist_ok=True)
    cur = load()
    cur.update(d)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(cur, f, ensure_ascii=False, indent=1)


def bands_now(tag):
    """现截一帧 → 量卡片 → 量文字带；返回 (截图路径, 卡片可见 y=[top,bottom], 带列表)。"""
    p = shot(tag)
    top, bottom, _cb = fm.card_span(p)
    if top is None:
        log("BANDS %s：没量到卡片亮块 ⇒ 菜单没开？" % tag)
        return p, None, []
    xr = fm.card_xrun(p, (top + bottom) // 2, top=top, bottom=bottom)
    if not xr:
        log("BANDS %s：量不到卡片横向范围" % tag)
        return p, (top, bottom), []
    bands = fm.row_bands(p, top, bottom, xr)
    log("BANDS %s：卡片 y=[%d,%d] x=[%d,%d]，%d 条带 %s"
        % (tag, top, bottom, xr[0], xr[1], len(bands), [b[0] for b in bands]))
    save({"bands": [list(b[:2]) for b in bands], "card": [top, bottom], "shot": p})
    return p, (top, bottom), bands


def cmd_open():
    if h231.keyboard_panel_visible() is not True:
        log("键盘不在 ⇒ bring_up 自家 App")
        h231.bring_up()
    if not h231.guard("h227-open"):
        log("GUARD 不过（没解锁或前台不是自家 App）⇒ 不点")
        return 1
    it.refresh()
    more = fm.find_more_tile()
    if not more:
        log("没挑出 `···` ⇒ 本轮作废（不猜坐标）")
        return 1
    it.hl(TAG_RE, clear=True, wait=0.2)
    log("点 `···` (%d,%d)" % more)
    h231.tap(more[0], more[1])
    time.sleep(1.4)
    opened = it.hl(r"H-241r2 func menu opened", wait=0.3)
    log("菜单开启日志 %d 条" % len(opened))
    bands_now("menu-top")
    return 0


def cmd_bottom():
    st = load()
    card = st.get("card")
    if not card:
        log("没有卡片几何 ⇒ 先跑 open")
        return 1
    if not h231.guard("h227-bottom"):
        log("GUARD 不过 ⇒ 不点")
        return 1
    top, bottom = card
    x = 640
    # 拖两次到底（拖过头会被钳回来，所以「往死里拖」＝精确已知状态）
    for i in range(2):
        drv.drag(x, bottom - 40, x, top + 40, velocity=1400)
        time.sleep(0.6)
    bands_now("menu-bottom")
    return 0


def cmd_tap(n):
    st = load()
    if not h231.guard("h227-tap-%d" % n):
        log("GUARD 不过 ⇒ 不点")
        return 1
    p, card, bands = bands_now("before-tap-%d" % n)
    if not bands or n >= len(bands):
        log("带数不足（%d 条，要第 %d 条）⇒ 不点" % (len(bands), n))
        return 1
    b = bands[n]
    cx = 640
    cy = (b[0] + b[1]) // 2
    it.hl(TAG_RE, clear=True, wait=0.2)
    log("点第 %d 条带 (540,%d) y=[%d,%d]" % (n, cy, b[0], b[1]))
    h231.tap(cx, cy)
    time.sleep(1.0)
    hits = it.hl(TAG_RE, wait=0.4)
    log("hilog 命中 %d 条：%s" % (len(hits), [h.split('H-227')[-1][:60] for h in hits]))
    time.sleep(0.4)
    shot("after-tap-%d" % n)
    return 0 if hits else 1


def cmd_tapy(y):
    """点**指定 y**（末屏三行被高亮底粘成一条带时，`tap N` 点不准；y 由人眼在截图上量、
    用行距 32vp×3.5=112px 推）。guard 每次重判；hilog 抓不到 `H-227 toggle option` 就算没点中。"""
    y = int(y)
    if not h231.guard("h227-tapy-%d" % y):
        log("GUARD 不过 ⇒ 不点")
        return 1
    it.hl(TAG_RE, clear=True, wait=0.2)
    log("点 (540,%d)" % y)
    h231.tap(540, y)
    time.sleep(1.0)
    hits = it.hl(TAG_RE, wait=0.4)
    log("hilog 命中 %d 条：%s" % (len(hits), [h.split("H-227")[-1][:60] for h in hits]))
    time.sleep(0.4)
    shot("after-y%d" % y)
    return 0 if hits else 1


def cmd_crop(n):
    st = load()
    bands = st.get("bands") or []
    if n >= len(bands):
        log("没有第 %d 条带的记录 ⇒ 先跑 tap/bands" % n)
        return 1
    b = bands[n]
    p = st.get("shot")
    if not p or not os.path.exists(p):
        log("截图不在了：%s" % p)
        return 1
    out = uniq("crop-row%d" % n, "png")
    h231.zoom_crop(p, (int(640 - 420), int(b[0]) - 8, int(640 + 420), int(b[1]) + 8), 3, out)
    log("CROP -> %s" % out)
    return 0


def cmd_close():
    pr = h231.panel_rect()
    if pr:
        h231.tap(pr[0] + pr[2] - 40, pr[1] + 40)
        time.sleep(0.6)
    log("CLOSE done")
    return 0


def cmd_state():
    st = load()
    log("STATE bands=%s card=%s" % (st.get("bands"), st.get("card")))
    return 0


def main():
    drv.setup()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "state"
    if cmd == "open":
        return cmd_open()
    if cmd == "bottom":
        return cmd_bottom()
    if cmd == "tap":
        return cmd_tap(int(sys.argv[2]))
    if cmd == "tapy":
        return cmd_tapy(int(sys.argv[2]))
    if cmd == "crop":
        return cmd_crop(int(sys.argv[2]))
    if cmd == "close":
        return cmd_close()
    return cmd_state()


if __name__ == "__main__":
    sys.exit(main())
