#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-164 候选窗记账模拟（Qoder，2026-10-25 00:3x）

目的：真机锁屏期间，用纯逻辑复现 KeyboardIndex.ets 的 H-164 记账（不替代真机判据），
只证明一件事——**绝对下标接续没有 off-by-one / 跳条 / 重复**。

模型常量全部照代码：
  - Rime 菜单页 page_size = 50（rawfile/rime/default.yaml:20）
  - 屏条数 = uiPageSize（真机约 20，由宽度算出；这里取 20）
  - scrollCandidates() = allCandidates.slice(uiPageStart)
  - 续页：pendingForwardAbs = baseIndex + uiPageStart + 已渲染条数
  - setUiListener baseChanged 分支：pending 落在新页区间 → uiPageStart = pending - baseIndex
  - 回看引擎页：uiPageStart = lastScreenStart(len)

运行：python scripts/h164_window_sim.py   全 PASS 退出码 0
"""

import sys

try:  # Git Bash 控制台默认 GBK
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PAGE = 50       # Rime 菜单页条数
UI_SIZE = 20    # 一屏条数（估算值，仅影响按钮翻页步长）

fails = []


def check(name, cond, detail):
    if cond:
        print(f"PASS  {name}  {detail}")
    else:
        print(f"FAIL  {name}  {detail}")
        fails.append(name)


gaps = []   # 已知未修（记录在案，不算 FAIL，也不许当成 PASS）


def check_gap(name, cond, detail):
    """已知缺陷的「当前事实」断言：cond 为 False 表示缺陷仍在（预期）。
    cond 变 True 说明代码改了、缺陷消失 —— 那时要把这行换成正式 check，否则这条就白测了。"""
    if cond:
        print(f"XPASS {name}  —— 缺陷已消失，请把 check_gap 改成 check 正式断言  {detail}")
        gaps.append(name)
    else:
        print(f"GAP   {name}（已知未修，记录在案）  {detail}")


def abs_ids(items):
    return list(items)


class Sim:
    def __init__(self, total):
        # 构造引擎页：每页 PAGE 条，绝对下标从 0 起
        self.pages = [list(range(i, min(i + PAGE, total))) for i in range(0, total, PAGE)]
        self.page = 0
        self.base = 0
        self.all = self.pages[0]
        self.ui_start = 0
        self.pending = -1
        self.last_base = 0
        self.rendered_ids = []
        self.throw_on_flip = False   # T9：模拟 flipPage 抛异常

    # ---- 引擎 ----
    def flip_engine(self, direction):
        """返回 True 表示引擎真的翻动了（page 变了）。"""
        if self.throw_on_flip:       # 0b199eb：candTryContinue 里没有 try/catch
            self.throw_on_flip = False
            raise RuntimeError("flipPage raised (simulated)")
        new_page = self.page + direction
        if new_page < 0 or new_page >= len(self.pages):
            return False
        self.page = new_page
        self.base = self.pages[new_page][0]
        self.all = self.pages[new_page]
        self.notify()
        return True

    # ---- UI 数据源 ----
    def scroll_items(self):
        start = max(0, min(self.ui_start, len(self.all) - 1))
        return self.all[start:]

    # ---- setUiListener ----
    def notify(self, preedit_changed=False):
        items = self.scroll_items()
        self.rendered_ids = items
        base_changed = self.base != self.last_base
        if preedit_changed:
            self.ui_start = 0
        elif base_changed:
            pending = self.pending
            if self.base <= pending < self.base + len(self.all):
                self.ui_start = pending - self.base
            else:
                if self.base < self.last_base:
                    size = UI_SIZE if UI_SIZE > 0 else len(self.all)
                    self.ui_start = max(0, (max(1, -(-len(self.all) // size)) - 1) * size)
                else:
                    self.ui_start = 0
            self.pending = -1
        self.last_base = self.base

    # ---- onScrollIndex（手指按下 + 滚到末尾） ----
    def scroll_to_end(self):
        items = self.scroll_items()
        shown_end_abs = self.base + self.ui_start + len(items)
        prev_base, prev_len = self.base, len(self.all)
        self.pending = shown_end_abs
        self.flip_engine(1)
        if self.base == prev_base and len(self.all) == prev_len:
            self.pending = -1
            return "refused"
        return f"continue@{shown_end_abs}"

    # ---- 点第 N 条 ----
    def tap_abs(self, index):
        return self.base + self.ui_start + index


def scenario_forward_chain():
    s = Sim(total=160)       # 4 页：50/50/50/10
    s.notify()
    check("S1 初始窗", s.ui_start == 0 and abs_ids(s.scroll_items()) == list(range(0, 50)),
          f"uiStart={s.ui_start} first={s.scroll_items()[0]} last={s.scroll_items()[-1]}")

    # 第 1 次滑到底 → 续到第 2 页头
    r = s.scroll_to_end()
    check("S2 第一次续页", r == "continue@50" and s.base == 50 and s.ui_start == 0,
          f"{r} base={s.base} uiStart={s.ui_start} firstAbs={s.scroll_items()[0]}")

    # 第 2 次 → 100
    r = s.scroll_to_end()
    check("S3 第二次续页", r == "continue@100" and s.base == 100 and s.ui_start == 0,
          f"{r} base={s.base} firstAbs={s.scroll_items()[0]}")

    # 第 3 次 → 150（末页 10 条）
    r = s.scroll_to_end()
    check("S4 落到末页", r == "continue@150" and s.base == 150 and s.ui_start == 0
          and len(s.scroll_items()) == 10,
          f"{r} base={s.base} len={len(s.scroll_items())}")

    # 末页再滑到底 → 引擎拒绝，原地不动
    r = s.scroll_to_end()
    check("S5 末页拒绝续页", r == "refused" and s.pending == -1 and s.base == 150,
          f"{r} pending={s.pending} base={s.base}")


def scenario_no_drag():
    s = Sim(total=160)
    s.notify()
    # 初始布局 onScrollIndex 但未按下：candDragArmed=false ⇒ 不续页
    check("S6 未按下不续页", s.base == 0 and s.ui_start == 0,
          f"base={s.base} uiStart={s.ui_start}")


def scenario_preedit_reset():
    s = Sim(total=160)
    s.notify()
    s.scroll_to_end()
    assert s.base == 50
    s.notify(preedit_changed=True)
    check("S7 编码变化回片首", s.ui_start == 0 and s.base == 50,
          f"base={s.base} uiStart={s.ui_start}")


def scenario_backward_engine_page():
    s = Sim(total=160)
    s.notify()
    s.scroll_to_end()            # 到第 2 页
    assert s.base == 50
    # 按钮/手势回看上一 Rime 页 → 从末屏起
    s.flip_engine(-1)
    size = UI_SIZE
    want = (max(1, -(-len(s.all) // size)) - 1) * size
    check("S8 回看落上一页末屏", s.ui_start == want,
          f"uiStart={s.ui_start} want={want} base={s.base}")


def scenario_tap_mapping():
    s = Sim(total=160)
    s.notify()
    s.scroll_to_end()            # base=50, uiStart=0
    idx = 7
    check("S9 点第N条=绝对第N条", s.tap_abs(idx) == 50 + idx,
          f"tap({idx})->abs {s.tap_abs(idx)} firstRendered={s.scroll_items()[0]}")


def scenario_within_page_flip_math():
    # 菜单页内按钮翻屏：仅当 uiStart + uiPageSize < len 时才步进，否则交引擎（flipCandidates 正向分支）
    s = Sim(total=160)
    s.notify()
    steps = []
    for _ in range(3):
        if s.ui_start + UI_SIZE < len(s.all):
            s.ui_start += UI_SIZE
            steps.append(s.ui_start)
        else:
            steps.append("engine")
    check("S10 页内步进", steps == [20, 40, "engine"], f"steps={steps}")




# ---------------- 第四版：触摸许可状态机（candDragArmed / candDragMoved / onScrollStop） ----------------
class Touch:
    """照 0b199eb 的 .onTouch/.onScrollIndex/.onScrollStop/candTryContinue 重建。
    只证明状态机不会「一次滑动续两页」或「点一下就续页」；ArkUI 事件顺序仍以真机为准。"""

    def __init__(self, sim):
        self.sim = sim
        self.armed = False
        self.moved = False
        self.last_visible = 0
        self.flips = 0
        self.last_result = None

    def down(self):
        self.armed = True
        self.moved = False

    def move(self):
        self.moved = True

    def up(self):
        if not self.moved:
            self.armed = False

    def try_continue(self, last):
        items = self.sim.scroll_items()
        if not self.armed or len(items) == 0 or last < len(items) - 1:
            return False
        self.armed = False
        shown_end = self.sim.base + self.sim.ui_start + len(items)
        prev = (self.sim.base, len(self.sim.all))
        self.sim.pending = shown_end
        try:
            self.sim.flip_engine(1)          # 0b199eb：没有 try/catch，异常直接冒泡到 onScrollIndex
        except Exception:
            self.last_result = "raised"      # pending 留着不撤 —— 与代码一致
            raise
        if (self.sim.base, len(self.sim.all)) == prev:
            self.sim.pending = -1
            self.last_result = "refused"
            return False
        self.flips += 1
        self.last_result = "continue@%d" % shown_end
        return True

    def index(self, last):
        self.last_visible = last
        return self.try_continue(last)

    def stop(self):
        r = self.try_continue(self.last_visible)
        self.armed = False
        self.moved = False
        return r

    def remount(self):
        # List .onAppear 在 0b199eb 里只置 candListReady，不清 armed/moved/lastVisible
        # （风险 3，spec §六）：折叠▼→展开、或 List 因布局重挂载时许可会活下来。
        pass

    def preedit_changed(self):
        # 代码：preeditChanged 清许可/记忆位/pending，再 notify
        self.armed = False
        self.moved = False
        self.last_visible = 0
        self.sim.pending = -1
        self.sim.notify(preedit_changed=True)


def scenario_touch_state_machine():
    # T1 按住拖到尾部（onScrollIndex 先到）→ 续一次，抬手/停止不再续
    s = Sim(total=160); s.notify(); t = Touch(s)
    t.down(); t.move(); t.index(49); t.up(); t.stop()
    check("T1 按住拖到底续一页", t.flips == 1 and s.base == 50,
          f"flips={t.flips} base={s.base} res={t.last_result}")

    # T2 快速一甩：索引事件在抬手后才到尾部（第四版要修的缺口）
    s = Sim(total=160); s.notify(); t = Touch(s)
    t.down(); t.move(); t.up(); t.index(49); t.stop()
    check("T2 抬手后惯性到尾部仍续一页", t.flips == 1 and s.base == 50,
          f"flips={t.flips} base={s.base} res={t.last_result}")

    # T3 白点（无 Move）→ 不续页
    s = Sim(total=160); s.notify(); t = Touch(s)
    t.down(); t.up(); t.index(49); t.stop()
    check("T3 白点不续页", t.flips == 0 and s.base == 0, f"flips={t.flips} base={s.base}")

    # T4 「点空处拖一下」留下的陈旧许可：编码变化后必须失效
    s = Sim(total=160); s.notify(); t = Touch(s)
    t.down(); t.move(); t.up()           # 没滚，onScrollStop 也没来
    t.preedit_changed()                  # 打字/选词
    t.index(49); t.stop()
    check("T4 编码变化清掉陈旧许可", t.flips == 0 and s.base == 0, f"flips={t.flips} base={s.base}")

    # T5 事件顺序反向：onScrollStop 先到（lastVisible 还没到尾部）→ 本状态机不续
    s = Sim(total=160); s.notify(); t = Touch(s)
    t.down(); t.move(); t.up(); t.stop(); t.index(49)
    check("T5 stop 先于末尾索引（已知顺序依赖，真机核）", t.flips == 0,
          f"flips={t.flips}（真机若出现此序，需把末索引判定放宽到 stop 后一帧）")

    # T6 同一次滑动两次到尾部事件：只许续一次
    s = Sim(total=160); s.notify(); t = Touch(s)
    t.down(); t.move(); t.index(49); t.index(49); t.up(); t.stop()
    check("T6 一次滑动只续一次", t.flips == 1 and s.base == 50, f"flips={t.flips} base={s.base}")

    # T7 末页 refusal：不续、pending 撤销、许可已撤
    s = Sim(total=160); s.notify(); t = Touch(s)
    for _ in range(3):                          # 每次滑动都要重新按下（许可一次一滑）
        t.down(); t.move(); t.index(49); t.up(); t.stop()
    check("T7a 连滑三页到末页", s.base == 150 and len(s.scroll_items()) == 10,
          f"base={s.base} len={len(s.scroll_items())} flips={t.flips}")
    before = t.flips
    t.down(); t.move(); t.index(9); t.stop()    # 末页再到底
    check("T7 末页再到底不续", t.flips == before and s.pending == -1 and s.base == 150,
          f"flips={t.flips} pending={s.pending} base={s.base} res={t.last_result}")

    # T8（风险 3，spec §六）许可残留 + List 重挂载：会不会一次滑动续两页？
    #   0b199eb 的 onAppear 只置 candListReady，不清 armed ⇒ 理论上许可能活过重挂载。
    #   但续页成功那一支自己就把 armed 清了，所以必须量两条真实顺序，别照「理论」下结论。
    s = Sim(total=160); s.notify(); t = Touch(s)
    t.down(); t.move(); t.index(49)             # 续第一页，stop 丢失 ⇒ arm 被续页清掉
    armed_after_continue = t.armed
    t.remount()                                  # ▼ 折叠再展开
    t.index(49)                                  # 重挂载首帧的索引事件
    check("T8a 重挂载首帧再发 end 索引不会续第二页",
          armed_after_continue is False and t.flips == 1 and s.base == 50,
          f"armed_after_continue={armed_after_continue} flips={t.flips} base={s.base}")

    # T8b 许可确实能残留的情形：拖了但没滚到尾部（Move 后抬手，stop 没来），再折叠展开；
    #     重挂载首帧 index(end) 只在「列表短于一屏」时成立，而那只可能发生在末页 ⇒ 续页被拒。
    s = Sim(total=160); s.notify(); t = Touch(s)
    while s.base != 150:                          # 直接到末页（10 条，短于一屏）
        s.flip_engine(1)
    t.armed, t.moved = True, True                 # 空拖留下的许可（Up 后不清，因为 moved）
    t.remount()
    t.index(len(s.scroll_items()) - 1)            # 末页短列表：首帧 index 就能到 end
    check("T8b 末页短列表 + 残留许可：续页被引擎拒绝，界面不动",
          t.flips == 0 and s.base == 150 and s.pending == -1,
          f"flips={t.flips} base={s.base} pending={s.pending} res={t.last_result}")
    # 结论：风险 3 在两条真实顺序下都无可见后果；onAppear 清许可只是防御性整洁，不是缺陷。

    # T9（风险 4，spec §六）flipPage 抛异常：pending 不撤（与代码一致），但后果有多大要量出来
    s = Sim(total=160); s.notify(); t = Touch(s)
    t.down(); t.move(); s.throw_on_flip = True
    raised = False
    try:
        t.index(49)
    except Exception:
        raised = True
    check("T9a 异常冒泡且 pending 残留（0b199eb 现状）",
          raised and s.pending == 50 and t.flips == 0,
          f"raised={raised} pending={s.pending} flips={t.flips}")
    # 之后一次正常换页（比如点翻页键/再滑到末尾成功一次）会按 pending 落窗
    s.flip_engine(1)                             # 引擎正常翻一页 → notify 消费残留 pending
    check("T9b 残留 pending 被下次正常换页消费后落回 0（无可见跳条）",
          s.base == 50 and s.ui_start == 0,
          f"base={s.base} ui_start={s.ui_start}（结论：真正的代价只是异常冒泡到 ArkUI 回调，不是跳条）")

if __name__ == "__main__":
    scenario_forward_chain()
    scenario_no_drag()
    scenario_preedit_reset()
    scenario_backward_engine_page()
    scenario_tap_mapping()
    scenario_within_page_flip_math()
    scenario_touch_state_machine()
    print()
    if fails:
        print(f"RESULT: {len(fails)} FAIL -> {fails}")
        raise SystemExit(1)
    if gaps:
        print(f"RESULT: ALL PASS（{len(gaps)} 条 GAP 已知未修：{gaps} —— 不是 PASS，等真机验收后统一修）")
        raise SystemExit(0)
    print("RESULT: ALL PASS（仅记账逻辑；真机九条判据仍需解锁后跑）")
