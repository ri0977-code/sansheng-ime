#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-241 契约 12 项「改前 / 改后」真机逐项取证（Qoder，2026-10-28 02:4x 起）

口径来自 `docs/SETTINGS-CONTRACT.md` §5-4：**每项改前/改后各量一次**（像素或 hilog），
取证落 `docs/evidence/2026-10-28/h239-settings-<key>/`，**带键名、不许同名覆盖**（H-238 踩过）。

量具复用 `scripts/h241_settings_device_check.py`（入口/卡片几何/写值那一套，已实机验过：
长按空格 600ms → `H-241 long-press space 600ms -> settings` ＋ 卡片像素 12 行）。

只在**自家 App**（com.sansheng.ime 的测试输入框）里打字，绝不碰主人的文档；
每一步前都过 `guard()`（已解锁＋前台是自家 App）。

用法：
  python scripts/h241_settings_items.py list                 # 看有哪些项、判据是什么
  python scripts/h241_settings_items.py run key_font_size    # 单项
  python scripts/h241_settings_items.py run-all              # 全 12 项（约 25 分钟）

**r3 口径更正（2026-10-28 03:4x，Qoder，全部来自真机实测，不是推测）**：
  ① 出泡判据的日志串：契约盯 `H-215 timer open bubble`，实测注入 longClick 走的是兜底手势，
     屏上真出泡、日志打的是 `LetterKey longpress q -> bubble` ＋ `H-215 v7 bubble q win …`，
     松手打 `H-215 cancel q`。老串**历史上一次都没出现过**（grep 全 docs/evidence 只有判据文本）。
     ⇒ 判据改盯三条并集（`BUBBLE_PAT`），诊断脚本 `scripts/h241_diag_bubble.py`。
  ② §3-6「700ms 不出泡」这条注入做不出来：longClick 的持按实测 ≈1.4s（出泡→松手 950ms ＋ 阈值 450），
     比阈值上限 700 还长 ⇒ 700 也一定出泡。改成**同一支笔下比「出泡→松手」的时长差**：
     阈值 300 比 700 应当长 ~400ms，两个时间戳同一台设备同一个时钟，不受时钟偏移影响。
  ③ §3-4 的 `setPageSize=` 只匹配引擎侧；UI 侧真实格式是 `setPageSize(9)`（KeyboardIndex.ets:1165）
     ⇒ 老判据永远「没有 setPageSize 行」。改成 `setPageSize[=(](\d+)` 取**数字**比对。
  ④ §3-9 上一版只要求「两次 hilog 文本不同」，两条都是 50 也算 PASS ⇒ 假阳性。改成要求
     序列里真的出现 20。
  ⑤ 候选带/L1 带不再按「窗顶＋44vp 顶栏」硬算（44vp 是**候选栏容器**，它上面没有顶栏；
     工具栏展开时又把整容器占掉）⇒ 改成从截图里自动检出（`_bands`），两帧同一带才可比。
     老算法量到的全是空白（暗像素=0），把 cand_font_size/show_preedit/page_size 三项误判成「未达判据」。
  ⑥ `set_to` 一下一停、每按下回读：离散表（page_size 3/5/7/9）按固定步长连按会越过目标来回振荡。
  ⑦ §3-12 `show_preedit` 又一次假阴性（r4 修）：带检出了（[8,1870,630,1891]）却量到 ink=0，
     因为 `_bands` 用阈值 170、`ink_stats` 默认 120，而 **L1 编码行的字是浅灰**（背景 243、
     笔画均值落在 120..170 之间）。⇒ 「检带」和「量带内暗像素」必须用同一个阈值；本项改用 170，
     实测同一批帧 开=585 / 关=0 / 再开=585（＝产品一直是好的）。候选行的字是深灰（<120 有 7570 个），
     所以 §3-2 沿用 120 没问题。
"""
import os
import re
import sys
import time
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h231_panel_check as h231                      # noqa: E402
import h241_settings_device_check as drv             # noqa: E402

ROOT = drv.ROOT
BASE = drv.BASE
LETTERS_ROW1 = "qwertyuiop"
LETTERS_ROW2 = "asdfghjkl"
LETTERS_ROW3 = "zxcvbnm"


def st():
    return drv.load_state()


def refresh():
    """重量面板几何（打字/改键高都会让行位置移动，缓存的 y 不能一路用到尾）。"""
    drv.cmd_probe()


def item_dir(key):
    d = os.path.join(BASE, "h239-settings-%s" % key)
    os.makedirs(d, exist_ok=True)
    return d


def uniq(d, name, ext="png"):
    """不许同名覆盖：已存在就加 -r2/-r3（H-238 的教训）。"""
    p = os.path.join(d, "%s.%s" % (name, ext))
    i = 2
    while os.path.exists(p):
        p = os.path.join(d, "%s-r%d.%s" % (name, i, ext))
        i += 1
    return p


def shot(key, name):
    """截屏并**直接落到该项的取证目录**（文件名带阶段，不覆盖）。"""
    d = item_dir(key)
    tmp = h231.screenshot("tmp-%s" % name)
    out = uniq(d, name, "jpeg")
    if tmp and os.path.exists(tmp):
        os.replace(tmp, out)
    drv.log("SHOT[%s] %s" % (key, out))
    return out


def zoom(key, name, box, scale=2):
    d = item_dir(key)
    src = h231.screenshot("tmpz-%s" % name)
    out = uniq(d, name, "png")
    h231.zoom_crop(src, [int(v) for v in box], scale, out)
    drv.log("ZOOM[%s] %s box=%s" % (key, out, [int(v) for v in box]))
    return out, src


def hl(pattern, wait=0.8, clear=False):
    return drv.hl(pattern, clear=clear, wait=wait)


def hlog_save(key, name):
    p = uniq(item_dir(key), name, "txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(h231.sh("shell", "hilog", "-x"))
    return p


def verdict(key, lines):
    """每项一份 `verdict.txt`：判据、改前值、改后值、量到的数、结论。"""
    d = item_dir(key)
    p = uniq(d, "verdict", "txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write("H-241 契约 §3 「%s」真机取证（Qoder %s）\n\n" % (key, time.strftime("%H:%M")))
        f.write("\n".join(lines) + "\n")
    drv.log("VERDICT[%s] -> %s" % (key, p))
    for ln in lines[-6:]:
        drv.log("  | %s" % ln)
    return p


# ---- 通用动作：开设置页 → 改一项 → 关 ----

SYNCED_MAP = {"keyFs": "key_font_size", "candFs": "cand_font_size", "lpp": "key_long_press_delay",
              "popup": "popup_on_key_press", "haptic": "kbd_haptic", "preedit": "show_preedit",
              "grid": "grid_page_size", "step": "space_swipe_step", "pageSize": "page_size"}
PRE_OPEN = {}


def snapshot_settings(reason):
    """`open_settings()` 清 hilog 缓冲**之前**，把 12 项现值抄一份进 `PRE_OPEN`。

    2026-10-28 04:29 实测教训（`undo_stack_limit` 收尾）：开页会把缓冲清掉 ⇒ `current_value()`
    读不到 ⇒ 走「按契约默认 10 起步」的兜底 ⇒ 判「现值已是 10 ⇒ 不按」，**而设备实际停在 6**。
    每一项的收尾恢复都建立在这条谎话上，等于整轮跑完设备全不在默认口径（下一轮起点又未知）。
    而应用自己在每次写成功后都会打一条全量 `H-241 settings synced: keyFs=… h=105%`，
    **缓冲里最后那条就是现值**——所以「清之前抄一次」比「清之后猜默认」诚实。
    `undo_stack_limit` 不在这条里，从 `applySettingsChanged: … undoLimit=NN` 末条取；
    `expand_toolbar_by_default` 两处都没有 ⇒ 快照里没有它，仍旧只能走默认兜底（已知缺口，记在契约里）。"""
    PRE_OPEN.clear()
    lines = drv.hl(r"settings synced|applySettingsChanged", wait=0.3)
    for ln in reversed(lines):
        if "settings synced" in ln:
            for k, v in re.findall(r"(\w+)=([-\w.%]+)", ln):
                if k == "h":
                    PRE_OPEN["kbd_height_pct"] = float(v.rstrip("%"))
                elif k in SYNCED_MAP:
                    PRE_OPEN[SYNCED_MAP[k]] = (1.0 if v == "true" else 0.0) if v in ("true", "false") else float(v)
            break
    for ln in reversed(lines):
        m = re.search(r"undoLimit=(\d+)", ln)
        if m:
            PRE_OPEN["undo_stack_limit"] = float(m.group(1))
            break
    drv.log("SNAPSHOT[%s] 抄到 %d 项 %s" % (reason, len(PRE_OPEN), dict(sorted(PRE_OPEN.items()))))
    return dict(PRE_OPEN)


def open_settings():
    s = st()
    if not s.get("space"):
        refresh()
        s = st()
    if not h231.guard("open-settings"):
        return False
    # 卡片还开着时空格/回车被遮在底下，长按＝白按（02:41 实测）。先确保是关的。
    drv.close_card_if_open(s.get("panel"), "ITEMS-OPEN")
    snapshot_settings("pre-open")
    drv.hl("never-match-x", clear=True)
    drv.long_press(*s["space"])
    ok = bool(hl(r"H-241 settings panel opened", wait=1.0))
    drv.log("OPEN-SETTINGS %s" % ("OK" if ok else "失败（没报 panel opened）"))
    return ok


def close_settings():
    s = st()
    pr = s["panel"]
    if not h231.guard("close-settings"):
        return
    before = drv.find_card_bbox(h231.screenshot("tmp-close-before"), pr[1])
    if not drv.is_card(before):
        # 2026-10-28 04:2x：卡片本来就没开时，那个「遮罩点」(x≈右缘, y≈键区第 2 行) 是**落在键盘上的一枪**
        # ——遮罩没了，点下去会打进输入框。以前每轮收尾都白按一次，只是恰好点在没接线的边上。
        drv.log("CLOSE-SETTINGS 卡片本来就没开（原始框 %s）⇒ 不按这一下" % (before,))
        return True
    x, y = drv.scrim_point(pr, before)
    h231.tap(int(x), int(y))                          # 卡片左对齐 ⇒ 遮罩露在**右侧**那条带
    time.sleep(0.8)
    shot_after = h231.screenshot("tmp-close")
    still = drv.find_card_bbox(shot_after, pr[1])
    drv.log("CLOSE-SETTINGS 点 (%d,%d) 卡片还开着? %s（原始框 %s）"
            % (x, y, drv.is_card(still), still))
    return not drv.is_card(still)


def bump(key, n):
    """在设置页里把 key 改 n 档（n<0 往小）。返回写侧 hilog 行。"""
    return drv.cmd_tap(key, str(n))


DEFAULTS = {"kbd_height_pct": 100, "cand_font_size": 18, "key_font_size": 20, "page_size": 5,
            "key_long_press_delay": 450, "undo_stack_limit": 10, "grid_page_size": 50,
            "space_swipe_step": 10}          # ＝ SettingsStore.ets 的 mkNum(def)…，run-all 开跑前先「恢复默认」


def set_to(key, target, max_presses=20):
    """在**已打开**的设置页里把 key 走到 target。

    2026-10-28 03:4x 定稿（两条实测教训）：
      ① `open_settings()` 为了差分计数会清 hilog ⇒ `current_value()` 读不到上一轮写的值，
         旧代码在这里 `return None`，**一次 ＋/－ 都没按**，判据却写成「阈值 450/700/300 三档
         出泡条数都是 0」，看着像功能没生效，其实是根本没改值。⇒ 读不到时按契约默认起步，
         并在 log 里点名是兜底（单独跑某一项时起点未知，这条兜底会偏）。
      ② 不能用「固定步长 × 一次按 N 下」：`page_size` 是离散表 [3,5,7,9]，从 5 按 4 下 ＋
         会夹在 9；反过来从 9 走回 5 会越过 5 掉到 3，来回振荡。
         ⇒ 改成**一下一停、每按下回读一次**，到值就停、值卡住不动（＝到边界）也停。"""
    cur = current_value(key)
    if cur is None:
        if key not in DEFAULTS:
            drv.log("SET[%s] 读不到现值且不在默认表里 ⇒ 不动" % key)
            return None
        cur = DEFAULTS[key]
        drv.log("SET[%s] hilog 读不到现值（多半是开页时清过）⇒ 按契约默认 %s 起步" % (key, cur))
    got = cur
    if got == target:
        drv.log("SET[%s] 现值已是 %s ⇒ 不按" % (key, got))
        return got
    for i in range(max_presses):
        direction = 1 if target > got else -1
        bump(key, direction)
        back = current_value(key)
        if back is None:
            drv.log("SET[%s] 按了 %d 下读不回值 ⇒ 停手（不盲按）" % (key, i + 1))
            break
        if back == got:
            drv.log("SET[%s] 按到 %s 不动了（＝到边界）目标 %s 到不了 ⇒ 停手" % (key, back, target))
            got = back
            break
        got = back
        if got == target:
            break
    drv.log("SET[%s] 写侧回读=%s（目标 %s）" % (key, got, target))
    return got


def row0_press(key, direction):
    """按**一次**第 0 行（`kbd_height_pct`）的 ＋/－：纯像素认按钮，**每按一次重新认一次**。

    为什么要单独有一条路（2026-10-28 04:1x 定稿）：通用 `cmd_tap` 走 `ensure_open()` → `card_anchor()`，
    那道闸的前提是「卡片高＝236vp ⇔ 键高 100%」。而这一项的判据恰恰要求把键高推离 100%：
    实测按到 105% 卡片已经变 802/894px，第 3 下必然 ANCHOR-ABORT（04:10 那次就是这么停在 110 的）。
    锚点是防「点错行」的，对**唯一一行、且 S=0 首屏最上面一条**的场合不需要它，所以撤得有边界。
    返回按下后从 hilog 读回的新值；认不出卡片/按钮、或这一下没写出日志 ⇒ None（**绝不盲按**）。"""
    s = st()
    scale = s.get("scale")
    if not scale:
        drv.log("ROW0 没有 scale（先跑 probe）⇒ 不动手")
        return None
    pr = h231.panel_rect()
    sh = h231.screenshot("row0-card")
    box = drv.find_card_bbox(sh, pr[1])
    if not drv.is_card(box):
        drv.log("ROW0 卡片框不像卡片（%s）⇒ 不动手" % (box,))
        return None
    btns = drv.find_step_buttons(sh, box)
    if not btns:
        drv.log("ROW0 卡里一条按钮都没认出来 ⇒ 不动手")
        return None
    y0 = int(btns[0])
    x = int(box[2] - (24 if direction > 0 else 112) * scale)
    if not h231.guard("row0"):
        return None
    drv.log("ROW0 卡片=%s 按钮=%s ⇒ 第 0 行按%s (%d,%d)"
            % (box, btns, "＋" if direction > 0 else "－", x, y0))
    hl(r"SettingsStore: set %s=" % re.escape(key), clear=True, wait=0.3)
    h231.tap(x, y0)
    time.sleep(1.1)
    lines = hl(r"SettingsStore: set %s=" % re.escape(key), wait=0.3)
    if not lines:
        drv.log("ROW0 这一下没写出 set 日志 ⇒ 停手")
        return None
    m = re.search(r"set %s=([-\d.]+)" % re.escape(key), lines[-1])
    if not m:
        drv.log("ROW0 日志读不出数值：%s" % lines[-1])
        return None
    drv.log("ROW0 -> %s=%s" % (key, m.group(1)))
    return float(m.group(1))


def set_to_row0(key, target, max_presses=6, assume=None):
    """把第 0 行走到 `target`（走 `set_to` 那条通用路会 ANCHOR-ABORT，见 `row0_press`）。
    起点优先用调用方在**开页清日志之前**抓的 `assume`；其次 hilog；都没有才按契约默认。"""
    got = assume if assume is not None else current_value(key)
    if got is None:
        got = DEFAULTS.get(key, 100)
        drv.log("SET0[%s] 读不到现值 ⇒ 按契约默认 %s 起步" % (key, got))
    if got == target:
        drv.log("SET0[%s] 现值已是 %s ⇒ 不按" % (key, got))
        return got
    for _ in range(int(max_presses)):
        back = row0_press(key, 1 if target > got else -1)
        if back is None:
            break
        if back == got:
            drv.log("SET0[%s] 按到 %s 不动了（＝到边界），目标 %s 到不了 ⇒ 停手" % (key, back, target))
            break
        got = back
        if got == target:
            break
    drv.log("SET0[%s] 写侧回读=%s（目标 %s）" % (key, got, target))
    return got


def row0_start_value(key):
    """开页**之前**（`open_settings()` 会清 hilog 缓冲）从缓冲里抓键高现值。

    2026-10-28 04:19 实测教训：这条不抓，`set_to_row0` 只能走「读不到 ⇒ 按默认 100 起步」的兜底，
    而设备当时实际停在 110% ⇒ 少按两档（100→「以为」→实按 115→120），
    收尾更误判「现值已是 100 ⇒ 不按」⇒ 设备一路留在非默认，下一项 `cmd_tap` 直接 ANCHOR-ABORT。
    03:5x、04:10 两次死锁的共同根因就是这里。两个来源都认：写侧 `set kbd_height_pct=NN`、
    同步侧 `H-241 settings synced: … h=NN%`。"""
    lines = hl(r"SettingsStore: set kbd_height_pct=|settings synced", wait=0.3)
    vals = []
    for ln in lines:
        m = re.search(r"set kbd_height_pct=([-\d.]+)", ln) or re.search(r" h=(\d+(?:\.\d+)?)%", ln)
        if m:
            vals.append(float(m.group(1)))
    if vals:
        drv.log("SET0-START[%s] 开页前缓冲里读到现值=%s（来源=%s）"
                % (key, vals[-1], lines[-1][-58:]))
        return vals[-1]
    drv.log("SET0-START[%s] 开页前缓冲里没有键高行 ⇒ 交给默认兜底（会有偏差，见 docstring）" % key)
    return None


def row0_home(max_presses=8):
    """收尾用**几何**把键高量回 100%：面板窗高默认实测 983px（110% 是 1050、120% 是 1117，
    每 5% ≈ 33px），偏差 >10px 就按一档 －/＋ 再量。日志兜底会说谎（见 `row0_start_value`），
    窗高不会——这项改的本来就是窗高。"""
    if not open_settings():
        return False
    for i in range(int(max_presses)):
        close_settings()
        pr = h231.panel_rect()
        if not pr:
            drv.log("HOME0 量不到面板矩形 ⇒ 停手")
            return False
        d = pr[3] - 983
        if abs(d) <= 10:
            drv.log("HOME0 面板窗高 %dpx（默认 983，差 %+d）⇒ 已回 100%%，用了 %d 次修正" % (pr[3], d, i))
            refresh()   # 04:24 实测：归位改了键高 ⇒ 缓存的空格/回车心全是 120% 时代的，
                        # 不重量下一步 `open_settings()` 就长按在空处（报「没报 panel opened」）。
            return True
        if not open_settings():
            return False
        if row0_press("kbd_height_pct", -1 if d > 0 else 1) is None:
            return False
    drv.log("HOME0 修正 %d 次仍没回到 983±10px ⇒ 交给人看" % max_presses)
    return False


def current_value(key):
    """从最近一条 `SettingsStore: set <key>=<v>` 或 `settings synced` 里取值。"""
    lines = hl(r"SettingsStore: set %s=" % re.escape(key), wait=0.2)
    if lines:
        m = re.search(r"set %s=([-\d.]+)" % re.escape(key), lines[-1])
        if m:
            return float(m.group(1))
    if key in PRE_OPEN:
        drv.log("VALUE[%s] 实时缓冲里没有写侧行 ⇒ 用开页前快照=%s（见 `snapshot_settings`）"
                % (key, PRE_OPEN[key]))
        return PRE_OPEN[key]
    return None


# ---- 像素量法 ----

def ink_stats(path, box, dark=120):
    """框内暗像素数与纵向跨度（＝字形高度）。"""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    px = im.load()
    x1, y1, x2, y2 = [int(v) for v in box]
    xs = []
    ys = []
    n = 0
    for y in range(max(0, y1), min(im.size[1], y2)):
        for x in range(max(0, x1), min(im.size[0], x2)):
            r, g, b = px[x, y]
            if (r + g + b) / 3.0 < dark:
                n += 1
                xs.append(x)
                ys.append(y)
    if not n:
        return {"ink": 0, "h": 0, "w": 0}
    return {"ink": n, "h": max(ys) - min(ys) + 1, "w": max(xs) - min(xs) + 1,
            "top": min(ys), "bot": max(ys)}


def key_box(letter, pad=0.86):
    """某个字母键的键帽框（屏幕 px）。行 y 用最近一次 refresh 的 rows_y。"""
    s = st()
    rows = s["rows_y"]
    pr = s["panel"]
    scale = s["scale"]
    if letter in LETTERS_ROW1:
        i = LETTERS_ROW1.index(letter)
        cx = pr[0] + 64 + i * 128
        cy = rows[0]
    elif letter in LETTERS_ROW2:
        i = LETTERS_ROW2.index(letter)
        cx = pr[0] + 128 + i * 128
        cy = rows[1]
    elif letter in LETTERS_ROW3:
        i = LETTERS_ROW3.index(letter)
        cx = pr[0] + 192 + i * 128
        cy = rows[2]
    else:
        return None
    hw = 64 * pad
    hh = 24 * scale * pad
    return [cx - hw, cy - hh, cx + hw, cy + hh]


def tap_letter(letter):
    b = key_box(letter, 0.9)
    if not b or not h231.guard("tap-" + letter):
        return False
    h231.tap((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    time.sleep(0.35)
    return True


def type_word(word):
    drv.log("TYPE '%s'（只打在自家 App 输入框）" % word)
    for ch in word:
        if not tap_letter(ch):
            return False
    time.sleep(0.6)
    return True


def clear_field():
    """用**自家键盘**清掉自家输入框：长按退格＝全选清空（H-167 定稿那条）。"""
    s = st()
    pr = s["panel"]
    x = pr[0] + pr[2] - 64
    y = s["rows_y"][2]
    if not h231.guard("clear-field"):
        return
    drv.long_press(x, y)
    time.sleep(1.0)
    drv.log("CLEAR-FIELD 长按退格（H-167 清空）@(%d,%d)" % (x, y))


def _bands(path, y0, y1, dark=170, min_n=4, x0=None, x1=None, skip_x=None):
    """在 [y0,y1) 里按行扫暗像素，返回**自动检出**的文字带 [(起, 止, 峰值行暗像素数)]。

    2026-10-28 03:3x 真机教训（Qoder）：原来 `candidate_band()` 是「窗顶 + 44vp 顶栏」公式硬算的，
    而实测打字态是 L1 编码行(≈1836..1857) ＋ 候选行(≈1888..1948) ＋ 键区(≈1990 起)，
    44vp 是**候选栏容器**（L1 16vp ＋ 候选 28vp），不是它上面还有一排顶栏；
    工具栏展开时又把这 44vp 整个占掉。公式一错，cand_font_size / show_preedit / page_size
    三项量到的都是空白（暗像素=0），判据一律「未达判据」＝**假阴性**。
    改成从截图里自己找带，带在哪量哪。

    `x0/x1`（04:4x 加，默认整宽＝老行为）：量**浮层卡片**里的行时必须只扫卡片那段 x。
    `h241_funcmenu_check.py` 第一次按整宽扫，把卡片外那圈被遮罩压暗的背景（灰 ≈150 <170）
    也算成暗像素 ⇒ 每一行都「有字」⇒ 一整块 822px 的假带。键区截图整宽扫没问题（键帽铺满整行），
    半屏宽的卡片不行。

    `skip_x`（05:1x 加，默认 None＝老行为）：要跳过的列集合。滚到底那一屏里 `Scroll` 的
    **自动滚动条**（x=[791,804]，14px 宽，实测每行都有 12~14 个暗像素）会把行与行粘成一条
    577px 的假带 ⇒ 末行中心算到行间空白上，点下去当然没反应（05:07 那次就是这么误判「还是被裁」）。
    竖条的特征是**几乎每一行都暗**，文字列只在它自己那几行暗，所以调用方按覆盖率挑出来交给这里。"""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    px = im.load()
    W = im.size[0]
    xa = max(0, int(x0)) if x0 is not None else 0
    xb = min(W, int(x1)) if x1 is not None else W
    skip = skip_x or ()
    out = []
    start = None
    peak = 0
    for y in range(max(0, int(y0)), min(im.size[1], int(y1))):
        n = 0
        for x in range(xa, xb, 2):
            if x in skip:
                continue
            r, g, b = px[x, y]
            if (r + g + b) / 3.0 < dark:
                n += 1
        if n > min_n:
            if start is None:
                start = y
                peak = 0
            peak = max(peak, n)
        elif start is not None:
            out.append((start, y - 1, peak))
            start = None
    if start is not None:
        out.append((start, y1 - 1, peak))
    return [b for b in out if b[1] - b[0] >= 6]


def candidate_band(path):
    """候选行像素带（自动检出）：在「窗顶 … 第一行键之上」里挑**最宽的那条暗像素带**。

    返回 [x1, y1, x2, y2]；一条带都没有（＝屏上没候选，比如工具栏展开态）返回 None。
    注意调用方：**两帧要比同一个带**，所以带用第一帧定，第二帧沿用。"""
    s = st()
    pr = s["panel"]
    scale = s["scale"]
    keys_top = s["rows_y"][0] - int(28 * scale)
    top = pr[1]
    bs = _bands(path, top, keys_top - 4)
    if not bs:
        drv.log("BAND 候选带没检出（窗顶 %d … 键顶 %d 之间无暗像素带）" % (top, keys_top))
        return None
    a, b, pk = max(bs, key=lambda t: t[2])
    drv.log("BAND 候选带检出 [%d, %d, %d, %d]（高 %dpx 峰值 %d，本区共 %d 条带）"
            % (pr[0] + 120, a, pr[0] + pr[2] - 40, b + 1, b - a + 1, pk, len(bs)))
    return [pr[0] + 120, a, pr[0] + pr[2] - 40, b + 1]


def preedit_band(path):
    """L1 编码行像素带（自动检出）：候选带**之上**那条矮带；没有就返回 None。"""
    s = st()
    pr = s["panel"]
    scale = s["scale"]
    cb = candidate_band(path)
    y1 = cb[1] if cb else pr[1] + int(28 * scale)
    bs = _bands(path, pr[1], y1 - 4)
    if not bs:
        return None
    a, b, pk = max(bs, key=lambda t: t[2])
    return [pr[0] + 8, a, pr[0] + int(180 * scale), b + 1]


def count_clusters(path, box, dark=140, gap=6, min_w=14):
    """候选带里数「有几个词」：按列扫暗像素成段。"""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    px = im.load()
    x1, y1, x2, y2 = [int(v) for v in box]
    cols = []
    for x in range(max(0, x1), min(im.size[0], x2)):
        hit = False
        for y in range(max(0, y1), min(im.size[1], y2), 2):
            r, g, b = px[x, y]
            if (r + g + b) / 3.0 < dark:
                hit = True
                break
        cols.append(hit)
    runs = []
    run = 0
    for i, h in enumerate(cols):
        if h:
            run += 1
        else:
            if run >= min_w:
                runs.append((i - run, i))
            run = 0
    if run >= min_w:
        runs.append((len(cols) - run, len(cols)))
    # 词内字距 <gap，词间留白 >=gap ⇒ 先按段合并
    merged = []
    for a, b in runs:
        if merged and a - merged[-1][1] < gap:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    return merged, runs


# ============================ 各项取证 ============================

def it_key_font_size():
    key = "key_font_size"
    refresh()
    if not open_settings():
        return verdict(key, ["入口没开起来，本项未取证"])
    close_settings()
    b = key_box("q")
    s0 = shot(key, "01-before-keys")
    m0 = ink_stats(s0, b)
    v0 = 20
    if not open_settings():
        return verdict(key, ["开页失败"])
    r = bump(key, 4)
    drv.log("BUMP %s -> %s" % (key, r))
    close_settings()
    s1 = shot(key, "02-after-keys")
    m1 = ink_stats(s1, b)
    sync = hl(r"H-241 settings synced", wait=0.3)
    verdict(key, [
        "判据：字母字形高度 px 变（契约 §3-3）",
        "改前 key_font_size=%svp  q 键框 %s  暗像素=%d 高=%d 宽=%d" % (v0, [int(x) for x in b], m0["ink"], m0["h"], m0["w"]),
        "改后 key_font_size=%svp（页面按 ＋ 四档，1vp/档）  暗像素=%d 高=%d 宽=%d" % (v0 + 4, m1["ink"], m1["h"], m1["w"]),
        "写侧 hilog：%s" % (current_value(key)),
        "同步 hilog：%s" % (sync[-1] if sync else "无"),
        "结论：%s" % ("PASS 字形确实变大（ink %+d、h %+d）" % (m1["ink"] - m0["ink"], m1["h"] - m0["h"])
                     if m1["ink"] > m0["ink"] * 1.12 else "未达判据（ink 没涨）"),
    ])


def it_kbd_haptic():
    key = "kbd_haptic"
    refresh()
    hl(r"vibrat|H-241 haptic", clear=True, wait=0.3)
    tap_letter("q")
    on_lines = hl(r"H-241 haptic off|startVibration|vibrat", wait=0.6)
    clear_field()
    if not open_settings():
        return verdict(key, ["开页失败"])
    bump(key, 1)                     # 开关：翻一次＝关
    close_settings()
    hl(r"vibrat|H-241 haptic", clear=True, wait=0.3)
    tap_letter("w")
    off_lines = hl(r"H-241 haptic off|startVibration|vibrat", wait=0.6)
    skip = [l for l in off_lines if "haptic off -> skip vibrate" in l]
    verdict(key, [
        "判据（契约 §3-5）：关掉后 hilog 里 0 条 vibrate 调用，只有那条 skip 日志",
        "改前（开）按键 w… 不，按键 q 之后 vibrat 相关行=%d 条，其中 skip=%d 条" % (len(on_lines), len([l for l in on_lines if 'skip' in l])),
        "改后（关）按键 w 之后 vibrat 相关行=%d 条，其中 skip=%d 条" % (len(off_lines), len(skip)),
        "改前样本：%s" % (on_lines[:2] or "（无——本包没申请振动权限，见下）"),
        "改后样本：%s" % (skip[:2] or "（无 skip 行＝开关没生效）"),
        "结论：%s" % ("PASS 关后只报 skip、不再调振动" if skip and not [l for l in on_lines if 'skip' in l]
                     else "部分：见上面两行原文"),
    ])


def it_expand_toolbar():
    key = "expand_toolbar_by_default"
    refresh()
    s0 = shot(key, "01-bar-before")
    if not open_settings():
        return verdict(key, ["开页失败"])
    bump(key, 1)
    flip = hl(r"H-241 expand_toolbar_by_default flipped", wait=0.4)
    close_settings()
    time.sleep(0.8)
    s1 = shot(key, "02-bar-after-flip")
    pr = st()["panel"]
    scale = st()["scale"]
    band = [pr[0] + 20, pr[1] + 6, pr[0] + pr[2] - 20, pr[1] + int(44 * scale)]
    m0 = ink_stats(s0, band, dark=200)
    m1 = ink_stats(s1, band, dark=200)
    verdict(key, [
        "判据（契约 §3-11）：翻转开关后**当场**动工具栏（hilog flipped）＋顶栏那一排像素内容变化",
        "顶栏带 %s 暗像素：改前 %d → 改后 %d" % ([int(v) for v in band], m0["ink"], m1["ink"]),
        "hilog：%s" % (flip[-1] if flip else "没有 flipped 行"),
        "结论：%s" % ("PASS" if flip and abs(m1["ink"] - m0["ink"]) > 200 else "未达判据"),
    ])


def page_size_logs(pattern=r"setPageSize[=(](\d+)"):
    """把 hilog 里所有 `setPageSize(n)`（UI 侧 KeyboardIndex:1165）/`setPageSize=n`（引擎侧）
    的**数字**按出现顺序取出来。老判据只写 `setPageSize=` ⇒ UI 侧那条永远匹配不上。"""
    out = []
    for ln in hl(pattern, wait=0.4):
        m = re.search(pattern, ln)
        if m:
            out.append(int(m.group(1)))
    return out


# ---- 长按气泡口径（2026-10-28 03:3x 真机诊断 `h241_diag_bubble.py` 定）----
#   契约 §3-6/§3-7 原来只盯 `H-215 timer open bubble`，而这条**历史上一次都没出现过**：
#   注入 longClick 实测走的是兜底手势那条路，屏上真出泡、日志打的是
#     `SSKeyboardIndex LetterKey longpress q -> bubble`
#     `SSKeyboardIndex H-215 v7 bubble q win x=2 y=4.857 w=102 h=40 kw=28.57`
#   松手时再打 `H-215 cancel q`。⇒ 判据改盯这三条的并集（老串留着，将来计时器路径回来还能命中）。
BUBBLE_PAT = (r"LetterKey longpress .* -> bubble|H-215 v7 bubble|H-215 timer open bubble")
BUBBLE_END_PAT = r"H-215 cancel"


def ts_ms(line):
    """hilog 行首 `10-28 03:30:39.652` → 当天 0 点起算的毫秒。解析不出来返回 None。"""
    m = re.search(r"\d{2}-\d{2} (\d{2}):(\d{2}):(\d{2})\.(\d{3})", line)
    if not m:
        return None
    h, mi, s, ms = [int(g) for g in m.groups()]
    return ((h * 60 + mi) * 60 + s) * 1000 + ms


def bubble_probe(ch="q"):
    """长按一次键 ch，返回 (出泡条数, 出泡时刻, 松手时刻, 原始行)。

    「同一支注入笔」的持按时长不由我们控制（uitest longClick 固定），所以**不能**用
    「700ms 不出泡」当判据；能控的是**出泡到松手之间的时长** = 持按总时长 − 阈值。
    阈值 300 与 700 各测一次，这个差值应当缩 ~400ms ⇒ 阈值真被读，且不受时钟偏移影响
    （两个时间戳同一台设备同一个时钟）。"""
    hl(BUBBLE_PAT, clear=True, wait=0.3)
    b = key_box(ch)
    drv.long_press((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    time.sleep(1.2)
    lines = hl(BUBBLE_PAT, wait=0.2)
    ends = hl(BUBBLE_END_PAT, wait=0.2)
    t0 = ts_ms(lines[-1]) if lines else None
    t1 = ts_ms(ends[-1]) if ends else None
    gap = (t1 - t0) if (t0 is not None and t1 is not None) else None
    return len(lines), t0, t1, gap


def it_long_press_delay():
    key = "key_long_press_delay"
    refresh()
    n0, a0, z0, g0 = bubble_probe("q")
    if not open_settings():
        return verdict(key, ["开页失败"])
    set_to(key, 700)
    close_settings()
    n_hi, a_hi, z_hi, g_hi = bubble_probe("q")
    shot(key, "03-at-700ms")
    if not open_settings():
        return verdict(key, ["开页失败(2)"])
    set_to(key, 300)
    close_settings()
    n_lo, a_lo, z_lo, g_lo = bubble_probe("q")
    shot(key, "04-at-300ms")
    sync = hl(r"H-241 settings synced", wait=0.3)
    held = ("注入笔持按总时长 ≈ %.0fms（= 阈值 300 ＋ 出泡后剩余 %dms）⇒ 阈值 700 时仍在持按窗口内，"
            "所以判据只能用「出泡→松手」的时长差，不能用「700 不出泡」。"
            % (300 + g_lo, g_lo)) if g_lo else "300ms 档没出泡 ⇒ 持按时长未知，本项无法差分"
    ok = (n0 > 0 and n_lo > 0 and g_lo is not None and g_hi is not None
          and (g_lo - g_hi) >= 200)
    verdict(key, [
        "判据（契约 §3-6 更正版 r3，Qoder 03:4x）：uitest longClick 的持按时长固定、不由我们控，",
        "  所以**不看「700 不出泡」**（那条永远可能是假阴性），改看同一支笔下",
        "  「出泡 → 松手」的时长差：阈值 300 应比阈值 700 **长 ~400ms**（＝持按 − 阈值）。",
        "  出泡口径 = hilog `%s`（诊断实测：注入走的是兜底手势，老串 timer open bubble 一次都没有）。" % BUBBLE_PAT,
        "默认 450ms：出泡 %d 条，出泡→松手 %s" % (n0, ("%dms" % g0) if g0 else "—"),
        "设到 700ms：出泡 %d 条，出泡→松手 %s" % (n_hi, ("%dms" % g_hi) if g_hi else "—"),
        "设到 300ms：出泡 %d 条，出泡→松手 %s" % (n_lo, ("%dms" % g_lo) if g_lo else "—"),
        "写侧回读=%s  同步行=%s" % (current_value(key), (sync[-1][-58:] if sync else "无")),
        "%s" % held,
        "结论：%s" % ("PASS 阈值进了出泡时机（300 比 700 晚松手 %dms）" % (g_lo - g_hi) if ok
                     else "未达判据：三档计数/时长差见上（差值 <200ms 或没出泡）"),
    ])
    if not open_settings():
        return
    set_to(key, 450)
    close_settings()


def it_popup_on_key_press():
    key = "popup_on_key_press"
    refresh()
    if not open_settings():
        return verdict(key, ["开页失败"])
    set_to("key_long_press_delay", 300)
    bump(key, 1)                      # 翻成「关」
    close_settings()
    n_off, a_off, z_off, g_off = bubble_probe("q")
    s_off = shot(key, "01-popup-off")
    if not open_settings():
        return verdict(key, ["开页失败(2)"])
    bump(key, 1)                      # 翻回「开」
    close_settings()
    n_on, a_on, z_on, g_on = bubble_probe("q")
    s_on = shot(key, "02-popup-on")
    clear_field()
    sync = hl(r"H-241 settings synced", wait=0.3)
    verdict(key, [
        "判据（契约 §3-7 更正版 r3）：同一支注入笔、阈值固定 300ms 下，",
        "  「按键时弹出字符」关 ⇒ 出泡日志 0 条；开 ⇒ ≥1 条。",
        "  像素侧说明：注入是**同步**的（longClick 返回时手指已抬起，泡当场就散了），",
        "  截图量到的是松手之后的画面 ⇒ 像素只能当旁证，不作判据（要「按住看得见泡」",
        "  这一条得主人真手，契约 §5-5）。",
        "关：出泡 %d 条（出泡→松手 %s）" % (n_off, ("%dms" % g_off) if g_off else "—"),
        "开：出泡 %d 条（出泡→松手 %s）" % (n_on, ("%dms" % g_on) if g_on else "—"),
        "同步行=%s" % (sync[-1][-58:] if sync else "无"),
        "截图=%s / %s" % (s_off, s_on),
        "结论：%s" % ("PASS 关掉不出泡、打开出泡" if n_off == 0 and n_on > 0
                     else "未达判据，见计数"),
    ])
    if not open_settings():
        return
    set_to("key_long_press_delay", 450)
    close_settings()


def it_show_preedit():
    key = "show_preedit"
    # r4（Qoder 03:4x 真机查回）：L1 编码行的字是**浅灰**（背景 243、笔画均值在 120..170 之间），
    # 而 `ink_stats` 默认阈值 120 ⇒ 三帧全量到 0，报「未达判据」＝假阴性。
    # 检带用的是 170（`_bands` 的 dark=170），**量带内暗像素就必须用同一个阈值**，否则
    # 「检出得到、量不到」自相矛盾。实测同一批帧：开=585 关=0 再开=585。
    L1_DARK = 170
    refresh()
    type_word("nihao")
    s0 = shot(key, "01-preedit-on")
    band = preedit_band(s0)
    if not band:
        return verdict(key, ["L1 编码带没检出（屏上没编码行＝打字没上屏，先修输入链路）"])
    m0 = ink_stats(s0, band, dark=L1_DARK)
    cb0 = candidate_band(s0)
    if not open_settings():
        return verdict(key, ["开页失败"])
    bump(key, 1)
    close_settings()
    s1 = shot(key, "02-preedit-off")
    m1 = ink_stats(s1, band, dark=L1_DARK)
    cb1 = candidate_band(s1)
    if not open_settings():
        return verdict(key, ["开页失败(2)"])
    bump(key, 1)
    close_settings()
    s2 = shot(key, "03-back-on")
    m2 = ink_stats(s2, band, dark=L1_DARK)
    cb2 = candidate_band(s2)
    clear_field()

    def row(tag, cb):
        return "%s 候选带=%s" % (tag, ("[%d, %d] 高 %dpx" % (cb[1], cb[3], cb[3] - cb[1])) if cb else "无")

    verdict(key, [
        "判据（契约 §3-12 更正版 r4）：关掉后 **L1 编码带**（自动检出 %s）暗像素掉到 <1/3；" % [int(v) for v in band],
        "  且**候选带不被拿回**（候选带起终点三帧基本不动＝那 16vp 画的是同高占位行）。",
        "L1 带暗像素（阈值 <%d，与检带同一个）：开=%d 关=%d 再开=%d" % (L1_DARK, m0["ink"], m1["ink"], m2["ink"]),
        row("开", cb0), row("关", cb1), row("再开", cb2),
        "结论：%s" % ("PASS（关掉后编码消失，候选带位置不动）"
                     if m0["ink"] > 3 * max(1, m1["ink"]) and m2["ink"] > 3 * max(1, m1["ink"])
                     and cb0 and cb1 and abs(cb0[1] - cb1[1]) <= 8
                     else "未达判据：见上面几行"),
    ])


def it_cand_font_size():
    key = "cand_font_size"
    refresh()
    clear_field()
    type_word("nihao")
    s0 = shot(key, "01-cand-18")
    band = candidate_band(s0)
    if not band:
        return verdict(key, ["候选带没检出：屏上根本没有候选（打字链路或候选栏状态问题），本项不取证"])
    cl0, _ = count_clusters(s0, band)
    m0 = ink_stats(s0, band)
    if not open_settings():
        return verdict(key, ["开页失败"])
    set_to(key, 22)
    close_settings()
    # 重打一遍让候选重画（字号只作用在字形上，行高不变＝契约 §3-2 更正）
    clear_field()
    type_word("nihao")
    s1 = shot(key, "02-cand-22")
    cl1, _ = count_clusters(s1, band)
    m1 = ink_stats(s1, band)
    band1 = candidate_band(s1)
    verdict(key, [
        "判据（契约 §3-2 更正版 r3）：候选词**字形高度/墨量**变；行高**故意不跟**（护 236vp 死线）。",
        "  候选带用**第一帧自动检出**的那条，两帧同一带才可比：%s" % [int(v) for v in band],
        "18vp：暗像素=%d 字高=%d 字宽=%d 词数=%d" % (m0["ink"], m0["h"], m0["w"], len(cl0)),
        "22vp：暗像素=%d 字高=%d 字宽=%d 词数=%d" % (m1["ink"], m1["h"], m1["w"], len(cl1)),
        "第二帧自己检出的候选带=%s（起终点与第一帧差 ≤8px ⇒ 行高没跟着字号涨）"
        % ([int(v) for v in band1] if band1 else "无"),
        "写侧回读=%s" % current_value(key),
        "结论：%s" % ("PASS 同一带里字变大（ink %+d、字高 %+d、字宽 %+d）"
                     % (m1["ink"] - m0["ink"], m1["h"] - m0["h"], m1["w"] - m0["w"])
                     if (m1["h"] > m0["h"] or m1["w"] > m0["w"]) and m1["ink"] > m0["ink"] * 1.10
                     else "未达判据：见两行数字"),
    ])
    clear_field()


def it_page_size():
    key = "page_size"
    refresh()
    clear_field()
    type_word("a")
    s0 = shot(key, "01-page-5")
    band = candidate_band(s0)
    cl0, _ = (count_clusters(s0, band) if band else ([], []))
    n0 = page_size_logs()
    if not open_settings():
        return verdict(key, ["开页失败"])
    set_to(key, 9)
    close_settings()
    hl(r"setPageSize", clear=True, wait=0.3)
    clear_field()
    type_word("a")
    s1 = shot(key, "02-page-9")
    cl1, _ = (count_clusters(s1, band) if band else ([], []))
    n1 = page_size_logs()
    verdict(key, [
        "判据（契约 §3-4 更正版 r3）：hilog `setPageSize(n)`（UI 侧）/`setPageSize=n`（引擎侧）",
        "  报出的数**跟着设置值走**，屏上候选带词数随之变。",
        "  2026-10-28 03:3x 教训：老判据写的是 `setPageSize=`，而 UI 侧真实格式是",
        "  `setPageSize(9)`（KeyboardIndex.ets:1165），只有引擎侧才是 `=` ⇒ 永远「没有 setPageSize 行」。",
        "默认（5）：hilog %s ｜ 屏上词数=%d" % (n0[-3:] or "无", len(cl0)),
        "设到 9 之后：hilog %s ｜ 屏上词数=%d" % (n1[-3:] or "无", len(cl1)),
        "候选带=%s" % ([int(v) for v in band] if band else "没检出（屏上无候选）"),
        "写侧回读=%s" % current_value(key),
        "结论：%s" % ("PASS 页大小进了引擎（setPageSize 出现 9）"
                     if any(x == 9 for x in n1) and not any(x == 9 for x in n0)
                     else "未达判据：setPageSize 序列 %s -> %s" % (n0, n1)),
    ])
    clear_field()
    if not open_settings():
        return
    set_to(key, 5)
    close_settings()


def step_counts(pat=r"H-180 space swipe"):
    """返回 (条数, 日志里报出的 step 值集合)。`step=` 那个数才是「设置有没有进去」的铁证，
    光比条数会把「划动本身没注入成功」也误判成生效/不生效。"""
    lines = hl(pat, wait=0.8)
    vals = []
    for ln in lines:
        m = re.search(r"step=([\d.]+)", ln)
        if m:
            vals.append(float(m.group(1)))
    return len(lines), sorted(set(vals))


def it_space_swipe_step():
    key = "space_swipe_step"
    refresh()
    clear_field()
    type_word("nihao")
    s = st()
    sp = s["space"]
    dist = 200
    hl(r"H-180 space swipe", clear=True, wait=0.3)
    drv.swipe(sp[0], sp[1], sp[0] + dist, sp[1], velocity=900)
    n0, v0 = step_counts()
    if not open_settings():
        return verdict(key, ["开页失败"])
    set_to(key, 5)
    close_settings()
    hl(r"H-180 space swipe", clear=True, wait=0.3)
    drv.swipe(sp[0], sp[1], sp[0] + dist, sp[1], velocity=900)
    n1, v1 = step_counts()
    shot(key, "01-after")
    verdict(key, [
        "判据（契约 §3-10 更正版 r3）：同一段划动（%dpx=%.1fvp）hilog `H-180 space swipe` 条数按 10/step" % (dist, dist / s["scale"]),
        "  成反比，**且日志里的 `step=` 自己要跟着变**（不然是别的原因造成的条数差）。",
        "步长 10vp：%d 条（理论 %.1f）日志 step=%s" % (n0, dist / s["scale"] / 10.0, v0 or "—"),
        "设到 5vp：%d 条（理论 %.1f）日志 step=%s" % (n1, dist / s["scale"] / 5.0, v1 or "—"),
        "写侧回读=%s" % current_value(key),
        "结论：%s" % ("PASS 步长进了换算（step %s→%s，条数 %d→%d）" % (v0, v1, n0, n1)
                     if v0 and v1 and v0 != v1 and n1 >= 1.5 * max(1, n0)
                     else "未达判据：见上面两行"),
    ])
    clear_field()
    if not open_settings():
        return
    set_to(key, 10)
    close_settings()


def grid_page_size_logs():
    """展开网格时向引擎要的条数（`setPageSize=n (UI pinned)`／`setPageSize(n)` 都算），取数字。"""
    return page_size_logs(r"setPageSize[=(](\d+)")


def it_grid_page_size():
    key = "grid_page_size"
    refresh()
    clear_field()
    type_word("a")
    pr = st()["panel"]
    scale = st()["scale"]
    # ▼ 在顶栏最右（H-165 形态 B：左上 › ＋ 顶栏图标行，最右一枚是展开网格）
    x = pr[0] + pr[2] - int(20 * scale)
    y = pr[1] + int(22 * scale)
    hl(r"setPageSize|H-168|expand", clear=True, wait=0.3)
    if h231.guard("tap-expand"):
        h231.tap(x, y)
        time.sleep(1.2)
    s0 = shot(key, "01-grid-50")
    a = grid_page_size_logs()
    # 量完必须**当场折叠回去**：网格盖住键区 ⇒ 空格按不到，开页只会得到「开页失败」
    # （03:01 那轮就是这样，而且 `expanded` 是 IME 面板的 @State，重启自家 App 也不清，
    #   把后面 grid_page_size/kbd_height_pct/undo_stack_limit 三项一起带崩、reset 也开不了页）。
    if h231.guard("tap-collapse-1"):
        h231.tap(x, y)
        time.sleep(1.0)
    if not open_settings():
        return verdict(key, ["开页失败"])
    set_to(key, 20)
    close_settings()
    hl(r"setPageSize|H-168", clear=True, wait=0.3)
    if h231.guard("tap-expand2"):
        h231.tap(x, y)
        time.sleep(1.2)
    s1 = shot(key, "02-grid-20")
    b = grid_page_size_logs()
    if h231.guard("tap-collapse-2"):
        h231.tap(x, y)
        time.sleep(1.0)
    verdict(key, [
        "判据（契约 §3-9 更正版 r3）：展开网格向引擎要的条数＝设置值 —— hilog `setPageSize…` 里的**数字**",
        "  要从 50 变到 20，屏上网格屏数随之变。",
        "  2026-10-28 03:3x 教训：上一版只要求「两次 hilog 文本不同」，两条都是 50 也算 PASS ⇒ 假阳性。",
        "默认 50：setPageSize 序列 %s" % (a or "无"),
        "设到 20：setPageSize 序列 %s" % (b or "无"),
        "写侧回读=%s" % current_value(key),
        "截图：%s / %s" % (s0, s1),
        "结论：%s" % ("PASS 引擎侧条数 %s→%s" % (a, b) if (20 in (b or []) and 20 not in (a or []))
                     else "未达判据：序列 %s -> %s" % (a, b)),
    ])
    clear_field()
    if not open_settings():
        return
    set_to(key, 50)
    close_settings()


def applied_rows():
    """`H-241 applySettingsChanged: row=NNvp undoLimit=NN` → 取 (row 列表, undoLimit 列表)。"""
    lines = hl(r"H-241 applySettingsChanged|relayout resize", wait=0.5)
    rows, undo = [], []
    for ln in lines:
        m = re.search(r"row=([\d.]+)vp", ln)
        if m:
            rows.append(float(m.group(1)))
        m2 = re.search(r"undoLimit=(\d+)", ln)
        if m2:
            undo.append(int(m2.group(1)))
    return rows, undo, lines


def it_kbd_height():
    key = "kbd_height_pct"
    refresh()
    pr0 = st()["panel"]
    assume = row0_start_value(key)
    if assume is None or abs(assume - 100) > 0.5:
        drv.log("HEIGHT 开跑前键高不在默认（缓冲读到 %s）⇒ 先用几何把窗高量回 983px" % assume)
        if not row0_home():
            return verdict(key, ["开跑前键高不是 100%% 且几何修正未成功（assume=%s）⇒ 不测，免得拿 110%% 当 100%%"
                                 % assume])
        pr0 = h231.panel_rect()
    hl(r"applySettingsChanged|relayout resize", clear=True, wait=0.3)
    s0 = shot(key, "01-height-100")
    r0, _u0, _l0 = applied_rows()
    if not open_settings():
        return verdict(key, ["开页失败"])
    set_to_row0(key, 120, assume=assume)
    close_settings()
    time.sleep(1.0)
    rows1, _u2, lines1 = applied_rows()
    s1 = shot(key, "02-height-120")
    pr1 = h231.panel_rect()
    drv.log("HEIGHT panel rect %s -> %s" % (pr0, pr1))
    # 末行键必须还在（H-213 静默裁切那一类）：底行白色键帽要量得到
    b = key_box("q")
    m1 = ink_stats(s1, b)
    verdict(key, [
        "判据（契约 §3-1 更正版 r3）：hilog `applySettingsChanged: row=…vp` 报出**新行高 = 48×120% = 57.6vp**",
        "  ＋ 面板窗高随之变化 ≥±6% ＋ 末行键不被裁。",
        "  （改前不需要 row 日志：开跑前已「恢复默认」，默认就是 48vp/100%%，窗高 %dpx=236vp 是量出来的。）" % pr0[3],
        "改前 WMS 面板矩形=%s" % (pr0,),
        "改后 WMS 面板矩形=%s  row 序列=%s" % (pr1, rows1 or "无"),
        "hilog：%s" % (" / ".join([l[-70:] for l in lines1[-3:]]) if lines1 else "无 applySettingsChanged 行"),
        "写侧回读=%s" % current_value(key),
        "改后 q 键仍可量到暗像素=%d（>0 ⇒ 键没被裁掉）" % m1["ink"],
        "结论：%s" % ("PASS 行高到 57.6vp、窗高 %d→%d px（%+.1f%%）"
                     % (pr0[3], pr1[3], 100.0 * (pr1[3] - pr0[3]) / pr0[3])
                     if any(abs(x - 57.6) < 0.8 for x in rows1) and pr1 and pr1[3] != pr0[3] and m1["ink"] > 0
                     else "未达判据"),
    ])
    if not row0_home():
        drv.log("HEIGHT 收尾没把窗高量回 983px ⇒ 下一项会 ANCHOR-ABORT，先看上面 HOME0 日志")
        close_settings()


def it_undo_stack_limit():
    key = "undo_stack_limit"
    refresh()
    hl(r"applySettingsChanged", clear=True, wait=0.3)
    if not open_settings():
        return verdict(key, ["开页失败"])
    set_to(key, 6)
    close_settings()
    _rows, undo, lines = applied_rows()
    shot(key, "01-undo-6")
    verdict(key, [
        "判据（契约 §3-8 更正版 r3）：`applySettingsChanged: … undoLimit=NN` 报出**新上限 6**（默认 10）",
        "  ⇒ 设置值真进了控制器（`this.undoLimit = SettingsStore.on('undo_stack_limit')` ＋ 当场 `while shift` 裁栈）。",
        "  行为侧（连打 N+2 段候选后能撤几步）注入量不出来，按契约 §5-5 归**主人真手**，本项记 PART 不算全绿。",
        "hilog：%s" % (" / ".join([l[-64:] for l in lines[-3:]]) if lines else "无 applySettingsChanged 行"),
        "undoLimit 序列=%s  写侧回读=%s" % (undo or "无", current_value(key)),
        "结论：%s" % ("PART（生效点已证：undoLimit=6；撤回步数待主人真手）"
                     if 6 in (undo or []) else "未达判据：undoLimit 没报出 6"),
    ])
    if not open_settings():
        return
    set_to(key, 10)
    close_settings()


ALL = [
    ("key_font_size", it_key_font_size),
    ("kbd_haptic", it_kbd_haptic),
    ("expand_toolbar_by_default", it_expand_toolbar),
    ("key_long_press_delay", it_long_press_delay),
    ("popup_on_key_press", it_popup_on_key_press),
    ("show_preedit", it_show_preedit),
    ("cand_font_size", it_cand_font_size),
    ("page_size", it_page_size),
    ("space_swipe_step", it_space_swipe_step),
    ("grid_page_size", it_grid_page_size),
    ("kbd_height_pct", it_kbd_height),
    ("undo_stack_limit", it_undo_stack_limit),
]


def cmd_nudge0(key, direction, times=1):
    """**逃生道**：把**第 0 行**（＝`kbd_height_pct`）加减 `times` 档，不碰 236vp 锚点。

    2026-10-28 03:5x 真机连环教训：`it_kbd_height` 在渲染 verdict 时踩到一个 `%，` 格式串 bug
    ⇒ 抛 ValueError，**跑在「改完 110% 之后、恢复 100% 之前」**⇒ 设备留在 110%；
    而 `card_anchor()` 见到卡片高 894px≠236vp(826px) 就**停手**（这道闸是对的，03:06 就是靠它没打错行），
    于是 `undo_stack_limit` 和收尾 `reset` 全部 ANCHOR-ABORT ⇒ **死锁：想改键高，得先能点行；能点行，得先改回键高**。
    ⇒ 逃生道绕开行公式，直接认「卡片里最上面那条按钮」＝第 0 行，按它的 －/＋。
      只认 S=0（首屏不用滚），只服务 idx=0，别的键一律拒绝——不做「顺手通用化」。
    04:1x 改成**每一按都重认一次**（`row0_press`）：04:08 那版按固定 y 连按两下，
    第二下靠「－ 按钮 28vp 高、误差 34px 还在框里」蒙对了；键高会让整卡上下移动，不能赌。"""
    idx = drv.IDX.get(key)
    if idx != 0:
        drv.log("NUDGE0 只服务第 0 行（kbd_height_pct），%s 的 idx=%s ⇒ 拒绝" % (key, idx))
        return 1
    if not open_settings():
        return 1
    ok = 0
    for i in range(int(times)):
        if row0_press(key, direction) is None:
            drv.log("NUDGE0 第 %d 下失败 ⇒ 收手（不盲按）" % (i + 1))
            break
        ok += 1
    close_settings()
    refresh()
    return 0 if ok == int(times) else 1


def main():
    drv.setup()
    if len(sys.argv) < 2 or sys.argv[1] == "list":
        for k, _f in ALL:
            print("%-26s %s" % (k, drv.KIND[k]))
        return 0
    if sys.argv[1] == "nudge0":
        return cmd_nudge0(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 1)
    if sys.argv[1] == "run":
        want = sys.argv[2]
        for k, f in ALL:
            if k == want:
                f()
                return 0
        print("没有这一项 %s" % want)
        return 1
    if sys.argv[1] == "reset":
        return drv.cmd_reset()
    if sys.argv[1] == "run-all":
        # 契约 §5：跑完要把设备留在默认口径 ⇒ 每项都从**已知默认**起步，数字才有可比性。
        drv.cmd_reset()
        for k, f in ALL:
            drv.log("========== %s ==========" % k)
            try:
                f()
            except Exception as e:
                drv.log("EXCEPTION[%s] %r" % (k, e))
        drv.log("========== 收尾：恢复默认 ==========")
        drv.cmd_reset()
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
