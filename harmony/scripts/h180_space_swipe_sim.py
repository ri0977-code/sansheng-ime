#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-180 空格滑移光标的「余量结转」不变式（Qoder，2026-10-26）

为什么写：空格滑移光标用「累计位移 / 步长」算走了几格。这类实现最常见的缺陷是
**每次 Move 都重新计数、丢掉不足一步的余量**——慢速滑动（每帧 2–3vp）时一步都走不出来，
用户会觉得「滑了半天没反应」。安卓口径（fcitx5-android `BaseKeyboard.kt`）：

    selectionSwipeThreshold = dp(10f)
    unconsumed = current - last + carry;  remains = unconsumed % threshold
    count = (unconsumed / threshold).toInt();  carry = remains

本脚本把 KeyboardIndex.ets 里的 `spaceSwipeHandle()` 累计逻辑照抄成 Python，
断言五条不变式：
  ① 粒度无关：同一段 50vp 的位移，无论拆成 1 次还是 50 次 Move，都走 5 格；
  ② 往返对称：0→+50→0 共走 5 右 + 5 左，净位移 0；
  ③ 方向符号：accum>0 走右（4），<0 走左（3），与 InputClient.moveCursorSync 同口径；
  ④ 抖动 3vp 不上屏、不移格；
  ⑤ 余量不跨手势（抬手清零，安卓 resetState 同口径）。

外加 H-186 的 ⑥：**只有 Down/Up、没有任何 Move** 的手势（真机快甩、`uitest swipe` 注入）
也必须按起点→终点满额结算 —— 老实现（只在 Move 里累计）在这里会 0 格。

负控两条：去掉「余量结转」必须让①变红；去掉「Up 补位移」必须让⑥变红。

用法：python scripts/h180_space_swipe_sim.py [--selftest]
"""
import sys

STEP = 10.0   # vp，与 KeyboardIndex.ets 的 SPACE_CURSOR_STEP 同值


class Swiper:
    """照抄 spaceSwipeHandle(): Down 清账、Move 累计并结转余量、Up 不清账（由 onClick 消费）。"""

    def __init__(self, step=STEP, carry=True):
        self.step = step
        self.carry = carry
        self.last = -1.0
        self.accum = 0.0
        self.steps = []          # 正数=右，负数=左
        self.swipe_done = False

    def down(self, x):
        self.last = x
        self.accum = 0.0
        self.swipe_done = False

    def move(self, x):
        if self.last < 0:
            return
        delta = x - self.last
        self.last = x
        self._consume(delta)

    def up(self, x=None):
        # H-186：抬手前把最后一段位移补进来（与 KeyboardIndex.ets 同步）。
        # 真手指快甩时 Move 可能很稀疏，注入工具（uitest swipe）常常只给 Down/Up——
        # 不补这一下会「滑了光标不动」。补完按同一取整逻辑结算，余量随后清零（resetState）。
        if x is not None and self.last >= 0:
            self._consume(x - self.last)
            self.last = x
        self.last = -1.0
        self.accum = 0.0
        return self.swipe_done

    def _consume(self, delta):
        self.accum = (self.accum + delta) if self.carry else delta
        while abs(self.accum) >= self.step:
            direction = 4 if self.accum > 0 else 3      # 4=右 3=左，同 moveCursorSync
            self.steps.append(1 if direction == 4 else -1)
            self.accum -= self.step if self.accum > 0 else -self.step
            self.swipe_done = True

    def click_commits_space(self):
        """onClick 是否会上屏空格：滑过的这一下被 spaceSwipeDone 拦住。"""
        if self.swipe_done:
            self.swipe_done = False
            return False
        return True


def run_path(sw, xs):
    sw.down(xs[0])
    for x in xs[1:]:
        sw.move(x)
    return sw.up(xs[-1])


def main():
    fails = []

    # ① 粒度无关：0→50 一次到位 vs 每 1vp 一次
    coarse = Swiper()
    run_path(coarse, [0.0, 50.0])
    fine = Swiper()
    run_path(fine, [float(i) for i in range(0, 51)])
    if len(coarse.steps) != 5:
        fails.append("①一次滑到位 50vp 应走 5 格，实际 %d" % len(coarse.steps))
    if len(fine.steps) != 5:
        fails.append("①每帧 1vp 滑到 50vp 应走 5 格，实际 %d（余量被丢？）" % len(fine.steps))
    if not all(s == 1 for s in coarse.steps + fine.steps):
        fails.append("①向右滑出现左移步")

    # ② 往返对称：0→50→0
    rnd = Swiper()
    run_path(rnd, [0.0] + [float(i) for i in range(1, 51)] + [float(i) for i in range(49, -1, -1)])
    right = sum(1 for s in rnd.steps if s > 0)
    left = sum(1 for s in rnd.steps if s < 0)
    if (right, left) != (5, 5):
        fails.append("②往返应 5 右 + 5 左，实际 %d 右 + %d 左" % (right, left))
    if rnd.click_commits_space():
        fails.append("②滑过之后的那次抬手不得上屏空格")

    # ③ 方向与 InputClient.moveCursorSync 口径一致（3=左 4=右），负位移走左
    lft = Swiper()
    run_path(lft, [100.0] + [100.0 - i for i in range(1, 31)])
    if not all(s == -1 for s in lft.steps) or len(lft.steps) != 3:
        fails.append("③向左滑 30vp 应 3 步全向左，实际 %r" % (lft.steps,))

    # ④ 没滑过的短按必须出空格
    tap = Swiper()
    tap.down(200.0)
    tap.move(203.0)      # 手指抖动 3vp，不足一步
    tap.up()
    if len(tap.steps) != 0:
        fails.append("④抖动 3vp 不该移光标")
    if not tap.click_commits_space():
        fails.append("④短按必须上屏空格（防误吞）")

    # ⑤ 余量不跨手势：抬手后余量必须清零（安卓 resetState 同口径）。
    #    两次各 9vp 的独立手势 = 0 步；若把上次的 9 结转过来就会凑成 1 步，属于错。
    carry_left = Swiper()
    run_path(carry_left, [0.0, 9.0])
    run_path(carry_left, [100.0, 109.0])
    if len(carry_left.steps) != 0:
        fails.append("⑤余量跨手势残留：两次各 9vp 的手势不该凑出一步，实际 %d" % len(carry_left.steps))

    # ⑥ H-186：注入/快甩只给 Down+Up（无 Move）也必须走满额位移。
    #    25vp 一次到位应走 2 格（余 5vp 丢弃，安卓 resetState 同口径）。
    only_ends = Swiper()
    only_ends.down(0.0)
    only_ends.up(25.0)
    if len(only_ends.steps) != 2:
        fails.append("⑥只有 Down/Up 的 25vp 滑动应走 2 格，实际 %d（Up 没补最后一段？）" % len(only_ends.steps))
    if only_ends.click_commits_space():
        fails.append("⑥只给 Down/Up 的滑动不得上屏空格")

    # 负控：去掉余量结转，① 的慢速滑动必须走不满 5 格
    bad = Swiper(carry=False)
    run_path(bad, [float(i) for i in range(0, 51)])
    if len(bad.steps) == 5:
        fails.append("负控失效：不结转余量的实现竟也走了 5 格，自测抓不到这类缺陷")

    # 负控（H-186）：Up 不补最后一段的老实现，⑥ 必须变红
    class OldSwiper(Swiper):
        def up(self, x=None):
            self.last = -1.0
            self.accum = 0.0
            return self.swipe_done

    old = OldSwiper()
    old.down(0.0)
    old.up(25.0)
    if len(old.steps) != 0:
        fails.append("负控失效：老的「Up 不补位移」实现也走出了 %d 格，⑥ 抓不到 H-186" % len(old.steps))

    if fails:
        for f in fails:
            print("[FAIL] " + f)
        print("结论：FAIL（%d 项）" % len(fails))
        return 1
    print("空格滑移不变式：PASS（粒度无关 5 格 / 往返 5+5 / 向左 3 步 / 抖动不上屏 / 余量不跨手势 / 只有 Down+Up 也走满 2 格）")
    print("负控：不结转余量的实现走不满 5 格；Up 不补位移的老实现 0 格 —— 自测有牙齿")
    return 0


if __name__ == "__main__":
    sys.exit(main())
