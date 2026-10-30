# -*- coding: utf-8 -*-
"""主人／值守会读的那几张表面，同一个数字是不是写成了两个值 —— 只读对账，不改任何文件。

为什么要这张表（H-141）
----------------------
同一个病这一晚出现三次，只是形状不同：H-138 错在**口径**（被 D-018 推翻的备案说法还活着）、
H-139 错在**呈现**（两份主人表面退化成流水账）、H-140 错在**覆盖**（合并成「唯一来源」后那一节不等于全集）。
这轮验第四条线：**一致性** —— 「8 行表」「16 项闸门」「14 例自测」这类数字在
`OWNER-ACTIONS.md`／`ROADMAP.md`／`HANDOFF.md` 三张表面上必须各指同一个实测值。

边界比判据更要紧（07:4x 第一版就在这儿错过一次）
------------------------------------------------
`HANDOFF.md` 的归档区里有一句「装机后必跑 15 项内容检查」，那是 10-22 19:5x 写的，
当时闸门确实只有 15 项 ⇒ 那是**历史行，不许涂改**。所以本脚本只读每张表面的**活区**：
  OWNER-ACTIONS：文件开头 → 第一条 `^## 附：`
  ROADMAP      ：文件开头 → 第一条 `^## 附：`
  HANDOFF      ：文件开头 → 第一条 `^## 文件归属` 或 `^## 交接记录`
判据一律从活区里抓锚点，抓不到就 FAIL（锚点被我改写 ⇒ 数字对账没跟着搬，必须有人知道）。

三条判据
--------
A 覆盖：每条锚点在它所在活区里至少出现一次；出现 0 次 = FAIL（不是跳过）。
B 一致：锚点旁的那个数字 == 本脚本当场量出来的值（量的方法写死在 measure() 里，不读文档）。
C 编号/归档：主人表面顶部 10-25 09:14 起是「一段话 + N 行表」，原先那套 ①–N 编号整段进了附录
  ⇒ 现在 C 判的是「活区若引用那套旧编号，指到的附必须等于附录标题实测出来的那个附」（H-193）。

用法
----
  python scripts/owner_surfaces_agreement.py            # 只读对账，exit 1 = 有不一致
  python scripts/owner_surfaces_agreement.py --slow     # 附带跑 53 秒的内容闸门自测，量「22 例」
  python scripts/owner_surfaces_agreement.py --selfcheck # 已知坏样本必须判 FAIL（4 例）
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIRCLED = u"①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
OWNER = "docs/OWNER-ACTIONS.md"
ROADMAP = "docs/ROADMAP.md"
HANDOFF = "docs/HANDOFF.md"

# ── 判据 B 的锚点表：(活区名, 抓数字的正则, 用哪个测量值, 一句人话) ──────────────────
# 正则必须只有一个捕获组，捕获的就是那个数字／编号字符。
CLAIMS = [
    (u"ROADMAP", u"一张 \\*\\*(\\d+) 行表\\*\\*", u"TOP", u"ROADMAP §0 引的那张顶部待办表行数"),
    (u"ROADMAP", u"顶部那张 (\\d+) 行表", u"TOP", u"ROADMAP §4 引的同一张表"),
    # 判据 C（10-26 11:2x 改口径，H-193）：主人表面顶部 10-25 09:14 起改成「一段话 + 12 行表」，
    # 原先那套 ①–N 编号整段移进附录 ⇒ 「①–N 上限」不再是活区里的数。取而代之：
    #   活区若引用那套旧编号，必须指对**归档在哪个附**（按附录标题实测，不读文档里的数字）。
    (u"ROADMAP", u"原文已于 10-25 09:14 整段移入[^\\n]*?附 (\\d+)", u"ARC", u"ROADMAP 说旧 ①–N 原文归档在哪个附"),
    (u"ROADMAP", u"(\\d+) 项检查的 ⑪", u"GATE", u"§0 ④ 里内容闸门的项数"),
    (u"ROADMAP", u"（(\\d+) 项检查表）", u"GATE", u"§7 配套文件里那张检查表"),
    (u"ROADMAP", u"\\*\\*(\\d+) 例 = ", u"S14", u"§0 ⑤ 里的交付＋时间戳判据自测例数"),
    # 10-26 11:2x：OWNER 活区那两句旧措辞（「16 项内容检查里」「N 项闸门」「下面那 N 条待办」…）
    # 已随 10-25 09:14 的合并整段进入附 4 ⇒ 锚点改成同一节**现在**的写法；数字含义不变。
    (u"OWNER", u"内容闸门 (\\d+) 项全绿", u"GATE", u"顶部说的离线内容闸门项数"),
    (u"OWNER", u"必跑 (\\d+) 项内容检查", u"GATE", u"铁律里装机后要跑的检查数"),
    (u"OWNER", u"下面 (\\d+) 条待办里", u"TOP", u"顶部那一节自己的行数说法"),
    # 判据变更记录（H-141）：旧第二锚「下面 (\d+) 条里只剩」在 2026-10-28 08:3x 的读前节合并里
    # 被改写掉了（0 命中＝判据 07:4x 自己写的规矩：句子搬了、账要搬 ⇒ 这条锚退役）。
    # 行数说法由上面那条唯一锚继续盯；活区若再出现第二种写法，按先例把锚补回来而不是放行。
    (u"HANDOFF", u"」(\\d+) 行表", u"TOP", u"值守活表引的顶部表行数"),
    (u"HANDOFF", u"旧编号 ①–⑧ 的原文已于 10-25 09:14 整段移入附 (\\d+)", u"ARC", u"值守表说旧编号归档在哪个附"),
    (u"HANDOFF", u"顶部 (\\d+) 行表", u"TOP", u"值守活表引的顶部表行数（另一处写法）"),
    (u"HANDOFF", u"--selfcheck` (\\d+) 例 exit 0", u"S14", u"值守活表里 h106 交付判据的自测例数"),
    (u"HANDOFF", u"--selfcheck` (\\d+) 例含 3 个已知坏样本", u"S4", u"值守活表里覆盖线检查器的自测例数"),
    # 下面三条只有 `--slow` 才量（内容闸门自测实跑约 53 秒 ⇒ 值守每 5 分钟那一轮不跑，白天/装机前跑一次）
    (u"HANDOFF", u"闸门自测 (\\d+) 例", u"S22", u"值守活表里的内容闸门自测例数（需 --slow 才有测量值）"),
    (u"HANDOFF", u"内容自测 (\\d+) 例", u"S22", u"同上，另一种写法"),
    # ROADMAP 那份本来就没写「22 例」⇒ 不能登记成必中锚点（07:4x --slow 首跑就这么假报警过一次：
    # 「若出现才比」的措辞和「0 次命中就 FAIL」的判据是矛盾的，要么删掉这条，要么改成可选锚点）。
    # 07:4x 首跑的两条 FAIL 经核**都是量具自己的错**（已改判据，没改文档）：
    # ① 「自测例数也从 11 例更正成 14 例」那句在 OWNER-ACTIONS 的**文末附录**（06:4x 归档块）里，
    #    不属于活区 ⇒ 锚点 0 次命中；活区里同样意思的话由 ROADMAP 那条 `**N 例 = ` 覆盖着，不重复登记。
    # ② `--selfcheck` (\d+) 例` 太宽：HANDOFF 同一行里既有 h106 的「14 例」又有覆盖线的「4 例」，
    #    拿一个测量值去比两个不同脚本的数 ⇒ 必然假报警。现在按各自的下文分开（「exit 0」／「含 3 个已知坏样本」）。
]


def read(rel):
    p = os.path.join(ROOT, rel.replace("/", os.sep))
    s = io.open(p, "r", encoding="utf-8", newline="\n").read()
    # 仓库用 CRLF 检出（.gitattributes/autocrlf），本机 HANDOFF.md 全行尾带 \r，
    # 硬断言 \r 不存在会让量具在这台机上永远跑不起来。改为：统一归一 LF，
    # 只在「同一文件里 CRLF 与裸 LF 混用」这种真异常时才报警（纯 CRLF 不算）。
    has_crlf = "\r\n" in s
    has_bare_lf = bool(re.search(r"(?<!\r)\n", s))
    if has_crlf and has_bare_lf:
        raise AssertionError(rel + " 行尾混用 CRLF/裸LF 了")
    return s.replace("\r\n", "\n").replace("\r", "\n")


def cut_before(text, pattern):
    m = re.search(pattern, text, re.M)
    return text[:m.start()] if m else text


def live_map(texts=None):
    texts = texts or {k: read(k) for k in (OWNER, ROADMAP, HANDOFF)}
    return {
        u"OWNER": cut_before(texts[OWNER], u"^##\\s*附："),
        u"ROADMAP": cut_before(texts[ROADMAP], u"^##\\s*附："),
        u"HANDOFF": cut_before(texts[HANDOFF], u"^##\\s*(文件归属|交接记录)"),
    }


def top_section(owner_live):
    """「早上只看这一节」标题 → 第一条单独 --- 之前。"""
    i = re.search(u"^## 早上只看这一节", owner_live, re.M)
    assert i, "OWNER-ACTIONS 里找不到「早上只看这一节」标题"
    seg = owner_live[i.start():]
    j = re.search(u"^---\\s*$", seg, re.M)
    return seg[:j.start()] if j else seg


def run_script(argv):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.Popen([sys.executable] + argv, cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, env=env)
    out = proc.communicate()[0].decode("utf-8", "replace")
    return proc.returncode, out


def measure(live, slow=False):
    """判据 B 用到的值全部当场量出来；故意不读文档里的数字。"""
    out = {}
    rows = [l for l in top_section(live[u"OWNER"]).split(u"\n") if re.match(u"^\\| \\d+ \\|", l)]
    out[u"TOP"] = len(rows)
    nums = [CIRCLED.index(c) + 1 for c in re.findall(u"^> ([%s]) " % CIRCLED, top_section(live[u"OWNER"]), re.M)]
    out[u"TOPNUM"] = max(nums) if nums else 0
    out[u"TOPNUM_OK"] = sorted(set(nums)) == list(range(1, (max(nums) if nums else 0) + 1))
    # ARC：旧 ①–N 编号原文归档在哪个附——从**附录标题**量（H-193）。标题没了 ⇒ -1 ⇒ 量具不可信。
    m_arc = re.search(u"^## 附 (\\d+)：09:14 合并前的", read(OWNER), re.M)
    out[u"ARC"] = int(m_arc.group(1)) if m_arc else -1
    out[u"ARC_OK"] = out[u"ARC"] > 0
    out[u"GATE"] = len(re.findall(u"^@check\\(", read("scripts/check_app_content.py"), re.M))
    rc, so = run_script(["scripts/h106_precheck.py", "--selfcheck"])
    hits = re.findall(u"(?m)^  (OK |!! )", so)
    out[u"S14"] = len(hits)
    out[u"S14_OK"] = rc == 0 and all(h.strip() == "OK" for h in hits) and len(hits) > 0
    rc2, so2 = run_script(["scripts/owner_actions_coverage.py", "--selfcheck"])
    m = re.search(u"自测 (\\d+) 例，未按预期触发 (\\d+) 例", so2)
    out[u"S4"] = int(m.group(1)) if m else -1
    out[u"S4_OK"] = bool(m) and rc2 == 0 and m.group(2) == "0"
    if slow:
        rc3, so3 = run_script(["scripts/check_app_content_selftest.py"])
        m3 = re.search(u"自测用例 (\\d+) 个[^\\n]*?未按预期触发 (\\d+) 个", so3)
        out[u"S22"] = int(m3.group(1)) if m3 else -1
        out[u"S22_OK"] = bool(m3) and rc3 == 0 and m3.group(2) == "0"
    return out


def check(live, meas):
    # 锚点正则本身必须能编译：07:4x 首跑就被没转义的 `**`（Markdown 粗体）咬了一次
    # ——「语法错」会让整张表崩在半路，而我要的是「一处不一致报一处」。
    for _a, _p, _k, _n in CLAIMS:
        assert re.compile(_p) and len(_p) > 0, _p
    fails, notes = [], []
    stat = {u"checked": 0, u"hits": 0, u"skipped": 0}   # 结论里的数必须跟着模式变（07:4x 就这么假报过自己一次）
    for key in (u"TOPNUM_OK", u"ARC_OK", u"S14_OK", u"S4_OK", u"S22_OK"):
        if key in meas and not meas[key]:
            fails.append(u"量具自己不可信：%s ⇒ 先去修那个脚本，别拿它的数对账文档" % key)
    for area, pat, key, note in CLAIMS:
        if key == u"S22" and key not in meas:
            stat[u"skipped"] += 1
            continue
        hits = re.findall(pat, live[area])
        stat[u"checked"] += 1
        stat[u"hits"] += len(hits)
        if not hits:
            fails.append(u"锚点在 %s 活区里 0 次命中：%s（%s）⇒ 句子被我改写过、数字对账没跟着搬" % (area, pat, note))
            continue
        # 单字符捕获既可能是「⑧」也可能是「8」⇒ 按 key 判类型，别按长度猜（07:4x 猜错过一次）
        def val(h):
            return CIRCLED.index(h) + 1 if key == u"TOPNUM" else int(h)
        bad = [h for h in hits if val(h) != meas[key]]
        if bad:
            fails.append(u"%s 写的是 %s、实测是 %d（%s）｜样例：%s"
                         % (note, "/".join(bad), meas[key], key,
                            re.search(pat, live[area]).group(0)[:48]))
        else:
            notes.append(u"  [OK  ] %-46s 实测=%-3s 命中=%d  %s" % (note[:46], meas[key], len(hits), pat[:20]))
    return fails, notes, stat


def selfcheck():
    """已知坏样本必须判 FAIL：改一个数字／删一个锚点／编号断一档。

    11:3x 自修：样本里的数字**一律从实测值推**，不再写死「8」。
    上一版把 `一张 **8 行表**` 硬编码进三个样本，主人表面从 8 行加到 9 行那天，
    样本会静默地「替换不到任何东西」⇒ 期望 FAIL 却判成一致，量具自己先瞎（和 W-198
    那条覆盖线坏样本是同一个病：样本形态跟着文档变，判据就不能钉死字面量）。
    """
    base = {k: read(k) for k in (OWNER, ROADMAP, HANDOFF)}
    lv0 = live_map(base)
    m0 = measure(lv0)
    n_top, n_gate, n_arc = m0[u"TOP"], m0[u"GATE"], m0[u"ARC"]
    if n_arc <= 0:
        raise AssertionError(u"量不到旧编号归档到哪个附（ARC=%d）⇒ 判据 C 的坏样本造不出来" % n_arc)
    cases = []
    d = dict(base); d[ROADMAP] = d[ROADMAP].replace(u"一张 **%d 行表**" % n_top, u"一张 **%d 行表**" % (n_top + 1))
    cases.append((u"1-top-row-count-drift(%d→%d)" % (n_top, n_top + 1), d, True))
    # 10-26 11:2x：OWNER 活区里的闸门数字随 09:14 合并换了措辞（「N 项闸门」→「内容闸门 N 项全绿」），
    # 样本跟着换锚点字样 —— 样本形态跟着文档变，判据就不该钉死字面量（同 11:3x 那次教训）。
    d = dict(base); d[OWNER] = d[OWNER].replace(u"内容闸门 %d 项全绿" % n_gate,
                                               u"内容闸门 %d 项全绿" % (n_gate + 1), 1)
    cases.append((u"2-gate-count-drift(%d→%d)" % (n_gate, n_gate + 1), d, True))
    d = dict(base); d[ROADMAP] = re.sub(u"一张 \\*\\*%d 行表\\*\\*" % n_top, u"一张待办表", d[ROADMAP], count=1)
    cases.append((u"3-anchor-removed", d, True))
    # 4 号负控（10-26 11:2x 换内容）：活区引用旧编号归档的那一句，把「附 N」写成「附 N+1」——
    # 这正是 H-193 那类漂移（参考文献搬家了、引用没跟着搬），必须变红。
    old_ref, new_ref = (u"整段移入 `OWNER-ACTIONS.md` **附 %d**" % n_arc,
                        u"整段移入 `OWNER-ACTIONS.md` **附 %d**" % (n_arc + 1))
    d = dict(base)
    assert d[ROADMAP].count(old_ref) == 1, u"样本 4 锚点命中 %d 次（应为 1）⇒ 表面形态变了，这条判据白测" % d[ROADMAP].count(old_ref)
    d[ROADMAP] = d[ROADMAP].replace(old_ref, new_ref)
    cases.append((u"4-archive-ref-drift(附%d→附%d)" % (n_arc, n_arc + 1), d, True))
    bad = 0
    for name, texts, expect_fail in cases:
        lv = live_map(texts)
        ms = measure(lv)
        f, _, _ = check(lv, ms)
        got = bool(f)
        ok = got == expect_fail
        bad += 0 if ok else 1
        print(u"  %-30s 期望 FAIL=%s 实际=%s  %s" % (name, expect_fail, got, (f or [u"一致"])[0][:56]))
    lv = live_map(base)
    f0, _, _ = check(lv, measure(lv))
    if f0:
        bad += 1
        print(u"  %-30s 活样本居然 FAIL：%s" % (u"0-live", f0[0][:60]))
    else:
        print(u"  %-30s ok" % u"0-live")
    print(u"自测 %d 例，未按预期触发 %d 例" % (len(cases) + 1, bad))
    return 1 if bad else 0


def main(argv):
    slow = "--slow" in argv
    if "--selfcheck" in argv:
        return selfcheck()
    live = live_map()
    meas = measure(live, slow=slow)
    print(u"== 主人／值守表面数字对账（只读）==")
    print(u"  实测：顶部表 %d 行｜旧 ①–N 原文归档=附 %d｜内容闸门 %d 项｜交付判据自测 %d 例｜覆盖线自测 %d 例%s"
          % (meas[u"TOP"], meas[u"ARC"], meas[u"GATE"], meas[u"S14"], meas[u"S4"],
             (u"｜内容闸门自测 %d 例" % meas[u"S22"]) if slow else u"（--slow 才量 22 例）"))
    fails, notes, stat = check(live, meas)
    for n in notes:
        print(n)
    tail = (u"（另有 %d 条锚点要 --slow 才量）" % stat[u"skipped"]) if stat[u"skipped"] else u"（含 --slow 的两条）"
    if fails:
        print(u"结论：本次核了 %d 条锚点／%d 处数字，不一致 %d 处" % (stat[u"checked"], stat[u"hits"], len(fails)))
        for f in fails:
            print(u"  [FAIL] %s" % f)
        return 1
    print(u"结论：本次核了 %d 条锚点／%d 处数字，全部与实测一致（漏锚 0 项）%s"
          % (stat[u"checked"], stat[u"hits"], tail))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
