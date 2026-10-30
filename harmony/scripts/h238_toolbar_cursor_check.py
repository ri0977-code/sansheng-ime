# -*- coding: utf-8 -*-
"""顶栏「文本编辑」⇆ 那枚的底色，在开／折前后到底变不变（Qoder，2026-10-28 01:2x）。

主人纠正：他说的灰底选中态是**顶栏那枚 ⇆**，不是键面 n 键。我此前量错了对象。
本脚本只量 ⇆ 图标盒的底色众数，四条路径各来一遍：
  P1 展开工具栏（还没开面板）
  P2 点 ⇆ 开面板
  P3 再点一次 ⇆ 折叠（主人最常用的那条：H-228 加的「再点即折叠」）
  P4 点 ⇆ 开面板 → 点 ‹ 折叠（我上一轮量的是这条）
参照色：常态栏底 #F2F3F5=(242,243,245)；按压态 #DCE2EC=(220,226,236)；BG_ACTIVE #B8C6E8=(184,198,232)。

两种跑法（每次各落一个带时间戳的子目录，复跑不许吃掉上一次取证）：
  python scripts/h238_toolbar_cursor_check.py          # 四条路径的底色对账（P1~P4）
  python scripts/h238_toolbar_cursor_check.py press    # P5 正控：按住那一帧必须还是按压色
"""
import io
import os
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h234_236_device_check as m          # noqa: E402
import h231_panel_check as h231            # noqa: E402
from PIL import Image                       # noqa: E402

BAR_Y = (1905, 1922)                         # ⇆ 图标盒内、字形上方的一条（01:1x 用 s1/s5 反推）
REF = {(242, 243, 245): u"常态栏底", (220, 226, 236): u"按压色 #DCE2EC", (184, 198, 232): u"BG_ACTIVE"}
RUN = m.EVID                                # use_run_evid() 会把它换成带时间戳的子目录


def use_run_evid():
    """每次跑单独落一个 `h238-run-<时分秒>/` 子目录。
    为什么要加这一层：01:10 修完复跑时，同名截图把 01:03 **修复前复现**那几张直接覆盖了
    （`t1-panel-open.jpeg` / `t3-folded-by-cursor.jpeg` / `T-*.png` 全没了，且那批文件当时
    还没提交 ⇒ git 里也捞不回来）。修复前的**数值**还逐条留在本文件与代码注释里，但画面证据
    确实丢了，这是本轮第 4 个量具错，与 H-144「归档目标从没存在过＝这一步从没跑过」同一类：
    复跑不许吃掉上一次取证。"""
    global RUN
    m.use_evid()
    RUN = os.path.join(m.EVID, "h238-run-" + time.strftime("%H%M%S"))
    os.makedirs(RUN, exist_ok=True)
    h231.EVID = RUN
    h231.LOG = os.path.join(RUN, "run.log")
    return RUN


def write_verdict(fname, lines):
    with io.open(os.path.join(RUN, fname), "w", encoding="utf-8") as f:
        f.write(u"\n".join(lines) + u"\n")



def name_of(rgb):
    for k, v in REF.items():
        if all(abs(a - b) <= 6 for a, b in zip(rgb, k)):
            return v
    return u"未知色"


def at(shot, cx):
    im = Image.open(shot).convert("RGB")
    px = im.load()
    x0, x1 = cx - 40, cx + 40
    c = Counter(px[x, y] for x in range(x0, x1, 2) for y in range(BAR_Y[0], BAR_Y[1], 2))
    rgb, n = c.most_common(1)[0]
    return rgb, n * 4


def press():
    """P5 正控：**按下那一瞬间**的高亮、**面板开着时**的选中色、**折叠后**回到常态，一次跑全。

    为什么必须分两次发 Down/Up：`uitest uiInput click` 是整次手势，拿不到按下与抬手之间那一帧。
    01:1x 第一版只验到「抬手后恢复」，结果把选中色一起砍掉了（主人 01:2x「现在连选中都没有颜色了！」）
    ⇒ 从此这条正控盯三层：**按下＝按压浅灰 #DCE2EC → 抬手（面板开）＝选中色 BG_ACTIVE → 再按再抬（面板关）＝栏底**。
    """
    use_run_evid()
    L = []
    st, why = h231.locked_state()
    L.append(u"P5 正控｜锁屏=%s（%s）｜取证目录 %s" % (st, why, os.path.basename(RUN)))
    if st != u"unlocked":
        print(u"\n".join(L))
        return 1
    h231.bring_up()
    top = m.key_area_top()
    s = h231.screenshot("p0-keys")
    _bar, cursor, _band = h231.expand_func_bar(s, top)
    assert cursor, u"没量到 ⇆"
    cx, cy = int(cursor["cx"]), int(cursor["cy"])

    def press_release(tag):
        h231.guard(u"p-" + tag) and h231.sh("shell", "uinput", "-T", "-d", str(cx), str(cy))
        time.sleep(0.35)
        down = h231.screenshot(tag + "-pressing")
        rgb_d = at(down, cx)
        h231.sh("shell", "uinput", "-T", "-u", str(cx), str(cy))
        time.sleep(1.4)
        up = h231.screenshot(tag + "-after-up")
        return down, rgb_d, up, at(up, cx)

    s1, rgb1, s2, rgb2 = press_release("p1")
    L.append(u"P5a 按住（开面板前，uinput -T -d %d %d）：⇆ 盒底色 %s（%s，%d px）"
             % (cx, cy, rgb1[0], name_of(rgb1[0]), rgb1[1]))
    L.append(u"P5b 抬手＝面板开着：⇆ 盒底色 %s（%s，%d px）" % (rgb2[0], name_of(rgb2[0]), rgb2[1]))
    s3, rgb3, s4, rgb4 = press_release("p3")
    L.append(u"P5c 再按住（要折叠）：⇆ 盒底色 %s（%s，%d px）" % (rgb3[0], name_of(rgb3[0]), rgb3[1]))
    L.append(u"P5d 再抬手＝已折叠：⇆ 盒底色 %s（%s，%d px）" % (rgb4[0], name_of(rgb4[0]), rgb4[1]))
    ok = (name_of(rgb1[0]) == u"按压色 #DCE2EC" and name_of(rgb2[0]) == u"BG_ACTIVE"
          and name_of(rgb3[0]) == u"按压色 #DCE2EC" and name_of(rgb4[0]) == u"常态栏底")
    L.append(u"P5 判定：%s（按下有浅灰 / 开着有选中色 / 折叠后回到栏底）" % (u"PASS" if ok else u"FAIL"))
    for tag, p in ((u"p0-前", s), (u"p1-按住", s1), (u"p2-开着", s2), (u"p3-再按住", s3), (u"p4-折叠", s4)):
        Image.open(p).convert("RGB").crop((cx - 70, 1880, cx + 70, 1970)) \
            .resize((420, 270), Image.LANCZOS).save(os.path.join(RUN, "P5-" + tag + u".png"))
    write_verdict(u"verdict-toolbar-press.txt", L)
    print(u"\n".join(L))
    return 0 if ok else 1


def main():
    use_run_evid()
    L = []
    st, why = h231.locked_state()
    L.append(u"锁屏=%s（%s）｜取证目录 %s" % (st, why, os.path.basename(RUN)))
    if st != u"unlocked":
        print(u"\n".join(L))
        return 1
    h231.bring_up()
    top = m.key_area_top()
    s = h231.screenshot("t0-keys")
    bar, cursor, band = h231.expand_func_bar(s, top)
    assert cursor, u"没量到 ⇆"
    cx = cursor["cx"]
    L.append(u"P1 展开工具栏（未开面板）：⇆ 盒底色 %s = %s（%s）" % (cx, at(bar, cx), name_of(at(bar, cx)[0])))
    shots = [(u"P1 工具栏展开", bar)]

    h231.guard(u"t-open") and h231.tap(cx, cursor["cy"])
    time.sleep(1.8)
    s2 = h231.screenshot("t1-panel-open")
    shots.append((u"P2 点 ⇆ 开面板", s2))
    L.append(u"P2 点 ⇆ 开面板：⇆ 盒底色 %s" % (at(s2, cx),))

    # P3：再点一次 ⇆ 折叠（这条是主人最常用的「折叠」）
    # 01:21 复跑发现：面板开着时 measure_bar 会把**面板自己的格子**也算成簇，cl[3] 落到了 829（剪贴板列，
    # 采到系统粘贴徽章的蓝 (10,88,246)）⇒ 那是量具瞄错，不是画面没变。⇆ 在开/合之间坐标不动
    # （P5c/P5d 用同一个点按两下：开着→折叠，颜色 BG_ACTIVE→栏底，已证），所以这里直接用 P1 的量值。
    cl, _b = h231.measure_bar(h231.screenshot("t2-bar-reopen"), m.key_area_top() or top)
    cur2 = cursor
    L.append(u"P3 折叠改用 P1 坐标 %d（面板开着时重测簇会串到面板格子上，见脚本注释）" % int(cur2["cx"]))
    h231.guard(u"t-fold-by-cursor") and h231.tap(cur2["cx"], cur2["cy"])
    time.sleep(1.8)
    s3 = h231.screenshot("t3-folded-by-cursor")
    shots.append((u"P3 再点 ⇆ 折叠", s3))
    L.append(u"P3 再点 ⇆ 折叠（⇆ 现量于 %d）：⇆ 盒底色 %s" % (cur2["cx"], at(s3, cur2["cx"])))

    # P4：开面板 → 点 ‹ 折叠（上一轮量的是这条）
    cl2, _b2 = h231.measure_bar(h231.screenshot("t3b-bar"), m.key_area_top() or top)
    cur3 = cl2[3] if len(cl2) >= 4 else cursor
    h231.guard(u"t-open-2") and h231.tap(cur3["cx"], cur3["cy"])
    time.sleep(1.6)
    s4 = h231.screenshot("t4-panel-open-2")
    cl3, _b3 = h231.measure_bar(h231.screenshot("t4b-bar"), m.key_area_top() or top)
    left = cl3[0] if cl3 else None
    if left:
        h231.guard(u"t-fold-by-chevron") and h231.tap(left["cx"], left["cy"])
        time.sleep(1.8)
        s5 = h231.screenshot("t5-folded-by-chevron")
        shots.append((u"P4 点 ‹ 折叠", s5))
        L.append(u"P4 点 ‹ 折叠：⇆ 盒底色 %s（注：‹ 会把工具栏整个收起，⇆ 那排已经不在了 ⇒ 这条只能看栏底）"
                 % (at(s5, cur3["cx"]),))
    write_verdict(u"verdict-toolbar-cursor.txt", L)
    print(u"\n".join(L))
    for tag, p in shots:
        im = Image.open(p).convert("RGB")
        o = os.path.join(RUN, u"T-" + os.path.basename(p).replace(u".jpeg", u"") + u".png")
        im.crop((int(cur3["cx"]) - 70, 1880, int(cur3["cx"]) + 70, 1970)).resize((420, 270), Image.LANCZOS).save(o)
    return 0


if __name__ == "__main__":
    # 无参 = 四条路径底色对账；`press` = 按下那一帧的正控（uinput 分两次发 Down/Up）
    raise SystemExit(press() if "press" in sys.argv[1:] else main())
