# -*- coding: utf-8 -*-
r"""信箱「待我处理的 OPEN 行」精确判据（CodeArts 巡检 v10 / Qoder 自查共用）。

为什么不能用 `grep -i OPEN`（2026-10-24 22:1x 实测）：
  - MAILBOX 表格每行 7 格，最后一格才是「状态」。整行 grep 会把**正文里提到 OPEN 的历史行**
    和「状态格其实是 OPEN」的现行行混在一起 —— 实测返回 47 条，其中 46 条是历史已处理行。
  - 后果：巡检每 5 分钟弹一次通知，回一条「有 47 条待处理」，几次之后人就忽略巡检，机制作废。

用法：
    python scripts/mail_open.py --who CodeArts     # 只数发给 CodeArts 的真 OPEN 行
    python scripts/mail_open.py --who Qoder        # 只数发给 Qoder 的真 OPEN 行
    python scripts/mail_open.py --who CodeArts -v  # 列出每条的 ID＋时间＋主题首句

退出码：0 = 有 OPEN 行（或存在读不到的坏行，见 [WARN]）；1 = 确认没有；2 = 用法/文件错误。

书写口径（H-225，2026-10-27 16:1x Qoder）：正文里要写竖线，**必须转义成 `\|`**；
没转义的 `|` 会把一行顶出多余的格子，本脚本报 WARN 并跳过该行的状态判定。
状态格一律**从行尾读**（现行 7 格、历史与部分行 6 格缺「文件」列，都读得到）。
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIL = os.path.join(ROOT, "docs", "MAILBOX.md")

# 收件人名单（`--who` 的合法值）
RECIP = {"CodeArts": True, "Qoder": True}

# (Qoder H-225) 与 `check_mailbox_states.py` 同一道界：M-190 以前是混格式时代
# （6/8/9 格、`SENT（…）`…），那批行全部已闭环，坏行 WARN 只报现行区，
# 否则每次巡检都被 8 条历史噪音刷掉真信号（H-185 记的「几次之后人就忽略巡检」）。
EPOCH = 190
ID_RE = re.compile(r"^M-(\d+)$")
ARROW_RE = re.compile(u"(?:→|->)")


def in_scope(mid):
    m = ID_RE.match(mid)
    return bool(m) and int(m.group(1)) >= EPOCH


def addressed(cell, who):
    r"""收件格（第 3 格）是否指向 who —— **箭头两种写法都认**，且只看箭头右侧。

    H-225 实测（2026-10-27 16:2x，脚本数出来的，不是猜的）：现行区 M-190 起有
    **11 行**把收件格写成 ASCII `->`（M-244～M-249 是他写的，M-250/251/253/254/255 是我写的），
    而老判据是精确子串 `u"→ CodeArts"` ⇒ **这 11 封信对巡检完全隐形**，其中就有我 12:1x
    给他的词库对齐派活 M-253——号还和他自己的 M-253 撞了。箭头字形不是契约，
    「箭头右侧是收件人」才是；所以这里只按箭头切、只看右半边。
    """
    parts = ARROW_RE.split(cell)
    return len(parts) >= 2 and who in parts[-1]


def open_rows(who, text=None):
    r"""返回 ([(ID, 时间, 主题)], [坏行 (ID, 格数)])；text 不给时读信箱文件。

    H-225(Qoder 2026-10-27 16:1x)——两处改动，和 `check_mailbox_states.py` 同一口径：
      1. **分段只吃未被反斜杠转义的竖线**。原来这里是 naive `ln.split("|")`，信箱里
         M-254/M-257/M-264 的正文写了符号气泡数据（`z=['|', Z]` 这类），一行被读成
         10~11 段 ⇒ 状态格判到错的列上，这些行对巡检**隐形**（H-185 那类事故）。
         正文里的竖线现在必须写 `\|`。
      2. **状态格从行尾取，不写死列号**。M-254/M-257/M-264 修行后又暴露第二件事：
         它们是 **6 格行**（少一个「文件」列），`p[7]` 根本不是状态格。6 格/7 格混着
         是历史遗留（H-223 记了「列口径等主人点头再统一」），在统一之前按固定列号解析
         ＝把待办判成正文，同样是隐形。从行尾数 ⇒ 6/7 格都能读到状态，谁也不用改谁的行。
      3. 收件人匹配但格数不是 6/7 的行**不再静默跳过**，改成 WARN 报出来：静默跳过
         就是隐形的开始（2026-10-26 那次「巡检报无 OPEN」的真根因就在这里）。
    """
    s = text if text is not None else io.open(MAIL, encoding="utf-8", newline="").read()
    # (Qoder H-225) 只在「## 消息表」之后找行：文件前半还有一张「任务执行表」，格式完全不同
    # （`Qoder→CodeArts` 不带空格、9 格）。今天靠箭头写法不同侥幸没撞上，但那是运气不是判据。
    pos = s.find(u"## 消息表")
    if pos >= 0:
        s = s[pos:]
    out = []
    malformed = []
    for ln in s.split("\n"):
        ln = ln.rstrip("\r")
        if not ln.startswith("| M-"):
            continue
        if ln.startswith("| M-xxx"):   # (Qoder) 跳过模板占位行（状态列恰为 OPEN 会误报）
            continue
        p = re.split(r"(?<!\\)\|", ln)
        if p and p[-1].strip() == "" and len(p) > 1:
            p = p[1:-1]                # 丢掉首尾 `|` 两侧的空段，剩下就是格子
        if len(p) < 4:
            continue
        if not addressed(p[2], who):
            continue
        if len(p) not in (6, 7):        # 正文换行被拆 / 夹了没转义的裸竖线 ⇒ 必须可见
            if in_scope(p[0].strip()):  # 历史区（M-190 前）混格式，不报，免得刷掉真信号
                malformed.append((p[0].strip(), len(p)))
            continue
        if p[-1].strip() != "OPEN":          # 状态格＝行尾最后一格，且必须精确等于 OPEN
            continue
        out.append((p[0].strip(), p[1].strip(), p[3].strip()))
    return out, malformed


def selftest():
    r"""本判据自己的正负控（主人定过的硬规矩：自动检查必须拿已知坏样本验证它真会拦，
    而且要说清命中走的是退出码还是 WARN）。返回 0/1。"""
    rows7 = "| M-300 | 2026-10-27 16:0x | Qoder → CodeArts | 标题 | 正文 | - | OPEN |"
    rows6 = "| M-301 | 2026-10-27 16:0x | Qoder → CodeArts | 标题 | 正文 | OPEN |"
    esc = r"| M-302 | 2026-10-27 16:0x | Qoder → CodeArts | 标题 | 气泡 z=['\|', Z] | - | OPEN |"
    bare = "| M-303 | 2026-10-27 16:0x | Qoder → CodeArts | 标题 | 气泡 z=['|', Z] | - | OPEN |"
    done = "| M-304 | 2026-10-27 16:0x | Qoder → CodeArts | 标题 | 正文 | - | DONE |"
    legacy_bad = "| M-053 | 2026-10-20 10:0x | Qoder → CodeArts | 标题 | 正文 | 尾巴 | x | OPEN |"
    tmpl = "| M-xxx | 时间 | 发 → 收 | 主题 | 正文 | 文件 | OPEN |"
    ascii_arrow = "| M-305 | 2026-10-27 16:0x | Qoder -> CodeArts | 标题 | 正文 | - | OPEN |"
    cc = "| M-306 | 2026-10-27 16:0x | CodeArts -> Qoder/主人 | 标题 | 正文 | - | OPEN |"
    sender_side = "| M-307 | 2026-10-27 16:0x | Qoder -> CodeArts | 标题 | 正文 | - | OPEN |"
    cases = [
        ("正控①：7 格 OPEN 行读得到", "CodeArts", rows7, ["M-300"], []),
        ("正控②：6 格行（缺文件列）状态从行尾读得到（H-225 修前＝隐形）", "CodeArts", rows6, ["M-301"], []),
        (r"正控③：正文里的 \| 不顶坏行", "CodeArts", esc, ["M-302"], []),
        ("负控④：正文夹裸竖线 ⇒ 进坏行名单，不再静默跳过", "CodeArts", bare, [], ["M-303"]),
        ("对照⑤：DONE 行不算待办", "CodeArts", done, [], []),
        ("对照⑥：历史区（M-190 前）坏行不报，免得刷掉真信号", "CodeArts", legacy_bad, [], []),
        ("对照⑦：模板占位行 M-xxx 不误报", "CodeArts", tmpl, [], []),
        ("正控⑧：收件格写 ASCII -> 也认（现行区实测 11 行这么写，H-225 修前全隐形）",
         "CodeArts", ascii_arrow, ["M-305"], []),
        ("正控⑨：`CodeArts -> Qoder/主人` 抄送写法算 Qoder 的待办", "Qoder", cc, ["M-306"], []),
        ("对照⑩：只认箭头右侧——同一行问 Qoder 必须数不出来（发件人不算收件人）",
         "Qoder", sender_side, [], []),
    ]
    bad = 0
    for name, who, row, want_rows, want_mal in cases:
        r, m = open_rows(who, "## 消息表\n" + row + "\n")
        got_rows = [x[0] for x in r]
        got_mal = [x[0] for x in m]
        ok = (got_rows == want_rows and got_mal == want_mal)
        print("%s %s（期望 OPEN=%s 坏行=%s｜实得 OPEN=%s 坏行=%s）"
              % ("SELFTEST OK " if ok else "SELFTEST FAIL", name,
                 want_rows, want_mal, got_rows, got_mal))
        if not ok:
            bad += 1
    print("SELFTEST %s（mail_open 判据 %d 条）" % ("PASS" if bad == 0 else "FAIL", len(cases)))
    return 0 if bad == 0 else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    if len(args) != 1 or args[0] not in RECIP:
        sys.stderr.write(__doc__)
        return 2
    who = args[0]
    if not os.path.exists(MAIL):
        sys.stderr.write("MAILBOX not found: %s\n" % MAIL)
        return 2
    rows, malformed = open_rows(who)
    if malformed:
        sys.stderr.write(u"[WARN] 发给 %s 的消息里有 %d 行不是 6/7 格（正文换行被拆或夹了没转义的裸竖线），"
                         u"巡检读不到它们的状态格，请转义成 \\| 或修行：%s\n"
                         % (who, len(malformed),
                            u"、".join(u"%s(%d格)" % (m, n) for m, n in malformed)))
    if not rows:
        if malformed:
            sys.stderr.write(u"[WARN] 上面的坏行本身可能就是待办——先修行再判断「无 OPEN」\n")
            return 0
        print(u"信箱无 OPEN 消息")
        return 1
    print(u"信箱有 %d 条 OPEN 消息待处理：%s" % (len(rows), u"、".join(r[0] for r in rows)))
    if verbose:
        for mid, ts, subj in rows:
            print(u"  %s | %s | %s" % (mid, ts, subj[:70]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
