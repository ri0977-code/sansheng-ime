# 复现 H-168 gridFlip 边界逻辑（与 KeyboardIndex.ets 一致），验证 CodeArts 的结论
def step_for(w):  # H-202: gridCols = 2 (w>=300) / 1；gridRows = 3 ⇒ page = cols*3
    return (2 if w >= 300 else 1) * 3

def old_flip(off, ln, step, direction):
    maxOff = max(0, ln - step)
    if direction > 0 and off + step <= maxOff:
        return off + step
    if direction < 0 and off - step >= 0:
        return off - step
    return None

def new_flip(off, ln, step, direction):
    maxOff = max(0, ln - step)
    if direction > 0 and off < maxOff:
        return min(off + step, maxOff)
    if direction < 0 and off > 0:
        return max(off - step, 0)
    return None

def btn_shows_next(off, ln, step):
    return off + step < ln   # 「下一页」按钮的显示条件

def reachable(ln, step, flip):
    seen, off = set(), 0
    while True:
        seen.add(off)
        nxt = flip(off, ln, step, 1)
        if nxt is None or nxt in seen:
            break
        off = nxt
    # 反向也走一遍
    seen2, off2 = set(), off
    while True:
        seen2.add(off2)
        nxt = flip(off2, ln, step, -1)
        if nxt is None or nxt in seen2:
            break
        off2 = nxt
    return seen | seen2

def covered(offsets, ln, step):
    cov = set()
    for o in offsets:
        cov |= set(range(o, min(o + step, ln)))
    return cov

print("%-5s %-5s | %-34s | %-34s" % ("len","step","OLD reachable/dead/miss","NEW reachable/dead/miss"))
print("-"*112)
bad_old = bad_new = 0
for ln in (13, 20, 50, 42, 8, 9, 16, 17, 25):
    for w in (360, 320, 480):
        step = step_for(w)
        o_off = reachable(ln, step, old_flip)
        n_off = reachable(ln, step, new_flip)
        # 死按钮：按钮显示「下一页」但点不动（正向 flip 返回 None）
        o_dead = [o for o in o_off if btn_shows_next(o, ln, step) and old_flip(o, ln, step, 1) is None]
        n_dead = [o for o in n_off if btn_shows_next(o, ln, step) and new_flip(o, ln, step, 1) is None]
        o_miss = set(range(ln)) - covered(o_off, ln, step)
        n_miss = set(range(ln)) - covered(n_off, ln, step)
        if o_miss or o_dead: bad_old += 1
        if n_miss or n_dead: bad_new += 1
        print("%-5d %-5d | off=%-20s dead=%-6s miss=%d | off=%-20s dead=%-6s miss=%d" % (
            ln, step, sorted(o_off), (o_dead or 'none'), len(o_miss),
            sorted(n_off), (n_dead or 'none'), len(n_miss)))
print("-"*112)
print("BAD combos: OLD=%d/27  NEW=%d/27" % (bad_old, bad_new))

# ---------------------------------------------------------------------------
# H-174/H-178：屏数不变式——gridScreenCount() 必须与 gridFlip 的 maxOff 口径一致。
# 旧式 ceil(len/step) 会把「末屏正好满屏」的场景多算一屏：50/8 → 7 屏，而
# maxOff=42 ⇒ 第 6 屏（offset 42..49 正好 8 格）之后无可翻 offset，第 7 屏永不可达
# ⇒ 界面显示 6/7 而 7 永远点不到。新式 floor(maxOff/step)+1 与可达 offset 一一对应。
def screen_count_old(ln, step):
    return max(1, -(-ln // step))                 # ceil

def screen_count_new(ln, step):
    maxOff = max(0, ln - step)
    return max(1, maxOff // step + 1)

fails = 0
for ln in (0, 1, 7, 8, 9, 16, 17, 25, 42, 49, 50):
    for w in (360, 320, 480):
        step = step_for(w)
        # 可达屏数（1 起算）＝可达 offset 里 off//step 的最大值 + 1
        offs = reachable(ln, step, new_flip)
        reach_screens = (max(o // step for o in offs) + 1) if offs else 1
        new_n = screen_count_new(ln, step)
        if new_n != reach_screens:
            fails += 1
            print("FAIL len=%d step=%d 屏数=%d 可达屏数=%d" % (ln, step, new_n, reach_screens))
# 已知坏样本负控（与当前步长无关，固定用 H-174 当时的 step=8 复算）：
# 旧式 ceil(50/8) 必须报 7（比可达 6 多一），证明「屏数公式」这条检查本身有牙齿。
if screen_count_old(50, 8) != 7:
    fails += 1
    print("FAIL 负控失效：旧式 ceil(50/8) 不再报 7，自测没有牙齿了")
print("屏数不变式：%s（floor(maxOff/step)+1 == 可达屏数；负控 ceil(50/8)=7 仍成立）"
      % ("PASS" if fails == 0 else "FAIL %d 例" % fails))
