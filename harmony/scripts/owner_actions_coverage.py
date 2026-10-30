#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「主人只看这一节」的覆盖线检查（H-140 的长期动作）。

为什么要有这个脚本：06:4x 我把两份 owner 表面合并成「早上只看这一节」，06:5x 又在 `HANDOFF.md`
写下「别处出现的条目数以它为准」—— 两句各自都对，合起来是一个新断言：他只看那一节就够了。
07:0x 人工对账发现它不成立（AGC 隐私声明走路 B／开发者名称 两格只在旧 §0 第 7 项）。
那种病不靠我记得做审计，只靠跑一条判据。

只读：不写任何文件。三条判据 ——
  A 台账里每个「要主人」的条目（`ISSUES.md` 归属列含 U 且非闭；`U→X` 视为已改派、不算）
    都必须在 COVERAGE 里登记，且它的关键词能在那一节里 grep 到；
  B COVERAGE 里 `defer=True` 的条目是「等材料齐了才叫他」的延后项（承诺函／最终验收），允许只写在
    §0.5／§4 —— 判据降为「全文命中即算，标 `延后`」，不要求在顶部节出现；
  C 那一节表头里写的行数（「这 8 条」这类）必须等于表内实际行数 —— 「8 行」这个数在文档里被
    6 处引用，一旦行数变了而散文没跟着变，就是 H-139 那一类呈现错。

用法：
  python scripts/owner_actions_coverage.py            # 检查当前工作区，exit 0/1
  python scripts/owner_actions_coverage.py --selfcheck # 拿真实文档 + 已知坏样本验判据本身

判据变更记录（COVERAGE 是要主人的事项清单，它跟着现实走，不让现实迁就它）
------------------------------------------------------------------
① 10-23 09:5x：H-108 归属从 A/U 改成 A（带括号备注）后，写死 H-108 的坏样本断言炸掉
   ⇒ 样本改成自己挑行（见 `selfcheck()` 坏样本 2）。
② 10-26 11:2x：「`U→X` 已改派不算」与 `OPEN（备注）` 也算 OPEN 两条口径落地（覆盖线盲区）。
③ 10-28 05:5x（Qoder）：首报 5 条 FAIL，逐条对着台账与代码复判 ——
   「AGC 开发者名称」「商店截图重拍」「解锁亮屏」三条是**真缺口**（事项确实还欠他／欠我一次上机），
   已把内容补进主人那一节（第 8 行加「开发者名称」那一格、顶部那段 ⑤(e) 加商店 5 张截图与解锁）；
   「默认输入法」＝H-086 早 CLOSED ⇒ 关键词换成现在那句「已经关掉」清单里的原文（见上面注释）；
   「今晚没有应用代码进展（H-106 未交付）」＝10-22 夜里的话，实物变了三轮 ⇒ 换成 **H-247**
   （三条 P0 老单按实物复判这件事本身，现在就是主人该看见的一条报备）。
④ 同一次复判查到的实测事实（写在这里是为了下次别再猜）：折叠出口在 `KeyboardIndex.ets:2514`
   （空闲单击 ▼）与 `:2521`（长按 ▼），`hideKeyboard()` 定义在 `KeyboardController.ets:414`；
   五手势在 `:3441/3662/3725`（`swipeAltDone`／`undoLastAction`／`startBackspaceRepeat`）；
   「九键」字面**只在 LayoutMenu 里**（`:4706`），底栏没有一级切换键 ⇒ H-107 那条判据仍未满足。
"""
import io
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OA = os.path.join("docs", "OWNER-ACTIONS.md")
IS = os.path.join("docs", "ISSUES.md")
OPENISH = ("OPEN", "DOING", "BLOCKED", "FIXED")   # FIXED 也算：H-104 是「FIXED 待他去 AGC 挂链接」

# 事项 | 来源 | 关键词（命中其一即算覆盖）| defer（允许只在 §0.5／§4，但顶部要有指向）
COVERAGE = [
    ("电子版权证书走哪条", "DECISIONS D-006", ["版权证书", "电子版权"], False),
    ("商店一句话简介", "H-118", ["一句话简介"], False),
    ("商户服务（12-31 截止）", "激励计划", ["商户服务"], False),
    ("签名材料备份出机器", "§1", ["拷到机外", "第三地", "备份"], False),
    ("软著插图与正文描述", "H-101 H-137", ["软著"], False),
    ("半角反斜杠打什么", "H-095", ["反斜杠"], False),
    ("斜杠符号 9 组留不留", "H-095", ["斜杠符号", "9 组"], False),
    ("AGC 字段上限现场核实", "listing §8.3", ["字段上限"], False),
    ("AGC 隐私声明走哪条（路 B 托管）", "H-104", ["托管"], False),
    ("AGC 开发者名称", "§0.5D", ["开发者名称"], False),
    ("商店截图重拍", "H-085", ["截图"], False),
    ("桌面图标哪套是品牌（黑底金 vs 蓝三条键帽）", "H-146", ["黑底金", "三条键帽"], False),
    # 10-28 05:5x（Qoder）判据换内容，原因见文件头「判据变更记录」⑤：
    # 旧条目写的是 10-22 夜里那句「今晚没有应用代码进展（H-106 未交付）」，实物早已变过三轮。
    ("三条 10-22 的 P0 老单待按实物复判（H-247）", "H-103 H-106 H-107 H-247", ["H-247"], False),
    # 10-28 05:5x：H-086 主人 10-23 00:25 就切好了、状态 CLOSED，且已列在顶部那节的「已经关掉」清单里
    # ⇒ 关键词从「切输入法」（当时那句「需要你解锁+切输入法」的旧措辞）改成「默认输入法」，
    #   量的还是同一件事（这件事在不在他那一节里），只是不再要求一句已经作废的原文。
    ("默认输入法（H-086 已闭，只要求在『已经关掉』清单里点名）", "H-086", ["默认输入法"], False),
    ("解锁亮屏与自动旋转", "H-085", ["解锁"], False),
    ("承诺函／最终验收（延后项）", "§4", ["承诺函", "最终验收"], True),
]


def rd(rel, base=ROOT):
    return io.open(os.path.join(base, rel), encoding="utf-8", newline="\n").read()


def cell(ln, n):
    parts = ln.strip().strip("|").split("|")
    return parts[n].strip() if len(parts) > n else ""


def top_section(text):
    """「早上只看这一节」= 文件开头到第一条单独一行的 `---` 之前。"""
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if ln.strip() == "---":
            return "\n".join(lines[:i]), i + 1
    return text, len(lines)


def is_openish(status):
    """`OPEN（备注）` 也算 OPEN —— 09:5x 实测：H-108 改成带括号的 OPEN 后，
    旧判据 `status in OPENISH` 会静默跳过整行（覆盖线盲区）。"""
    return re.match(r"^(OPEN|DOING|BLOCKED|FIXED)(?![A-Za-z])", status) is not None


def owner_rows(issues_text):
    """台账里「要主人且还没闭」的行：归属含 U，`U→X` 已改派不算，VERIFIED 不算。"""
    out = []
    for ln in issues_text.split("\n"):
        if not re.match(r"^\| H-\d+ \|", ln):
            continue
        owner, status, hid = cell(ln, 3), cell(ln, 1), cell(ln, 0)
        if not is_openish(status) or "U" not in owner:
            continue
        if re.match(r"^U\s*(→|->)", owner):
            continue          # H-090 那类：归属已改派，台账不该再暗示「主人还欠一句」
        out.append((hid, status, owner[:14]))
    return out


def audit(oa_text, issues_text):
    top, top_end = top_section(oa_text)
    hits = []

    # A/B 覆盖线
    missing, deferred_ok = [], []
    for label, src, keys, defer in COVERAGE:
        found = [k for k in keys if k in top]
        if found:
            hits.append((label, src, "、".join(found), "OK"))
        elif defer:
            somewhere = [k for k in keys if k in oa_text]
            if somewhere:
                hits.append((label, src, "、".join(somewhere) + "（在 §0.5/§4）", "延后"))
            else:
                missing.append((label, src, "延后项在全文也 grep 不到：" + "／".join(keys)))
        else:
            missing.append((label, src, "顶部那一节 grep 不到任何关键词：" + "／".join(keys)))

    # A 的第二半：台账里每一条要主人的行都必须登记过（漏登记 = 下次合并表面时最容易掉的那一格）
    unregistered = []
    for hid, status, owner in owner_rows(issues_text):
        if not any(hid in src or hid in " ".join(keys) for _l, src, keys, _d in COVERAGE):
            unregistered.append("%s(%s, 归属 %s)" % (hid, status, owner))

    # C 「这 N 条」与表内实际行数
    rows = [l for l in top.split("\n") if re.match(r"^\|\s*\d+\s*\|", l)]
    prose = [int(m.group(1)) for m in re.finditer(r"(?:下面这|不在下面|只看这|条数[:：])\s*(\d+)\s*条", top)]
    count_bad = [] if not prose or all(n == len(rows) for n in prose) else \
        ["顶部表实际 %d 行，散文写的是 %s" % (len(rows), "/".join(str(x) for x in sorted(set(prose))))]

    return top, top_end, hits, missing, unregistered, count_bad, len(rows)


def report(base=ROOT, stream=sys.stdout):
    oa, issues = rd(OA, base), rd(IS, base)
    top, top_end, hits, missing, unreg, count_bad, nrows = audit(oa, issues)
    print("=" * 74, file=stream)
    print("覆盖线检查（只读）｜ 那一节 = 文件前 %d 行（到第一条 `---` 之前，表 %d 行）" % (top_end, nrows), file=stream)
    print("=" * 74, file=stream)
    print("需要主人的事项｜来源｜顶部节命中｜判定", file=stream)
    for label, src, k, verdict in hits:
        print("  [OK  ] %-30s %-14s 命中=%s %s" % (label, src, k, verdict), file=stream)
    for label, src, why in missing:
        print("  [FAIL] %-30s %-14s %s" % (label, src, why), file=stream)
    if unreg:
        print("  [FAIL] 台账里这些「要主人且非闭」的行没在 COVERAGE 登记 ⇒ 新条目要先进那一节: %s"
              % "、".join(unreg), file=stream)
    for c in count_bad:
        print("  [FAIL] 行数不一致：%s" % c, file=stream)
    bad = len(missing) + len(unreg) + len(count_bad)
    print("结论：%s（覆盖 %d 项 / 漏 %d 项 / 未登记 %d 条 / 行数判据 %d 项）"
          % ("通过" if bad == 0 else "不通过", len(hits), len(missing), len(unreg), len(count_bad)), file=stream)
    return 0 if bad == 0 else 1


def selfcheck():
    """判据必须能被已知坏样本打到：真文档 0，坏样本 1。"""
    oa, issues = rd(OA), rd(IS)
    top, _ = top_section(oa)
    tmp = tempfile.mkdtemp(prefix="oa-cov-")
    for rel in (OA, IS):
        d = os.path.join(tmp, os.path.dirname(rel))
        if d and not os.path.isdir(d):
            os.makedirs(d)
        with io.open(os.path.join(tmp, rel), "w", encoding="utf-8", newline="\n") as f:
            f.write(rd(rel))
    ok = True

    def expect(name, base, want):
        got = report(base=base, stream=io.StringIO())
        print("  %-26s 期望 exit %d 实际 exit %d  %s" % (name, want, got, "ok" if got == want else "MISMATCH"))
        return got == want

    r = [expect("0-live", tmp, 0)]
    # 坏样本 1：把「托管」那一格从顶部节里删掉（就是 07:0x 之前的真实状态）
    bad1 = oa.replace(top, top.replace("托管", "××"))
    io.open(os.path.join(tmp, OA), "w", encoding="utf-8", newline="\n").write(bad1)
    r.append(expect("1-hosted-removed", tmp, 1))
    # 坏样本 2：恢复文档，把台账里一条「没登记过、归属也不是 U」的 OPEN 行改成 U ——
    # 模拟「新出现的要主人的行没登记」。**不写死 H-108**：09:5x 它的归属从 A/Q 改成 A（带括号备注）
    # 后旧样本断言就炸了；行形态本来就会变，样本应当自己挑行，而不是让文档迁就样本。
    io.open(os.path.join(tmp, OA), "w", encoding="utf-8", newline="\n").write(oa)
    fake = issues.split("\n")
    registered = [src for _l, src, _k, _d in COVERAGE]
    picked = None
    for i, ln in enumerate(fake):
        if not re.match(r"^\| H-\d+ \|", ln):
            continue
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(c) < 4 or "U" in c[3] or not is_openish(c[1]):
            continue
        if any(c[0] in src for src in registered):
            continue
        picked = i
        break
    assert picked is not None, "坏样本 2：台账里找不到「非 U、未登记、仍 OPEN」的行，这条判据就白测了"
    ln = fake[picked]
    c = [x.strip() for x in ln.strip().strip("|").split("|")]
    c[3] = "U"
    fake[picked] = "| " + " | ".join(c) + " |"
    changed = 1
    mutated_hid = c[0]
    detected = [hid for hid, _s, _o in owner_rows("\n".join(fake))]
    assert mutated_hid in detected, "坏样本 2：改成 U 之后 owner_rows() 仍看不见它（判据本身瞎了）"
    io.open(os.path.join(tmp, IS), "w", encoding="utf-8", newline="\n").write("\n".join(fake))
    r.append(expect("2-unregistered-U-row(%s)" % mutated_hid, tmp, 1))
    # 坏样本 3：行数判据 —— 顶部表多删一行（第 7 行），散文还说 8 条
    rows = [l for l in top.split("\n") if re.match(r"^\|\s*7\s*\|", l)]
    assert len(rows) == 1, "顶部表的第 7 行形态变了"
    bad3 = oa.replace(rows[0] + "\n", "", 1)
    io.open(os.path.join(tmp, IS), "w", encoding="utf-8", newline="\n").write(issues)
    io.open(os.path.join(tmp, OA), "w", encoding="utf-8", newline="\n").write(bad3)
    r.append(expect("3-row-count-drift", tmp, 1))
    print("自测 %d 例，未按预期触发 %d 例" % (len(r), r.count(False)))
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if all(r) else 2


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if "--selfcheck" in sys.argv[1:]:
        return selfcheck()
    if len(sys.argv) > 1:
        print("用法：owner_actions_coverage.py [--selfcheck]")
        return 2
    return report()


if __name__ == "__main__":
    sys.exit(main())
