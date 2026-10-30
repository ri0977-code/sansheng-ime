#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-234 / H-235 / H-236 真机取证（Qoder，2026-10-28 00:3x 起）

主人 00:3x 说「从一开始就取消密码了」⇒ 不用等他给口令，我自己装机、自己量。

**为什么不走控件树**（2026-10-28 00:36 实测）：`uitest dumpLayout -i` 捞到的 125 个节点全是
**宿主 App 页面**的文本，键盘/面板那扇窗（SCBKeyboardPanel）**一个字都没进树** —— 上一版脚本
里「面板控件树文本项」那几行其实一直读的是自家设置页的文字。⇒ 本轮判据只能用
**像素 + hilog**，格子文案由放大图人工读（我自己在屏上核，不靠推）。

四步（每步落截图/放大图，全部只点**自家 App**与键盘自己，不打字、不删字符）：
  A  面板展开 ⇒ 裁出中间行三格与右列五格放大图（看是不是「上5行/选择/下5行」「全选/剪切/复制/粘贴/⌫」）
  B  点「上5行」⇒ hilog 必须有 `H-218 moveCursorPage n=5 dir=1`（接线；宿主响不响另判）
  C  点「选择」⇒ hilog `H-231 gridSelect tapped`；蓝底（#B8C6E8）像素数应跳上去
  D  点顶栏「‹」折叠（**不是**再点一次 ⇆，那条以前也漏）⇒ hilog 必须有 `H-234 折叠`
     + `toggleSelectionMode -> false`；折叠后键区蓝底必须掉回基线；再开面板那格必须回「选择」

用法：
  python scripts/h234_236_device_check.py probe      # 只看锁屏/前台，零注入
  python scripts/h234_236_device_check.py up         # 只拉起键盘并裁键区（找 n 键位置）
  python scripts/h234_236_device_check.py run        # A→B→C→D 全套
产出：docs/evidence/2026-10-28/h234-236-device/（run.log、verdict.txt、各步截图与放大图）
"""
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h231_panel_check as h231          # noqa: E402  复用已验证的锁屏判定/前台双闸/点按/截图/裁图

ROOT = os.path.dirname(HERE)
EVID = os.path.join(ROOT, "docs", "evidence", "2026-10-28", "h234-236-device")
SEL_RGB = (184, 198, 232)                # BG_ACTIVE（键面）= BG_KEY_ACTIVE（面板）同一个色
TOL = 14
NONE = r"(?!never)x"   # 只用来「清一次 hilog 并丢掉结果」，别真去匹配全文
STEP = 2                                 # 每 2 像素采样，结果 ×4 折算


def use_evid():
    os.makedirs(EVID, exist_ok=True)
    h231.EVID = EVID
    h231.LOG = os.path.join(EVID, "run.log")


def blue_count(shot, y0, y1):
    """[y0,y1) 这段屏幕里 #B8C6E8 底色像素数（整像素折算）。"""
    from PIL import Image
    im = Image.open(shot).convert("RGB")
    w, h = im.size
    y0, y1 = max(0, int(y0)), min(h, int(y1))
    px = im.load()
    n = 0
    for y in range(y0, y1, STEP):
        for x in range(0, w, STEP):
            r, g, b = px[x, y]
            if abs(r - SEL_RGB[0]) <= TOL and abs(g - SEL_RGB[1]) <= TOL and abs(b - SEL_RGB[2]) <= TOL:
                n += 1
    return n * STEP * STEP


def key_area_top():
    """键区/面板顶沿＝SCBKeyboardPanel 顶 + 候选栏高（候选栏约占 1 行键高）。"""
    pr = h231.panel_rect()
    return pr[1] if pr else None


def hl(pattern, clear=False):
    if clear:
        h231.sh("shell", "hilog", "-r")
        time.sleep(0.4)
    time.sleep(1.0)
    txt = h231.sh("shell", "hilog", "-x")
    return [ln.strip() for ln in txt.splitlines() if re.search(pattern, ln)]


def rep(lines, s):
    h231.log(s)
    lines.append(s)


def cells_from(shot, top):
    """面板 3 行 × 左列 + 右列的格子几何（用 OFF 态白段量，ON 态蓝底不影响坐标复用）。"""
    info = h231.find_panel_cells(shot, top)
    return info


def crop_cells(shot, info, tag):
    """把左列三行与右列整列各裁一张放大图。"""
    from PIL import Image
    im = Image.open(shot).convert("RGB")
    w, h = im.size
    outs = []
    bands = info["bands"]
    lx0 = info["left_x0"]
    # 左列：三行整行（含 3 格）
    for i, bd in enumerate(bands):
        segs = h231.white_segments(im, min(bd[1], bd[0] + 6))
        x1 = segs[0][0] if segs else lx0
        x2 = segs[-1][1] if segs else lx0 + 620
        out = os.path.join(EVID, "%s-left-row%d.png" % (tag, i + 1))
        outs.append(h231.zoom_crop(shot, (x1 - 6, bd[0] - 6, x2 + 6, bd[1] + 6), 3, out))
    # 右列：整列一条
    out = os.path.join(EVID, "%s-right-col.png" % tag)
    outs.append(h231.zoom_crop(shot, (int(w * 0.70), bands[0][0] - 8, w - 4, h - 4), 3, out))
    return outs


def probe():
    st, why = h231.locked_state()
    h231.log("LOCK %s（%s）" % (st, why))
    ok, fwhy = h231.own_foreground()
    h231.log("FOREGROUND %s：%s" % ("本应用" if ok else "非本应用", fwhy))
    return 0 if st == "unlocked" else 1


def up():
    c = h231.bring_up()
    if not c:
        return 1
    top = key_area_top()
    shot = h231.screenshot("keys-only")
    h231.log("键区顶沿 y=%s；基线蓝底（键盘空闲态）=%d 像素（%s）" % (top, blue_count(shot, top, 10 ** 9), shot))
    return 0


def run():
    L = []
    st, why = h231.locked_state()
    rep(L, "① 锁屏判定：%s（%s）" % (st, why))
    if st != "unlocked":
        rep(L, "不是已解锁 ⇒ 中止（绝不猜口令、不叫醒屏）")
        return 1
    if not h231.bring_up():
        rep(L, "键盘没拉起来 ⇒ 中止")
        return 1
    top = key_area_top()
    s0 = h231.screenshot("s0-idle")
    blue_idle = blue_count(s0, top, 10 ** 9)
    rep(L, "② 键盘空闲态：面板窗顶沿 y=%s，键区 #B8C6E8 蓝底像素=%d（%s）" % (top, blue_idle, s0))

    # ── 展开工具栏 → 点 ⇆ 开面板 ────────────────────────────────────
    shot_bar, cursor, band = h231.expand_func_bar(s0, top)
    if cursor is None:
        rep(L, "没量到 ⇆ 图标 ⇒ 面板开不了，中止（不猜坐标）")
        return 2
    if not h231.guard("open-panel"):
        return 1
    h231.tap(cursor["cx"], cursor["cy"])
    time.sleep(1.8)
    top2 = key_area_top() or top
    s1 = h231.screenshot("s1-panel-off")
    info = cells_from(s1, top2)
    if not info.get("ok"):
        rep(L, "面板格子没量到：%s ⇒ 中止" % info.get("why"))
        return 2
    crops = crop_cells(s1, info, "A")
    sel = info["cell"]
    rep(L, "③【A / H-235+H-236】面板已开：左列行带=%s，「选择」格中心=(%d,%d)；"
            "放大图=%s ⇒ **文案我自己在图上读**（控件树读不到 IME 窗）"
            % (info["bands"], sel["cx"], sel["cy"], [os.path.basename(c) for c in crops]))

    # ── B：点「上5行」看接线 ────────────────────────────────────────
    mid_segs = info["segments"]
    up_cell = mid_segs[0]
    hl(NONE, clear=True)
    if h231.guard("tap-up5"):
        h231.tap((up_cell[0] + up_cell[1]) // 2, sel["cy"])
        hits = hl(r"H-218 moveCursorPage n=5 dir=1")
        raw = hl(r"H-177 moveEditorCursor dir=1 ok")
        s2 = h231.screenshot("s2-tap-up5")
        rep(L, "④【B / H-235】点中间行第 1 格 (%d,%d)：hilog `moveCursorPage n=5 dir=1` 命中 %d 行、"
                "`moveCursorSync(1) ok` 命中 %d 行 ⇒ 接线=%s（宿主认不认这条纵向移动＝屏上另判，"
                "我在这条里不替它背书）。截图 %s"
                % ((up_cell[0] + up_cell[1]) // 2, sel["cy"], len(hits), len(raw),
                   "PASS" if hits else "FAIL", s2))

    # ── C：点「选择」 ⇒ 蓝底应跳上去 ────────────────────────────────
    hl(NONE, clear=True)
    if h231.guard("tap-select"):
        h231.tap(sel["cx"], sel["cy"])
        time.sleep(1.2)
        g = hl(r"H-231 gridSelect tapped")
        t = hl(r"H-220 toggleSelectionMode -> true")
        s3 = h231.screenshot("s3-select-on")
        blue_on = blue_count(s3, top2, 10 ** 9)
        crops3 = crop_cells(s3, info, "C")
        rep(L, "⑤【C】点「选择」格：hilog `gridSelect tapped` 命中 %d 行、`toggleSelectionMode -> true` %d 行；"
                "面板区蓝底像素=%d（空闲态 %d）⇒ 亮底=%s；放大图=%s"
                % (len(g), len(t), blue_on, blue_idle, "是" if blue_on > blue_idle * 3 + 200 else "没跳",
                   [os.path.basename(c) for c in crops3]))
    else:
        blue_on = -1

    # ── D：点顶栏「‹」折叠 ⇒ 必须自动退出选择 ───────────────────────
    clusters, _b = h231.measure_bar(h231.screenshot("s4-bar-with-panel"), top2)
    fold = clusters[0] if clusters else None
    hl(NONE, clear=True)
    verdict_d = "未跑"
    blue_folded = -1
    if fold and h231.guard("fold-by-left-chev"):
        h231.tap(fold["cx"], fold["cy"])
        time.sleep(1.8)
        cd = hl(r"H-234 折叠")
        off = hl(r"H-220 toggleSelectionMode -> false")
        top3 = key_area_top() or top
        s5 = h231.screenshot("s5-folded-by-chevron")
        blue_folded = blue_count(s5, top3, 10 ** 9)
        verdict_d = "PASS" if (cd and off and blue_folded <= blue_idle + 120) else "FAIL"
        rep(L, "⑥【D / H-234】点顶栏最左「‹」(%d,%d) 折叠：hilog `H-234 折叠` 命中 %d 行、"
                "`toggleSelectionMode -> false` %d 行；折叠后键区蓝底=%d（空闲基线 %d，开着选择时 %d）"
                "⇒ **%s**（%s）"
                % (fold["cx"], fold["cy"], len(cd), len(off), blue_folded, blue_idle, blue_on,
                   verdict_d, s5))
        for ln in cd[-2:] + off[-2:]:
            rep(L, "     · " + ln[:180])
        # 复验：重开面板，那格文案必须回到「选择」
        # 00:38 首跑在这一步栽了：折叠后顶栏回到收起态，**不能**沿用上一步量到的 ⇆ 坐标，
        # 必须重新 expand_func_bar（它会自己点「›」把工具栏再展开，再挑 ⇆）。
        if h231.guard("reopen-panel"):
            _sb, cursor2, _bd = h231.expand_func_bar(h231.screenshot("s5b-bar-refolded"), top3)
            if cursor2 is None:
                rep(L, "⑦【D 复验】重开面板时没量到 ⇆ ⇒ 这条不跑（不猜坐标）")
            else:
                h231.tap(cursor2["cx"], cursor2["cy"])
                time.sleep(1.8)
                rt = key_area_top() or top2
                s6 = h231.screenshot("s6-panel-reopen")
                info6 = cells_from(s6, rt)
                crops6 = crop_cells(s6, info6, "D") if info6.get("ok") else []
                blue_re = blue_count(s6, rt, 10 ** 9)
                rep(L, "⑦【D 复验】重开面板（⇆ 现量于 (%d,%d)）：蓝底=%d（应≈未选态 %d）；放大图=%s ⇒ 那格是不是「选择」我看图"
                        % (cursor2["cx"], cursor2["cy"], blue_re, blue_idle, [os.path.basename(c) for c in crops6]))
    else:
        rep(L, "⑥【D】顶栏「‹」没量到或前台不合规 ⇒ 这条不跑（不猜坐标）")

    rep(L, "结论：A=图已出（我读图）｜B=%s｜C=蓝底 %d→%d｜D=%s（蓝底回落到 %d）"
        % ("见④", blue_idle, blue_on, verdict_d, blue_folded))
    with open(os.path.join(EVID, "verdict.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return 0


def reopen():
    """⑦ 单独补跑（00:38 那次没跑成的原因找到了）：
    折叠后顶栏回到**收起态**，⇆ 那枚的坐标和展开态不是一个位置 ——
    老代码拿展开态量到的 `cursor` 去点，点到的是别的键 ⇒ 面板没开、格子量不到。
    这里每次都重新 `expand_func_bar`（它会自己点「›」再展开），不沿用上一步的坐标。
    """
    L = []
    st, why = h231.locked_state()
    rep(L, "⑦ 补跑 · 锁屏判定：%s（%s）" % (st, why))
    if st != "unlocked":
        rep(L, "不是已解锁 ⇒ 中止")
        return 1
    if not h231.bring_up():
        rep(L, "键盘没拉起来 ⇒ 中止")
        return 1
    top = key_area_top()
    s0 = h231.screenshot("r0-idle")
    blue_idle = blue_count(s0, top, 10 ** 9)
    shot_bar, cursor, band = h231.expand_func_bar(s0, top)
    if cursor is None:
        rep(L, "没量到 ⇆ ⇒ 中止（不猜坐标）")
        return 2
    if not h231.guard("reopen-panel"):
        return 1
    h231.tap(cursor["cx"], cursor["cy"])
    time.sleep(1.8)
    top2 = key_area_top() or top
    s1 = h231.screenshot("r1-panel-reopen")
    info = cells_from(s1, top2)
    if not info.get("ok"):
        rep(L, "重开后面板格子仍没量到：%s ⇒ 中止" % info.get("why"))
        return 2
    crops = crop_cells(s1, info, "R")
    blue_re = blue_count(s1, top2, 10 ** 9)
    rep(L, "⑦【D 复验·补跑】折叠后重开面板（⇆ 现量于 (%d,%d)）：键区蓝底=%d（空闲基线 %d）；"
            "放大图=%s ⇒ 中间那格文案我读图"
            % (cursor["cx"], cursor["cy"], blue_re, blue_idle, [os.path.basename(c) for c in crops]))
    with open(os.path.join(EVID, "verdict-reopen.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return 0


KEY_GRAY = (202, 206, 218)          # 键面常态底
BG_ACTIVE_RGB = (184, 199, 232)     # 实测到的键面高亮底（= #B8C6E8，JPEG 抖 1）
PROBE_Y = 2360                      # 第三行字母行（z x c v b n m）所在扫描线
BODY_Y = (2350, 2380)               # 键体取色带：00:46 首跑取的是 2290..2320，**落在上一排的灰条上**
                                    # ⇒ 三张图量出同一个 (202,206,218)，正控假失败（图没错，取色带错）


def fold_panel_if_open(tag):
    """面板还开着 ⇒ 键面被面板盖住，量不到 n 键。点顶栏最左「‹」收起来（就是 H-234 那条路径）。"""
    top = key_area_top()
    shot = h231.screenshot(tag + "-before-fold")
    if gray_row_segments(shot):
        return True, top, shot
    clusters, _b = h231.measure_bar(h231.screenshot(tag + "-bar"), top)
    if not clusters:
        return False, top, shot
    if not h231.guard("fold-" + tag):
        return False, top, shot
    h231.tap(clusters[0]["cx"], clusters[0]["cy"])
    time.sleep(1.6)
    shot = h231.screenshot(tag + "-after-fold")
    return bool(gray_row_segments(shot)), top, shot


def gray_row_segments(shot):
    """第三行字母行里的**灰底键**段（白底键 z/b 不算）。认得出「↑ … ⌫」首尾 ⇒ 这是 QWERTY 面。"""
    from PIL import Image
    im = Image.open(shot).convert("RGB")
    w, h = im.size
    px = im.load()
    segs, cur = [], None
    for x in range(w):
        hit = all(abs(a - b) <= 8 for a, b in zip(px[x, PROBE_Y], KEY_GRAY))
        if hit:
            cur = [x, x] if cur is None else [cur[0], x]
        else:
            if cur and cur[1] - cur[0] > 20:
                segs.append(tuple(cur))
            cur = None
    if cur and cur[1] - cur[0] > 20:
        segs.append(tuple(cur))
    # QWERTY 面的形状闸：最左＝↑（x≈18..164），最右＝⌫（右沿 >1100），中间至少 4 段灰键
    if len(segs) < 6 or segs[0][0] > 40 or segs[-1][1] < 1100:
        return []
    return segs


def n_key_rect(shot):
    """n 键（键面小字标着「选择」那枚）＝灰段里中心落在 820..980 的那一段。量不到返回 None。"""
    for s in gray_row_segments(shot):
        cx = (s[0] + s[1]) // 2
        if 820 <= cx <= 980:
            return {"x0": s[0] + 6, "x1": s[1] - 6, "cx": cx, "cy": PROBE_Y}
    return None


def mode_color(shot, x0, x1, y0, y1):
    """返回这块区域里出现最多的那个 RGB（不是 (色,次数)）。"""
    from collections import Counter
    from PIL import Image
    im = Image.open(shot).convert("RGB")
    px = im.load()
    c = Counter(px[x, y] for x in range(x0, x1, 2) for y in range(y0, y1, 2))
    return c.most_common(1)[0][0]


def long_press(x, y):
    """n 键的「选择」是**长按**语义（KeyboardIndex.ets:3241 `ch === 'n'` 在长按分支里），
    00:44 首跑我用 `click` 点了两下 ⇒ hilog 0 命中、键色不变 —— 那是**量具用错**，
    不是功能没接。这里改用 uitest 的 longClick。"""
    h231.sh("shell", "uitest", "uiInput", "longClick", str(int(x)), str(int(y)))


def nkey():
    """正控（没有它，「折叠后 n 键底色=常态」这句话等于没量）：
    键面 n 键**开选择时到底会不会变色** —— 变，才说明 ⑥ 量到的回落是真回落。
    全程只按 n 键两次（开→关），不打字、不删字符。"""
    L = []
    st, why = h231.locked_state()
    rep(L, "正控 · 锁屏判定：%s（%s）" % (st, why))
    if st != "unlocked":
        rep(L, "不是已解锁 ⇒ 中止")
        return 1
    if not h231.bring_up():
        rep(L, "键盘没拉起来 ⇒ 中止")
        return 1
    ok, top, shot = fold_panel_if_open("n0")
    if not ok:
        rep(L, "键面 n 键量不到（面板没收起来或不是 QWERTY 面）⇒ 中止，不猜坐标")
        return 2
    n = n_key_rect(shot)
    rep(L, "键面已露出：n 键灰段 x=%d..%d（y=%d）" % (n["x0"], n["x1"], PROBE_Y))
    before = mode_color(shot, n["x0"], n["x1"], BODY_Y[0], BODY_Y[1])
    rep(L, "① 按之前 n 键底色众数=%s（常态灰=%s）" % (before, KEY_GRAY))
    hl(NONE, clear=True)
    if not h231.guard("longpress-n-on"):
        return 1
    long_press(n["cx"], n["cy"])
    time.sleep(1.4)
    s1 = h231.screenshot("n1-select-on")
    on = mode_color(s1, n["x0"], n["x1"], BODY_Y[0], BODY_Y[1])
    hits = hl(r"H-220 toggleSelectionMode -> true")
    rep(L, "② **长按**一次 n ⇒ n 键底色众数=%s；hilog `toggleSelectionMode -> true` 命中 %d 行"
            % (on, len(hits)))
    if not h231.guard("longpress-n-off"):
        return 1
    long_press(n["cx"], n["cy"])
    time.sleep(1.4)
    s2 = h231.screenshot("n2-select-off")
    off = mode_color(s2, n["x0"], n["x1"], BODY_Y[0], BODY_Y[1])
    hits2 = hl(r"H-220 toggleSelectionMode -> false")
    rep(L, "③ 再长按一次 n ⇒ n 键底色众数=%s；hilog `-> false` 命中 %d 行" % (off, len(hits2)))
    changed = on != before
    back = all(abs(a - b) <= 6 for a, b in zip(off, before))
    rep(L, "结论：n 键开选择时**会**变色=%s（%s → %s；高亮底实测=%s）｜再长按能回到常态=%s（%s）"
            % ("是" if changed else "否（这条正控不成立，⑥ 的回落不能算证据）", before, on, BG_ACTIVE_RGB,
               "是" if back else "否", off))
    with open(os.path.join(EVID, "verdict-nkey.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return 0


def main():
    use_evid()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "probe"
    h231.log("=== h234_236_device_check %s @ %s ===" % (cmd, time.strftime("%Y-%m-%d %H:%M:%S")))
    return {"probe": probe, "up": up, "run": run, "reopen": reopen, "nkey": nkey}.get(cmd, probe)()


if __name__ == "__main__":
    sys.exit(main())
