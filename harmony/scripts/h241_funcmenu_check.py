#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-241r2（Qoder 2026-10-28 03:5x）：`···` 功能菜单里那枚「设置」行**到底画没画全**。

为什么会单开一支脚本：我在 H-241 里给这个菜单加了第 7 行（「设置（键盘与候选）」），
静态算下来菜单 268vp > 面板窗口内容区实测 236vp（hilog `H-215 root area win? … h=236`），
Stack 居中 ⇒ 上下各裁 ~56px＝16vp ⇒ 新行**只剩上半截**。但这算法没上屏验过就不算结论
（H-137／H-144：描述 UI 的东西每次布局变动都会烂；「算出来」≠「量到」）。

量什么（三步，全在自家 App＋自家键盘，不碰主人任何文档）：
  ① 把工具栏弄成展开态 → 从图标簇里挑出 `···`（**三个点在簇里各算一簇**，老脚本记过这个坑）→ 点它；
  ② 截屏，沿 x=640 竖着扫「卡片亮块」（菜单底 `BG_BAR`=#F2F3F5≈242，遮罩把身后压到 ≈150，
     所以「≥230 的连续段」＝卡片），得到卡片**可见**上下沿；再在卡片里按行检出文字带（`_bands`）；
  ③ 清 hilog → 按「设置」行**该在的位置**（卡片可见区最底一条文字带的中心）点一下 →
     看有没有 `H-241 settings panel opened`。点得动＝入口活着；点不动＝裁到不可交互。

判据（写死在 verdict 里，不许事后放宽）：
  改前（装机版＝菜单没有 Scroll）：卡片下沿 == 面板内容底（＝贴窗被裁）或最底一条带高度 < 20px；
  改后（重建装机版）：① 卡片整块在面板窗口内容区内（顶 ≥ 窗顶、底 ≤ 内容底、高 ≤ 236vp）；
       ② **先在卡片内上滚到底**，再点末屏最底一条文字带 ⇒ hilog 出现 `H-241 settings panel opened`。

判据变更记录（口径动了就必须留痕，否则下一轮拿旧口径判新问题会判错）：
  r5（2026-10-28 04:5x）原判据第 ② 条写的是「首屏检出 ≥6 条带且点首屏最底一条带」。
      这条**只在坏布局下成立**——那时 8 行硬塞进 236vp，`设置` 行恰好顶在最底。
      修成「外壳定高 + 内层 Scroll」后，首屏按设计只显 6 条（标题 + 5 行），`设置` 行落在折叠区；
      继续用旧口径 ⇒ 把「可滚」判成「仍被裁」＝假阴性。⇒ 改成现在这句：滚动是**取证步骤**，不是放宽。
  r2（2026-10-28 04:3x）认错图标簇（把工具栏第 5 枚「剪贴板」当成 `···`），量的其实是别人的浮层。
      ⇒ 加两条硬闸：`···` 必须按「簇间距 ≤60px 且 ≥3 簇」挑；卡片开启日志 `H-241r2 func menu opened`
      缺失且文字带 <5 条 ⇒ 判据作废重认，不许出 PASS。
  文字带扫描必须限制在卡片横向 x 段内（全宽会把身后 ≈150 灰的遮罩当墨，多出假带）。

用法：
  PYTHONIOENCODING=utf-8 python scripts/h241_funcmenu_check.py check      # 打开菜单并量
  PYTHONIOENCODING=utf-8 python scripts/h241_funcmenu_check.py close      # 只把菜单关掉（遮罩点一下）
取证落 `docs/evidence/2026-10-28/h241-funcmenu/`，同名不覆盖（`-r2/-r3`）。
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h231_panel_check as h231                      # noqa: E402
import h241_settings_device_check as drv             # noqa: E402
import h241_settings_items as it                     # noqa: E402  （复用 _bands/uniq 那套）

from PIL import Image                                # noqa: E402

BASE = drv.BASE
DIR = os.path.join(BASE, "h241-funcmenu")

CARD_MIN_GRAY = 230          # 卡片底 #F2F3F5 亮度 ≥230；身后被遮罩压到 ≈150


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
    tmp = h231.screenshot("tmp-fm-%s" % name)
    out = uniq(name, "jpeg")
    if tmp and os.path.exists(tmp):
        os.replace(tmp, out)
    log("SHOT[%s] %s" % (name, out))
    return out


def card_span(path, x=640):
    """沿 x 这一列找「亮块」上下沿＝菜单卡片可见范围。返回 (top, bottom, 内容底线)。"""
    im = Image.open(path).convert("RGB")
    px = im.load()
    pr = h231.panel_rect()
    # 内容底用驱动缓存：窗顶 + 236vp（实测像素法与公式法差 1px，这里只要「窗口界」这条参考线）
    cb = int(pr[1] + 236 * it.st()["scale"])
    ys = []
    for y in range(pr[1], min(im.size[1], pr[1] + pr[3] + 40)):
        r, g, b = px[x, y]
        if (r + g + b) / 3.0 >= CARD_MIN_GRAY:
            ys.append(y)
    if len(ys) < 40:
        return None, None, cb
    return ys[0], ys[-1], cb


def card_xrun(path, ymid, x=640, top=None, bottom=None):
    """卡片真实横向范围＝**在多行里各量一次亮块、取最宽的那次**。
    04:44 实测：只量中间一行会把「行末那个灰蓝色状态胶囊」（#B8C6E8，均值 ≈190 <230）当成块边界，
    量出 x=[237,738]＝143vp，而卡片是 64%×365.7vp≈234vp ⇒ 半张卡被当成背景，文字带也数少了。
    胶囊只占某几行，换几行就撞不到它。"""
    im = Image.open(path).convert("RGB")
    px = im.load()
    W = im.size[0]

    def bright(xx, yy):
        r, g, b = px[xx, yy]
        return (r + g + b) / 3.0 >= CARD_MIN_GRAY

    y0 = int(top) + 4 if top is not None else int(ymid)
    y1 = int(bottom) - 4 if bottom is not None else int(ymid) + 1
    best = None
    step = max(1, (y1 - y0) // 12)
    for y in range(y0, y1, step):
        if not bright(x, y):
            continue
        a = x
        while a > 0 and bright(a - 1, y):
            a -= 1
        b = x
        while b < W - 1 and bright(b + 1, y):
            b += 1
        if best is None or (b - a) > (best[1] - best[0]):
            best = (a, b)
    return best


def vert_strips(path, top, bottom, xa, xb, dark=170, frac=0.55):
    """卡片里**大部分行都暗**的列＝竖条（滚动条滑块/分隔线），不是文字。返回 (列集合, 各列覆盖率)。

    05:07 真机教训：`Scroll().scrollBar(BarState.Auto)` 滚完会留一条 14px 宽的滚动条
    （x=[791,804]，灰度 <170），它把 6 条文字带粘成 1 条 577px 假带 ⇒ 「末行中心」算到行间空白，
    点下去没反应 ⇒ 把修好的菜单误判成「还是被裁」。
    05:11 第一次修没生效的教训：阈值先写 0.85 是**想当然**——滚动条是「滑块」不是「轨道」，
    它只占内容可见比例那一段（实测 y=[2076,2652]＝卡片高的 76%），0.85 一列都没挑中。
    文字列的覆盖率实测 ≤38%（行高 45px / 行距 119px），所以 0.55 分得开，且分得开的余量
    由 `FM 竖条覆盖率` 那行日志当场证明（两档各报一个数），不是靠我再说一遍。"""
    im = Image.open(path).convert("RGB")
    px = im.load()
    ys = list(range(int(top) + 2, int(bottom) - 1, 3))
    n_y = max(1, len(ys))
    hits = {}
    for y in ys:
        for x in range(int(xa), int(xb), 2):
            r, g, b = px[x, y]
            if (r + g + b) / 3.0 < dark:
                hits[x] = hits.get(x, 0) + 1
    cov = {x: c / float(n_y) for x, c in hits.items()}
    return {x for x, c in cov.items() if c >= frac}, cov


def row_bands(path, top, bottom, xr):
    """卡片里的文字带（每行一条）——**只在卡片那段 x 里数暗像素**，并剔掉竖条列。"""
    xa, xb = xr[0] + 8, xr[1] - 8
    skip, cov = vert_strips(path, top, bottom, xa, xb)
    rest = [c for x, c in cov.items() if x not in skip]
    log("FM 竖条覆盖率：剔除 %d 列%s（覆盖 ≥%.2f）／未剔除列最高 %.2f（文字行高/行距）"
        % (len(skip),
           " x=[%d,%d]" % (min(skip), max(skip)) if skip else "",
           0.55, max(rest) if rest else 0.0))
    return it._bands(path, top + 2, bottom - 1, dark=170, min_n=3, x0=xa, x1=xb, skip_x=skip)


def my_verdict(lines):
    p = uniq("verdict", "txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write("H-241r2 `···` 菜单裁切取证（Qoder %s）\n\n" % time.strftime("%H:%M"))
        f.write("\n".join(lines) + "\n")
    log("VERDICT -> %s" % p)
    for ln in lines[-6:]:
        log("  | %s" % ln)
    return p


def find_more_tile():
    """工具栏展开态里挑 `···`：**三个点各自成簇 ⇒ 认「间距很小、连成一条的 ≥3 簇」**，不是「中间那几簇」。

    2026-10-28 04:33 真机教训：旧写法取「最左簇+200 .. 最右簇-60」之间的簇求均值，
    实测展开态九簇是 x=69(‹) 260(undo) 448(redo) 639(光标) 829(剪贴板) 994/1019/1043(···) 1209(▼)，
    那段区间把 829 也吞了进去 ⇒ 均值落在 **828＝剪贴板**，点下去弹的是剪贴板说明条，
    整份「裁切证据」量的其实是别人的浮层。三个点的特征是**簇间距 ≈25px**，别的图标间距 ≈190px。"""
    pr = h231.panel_rect()
    s = h231.screenshot("fm-bar")
    path, cur, band = h231.expand_func_bar(s, pr[1] if pr else 1849)
    if not path:
        return None
    pr = h231.panel_rect()
    clusters, _b = h231.measure_bar(path, pr[1] if pr else 1849)
    if not clusters:
        return None
    cs = sorted(clusters, key=lambda c: c["cx"])
    groups = [[cs[0]]]
    for c in cs[1:]:
        if c["cx"] - groups[-1][-1]["cx"] <= 60:      # 同一枚图标的多个笔画
            groups[-1].append(c)
        else:
            groups.append([c])
    multi = [g for g in groups if len(g) >= 3]
    if not multi:
        log("没认出「≥3 个紧挨小簇」的 `···`，分组=%s" % [[round(c["cx"]) for c in g] for g in groups])
        return None
    if len(multi) > 1:
        log("认出的紧挨组不止一个：%s ⇒ 取最靠右的那个（`···` 在 ▼ 左边，是倒数第二枚）"
            % [[round(c["cx"]) for c in g] for g in multi])
    g = multi[-1]
    cx = sum(c["cx"] for c in g) / len(g)
    cy = sorted(c["cy"] for c in g)[len(g) // 2]
    log("挑出 `···`＝%d 簇均值 (%d,%d)（各簇 x=%s）" % (len(g), cx, cy, [round(c["cx"]) for c in g]))
    return (cx, cy)


def cmd_close():
    pr = h231.panel_rect()
    if pr:
        h231.tap(pr[0] + pr[2] - 40, pr[1] + 40)
        time.sleep(0.6)
    log("CLOSE-FM done")
    return 0


def cmd_check():
    # 04:55 装机后第一次跑就 GUARD-ABORT：`guard` 在 `bring_up` **前面**，而刚装完包自家进程被杀
    # （前台是别人家的 notepad）⇒ 闸门按设计拒绝注入。顺序得反过来：先把**自家 App** 拉到前台
    # （`bring_up` 只启动 BUNDLE 自己、只点自家 TextArea），再让闸门决定能不能落指。
    if h231.keyboard_panel_visible() is not True:
        h231.bring_up()
    if not h231.guard("funcmenu-setup"):
        log("GUARD 不过（没解锁或前台不是自家 App）⇒ 不点")
        return 1
    it.refresh()                      # 面板几何必须现量（缓存的是取证跑完那一次的）
    more = find_more_tile()
    if not more:
        log("FM 结论：工具栏没展开或 `···` 没挑出来 ⇒ 不猜坐标，本轮作废")
        return 1
    log("点 `···` (%d,%d)" % more)
    it.hl("H-241r2 func menu", clear=True, wait=0.2)
    h231.tap(more[0], more[1])
    time.sleep(1.4)
    fm = it.hl(r"H-241r2 func menu opened", wait=0.3)
    p = shot("menu")
    top, bottom, cb = card_span(p)
    if top is None:
        log("FM 结论：没量到亮块（菜单没开？亮阈值 %d）" % CARD_MIN_GRAY)
        my_verdict(["判据：见本文件头", "FM 结论：没量到卡片亮块", "结论：未达判据（量具没看见）"])
        return 1
    pr = h231.panel_rect()
    xr = card_xrun(p, (top + bottom) // 2, top=top, bottom=bottom)
    if not xr:
        log("FM 在 y=%d 这一行没量到「包含 x=640 的亮块」⇒ 卡片不居中或没开" % ((top + bottom) // 2))
        my_verdict(["判据：见本文件头", "FM 结论：量不到卡片横向范围", "结论：未达判据（量具没看见）"])
        return 1
    bands = row_bands(p, top, bottom, xr)
    log("FM 卡片横向 x=[%d,%d] 宽 %dpx（%.1fvp，面板宽 %dpx）"
        % (xr[0], xr[1], xr[1] - xr[0], (xr[1] - xr[0]) / it.st()["scale"], pr[2]))
    log("FM 卡片可见 y=[%d,%d] 高 %dpx（窗口内容底参考线 %d，窗 [%d,%d]）"
        % (top, bottom, bottom - top, cb, pr[1], pr[1] + pr[3]))
    log("FM 卡片内检出 %d 条文字带：%s" % (len(bands), [(b[0], b[1], b[1] - b[0] + 1, b[2]) for b in bands]))
    log("FM 菜单开启日志命中 %d 条%s" % (len(fm), "（本构建没有这条日志 ⇒ 只能靠文字带数认）" if not fm else ""))
    if not fm and len(bands) < 5:
        # 04:33 事故的正闸：把「剪贴板」认成 `···` 时，弹的是两行说明条（1~2 条带），
        # 而开关菜单是 1 标题 + 7 行。带数不够就说明点的不是菜单 —— 别拿别人的浮层当证据。
        log("FM 文字带只有 %d 条且没有菜单开启日志 ⇒ **这弹出来的不是 `···` 菜单**，判据作废重认簇"
            % len(bands))
        my_verdict(["判据：见本文件头", "点 (%d,%d) 后卡片内只有 %d 条文字带，且无 `H-241r2 func menu opened`"
                    % (more[0], more[1], len(bands)), "结论：未达判据（认错了簇，量的不是菜单）"])
        cmd_close()
        return 1
    zbox = [xr[0] - 6, max(pr[1], top - 6), xr[1] + 6, min(cb, bottom) + 6]
    zp = uniq("zoom-card", "png")
    h231.zoom_crop(p, zbox, 1, zp)
    log("FM 卡片放大图 %s box=%s" % (zp, zbox))
    # ---- 先滚到底，再认「末行点得动」（H-241r2 新结构＝外壳定高 + 内层 Scroll）----
    # 旧口径「首屏最底一条带＝设置行」只有在**坏布局**下才成立（那时 8 行硬塞 236vp，设置行整行在窗外）。
    # 修好之后首屏只显 6 条带（标题 + 5 行），设置行本来就在折叠区里 ⇒ 判据得跟着改成
    # 「滚到底 ⇒ 它出现且点得动」；不改就会把「按设计可滚」判成「还是被裁」＝假阴性。
    scrolls = []
    bands_first = len(bands)
    top0, bottom0 = top, bottom          # 首屏几何（滚动会覆盖，判据要留两份）
    for i in range(3):
        prev = bands[-1][1] if bands else 0
        cx = (xr[0] + xr[1]) // 2
        if not h231.guard("funcmenu-scroll%d" % (i + 1)):
            break
        drv.drag(cx, bottom - 60, cx, top + 60, 1200)
        time.sleep(1.0)
        p = shot("menu-scrolled%d" % (i + 1))
        top, bottom, cb = card_span(p)
        xr = card_xrun(p, (top + bottom) // 2, top=top, bottom=bottom) or xr
        bands = row_bands(p, top, bottom, xr)
        now = bands[-1][1] if bands else 0
        scrolls.append((prev, now, len(bands)))
        log("FM 第 %d 次上滚：末带 %d → %d，检出 %d 条带，卡片底 %d" % (i + 1, prev, now, len(bands), bottom))
        if bands and now >= bottom - 70:       # 末行贴到卡片底（卡片有 6vp 下内边距）⇒ 已到底
            break
        if now == prev:                         # 拖了不动 ⇒ 也当到底（边界/惯性用尽）
            break
    # 滚到底后的卡片放大图（`设置` 行应当出现在这张里，改后判定的肉眼证据）
    zp2 = zp
    if scrolls:
        zp2 = uniq("zoom-end", "png")
        zbox2 = [xr[0] - 6, max(pr[1], top - 6), xr[1] + 6, min(cb, bottom) + 6]
        h231.zoom_crop(p, zbox2, 1, zp2)
        log("FM 滚到底放大图 %s box=%s" % (zp2, zbox2))
    # 点最底一条带的中心
    hit = None
    if bands:
        a, b, _pk = bands[-1]
        hit = (((xr[0] + xr[1]) // 2, (a + b) // 2))
        it.hl("H-241 settings panel opened", clear=True, wait=0.2)
        log("FM 点最底一条带中心 (%d,%d) 该行高 %dpx" % (hit[0], hit[1], b - a + 1))
        if not h231.guard("funcmenu-tap-last"):
            return 1
        h231.tap(hit[0], hit[1])
        time.sleep(1.0)
        got = it.hl("H-241 settings panel opened", wait=0.4)
        p2 = shot("after-tap")
        t2, b2, cb2 = card_span(p2)
        log("FM 点完 hilog 命中 %d 条；再截一屏（卡片亮块 %s）" % (len(got), (t2, b2) if t2 else "无"))
        opened = len(got) > 0
    else:
        opened = False
    scale = it.st()["scale"]
    fits = (bottom <= cb + 2) and (top >= pr[1] - 2) and (bottom - top) <= 236 * scale + 2
    clipped = not fits
    lines = [
        "判据（本文件头）：卡片整块必须在面板窗口内容区内（顶 ≥ 窗顶、底 ≤ 内容底、高 ≤ 236vp），"
        "且**滚到底后**最底一行点得动（`H-241 settings panel opened`）。",
        "卡片横向 x=[%d, %d]（%.1fvp，面板 %dpx）；文字带只在这段 x 内数"
        % (xr[0], xr[1], (xr[1] - xr[0]) / scale, pr[2]),
        "首屏卡片可见 y=[%d, %d] 高 %dpx（%.1fvp）＝检出 %d 条文字带"
        % (top0, bottom0, bottom0 - top0, (bottom0 - top0) / scale, bands_first),
        "滚到底卡片可见 y=[%d, %d] 高 %dpx；窗口内容底参考线=%d（窗顶 %d，密度 %.4f px/vp）"
        % (top, bottom, bottom - top, cb, pr[1], scale),
        "滚动轨迹（次数：末带上沿 前→后，检出条数）：%s"
        % (", ".join("#%d: %d→%d, %d条" % (i + 1, a, b, n) for i, (a, b, n) in enumerate(scrolls))
           or "没滚（首屏已到底或闸门拒绝）"),
        "末屏卡片内 %d 条文字带（起,止,高,峰值暗像素）：%s"
        % (len(bands), [(b[0], b[1], b[1] - b[0] + 1, b[2]) for b in bands]),
        "点最底一条带 (%s) ⇒ `H-241 settings panel opened` %s"
        % (("%d,%d" % hit) if hit else "没点到", "命中" if opened else "没命中"),
        "菜单开启日志 `H-241r2 func menu opened`：%s"
        % ("命中 %d 条（证明弹的确实是 `···` 菜单，不是别的浮层）" % len(fm) if fm
           else "无 ⇒ 本构建还没这条日志，只能靠 ≥5 条文字带 + 放大图人工确认"),
        "放大图：首屏 %s ／ 滚到底 %s" % (zp, zp2),
        "结论：%s" % ("PASS（菜单整单进窗、滚到底后末行点得动）" if (opened and not clipped)
                     else "卡片出窗（%s）或末行点不动（opened=%s）⇒ 这就是 H-241r2 登记的裁切"
                          % ("顶/底/高越界" if clipped else "在窗内", opened)),
    ]
    my_verdict(lines)
    cmd_close()
    return 0


def main():
    drv.setup()
    what = sys.argv[1] if len(sys.argv) > 1 else "check"
    if what == "close":
        return cmd_close()
    return cmd_check()


if __name__ == "__main__":
    sys.exit(main())
