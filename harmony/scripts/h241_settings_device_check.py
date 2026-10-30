#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-241 设置页真机取证量具（Qoder，2026-10-28 02:3x 起）

主人的原话（H-239/H-241 的验收对象）：
  「让长按空格，或者回车键，调出设置页面，里面的功能参考安卓里的，键盘调节啊，字体设置啊……」
契约 `docs/SETTINGS-CONTRACT.md` §5-4：**每项改前/改后各量一次**，取证落
  `docs/evidence/2026-10-28/h239-settings-<key>/`（带键名、不许同名覆盖）。

**为什么全走像素＋hilog，不走控件树**（2026-10-28 00:36 实测，已写进 h234-236 取证文档）：
`uitest dumpLayout` 捞不到 IME 那扇窗（SCBKeyboardPanel 一个节点都不进树）⇒ 设置页那 12 行的
文案只能靠放大图我自己核，几何靠「白卡片包围盒＋步进按钮色块」锚，值靠 hilog
`SettingsStore: set <key>=<v>` 与 `H-241 settings synced: ...` 定案。

**几何口径**（照 `SettingsPanel.ets` 实际写死的数，vp 全部乘 px/vp 比例）：
  卡片宽 = 面板宽 88%、高 = 面板高（100%）；上内边距 6 ＋ 标题行 24 ＋ Column space 4
  ⇒ Scroll 视口 = 卡片内 [34, 230]vp（196vp 高），内容 12×32=384vp ⇒ **必须滚**（H-213 那条死线）。
  最大滚动量 S_max = 384-196 = 188vp（拖过头会被钳回来，所以「往死里拖」＝精确已知状态）。
  行 i 中心（卡片内坐标）= 34 + 32i + 16 - S。
  ⇒ 不滚＝行 0..4 可见（S=0）；滚到底＝行 5..11 可见（S=188）。这两态里 12 行全覆盖，
     不需要「猜停在中间」——这是本量具敢用公式定 y 的唯一原因。
  ＋ 按钮中心 x = 卡片右 - 24vp；－ 按钮 = 卡片右 - 124vp；开关行「开/关」文字 = 卡片右 - 20vp。

用法：
  python scripts/h241_settings_device_check.py probe           # 拉键盘＋量面板窗＋算空格/回车中心
  python scripts/h241_settings_device_check.py entry           # 长按空格 → 设置页（入口判据）
  python scripts/h241_settings_device_check.py card            # 核卡片几何＋切放大图（我人眼读文案）
  python scripts/h241_settings_device_check.py tap <key> <±n>  # 滚到位→按 ＋/－ n 次（bool 翻一次）
  python scripts/h241_settings_device_check.py close           # 点遮罩关页
  python scripts/h241_settings_device_check.py reset           # 长按开页→点「恢复默认」→日志确认
  python scripts/h241_settings_device_check.py check           # 只看状态（零注入）
产出：docs/evidence/2026-10-28/h239-settings/_driver/
"""
import os
import re
import sys
import time
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h231_panel_check as h231          # noqa: E402  复用已验证的锁屏/前台双闸、点按、截图、裁图

ROOT = os.path.dirname(HERE)
BASE = os.path.join(ROOT, "docs", "evidence", "2026-10-28")
EVID = os.path.join(BASE, "h239-settings", "_driver")
STATE = os.path.join(EVID, "state.json")

# 契约 §3 表序＝SettingsStore.SPECS 注册序＝页面 LABELS 下标（H-242 守卫按这个对账）。
SPEC = [
    ("kbd_height_pct", "num"), ("cand_font_size", "num"), ("key_font_size", "num"),
    ("page_size", "num"), ("kbd_haptic", "bool"), ("key_long_press_delay", "num"),
    ("popup_on_key_press", "bool"), ("undo_stack_limit", "num"), ("grid_page_size", "num"),
    ("space_swipe_step", "num"), ("expand_toolbar_by_default", "bool"), ("show_preedit", "bool"),
]
IDX = {k: i for i, (k, _t) in enumerate(SPEC)}
KIND = {k: t for k, t in SPEC}

CARD_BG = (255, 255, 255)          # 卡片底 '#FFFFFF'
STEP_BG = (228, 231, 236)          # ＋/－ 底 BG_STEP '#E4E7EC'
TOL = 10
ROW_VP = 32.0
VP_TOP_VP = 34.0                   # 视口顶（卡片内坐标）
VP_BOT_VP = 230.0                  # 视口底（236 - 6 下内边距）
CARD_H_VP = 236.0                  # 卡片高＝键盘容器内容高（键高 100% 时），见 `card_anchor`
S_MAX_VP = 12 * ROW_VP - (VP_BOT_VP - VP_TOP_VP)   # 188


def card_anchor(box, scale=None, tag="CARD"):
    """卡片的**真顶 y**——所有行心都从它算，不用 `find_card_bbox` 的 `box[1]`。

    2026-10-28 03:06 实测：卡片挂在**内容底锚定**的键盘容器里（`height('100%')`＝236vp 预算），
    打字时窗顶会往上长（编码行出现：1849 → 1815），而**卡片顶仍是 1849**；
    `find_card_bbox` 从窗顶往下扫，把编码行/候选栏那条白也框进来 ⇒ `box[1]` 少 34px。
    铁证：S=0 时行 0 的 ＋ 实测中心 y=2024 = 2675 − 236×3.5 + 34×3.5 + 16×3.5，
    按 `box[1]=1815` 预测得 1990，**四行整整齐齐差 34px**（残差 [34,34,34,34]）；
    按底沿反推的 1849 预测 2024/2136/2248/2360 ↔ 实测 2024/2136/2248/2360，分毫不差。

    返回 None＝口径不成立（卡片高和 236vp 差 >60px，多半是「键盘高度百分比」不是 100），
    调用方必须**停手**（先 `reset`），别拿错锚点去点行——那正是 02:54 误碰振动开关那类事故。"""
    scale = scale or (load_state().get("scale") or 3.5)
    h = CARD_H_VP * scale
    d = (box[3] - box[1]) - h
    if abs(d) <= 12:
        return box[1]
    top = int(box[3] - h)
    if d > 12 and top >= box[1] and d <= 60:
        log("%s 框顶=%d ⇒ 按底沿反推真顶=%d（顶部多 %dpx＝编码行/候选栏的白被一起框进来了）"
            % (tag, box[1], top, d))
        return top
    log("%s ANCHOR-ABORT 卡片高 %dpx 与 236vp(%.0fpx) 差 %+dpx ⇒ 键高不是 100%%，先跑 reset 再点行"
        % (tag, box[3] - box[1], h, d))
    return None


def setup():
    os.makedirs(EVID, exist_ok=True)
    h231.EVID = EVID
    h231.LOG = os.path.join(EVID, "run.log")


def log(m):
    h231.log(m)


def load_state():
    if os.path.exists(STATE):
        try:
            with open(STATE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(d):
    cur = load_state()
    cur.update(d)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(cur, f, ensure_ascii=False, indent=1)
    return cur


def hl(pattern, clear=False, wait=1.0):
    if clear:
        h231.sh("shell", "hilog", "-r")
        time.sleep(0.4)
    time.sleep(wait)
    txt = h231.sh("shell", "hilog", "-x")
    return [ln.strip() for ln in txt.splitlines() if re.search(pattern, ln)]


def dump_hlog(name):
    p = os.path.join(EVID, name + ".hilog.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(h231.sh("shell", "hilog", "-x"))
    return p


def long_press(x, y):
    h231.sh("shell", "uitest", "uiInput", "longClick", str(int(x)), str(int(y)))


def drag(x1, y1, x2, y2, velocity=1400):
    h231.sh("shell", "uitest", "uiInput", "drag",
            str(int(x1)), str(int(y1)), str(int(x2)), str(int(y2)), str(int(velocity)))


def swipe(x1, y1, x2, y2, velocity=900):
    """H-241 空格横滑判据要的是 swipe（不是 drag）：uiInput swipe 会走键盘的滑动手势分支。
    items.space_swipe_step 直接调这个；distance 由调用方给，vp 换算也在那边做。"""
    h231.sh("shell", "uitest", "uiInput", "swipe",
            str(int(x1)), str(int(y1)), str(int(x2)), str(int(y2)), str(int(velocity)))


def panel_rect():
    return h231.panel_rect()


def content_bottom_px(shot, pr):
    """键盘内容的**下沿**＝从窗口矩形底部往上，跨过系统导航条黑带后的第一行。

    2026-10-28 02:3x 实拍：WMS 报 SCBKeyboardPanel 高 983px，但 2680..2832 是纯黑导航条区
    （采样 (36,36,36)）⇒ 真内容底 ≈2675。**用窗口 h 折算密度会得到 4.17 这种假数**，
    点下去正好落在黑条上（我第一次估的空格 y=2732 就是这么错的）。
    """
    from PIL import Image
    im = Image.open(shot).convert("RGB")
    w, _h = im.size
    px = im.load()
    y = int(pr[1] + pr[3]) - 4
    while y > pr[1]:
        dark = 0
        for x in range(0, w, 8):
            r, g, b = px[x, y]
            if r < 70 and g < 70 and b < 70:
                dark += 1
        if dark < (w // 8) * 0.9:
            break
        y -= 2
    return y


def locate_bottom_row(shot, pr, scale):
    """**按像素**找底行（空格/回车那一排）——不靠「236vp 预算」推。"""
    from PIL import Image
    im = Image.open(shot).convert("RGB")
    w, _h = im.size
    px = im.load()
    cb = content_bottom_px(shot, pr)
    content_bottom = int(pr[1] + 236 * scale)
    log("内容底：像素法=%d 公式法(窗顶+236vp)=%d 差=%d" % (cb, content_bottom, cb - content_bottom))
    best = (0, 0, 0, 0)          # (连续白段长, 起 px, 止 px, 行 y)
    for yy in range(cb - int(48 * scale), cb - int(10 * scale), 4):
        run = 0
        for i in range(w // 2):
            x = i * 2
            r, g, b = px[x, yy]
            if r > 245 and g > 245 and b > 245:
                run += 1
                if run > best[0]:
                    best = (run, (i - run + 1) * 2, (i + 1) * 2, yy)
            else:
                run = 0
    x1, x2, y = best[1], best[2], best[3]
    wide_vp = (x2 - x1) / scale
    log("底行像素定位：内容底=%d 最长连续白段 x=[%d,%d] 宽 %.1fvp y=%d" % (cb, x1, x2, wide_vp, y))
    # 自检：空格键面在契约里是「底行中间那枚宽键」≈160vp；量出来差太远＝密度错了，别接着点
    if not 130 <= wide_vp <= 190:
        log("LOCATE-ABORT 空格宽度 %.1fvp 不在 130..190 ⇒ 密度/内容底判错，停手" % wide_vp)
        return None, None, cb
    space = [(x1 + x2) / 2.0, y]
    # 回车＝底行那枚**金色圆钮**（实测底色 (184,131,15)）⇒ 按色找质心，不按「右边 42vp」猜。
    gxs = []
    gys = []
    for yy in range(cb - int(46 * scale), cb - int(6 * scale), 3):
        for xx in range(x2 + 10, pr[0] + pr[2] - 4, 3):
            r, g, b = px[xx, yy]
            if r > 140 and 90 < g < 185 and b < 90:
                gxs.append(xx)
                gys.append(yy)
    if len(gxs) > 40:
        enter = [sum(gxs) / len(gxs), sum(gys) / len(gys)]
        log("回车按金色质心定位=(%d,%d)（采样 %d 点）" % (enter[0], enter[1], len(gxs)))
    else:
        enter = [pr[0] + pr[2] - 42 * scale, y]
        log("△ 没量到金色回车（采样 %d 点）⇒ 退回右边 42vp 估算" % len(gxs))
    return space, enter, cb



def is_card(bbox):
    """bbox 到底像不像「设置卡片」——必须**竖向铺满大半个内容高**。
    2026-10-28 02:44 实测教训：卡片关掉后，光键盘自己的候选栏（y 1849..2003）也能凑出
    ≥900px 的连续白段，于是 `find_card_bbox` 在**关着的键盘**上照样返回一个框（[56,1849,1230,2003]），
    「卡片还在? True」全是假的。卡片真高 826px（236vp×3.5）、真宽 1124px，
    所以只有**又高又宽**的白块才算卡片开着。"""
    return bool(bbox) and (bbox[3] - bbox[1]) >= 600 and (bbox[2] - bbox[0]) >= 900


def collapse_grid(pr, scale, tag="COLLAPSE-GRID"):
    """候选网格还开着就折叠回去（单击顶栏最右那枚 ▼/▲，KeyboardIndex 2501-2516 随状态切换）。
    2026-10-28 03:01 起连串 LOCATE-ABORT 的**真因**不是密度：上一项 `grid_page_size` 点了 ▼，
    键区被整块换成候选网格（网格没有底行宽键 ⇒ 最长白段只剩 9.1vp），而 `expanded` 是 IME
    面板的 @State、**重启自家 App 也不清**，于是后面每一项都量不到空格、开页全失败。
    △ 副作用：网格开着但此刻无候选时，那枚单击会走 `hideKeyboard()` 分支把键盘收掉 ⇒
    调用方量不到就得自己 bring_up 重来。"""
    x = int(pr[0] + pr[2] - 20 * scale)
    y = int(pr[1] + 22 * scale)
    if not h231.guard(tag):
        return h231.screenshot("grid-uncollapsed")
    log("%s 底行量不到 ⇒ 点网格折叠键 (%d,%d)" % (tag, x, y))
    h231.tap(x, y)
    time.sleep(1.0)
    return h231.screenshot("after-collapse-grid")


def scrim_point(pr, card=None):
    """关整页要点**遮罩**。卡片是 `width('88%')` 且**左对齐**（实测 bbox [0,1849,1124,2675]），
    所以遮罩露出来的那条带在**右边** 156px 里；以前点 `pr[0]+14`（左边 14px）落在卡片自己身上，
    根本关不掉——2026-10-28 02:41 实测：卡片还开着 → 白板被当成键帽量出 321.7vp「空格」。
    y 取内容中带（窗顶 + 118vp），避开 ✕ 按钮和任何键。"""
    scale = load_state().get("scale") or 3.5
    right = int((card or [0, 0, int(pr[0] + pr[2] * 0.88), 0])[2])
    x = max(pr[0] + 2, min(right + 26, pr[0] + pr[2] - 6))
    y = int(pr[1] + 118 * scale)
    return x, y


def find_card_bbox(shot, y_min):
    """在 [y_min, 屏底] 里找整块白卡片（键帽在遮罩下变灰，纯白只有卡片）。
    **左右沿取「最长连续白段」的公共边界（中位数）**，不是「任意一行白就算进来」——
    2026-10-28 02:5x 实测教训：旧写法的 x 向二次扫描把键盘键帽的白也吸进来，
    卡片右沿从 1124 漂到 1210 ⇒ 按「右沿内缩 14vp」放的按钮探针列直接落到卡片外面，
    滚动量/行心全跟着错。"""
    from PIL import Image
    im = Image.open(shot).convert("RGB")
    w, h = im.size
    px = im.load()
    need = int(w * 0.88 * 0.8)                  # ≥80% 卡宽的**连续**白段才算卡片行
    rows = []
    for y in range(max(0, int(y_min)), h, 2):
        run = 0
        start = 0
        best = (0, 0, 0)                         # (长度, 左, 右)
        for x in range(0, w):
            r, g, b = px[x, y]
            if abs(r - 255) <= TOL and abs(g - 255) <= TOL and abs(b - 255) <= TOL:
                if run == 0:
                    start = x
                run += 1
                if run > best[0]:
                    best = (run, start, x + 1)
            else:
                run = 0
        if best[0] >= need:
            rows.append((y, best))
    if not rows:
        return None
    ys = [y for y, _b in rows]
    lefts = sorted(b[1] for _y, b in rows)
    rights = sorted(b[2] for _y, b in rows)
    n = len(rows) // 2
    return [lefts[n], min(ys), rights[n], max(ys) + 2]


def find_step_buttons(shot, box):
    """卡片右侧带里找 ＋ 按钮（#E4E7EC 底）⇒ 返回每个可见数值行的中心 y。
    2026-10-28 02:47 实测教训：探针列原来取 `x2 - 24vp`＝按钮**正中心**，那里正好被「＋」
    字形的横竖笔画切断——一条 91px 的按钮变成 (29,34) 两段，"实测序列"就成了 52~60px 间距的噪音，
    把本来分毫不差的行公式（预测 2248 ↔ 实测中心 2248）误判成「差 29px ⇒ 打偏」而 ABORT。
    现在探针列取 `x2 - 14vp`（按钮右半，避开字形），命中判定改成「**不是卡片白底**」，
    按钮整段连续（含字形），再用 ≥40px 门槛滤掉零碎。"""
    from PIL import Image
    im = Image.open(shot).convert("RGB")
    px = im.load()
    x1, y1, x2, y2 = box
    scale = load_state().get("scale") or 3.0
    probe_x = min(max(int(x2 - 14 * scale), x1 + 1), im.size[0] - 1)
    out = []
    y = max(0, y1)
    run_start = None
    # 只扫**卡片以内**（03:06 实测：多扫 40px 会把卡片底下的导航条黑带当成一枚按钮，
    # 量出 y=2695 这种“多出来的一发”，把 S 拟合带偏）。
    lim = min(im.size[1], y2 - 2)
    while y < lim:
        r, g, b = px[probe_x, y]
        hit = not (abs(r - 255) <= TOL and abs(g - 255) <= TOL and abs(b - 255) <= TOL)
        if hit and run_start is None:
            run_start = y
        elif not hit and run_start is not None:
            if y - run_start >= 40:
                out.append((run_start + y) // 2)
            run_start = None
        y += 1
    if run_start is not None and lim - run_start >= 40:
        out.append((run_start + lim) // 2)
    return out


def row_center_y(card, scale, idx, scrolled):
    """行 idx 的中心屏幕 y：不滚 S=0（行 0..4），滚到底 S=S_MAX（行 5..11）。"""
    s = S_MAX_VP if scrolled else 0.0
    return card[1] + (VP_TOP_VP + ROW_VP * idx + ROW_VP / 2.0 - s) * scale


def need_scrolled(idx):
    return idx >= 5


def anchor_box(box, scale=None, tag="CARD"):
    """把 `find_card_bbox` 的框**顶边换成真顶**（见 `card_anchor`）后返回；口径不成立返回 None。
    这样下游所有 `card[1] + (34 + 32i + 16 − S)×scale` 一律不用改。"""
    if not box:
        return None
    top = card_anchor(box, scale, tag)
    if top is None:
        return None
    return [box[0], int(top), box[2], box[3]]


def ensure_open():
    """返回 (截图, 卡片框)；**卡片真开着**才给框，且框顶已按底沿校正（`anchor_box`）。
    关掉时键盘候选栏也会凑出一个白框（见 `is_card` 的注释），不筛就会拿假框去点行。"""
    st = load_state()
    shot = h231.screenshot("state")
    box = find_card_bbox(shot, (st.get("panel") or [0, 0, 0, 0])[1])
    return shot, (anchor_box(box, st.get("scale"), "CARD") if is_card(box) else None)


def measure_scroll(shot, card, scale):
    """用**实测**的 ＋ 按钮中心反推当前滚动量 S（vp）——不猜、量出来。
    行 i 的按钮中心 = card_top + (34 + 32i + 16 − S)×scale。
    S 从 0 试到 260vp（视口高会随「有没有编码行」在 236/245vp 之间动 ⇒ 上限给足），
    每个候选 S 都要过两关：**①** 视口内该有按钮的行**每一行**都能在 ±14px 内找到实测点；
    **②** 实测点总数不能比预测多（多的就是拟合错了）。只按残差最小选会**差一整个行距**
    地错位（32vp 一个周期），所以把「谁该在、谁不该在」也拿来当判据。
    返回 (S, 平均残差px, 实测中心列表)；一个按钮都没量到 ⇒ (None, None, [])。"""
    meas = find_step_buttons(shot, card)
    if not meas:
        return None, None, []
    vp_top = card[1] + VP_TOP_VP * scale
    vp_bot = card[1] + VP_BOT_VP * scale
    num_rows = [i for i, (_k, t) in enumerate(SPEC) if t == "num"]
    best = None
    s = 0.0
    while s <= 260.0 + 1e-6:
        pred = [card[1] + (VP_TOP_VP + ROW_VP * i + ROW_VP / 2.0 - s) * scale for i in num_rows]
        inside = [p for p in pred if vp_top + 6 <= p <= vp_bot - 6]
        miss = sum(1 for p in inside if min([abs(m - p) for m in meas] or [9999]) > 14)
        extra = max(0, len(meas) - len(inside))
        res = (sum(min(abs(m - p) for p in pred) for m in meas) / float(len(meas))
               if pred else 9999)
        score = res + 400.0 * miss + 120.0 * extra
        if best is None or score < best[1]:
            best = (s, score, res)
        s += 2.0
    return best[0], best[2], meas


def scroll_state(shot, card, scale, tag):
    """量一次滚动状态并点名：S=…vp（残差…px），滚到没到位由 caller 决定。"""
    s, res, meas = measure_scroll(shot, card, scale)
    log("%s 滚动量实测 S=%s vp（残差 %.1fpx，可见按钮 y=%s）"
        % (tag, "?" if s is None else round(s), -1 if res is None else res, meas))
    return s, res, meas


def scroll_to(scrolled, card, scale, tag="SCROLL"):
    """把卡片滚到顶（量到 S≈0）或滚到底（**连着两次量到同一个 S＝再拖不动了＝到底**）。
    2026-10-28 02:54 实测教训：以前的拖拽端点按 `span=视口高×1.6` 算，起点落到 y=2860
    ——**已经掉出面板窗外**（内容底 2674，导航条盖在 2675 以下），uitest 从窗外按下去
    根本不会驱动 Scroll ⇒ 卡片原地不动（截图 S=0），而按 ＋/开关 的坐标是**按「已滚到底」算的**
    ⇒ 第 11 行「默认展开工具栏」那一枪打在 S=0 的第 5 行「按键时振动」上（铁证：
    hilog `SettingsStore: set kbd_haptic=true rev=37`）。
    现在端点夹在视口内，且**闭环**：拖一次量一次，到位才返回；返回的是**实测 S**，
    调用方按它算行心——视口高会随「有没有编码行」在 236/245vp 之间动，所以不硬编 188vp。"""
    cx = (card[0] + card[2]) // 2
    top = card[1] + VP_TOP_VP * scale
    bot = card[1] + VP_BOT_VP * scale
    y_from = bot - 12 if scrolled else top + 12
    y_to = top + 12 if scrolled else bot - 12
    got = None
    prev = None
    for i in range(4):
        if i:
            time.sleep(0.5)
        drag(cx, y_from, cx, y_to)
        time.sleep(0.9)
        shot = h231.screenshot("%s-%d" % (tag, i))
        got, res, _m = scroll_state(shot, card, scale, "%s 第%d次" % (tag, i + 1))
        if got is None:
            continue
        if not scrolled and got <= 3.0:
            return got
        if scrolled and prev is not None and abs(got - prev) < 2.0:
            return got
        prev = got
    log("%s △ 拖了 4 次仍未确认到位（最后一次实测 S=%s）——**按实测值点**，不硬猜" % (tag, got))
    return got


def row_target_S(idx):
    """把行 idx 摆到**视口中线**所需的滚动量（vp），夹在 [0, S_MAX]。
    03:10 实测教训：以前只有「顶/底」两态（S=0/188），以为滚到底＝行 5..11 全可见。
    其实 S=188 时行 5 的中心落在卡片坐标 22vp，比视口顶 34vp 还高 ⇒ **行 5 被标题行盖住**，
    按它 = 按「恢复默认/✕」（危险）。视口 196vp、行距 32vp ⇒ 目标 S = 32i − 82。"""
    return max(0.0, min(S_MAX_VP, ROW_VP * idx - 82.0))


def row_visible(card, scale, s, idx):
    """行 idx 在滚动量 s 下是否**在视口里且留得住手指**（上下各 14px 余量）。"""
    y = card[1] + (VP_TOP_VP + ROW_VP * idx + ROW_VP / 2.0 - s) * scale
    return card[1] + VP_TOP_VP * scale + 14 <= y <= card[1] + VP_BOT_VP * scale - 14


def scroll_to_S(idx, card, scale, tag="SCROLL-S", tries=4):
    """把行 idx 拖进视口（**只要看得见就收手**，不强求摆到正中）。
    03:12 实测两件事：
      ① `uitest drag` 带惯性——拖 315px 内容走了 168vp（≈1.87 倍），所以拖距按
         `FLING_GAIN=0.55` 折算，否则永远在「过头 ↔ 回到顶」之间来回（那一轮 4 次全这样）。
      ② 顶/底两态不够：行 5 在 S=0 就已经可见（视口 196vp＝6.1 行），而 S=188 时它反而被
         标题行盖住——所以判据改成“这一行现在在不在视口里”，不在才拖。"""
    FLING_GAIN = 0.55
    shot = h231.screenshot("%s-0" % tag)
    now, _res, _m = scroll_state(shot, card, scale, "%s 起点" % tag)
    if now is None:
        return None
    if row_visible(card, scale, now, idx):
        return now
    target = row_target_S(idx)
    cx = (card[0] + card[2]) // 2
    top = card[1] + VP_TOP_VP * scale
    bot = card[1] + VP_BOT_VP * scale
    for i in range(tries):
        delta = target - now
        dist = int(max(30.0, min(abs(delta) * scale * FLING_GAIN, (bot - top) - 24.0)))
        if delta > 0:
            drag(cx, bot - 12, cx, bot - 12 - dist)
        else:
            drag(cx, top + 12, cx, top + 12 + dist)
        time.sleep(0.9)
        shot = h231.screenshot("%s-%d" % (tag, i + 1))
        got, _res, _m = scroll_state(shot, card, scale, "%s 第%d次(拖 %dpx 往%s)"
                                            % (tag, i + 1, dist, "上" if delta > 0 else "下"))
        if got is None:
            return now
        now = got
        if row_visible(card, scale, now, idx):
            return now
    log("%s △ %d 次后仍没把行 %d 拖进视口（最后 S=%s）" % (tag, tries, idx, round(now)))
    return now


def close_card_if_open(pr, tag):
    """卡片开着就先关掉（右侧遮罩 → 失败再按标题行 ✕），返回新截图。
    长按空格/回车这个入口**只有在键盘露出来时才按得到**；卡片还开着时那两个坐标落在卡片上，
    长按＝白按，hilog 里不会有 `panel opened`（02:41 那轮就是这么失败的）。"""
    shot = h231.screenshot("%s-card-state" % tag)
    if not pr:
        return shot
    card = find_card_bbox(shot, pr[1])
    if not is_card(card):
        return shot
    x, y = scrim_point(pr, card)
    log("%s 检测到设置卡片开着 ⇒ 点右侧遮罩 (%d,%d) 关掉" % (tag, x, y))
    h231.tap(x, y)
    time.sleep(0.9)
    shot = h231.screenshot("%s-card-state" % tag)
    card2 = find_card_bbox(shot, pr[1])
    if is_card(card2):
        scale = load_state().get("scale") or 3.5
        a2 = anchor_box(card2, scale, tag) or card2
        bx, by = int(a2[2] - 19 * scale), int(a2[1] + 18 * scale)
        log("%s △ 点了遮罩卡片还在 ⇒ 改按标题行 ✕ (%d,%d)" % (tag, bx, by))
        h231.tap(bx, by)
        time.sleep(0.9)
        shot = h231.screenshot("%s-card-state" % tag)
        log("%s ✕ 后卡片还开着? %s" % (tag, is_card(find_card_bbox(shot, pr[1]))))
    else:
        log("%s 遮罩已把卡片关掉" % tag)
    return shot


def cmd_probe():
    setup()
    st, why = h231.locked_state()
    log("LOCK %s：%s" % (st, why))
    c = h231.bring_up()
    if c is None:
        log("PROBE-FAIL 键盘没能起来（不乱点）")
        return 1
    pr = panel_rect()
    # **先确认设置页是关着的**：上一轮跑完卡片还开着 ⇒ 整块白卡片会被当成「键帽」量，
    # 底行定位直接错到 y=2506（2026-10-28 02:39 实测，被 130..190vp 那条自检拦住）。
    shot = close_card_if_open(pr, "PROBE")
    ra = hl(r"H-215 root area", wait=0.2)
    for ln in ra[-2:]:
        log("ROOT-AREA %s" % ln)
    cb = content_bottom_px(shot, pr)
    # 密度＝**像素内容高 ÷ 契约内容高(236vp)**：2026-10-28 02:3x 实测 (2675-1849)/236 = 3.500，
    # 与自家 root area 报的 w=365.71vp↔1280px（＝3.4999）互相印证。
    # 一旦「键盘高度百分比」被改（≠100），内容高就不是 236vp ⇒ 那种漂移**不能**当密度用，
    # 所以缓存优先、并只在漂移 >2% 时点名说明。
    cached = load_state().get("scale")
    meas = (cb - pr[1]) / 236.0 if pr and cb > pr[1] else None
    scale = cached or meas
    if meas and cached and abs(meas - cached) / cached > 0.02:
        log("密度：像素法 %.4f 与缓存 %.4f 差 >2%% ⇒ 这是**键高被改了**（不是屏幕变了），"
            "几何仍按缓存算，像素法那个数留给 kbd_height_pct 当判据" % (meas, cached))
    log("PANEL RECT [x,y,w,h]=%s 内容底=%d PX/VP=%.4f（像素法 %.4f／缓存 %.4f／root area %s）"
        % (pr, cb, scale or 0, meas or 0, cached or 0,
           (re.search(r"w=([\d.]+)", ra[-1]).group(1) if ra and re.search(r"w=([\d.]+)", ra[-1]) else "?")))
    space = enter = None
    if pr and scale:
        # 量不到底行时**先自救再停手**：网格没折叠（collapse_grid）／输入法面板挂着残留态
        # （bring_up 重连）都是可恢复的，直接 return 1 会让每一项都写成「开页失败」假结论。
        for attempt in (0, 1, 2):
            space, enter, cb = locate_bottom_row(shot, pr, scale)
            if space:
                break
            if attempt == 0:
                shot = collapse_grid(pr, scale)
            elif attempt == 1:
                log("PROBE-RETRY 折叠后仍量不到 ⇒ 重新拉起键盘（清 IME 面板残留态）")
                if h231.bring_up() is None:
                    break
                pr = panel_rect()
                shot = close_card_if_open(pr, "PROBE-RETRY")
                cb = content_bottom_px(shot, pr)
        if not space:
            return 1
        log("空格中心=%s 回车中心=%s（内容底=%d）" % ([int(v) for v in space], [int(v) for v in enter], cb))
    h231.zoom_crop(shot, [pr[0], pr[1], pr[0] + pr[2], cb], 1,
                   os.path.join(EVID, "probe-panel.png"))
    # 四行键的中心 y：内容底往上，每行 48vp（=168px），行心＝底 - 24vp - n×48vp。
    # 2026-10-28 02:3x 实拍核对：算得 2087/2255/2423/2591，像素带 2016-2160 / 2189-2329 /
    # 2349-2489 / 2516-2660 的中心 2088/2259/2419/2588 ⇒ 逐行差 ≤8px（键帽本身 42vp 高，容差够）。
    rows_y = [cb - int(24 * scale) - n * int(48 * scale) for n in (3, 2, 1, 0)]
    log("四行键中心 y=%s" % rows_y)
    save_state({"panel": pr, "scale": scale, "space": space, "enter": enter,
                "content_bottom": cb, "content_h_px": cb - pr[1], "rows_y": rows_y,
                "probe_shot": shot})
    log("PROBE-DONE %s" % shot)
    return 0


def cmd_entry():
    setup()
    st = load_state()
    if not st.get("space"):
        log("ENTRY-ABORT 先跑 probe")
        return 1
    x, y = st["space"]
    if not h231.guard("long-press-space"):
        return 1
    close_card_if_open(st.get("panel"), "ENTRY")
    hl("never-match-x", clear=True)
    long_press(x, y)
    log("对空格中心 (%d,%d) 注入 longClick" % (x, y))
    fired = hl(r"H-241 long-press space", wait=1.0)
    opened = hl(r"H-241 settings panel opened", wait=0.2)
    sup = hl(r"H-241 suppress click", wait=0.2)
    for ln in (fired + opened + sup)[-6:]:
        log("HILOG %s" % ln)
    shot = h231.screenshot("entry-settings-open")
    box = find_card_bbox(shot, st["panel"][1])
    log("入口后截图=%s fired=%d opened=%d suppress=%d 卡片=%s 像卡片=%s"
        % (shot, len(fired), len(opened), len(sup), box, is_card(box)))
    if is_card(box):
        h231.zoom_crop(shot, box, 2, os.path.join(EVID, "entry-card.png"))
    dump_hlog("entry")
    save_state({"entry_fired": bool(fired), "entry_opened": bool(opened),
                "entry_suppress": bool(sup), "entry_shot": shot, "card": box})
    return 0 if fired and opened else 2


def cmd_card():
    setup()
    st = load_state()
    scale = st.get("scale")
    shot, box = ensure_open()
    if not box or not scale:
        log("CARD-ABORT 卡片没开（先跑 entry）box=%s scale=%s" % (box, scale))
        return 1
    save_state({"card": box})
    log("CARD bbox=%s（宽 %dpx=%.1fvp，高 %dpx=%.1fvp）"
        % (box, box[2] - box[0], (box[2] - box[0]) / scale, box[3] - box[1], (box[3] - box[1]) / scale))
    buttons = find_step_buttons(shot, box)
    pred = [row_center_y(box, scale, i, False) for i in (0, 1, 2, 3)]
    log("S=0 实测步进按钮中心 y=%s | 公式预测 行0..3=%s"
        % (buttons, [int(v) for v in pred]))
    for i in range(4):
        h231.zoom_crop(shot, [box[0], int(box[1] + (VP_TOP_VP + ROW_VP * i - 2) * scale),
                              box[2], int(box[1] + (VP_TOP_VP + ROW_VP * (i + 1) + 2) * scale)],
                       3, os.path.join(EVID, "card-row-%02d.png" % i))
    # 滚到底再看后 8 行（**滚动量以实测为准**，公式里的 S 用量出来的那个）
    S2 = scroll_to(True, box, scale, tag="CARD")
    S2 = S_MAX_VP if S2 is None else S2
    shot2 = h231.screenshot("card-scrolled")
    box2 = find_card_bbox(shot2, st["panel"][1])
    box2 = anchor_box(box2, scale, "CARD-BOT") if is_card(box2) else box
    box2 = box2 or box
    buttons2 = find_step_buttons(shot2, box2)
    pred2 = [box2[1] + (VP_TOP_VP + ROW_VP * i + ROW_VP / 2.0 - S2) * scale for i in (5, 7, 8, 9)]
    log("S=%s（实测）步进按钮中心 y=%s | 公式预测 行5/7/8/9=%s"
        % (round(S2), buttons2, [int(v) for v in pred2]))
    for i in (5, 6, 7, 8, 9, 10, 11):
        h231.zoom_crop(shot2, [box2[0], int(box2[1] + (VP_TOP_VP + ROW_VP * i - S2 - 2) * scale),
                               box2[2], int(box2[1] + (VP_TOP_VP + ROW_VP * (i + 1) - S2 + 2) * scale)],
                       3, os.path.join(EVID, "card-row-%02d.png" % i))
    scroll_to(False, box2, scale, tag="CARD-BACK")
    h231.screenshot("card-at-top")
    err = [abs(a - b) for a, b in zip(buttons, pred)]
    log("CARD 几何残差(px)=%s —— >12 就别用公式，改按实测" % err)
    save_state({"card_buttons_top": buttons, "card_buttons_bottom": buttons2})
    return 0


def cmd_tap(key, n):
    setup()
    try:
        n = int(n)                                # 命令行传进来是字符串，items.bump 也转手传字符串
    except (TypeError, ValueError):
        n = 1
    st = load_state()
    scale = st.get("scale")
    if key not in IDX or not scale:
        log("TAP-ABORT 键 %s 不在表里或没几何" % key)
        return 1
    if not h231.guard("tap-" + key):
        return 1
    shot, box = ensure_open()
    if not box:
        log("TAP-ABORT 设置页没开（先 entry）")
        return 1
    save_state({"card": box})
    idx = IDX[key]
    kind = KIND[key]
    tgt_S = row_target_S(idx)
    got_S = scroll_to_S(idx, box, scale, tag="TAP[%s]" % key)
    shot = h231.screenshot("pre-tap-%s" % key)
    if got_S is None:
        log("TAP-ABORT[%s] 滚动量量不到（卡里一个 ＋ 按钮都没认出来）⇒ 不动手" % key)
        return 3
    # **按实测滚动量**算行心，不按「我以为滚到哪了」——02:54 那一枪就是这么打偏到第 5 行的
    y = int(box[1] + (VP_TOP_VP + ROW_VP * idx + ROW_VP / 2.0 - got_S) * scale)
    vp_top = box[1] + VP_TOP_VP * scale
    vp_bot = box[1] + VP_BOT_VP * scale
    if not (vp_top + 10 <= y <= vp_bot - 10):
        log("TAP-ABORT[%s] 行 %d 在 S=%s 下落到 y=%d，不在视口 [%d,%d] ⇒ 这行现在点不到，停手"
            % (key, idx, round(got_S), y, vp_top, vp_bot))
        return 3
    right = box[2]
    if kind == "num":
        # 从卡片右边往内：padding 10 ＋ ＋28  间距 6 ＋ 数值 54 ＋ 间距 6 ＋ －28
        # ⇒ ＋ 心 = 右-24vp，－ 心 = 右-112vp（旧值 118 也在 － 的框内，顺手改准）
        x = int(right - (24 if n >= 0 else 112) * scale)
    else:
        x = int(right - 20 * scale)
    meas = find_step_buttons(shot, box)
    near = min([abs(m - y) for m in meas] or [999])
    log("TAP[%s] idx=%d 目标S=%s 实测S=%s 预测 y=%d（%s 行，最近按钮实测差 %.0fpx）"
        % (key, idx, round(tgt_S), round(got_S), y, kind, near))
    if kind == "num" and near > 14:
        log("TAP-ABORT[%s] 预测与实测对不上（%.0fpx），不动手——先跑 card 核几何" % (key, near))
        return 3
    times = abs(int(n)) if kind == "num" else 1
    before = hl(r"SettingsStore: set %s=" % re.escape(key), wait=0.1)
    before_any = hl(r"SettingsStore: set ", wait=0.1)
    for i in range(times):
        h231.tap(x, y)
        time.sleep(0.5)
    after = hl(r"SettingsStore: set %s=" % re.escape(key), wait=0.6)
    after_any = hl(r"SettingsStore: set ", wait=0.1)
    mine = after[len(before):]
    wrong = [ln for ln in after_any[len(before_any):] if key not in ln]
    for ln in mine[-4:]:
        log("HILOG %s" % ln)
    for ln in wrong[-3:]:
        log("HILOG-打偏 %s" % ln)
    synced = hl(r"H-241 settings synced", wait=0.3)
    for ln in synced[-1:]:
        log("HILOG %s" % ln)
    shot = h231.screenshot("after-tap-%s" % key)
    save_state({"last_tap": {"key": key, "n": n, "mine": mine, "wrong": wrong,
                             "synced": synced[-1] if synced else "", "shot": shot}})
    dump_hlog("tap-%s" % key)
    log("TAP[%s] 本键写侧日志 +%d，打偏 +%d" % (key, len(mine), len(wrong)))
    return 0 if mine and not wrong else 2


def find_reset_button(shot, card, scale):
    """在标题行里**用暗像素团**定位「恢复默认」的中心，不按字号猜坐标。
    标题行 = 卡片顶 + 6vp 内边距起、高 24vp；里面从左到右是「设置」(粗体)、「恢复默认」、✕。
    「恢复默认」四个字最宽（≈4×12fp），所以取**右半区里最宽的那一团**＝它。"""
    from PIL import Image
    im = Image.open(shot).convert("RGB")
    px = im.load()
    y1 = int(card[1] + 6 * scale)
    y2 = int(card[1] + 30 * scale)
    xs = []
    for x in range(card[0], card[2] + 1):
        for y in range(y1, y2):
            r, g, b = px[x, y]
            if (r + g + b) / 3.0 < 150:
                xs.append(x)
                break
    if not xs:
        return None
    groups = []
    cur = [xs[0], xs[0]]
    for x in xs[1:]:
        if x - cur[1] > 8:
            groups.append(tuple(cur))
            cur = [x, x]
        else:
            cur[1] = x
    groups.append(tuple(cur))
    mid = (card[0] + card[2]) / 2.0
    right = [gp for gp in groups if (gp[0] + gp[1]) / 2.0 > mid]
    if not right:
        return None
    best = max(right, key=lambda gp: gp[1] - gp[0])
    cx = (best[0] + best[1]) / 2.0
    log("RESET 定位：标题行暗团=%s → 取右半最宽 %s 中心 x=%.0f y=%.0f"
        % (groups, best, cx, (y1 + y2) / 2.0))
    return [int(cx), int((y1 + y2) / 2.0)]


def cmd_reset():
    """点「恢复默认」把 12 项全部写回默认，并**用日志证明点到了**。
    契约 §5 要求取证跑完把设备留在默认口径上；这一步就是收尾（也是 run-all 的开跑前提）。"""
    setup()
    st = load_state()
    scale = st.get("scale")
    if not scale:
        log("RESET-ABORT 先跑 probe")
        return 1
    if not h231.guard("reset"):
        return 1
    shot, box = ensure_open()
    if not box:
        log("RESET 卡片没开 ⇒ 长按空格开一次")
        if not st.get("space"):
            return 1
        close_card_if_open(st.get("panel"), "RESET")
        hl("never-match-x", clear=True)
        long_press(*st["space"])
        if not hl(r"H-241 settings panel opened", wait=1.0):
            log("RESET-ABORT 卡片开不起来")
            return 1
        shot, box = ensure_open()
        if not box:
            # 2026-10-28 04:1x 逃生道（和 `h241_settings_items.row0_press` 同一个理由）：
            # `ensure_open` 的 236vp 锚点前提是「键高 100%」，而**上一项跑崩在半路**时偏偏就是
            # 键高不是 100%——那种时候最需要做的正是这一步「恢复默认」。
            # 标题行只认「卡片顶 +6..30vp 里右半区最宽的一团暗像素」，不吃行公式，
            # 所以这里允许退回**未校正的原始框**；点行（`cmd_tap`）仍然必须有锚点，不放水。
            raw = find_card_bbox(shot, (st.get("panel") or [0, 0, 0, 0])[1])
            if is_card(raw):
                log("RESET 锚点不成立（键高不是 100%%）⇒ 退回原始卡片框 %s，只点标题行" % (raw,))
                box = raw
            else:
                log("RESET-ABORT 卡片开了但量不到框")
                return 1
    btn = find_reset_button(shot, box, scale)
    if not btn:
        log("RESET-ABORT 标题行没找到「恢复默认」")
        return 1
    before = hl(r"reset all to defaults", wait=0.1)
    h231.tap(btn[0], btn[1])
    time.sleep(1.2)
    fired = hl(r"reset all to defaults", wait=0.6)
    synced = hl(r"H-241 settings synced", wait=0.4)
    for ln in fired[-2:]:
        log("HILOG %s" % ln)
    for ln in synced[-1:]:
        log("HILOG %s" % ln)
    new = len(fired) > len(before)
    log("RESET 点 (%d,%d) → 写侧日志 %s，末次同步=%s"
        % (btn[0], btn[1], "已到" if new else "没到", synced[-1][-90:] if synced else "无"))
    dump_hlog("reset")
    return 0 if new else 2


def cmd_close():
    setup()
    st = load_state()
    pr = st.get("panel")
    if not pr:
        return 1
    if not h231.guard("close-card"):
        return 1
    before = find_card_bbox(h231.screenshot("before-close"), pr[1])
    x, y = scrim_point(pr, before if is_card(before) else None)
    h231.tap(x, y)
    time.sleep(0.9)
    shot = h231.screenshot("after-close")
    still = find_card_bbox(shot, pr[1])
    log("CLOSE 点 (%d,%d) → 卡片还开着? %s（原始框 %s，竖向 %s px）"
        % (x, y, is_card(still), still, (still[3] - still[1]) if still else 0))
    save_state({"card_open": is_card(still)})
    return 0 if not is_card(still) else 2


def cmd_open_again():
    setup()
    return cmd_entry()


def cmd_check():
    setup()
    st = load_state()
    pr = panel_rect()
    log("PANEL=%s 缓存=%s" % (pr, bool(st.get("panel"))))
    if pr and st.get("panel") and pr != st.get("panel"):
        log("面板窗几何变了（%s → %s）——高度类设置的证据就在这种差分里" % (st.get("panel"), pr))
        # **别拿 pr[3]/236 当密度**：WMS 的 983 含了 157px 黑导航条，算出来 4.1653 是假的
        # （02:3x 实测：按它点空格会点到黑条里）。密度只认像素内容高/缓存。
        save_state({"panel": pr})
    shot, box = ensure_open()
    log("卡片当前=%s" % box)
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    c = sys.argv[1]
    if c == "probe":
        return cmd_probe()
    if c == "entry":
        return cmd_entry()
    if c == "card":
        return cmd_card()
    if c == "tap":
        return cmd_tap(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "1")
    if c == "close":
        return cmd_close()
    if c == "reset":
        return cmd_reset()
    if c == "reopen":
        return cmd_open_again()
    if c == "check":
        return cmd_check()
    print("未知子命令 %s" % c)
    return 1


if __name__ == "__main__":
    sys.exit(main())
