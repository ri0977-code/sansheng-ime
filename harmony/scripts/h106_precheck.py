#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-106 底栏收起键 —— 交付前的结构自检（只读，不改任何应用代码）。

为什么要这个脚本：H-106 已经来回三四轮，每一轮都是「改了但没改全」——
底栏加了键却没同时加到符号分支、或者把功能键挤掉了、或者干脆动了控制器。
这些在装机之前就能用静态检查判出来，不需要消耗一次真机安装（主人明确说过
不要反复装机）。所以：CodeArts 自己先跑，我验收时也跑同一份，判据一致。

判据分两级，只有 BLOCK 级决定退出码（历史上吃过亏：把提示级判据算进阻断，
夜间值守会永远「不可测」，等于闸门失效）：
  BLOCK  每个可见底栏 Row 都要有收起键 / 功能键不能少 / 不能越界操作面板 / 交付形式齐
  WARN   候选栏 ▼ 的老语义（版本结构不同，不作为阻断条件）

用法：
    python scripts/h106_precheck.py              # 当前工作树 + 交付形式
    python scripts/h106_precheck.py --json       # 机器可读（夜间值守用）
    python scripts/h106_precheck.py --kb <文件>  # 自测：只判结构（指 HEAD 副本验证判据不是恒 FAIL）
    python scripts/h106_precheck.py --selfcheck  # 自测：用临时台账验证交付判据不是恒 OK
    python scripts/h106_precheck.py --self-built  # 自建轮：只判结构，跳过交付判据（H-237）

退出码：0=BLOCK 全过（可以进入独立构建）；2=有 BLOCK 未过（先补齐，别报交付）
"""
import io
import json
import os
import re
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB = os.path.join(ROOT, "entry", "src", "main", "ets", "pages", "KeyboardIndex.ets")
WIP = os.path.join(ROOT, "docs", "WIP.md")
MAILBOX = os.path.join(ROOT, "docs", "MAILBOX.md")
PROGRESS = os.path.join(ROOT, "docs", "PROGRESS.md")

BLOCK, WARN = "BLOCK", "WARN"
# H-134：台账行的分钟位写成 x 时按整十点取（05:5x ⇒ 05:50），容差 6 分钟够吸收「刚写完这一行」
TS_AHEAD_TOL = 360

# 底栏不许消失的功能键（pressKey/releaseKey 的键 id 是稳定标识，比文案可靠）
REQUIRED_KEYS = ["sym123", "space", "dot", "enter", "lang"]
# 面板 API 只能由控制器封装；底栏直接碰这些 = 越界（历史上出过两次）
FORBIDDEN_PANEL_API = ["hidePanel", "destroyPanel", "setUiContent", "panel.show", "panel.hide"]
MTIME_MIN_AGE = 120  # 秒：构建前要等代码稳定


def read(path):
    return io.open(path, encoding="utf-8", errors="replace").read()


def match_block(text, open_idx):
    """从 text[open_idx]（必须是 '{'）做括号配对，返回闭合 '}' 的下标。"""
    depth = 0
    i = open_idx
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return len(text) - 1


def bottom_bar_span(src):
    """BottomBar() 构建函数的 (起始行, 结束行)（1-based，含端点）；找不到返回 None。"""
    lines = src.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if re.search(r"\bBottomBar\s*\(\s*\)\s*\{", ln):
            start = i
            break
    if start is None:
        return None
    tail = "\n".join(lines[start:])
    end_idx = match_block(tail, tail.index("{"))
    return (start + 1, start + tail[:end_idx].count("\n") + 1)


def top_rows(body):
    """底栏里并列可见的 Row 块（嵌套的不算），返回 [(分支标签, 内容)]。

    标签取该 Row 之前最近的分支条件 —— 这正是 H-106 反复返工的点：只给一个
    分支加键，切到另一个面板就没有收起键。写成「每个 Row 都要有」而不是「两个
    分支都要有」，这样单栏版本（HEAD 那种）也不会被误判成不合格。
    """
    spans = []
    for m in re.finditer(r"Row\s*\(\s*\)\s*\{", body):
        o = body.index("{", m.start())
        e = match_block(body, o)
        if any(s <= m.start() < en for s, en in spans):
            continue  # 嵌套在其他 Row 里，跳过
        spans.append((o + 1, e))
    out = []
    for s, e in spans:
        pre = body[:s]
        ifs = [mm for mm in re.finditer(r"panelMode\s*===\s*'(\w+)'", pre)]
        els = [mm for mm in re.finditer(r"}\s*else\s*\{", pre)]
        i_pos = ifs[-1].start() if ifs else -1
        e_pos = els[-1].start() if els else -1
        label = ifs[-1].group(1) if (ifs and i_pos > e_pos) else ("else" if e_pos >= 0 else "单栏")
        out.append((label, body[s:e]))
    return out


def weights(seg):
    return [float(x) for x in re.findall(r"\.layoutWeight\(\s*([0-9.]+)\s*\)", seg)]


def git(args):
    try:
        p = subprocess.run(["git", "-C", ROOT] + args, capture_output=True)
        return p.stdout.decode("utf-8", "replace").strip()
    except Exception as e:
        return "ERR:%s" % e


def last_id_row(path, pat):
    last = None
    for ln in read(path).splitlines():
        if re.match(pat, ln):
            last = ln
    return last


# M-107/M-108 里我自己写的字节数示例，绝不能被当成 CodeArts 报的数
# M-143 / H-131: delivery byte counts must state the build origin.
# This workspace carries 271,577 B of CRLF drift (19 packaged rawfile files with CR,
# and rawfile is stored uncompressed in the HAP), so the same commit built in a
# different directory/machine yields a HAP smaller by that much.
BUILD_ORIGIN_RE = re.compile(u"本机构建|同一工作区|本机产物|同一台机器")

PLACEHOLDER_DIGITS = "1234567"
DEFAULT_GATE = "H-106"

FRESH_HOURS = 3          # 本轮交付的新鲜度窗口（小时），见 delivery_rows() 里的说明
TS_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})[^0-9]{1,4}(\d{2}):(\d)")
EPOCH = __import__("calendar").timegm


def row_ts(ln):
    """把台账行的「2026-10-23 02:4x」这类时间读成秒；分钟位写成 x 时按 0 处理。读不到返回 None。"""
    m = TS_RE.search(ln)
    if not m:
        return None
    y, mo, d, hh, mi = (int(x) for x in m.groups())
    try:
        return EPOCH((y, mo, d, hh, mi, 0, 0, 0, 0))
    except Exception:
        return None


def cell(ln, n):
    parts = ln.strip().strip("|").split("|")
    return parts[n].strip() if len(parts) > n else ""


def future_rows(lines, now, tol=TS_AHEAD_TOL):
    """H-134：找出「行时间戳比本机时钟还往前」的台账行，返回 [(行号, 第一格, 超前分钟)]。

    为什么要机器判而不是靠自觉：05:3x 我对了一下 `git log`，发现自己整晚写的行标签
    一直超前真实时钟 5～17 分钟（提交于 05:15:42 的行标成 05:2x、05:23:59 标 05:4x、
    05:33:20 标 05:5x）—— 根因是拿上一轮的标签段往下推、没先读时钟。
    危害落在两处判据上：① 值守的并发闸门「PROGRESS 最后一行距今不足 20 分钟 ⇒ 本轮只读」，
    未来时间戳算出负龄 ⇒ 主会话其实早就静默了，值守还得继续只读，CodeArts 交付后要晚十来分钟才有人动；
    ② 本脚本的「交付行须在最新行往前 3 小时内」，最新行被写虚了窗口就跟着飘。
    只判 WARN：历史行既成事实不涂改，让它随时钟自然消退。
    now 必须用 now_local_epoch() 同基准传进来，否则本地墙上时间会凭空多算 8 小时。
    """
    hits = []
    for i, ln in enumerate(lines):
        ts = row_ts_band(ln)
        if ts and ts > now + tol:
            hits.append((i + 1, cell(ln, 0) or cell(ln, 1), int((ts - now) / 60)))
    return hits


def now_local_epoch():
    """台账里写的是本地墙上时间，而 row_ts/row_ts_band 用 calendar.timegm 解释它 ⇒ 取「现在」必须用同一基准。"""
    return EPOCH(time.localtime()[:6] + (0, 0, 0))


BAND_TS_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})[^0-9]{1,4}(\d{2}):(\d)(?:([0-5]\d|[xX]))?")


def row_ts_band(ln):
    """和 row_ts 的区别只有一个，但这条判据必须有：把「05:5x」读成 05:50（十分钟段起点）。

    row_ts 的正则只取冒号后第一个数字，于是 05:5x 被读成 05:05 —— 与它自己的注释（「x 按 0 处理」）不符，
    这是 H-135，已登记但今晚不动它：11 个已验样本的先后顺序是按 row_ts 跑的，同一小时内它的单调性还在，
    而 3 小时新鲜度窗口对 ≤50 分钟的误差不敏感，动它要重跑全部判据自测。
    本函数算的是「比时钟往前多少分钟」，误差 45 分钟就会把诚实的标签判成未来时间戳，所以单独实现。
    """
    m = BAND_TS_RE.search(ln)
    if not m:
        return None
    y, mo, d, hh, tens, rest = m.groups()
    mi = int(tens) * 10 if (rest is None or rest in ("x", "X")) else int(rest)
    try:
        return EPOCH((int(y), int(mo), int(d), int(hh), mi, 0, 0, 0, 0))
    except Exception:
        return None


def delivery_rows():
    """待验收的交付 = 台账里最后一条「CodeArts 署名 + 真实字节数」，且那个字节数没被它之后的行回抄过。

    02:5x 改这条的原因（值守 01:56 用真实代码复现的互等死锁，脚本在仓库外 Temp/tail_mask_repro.py）：
    旧写法只看「最新一行是不是 CodeArts」。台账只会越写越长 —— 他报完交付后，任何人（我、值守、他自己）
    再追加一行就把交付遮住，于是判据说「没有交付」、他说「你明明没理我」，两边都在等对方先动。
    现在改成从后往前扫第一条形态像交付的行，并用「字节数有没有被后面的行抄走」判是否已处理：
    遮住不了，也照样拦住重复构建同一个 HAP（我的验收行必须回抄他报的字节数，格式见 M-109）。
    仍然不用关键字筛（H-106／底栏／收起键 都会被历史行命中）：署名 + 真实字节数才是交付的形态。

    10:2x 修（H-158，两处都是**危险方向**的失效，不是显示问题）：
    ① 千位逗号 —— real_byte_counts() 出来是去掉逗号的「28203881」，而约定要我的 -re 行
       「逐字回抄他报的字节数」，文档里的写法带逗号（28,203,881）⇒ 旧写法 `c in after` 永不成立。
    ② 跨文件 —— 我的验收行按分工写在 MAILBOX（M-xxx-re），而他的交付行在 WIP，
       旧写法只把「同一个文件里后面的行」当干草堆 ⇒ 就算我把数抄得一字不差，W-215 仍算「待验收」，
       判据会继续放行「sign+install 这个包」，直接对着「同一个 HAP 不重复安装」那条铁律。
    现在：比较前两边都去掉千位逗号与空格，且「之后」按时间戳跨 WIP/MAILBOX 两个台账取。
    误判方向是安全的：多算一次「已处理」= 我少构建一次，最多让他重报一行；
    少算一次「已处理」= 我可能重复装机并浪费主人一次密码。

    10:4x 修（H-161，同一处判据的**反方向**失效）：上面那句「误判方向是安全的」当时并不成立 ——
    干草堆是「之后所有行的全文」，于是**任何一行**只要提到某个字节数就会把它判成已处理，包括我自己
    写的说明行。我 10:4x 写 M-161 时把 CodeArts 10:20 那两份产物的字节数（28,206,642／28,311,946）
    当事实抄了进去 ⇒ 他哪天提交后拿这同一组字节数报交付，判据会说「已处理、不用构建」，
    而实际上我根本没验收过那份。这正是 02:5x 那个互等死锁的另一种复活形式。
    现在把「回抄」限定成它本来的意思：**Qoder 署名、且点名引用了那条交付行 ID 的行**（我的验收行
    按约定都会写「W-215 ……」，见 M-159／M-160 实测）才算。两个方向各有样本：
    ① Qoder 行带数但不点 ID ⇒ 仍算待验收（新坏样本，防我把闸门做成「谁提过这个数就永久封死」）；
    ② Qoder 行点 ID 又带数 ⇒ 算已处理（保住 H-158 那条防重复装机的保护）。
    """
    out = []
    ledgers = ((WIP, r"^\| W-\d+"), (MAILBOX, r"^\| M-\d+"))
    per_file = {path: [ln for ln in read(path).splitlines() if re.match(pat, ln)]
                for path, pat in ledgers}
    for path, pat in ledgers:
        lines = per_file[path]
        other = per_file[MAILBOX if path == WIP else WIP]
        newest = max([ts for ts in (row_ts(ln) for ln in lines) if ts], default=None)
        for idx in range(len(lines) - 1, -1, -1):
            ln = lines[idx]
            if not cell(ln, 2).startswith("CodeArts"):
                continue
            counts = real_byte_counts(ln)
            if not counts:
                continue
            ts = row_ts(ln)
            rid = cell(ln, 0)
            ref = re.compile(r"(?<![\w-])%s(?!\d)" % re.escape(rid))
            later_cross = [l for l in other if ts is not None
                           and row_ts(l) is not None and row_ts(l) > ts]
            # 只有「Qoder 署名 + 点名引用了这条交付行」的行才算回抄（H-161）
            after = "\n".join(l for l in (lines[idx + 1:] + later_cross)
                              if cell(l, 2).startswith("Qoder") and ref.search(l))
            after_norm = re.sub(r"[, ]", "", after)
            if any(c in after_norm for c in counts):
                continue  # 字节数已被我的验收行抄走 = 已处理，不重复构建

            # 新鲜度窗口：台账里「最新的带时间戳行」往前 3 小时以内才算本轮。
            # 为什么要有这条：02:5x 我第一次跑新判据，它把 W-078（10-22 15:07）和
            # M-085-re2（10-22 18:40）当成待验收交付 —— 那是昨天早就验收并装过机的行，
            # 只是「验收行必须回抄字节数」这个约定今天才立，历史行没人抄过 ⇒ 复活了。
            # 复活旧行比漏判新行危险得多：漏判最多让他重报一次，复活会让我 sign+install
            # 一个他根本没说过的包。所以窗口窄一点是有意的保守。
            if ts is None or newest is None or newest - ts > FRESH_HOURS * 3600:
                continue  # 读不出时间戳 = 没法证明是本轮的，一律不算（03:0x 实测：M-044-re 写的是「~22:35」）
            out.append((os.path.basename(path), cell(ln, 0), ln))
            break
    return out


DIGIT_RE = re.compile(r"(?<![\d,.])(\d[\d,]{5,})(?![\d])")


def build_origin_unmarked(rows):
    """M-143／H-131：交付行报了字节数却没写「本机构建/同一工作区」⇒ 把这些行挑出来（WARN，不阻断）。

    10:2x 修（H-157）：旧写法在 main() 里取的是 `r[0]`，而 delivery_rows() 返回的是
    `(basename, row_id, full_line)` —— `r[0]` 是文件名 "WIP.md"，拿它去搜「本机构建」永远搜不到，
    所以 10-23 14:1x 起**每一条**待验收交付行都被这条 warn 误报，包括明明写了「(本机构建)」的
    W-214/W-215。warn 不参与阻断（exit code 不受它影响），但它把「让 CodeArts 补一句他早就写了的话」
    变成每轮都出现的提示 —— 现在改成看整行文本 `r[2]`，并加两个自测样本（写了⇒不点名，没写⇒点名）。
    """
    out = []
    for r in rows:
        if not BUILD_ORIGIN_RE.search(r[2]):
            out.append(u"%s: %s" % (r[1], r[2][:70]))
    return out


def real_byte_counts(text):
    """提取真实字节数：>=6 位、非占位示例、且带字节标记（28179829B / 28202740 B / 28179829 字节 / 字节数 28179829）。

    09:2x 修：旧版只按位数抓，于是 W-192 里手机序列号 7GL0226408083897 被当成
    「他报的字节数 0226408083897」，而且整条 selfcheck 仍然全绿。型号/序列号/像素计数
    这类长数字满天飞，字节数必须由「B / 字节」标记认领，不能靠长度猜。
    """
    hits = []
    for m in DIGIT_RE.finditer(text):
        digits = m.group(1).replace(",", "")
        if len(digits) < 6 or digits == PLACEHOLDER_DIGITS or digits in hits:
            continue
        after = text[m.end():m.end() + 4]
        before = text[max(0, m.start() - 8):m.start()]
        marked = (after.lstrip()[:1] in ("B", "b") or after.lstrip().startswith("字节")
                  or re.search(r"字节数?\s*[:=]?\s*$", before) is not None
                  or re.search(r"bytes?\s*[:=]?\s*$", before, re.I) is not None)
        if marked:
            hits.append(digits)
    return hits


def add(checks, name, ok, detail, sev=BLOCK):
    checks.append({"name": name, "ok": bool(ok), "detail": detail, "sev": sev})


def delivery_ok():
    """交付判据（台账尾部是 CodeArts 署名 + 报了真实字节数）是否成立。"""
    rows = delivery_rows()
    return rows, (real_byte_counts(" ".join(r[2] for r in rows)) if rows else [])


def selfcheck():
    """把「交付判据」本身拿去跑已知坏样本 —— 这次误报的成因就是没做这一步。

    每个样本都写清「应当判成什么」，判错就 exit 2。这样夜间值守和我用的是同一份
    判据，而且判据坏了会立刻暴露，不用等一次装机才发现。
    """
    global WIP, MAILBOX
    tmp = os.path.join(os.environ.get("TEMP", "/tmp"), "h106_selfcheck")
    os.makedirs(tmp, exist_ok=True)
    wip = os.path.join(tmp, "WIP.md")
    mail = os.path.join(tmp, "MAILBOX.md")

    def lead(extra):
        base = [
            "| W-147 | 2026-10-23 01:18 | Qoder | M6⑥ | DONE | x | 我写的说明，里面带形如 1234567B 的示例 | y | 待读 |",
            "| M-108 | 2026-10-23 01:18 | Qoder → CodeArts | 先跑 precheck | 交付三件套：字节数（形如 1234567B）| x | 未读 |",
        ]
        return base + list(extra)

    good = "| M-108-re | 2026-10-23 02:10 | CodeArts → Qoder | H-106 交付 | 两分支都加了 hideKeyboard，unsigned 28179829B | x | 已读 |"
    # 10:4x（H-161）：我的验收行必须**点名引用**被验收那条的 ID，否则不算回抄 ⇒ 样本跟着补上 M-108-re
    mine = "| M-109-re | 2026-10-23 03:00 | Qoder → CodeArts | H-106 验收通过 | M-108-re 那份，独立构建 28179829B 与他报字节数一致，已装机 | x | 未读 |"
    cases = [
        ("台账尾部还是我的指令（他没交付）", [], False),
        ("尾部是 CodeArts 但没报字节数", [
            "| M-108-re | 2026-10-23 02:10 | CodeArts → Qoder | H-106 完成 | 两分支都加了 hideKeyboard | x | 已读 |"], False),
        ("尾部是 CodeArts 但只抄了示例 1234567B", [
            "| M-108-re | 2026-10-23 02:10 | CodeArts → Qoder | H-106 | unsigned 字节数 1234567B | x | 已读 |"], False),
        ("他交付后我又写了验收行（不重复构建同一个 HAP）", [good, mine], False),
        ("同上，但我按文档写法带千位逗号「28,179,829 B」（H-158 的坏样本：旧写法认不出回抄，会诱导重复装机）", [
            good,
            "| M-109-re | 2026-10-23 03:00 | Qoder → CodeArts | H-106 验收通过 | M-108-re 那份，独立构建 28,179,829 B 与他报字节数一致，已装机 | x | 未读 |"], False),
        ("回抄写在**另一个台账**里（他交付在 WIP、我验收在 MAILBOX）⇒ 也必须认出已处理（H-158 第二处）", [
            "| W-900 | 2026-10-23 02:10 | CodeArts | H-106 | READY | x | unsigned 28179829B(本机构建) | y | 待读 |",
            "| M-109-re | 2026-10-23 03:00 | Qoder → CodeArts | H-106 验收通过 | W-900 那份，独立构建 28,179,829 B 与他报一致，已装机 | x | 未读 |"], False),
        ("我的行只是**转述**同一组字节数、没点交付行 ID ⇒ 不能算已处理（H-161 坏样本：否则任何一次转述都永久封死这条交付）", [
            good,
            "| M-110 | 2026-10-23 03:10 | Qoder → CodeArts | 事实转述，不是验收 | 你 10:20 那两份产物 unsigned 28179829B／signed 28311946B，我没放行 | x | 未读 |"], True),
        ("他自己在后面的行里重复同一个数 ⇒ 也不算已处理（回抄的署名必须是 Qoder）", [
            good,
            "| M-111-re | 2026-10-23 03:15 | CodeArts → Qoder | 再确认一次 | M-108-re 那份 unsigned 28179829B | x | 已读 |"], True),
        ("跨台账但没抄数字 ⇒ 必须仍算待验收（反向样本，防我把判据修成永远「已处理」）", [
            "| W-900 | 2026-10-23 02:10 | CodeArts | H-106 | READY | x | unsigned 28179829B(本机构建) | y | 待读 |",
            "| M-109-re | 2026-10-23 03:00 | Qoder → CodeArts | H-106 验收通过 | 独立构建通过，已装机（数字见 W-900） | x | 未读 |"], True),
        ("上一版误报的原样复现：尾部 M-108 是我写的", [
            "| M-108 | 2026-10-23 01:18 | Qoder → CodeArts | 报 unsigned 28111111B | x | 未读 |"], False),
        ("尾部是 CodeArts 且报了真实字节数", [good], True),
        ("交付行被后面的无关行遮住（旧写法在这里死锁，新写法必须仍能看见）", [good,
            "| M-110 | 2026-10-23 03:10 | Qoder → CodeArts | 一句与新交付无关的指令 | 这轮别动 module.json5 | x | 未读 |"], True),
        ("他又返工重报了一次新字节数（要按最新那条构建）", [good,
            "| M-112-re | 2026-10-23 03:20 | CodeArts → Qoder | H-106 返工 | 补齐另一栏，unsigned 28180000B | x | 已读 |"], True),
        ("昨天已验收的旧交付行（超窗口）不得复活", [
            "| M-085-re2 | 2026-10-22 18:40 | CodeArts → Qoder | H-096 修两个静态缺陷，signed 28,255,548 B | x | 已读 |"], False),
        ("交付行时间戳写成 ~22:35 这种带波浪号的（正则曾漏读而复活）", [
            "| M-044-re | 2026-10-21 ~22:35 | CodeArts → Qoder | H-054 全部完成，unsigned 27781430B | x | 已读 |"], False),
        ("交付行没有时间戳 ⇒ 无法证明是本轮，判不算", [
            "| M-120-re | 无时间 | CodeArts → Qoder | H-106 交付 | 两栏都有收起键，unsigned 28190000B | x | 已读 |"], False),
        ("09:2x 实测抓到的坏样本：真机自验行只写了手机序列号 7GL0226408083897", [
            "| W-192 | 2026-10-23 09:11 | CodeArts → Qoder | 真机自验 | Mate80 7GL0226408083897 点收起键折叠，金色回车像素 1807→0 | x | 待读 |"], False),
        ("字节数只写「字节数 28313998」不带 B 后缀也算（前缀标记）", [
            "| W-193 | 2026-10-23 09:30 | CodeArts → Qoder | H-106 返工 | 联合包 unsigned 字节数 28202740，signed 字节数 28313998 | x | 待读 |"], True),
    ]

    real_wip, real_mail = WIP, MAILBOX
    bad = 0
    print("== 交付判据自测（坏样本必须判 FAIL，好样本必须判 OK）==")
    for name, extra, expect_ok in cases:
        io.open(wip, "w", encoding="utf-8", newline="\n").write("\n".join(lead(extra)) + "\n")
        io.open(mail, "w", encoding="utf-8", newline="\n").write("\n".join(lead(extra)) + "\n")
        WIP, MAILBOX = wip, mail
        rows, digits = delivery_ok()
        got = bool(rows) and bool(digits)
        WIP, MAILBOX = real_wip, real_mail
        mark = "OK " if got == expect_ok else "!! "
        if got != expect_ok:
            bad += 1
        print("  %s 期望=%-4s 实际=%-4s 尾部交付=%s 数=%s  %s" %
              (mark, "OK" if expect_ok else "FAIL", "OK" if got else "FAIL",
               "/".join(r[1] for r in rows) or "-", digits, name))
    print("== 时钟判据自测（H-134：未来时间戳会不会被点名）==")
    # 基准必须与 future_rows 内部一致（本地墙上时间当 UTC），否则样本会整体偏 8 小时
    base = now_local_epoch()
    # 标签写成 x 段时按整十点取起点（05:5x ⇒ 05:50），所以样本各留 30 分钟余量
    fut = time.strftime("%Y-%m-%d %H:%M", time.gmtime(base + 1800))[:-1] + "x"
    past = time.strftime("%Y-%m-%d %H:%M", time.gmtime(base - 1800))[:-1] + "x"
    ccases = [
        ("超前约 30 分钟的行 ⇒ 必须点名", ["| W-9 | %s | Qoder | x |" % fut], 1),
        ("30 分钟前的行 ⇒ 不得点名", ["| W-9 | %s | Qoder | x |" % past], 0),
        ("读不出时间戳的行 ⇒ 不得点名", ["| W-9 | 无时间 | Qoder | x |"], 0),
    ]
    for name, lns, expect in ccases:
        got = len(future_rows(lns, base))
        ok = got == expect
        if not ok:
            bad += 1
        print("  %s 期望点名=%d 实际=%d  %s（样本标签 %s）" % ("OK " if ok else "!! ", expect, got, name,
                                                              lns[0].split("|")[2].strip() if got or expect else "-"))

    print("== 构建来源判据自测（H-157：warn 挑的是整行，不是文件名）==")
    ocases = [
        ("交付行写了「(本机构建)」⇒ 不得点名", [good.replace("unsigned 28179829B", "unsigned 28179829B(本机构建)")], 0),
        ("同一条行没写构建来源 ⇒ 必须点名", [good], 1),
    ]
    for name, extra, expect in ocases:
        io.open(wip, "w", encoding="utf-8", newline="\n").write("\n".join(lead(extra)) + "\n")
        io.open(mail, "w", encoding="utf-8", newline="\n").write("\n".join(lead(extra)) + "\n")
        WIP, MAILBOX = wip, mail
        rows2, _ = delivery_ok()
        got = len(build_origin_unmarked(rows2))
        WIP, MAILBOX = real_wip, real_mail
        ok = got == expect
        if not ok:
            bad += 1
        print("  %s 期望点名=%d 实际=%d  %s" % ("OK " if ok else "!! ", expect, got, name))

    print("结论：%s" % ("判据可信" if not bad else "判据有问题（%d 个样本判错），先别拿它验收" % bad))
    return 0 if not bad else 2


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    want_json = "--json" in sys.argv
    if "--selfcheck" in sys.argv:
        return selfcheck()
    selftest = "--kb" in sys.argv
    # H-237(CodeArts): 自建轮通路——跳过交付判据（checkpoint/交付行/字节数），
    # 只跑结构判据（BottomBar/功能键/越界）。自建轮没有 CodeArts 交付行，三条永远补不上。
    self_built = "--self-built" in sys.argv
    kb_path = sys.argv[sys.argv.index("--kb") + 1] if selftest else KB
    checks = []

    src = read(kb_path)
    lines = src.splitlines()
    span = bottom_bar_span(src)
    if not span:
        add(checks, "结构:找到 BottomBar()", False, "源码里没有 BottomBar() 构建函数")
        report(want_json, checks, "（未取到 HEAD）")
        return 2
    add(checks, "结构:找到 BottomBar()", True, "L%d..L%d" % span)
    body = "\n".join(lines[span[0] - 1:span[1]])
    rows = top_rows(body)
    add(checks, "结构:底栏 Row 解析", len(rows) >= 1,
        "并列 Row %d 个：%s" % (len(rows), ", ".join(lbl for lbl, _ in rows)))

    # 核心判据：每个可见底栏都要有收起键（这条写法自动覆盖「两个分支都要加」）
    # 主人 2026-10-23 10:23 明确指示改判据（W-200／M-130）：
    # 「右上角箭头不能折叠…你又在左下角加了一个箭头…那右上角箭头干嘛用啊」
    # ⇒ 折叠入口收敛到**候选栏右上角那一个三角**（智能双功能：有候选＝展开网格／无候选＝收起键盘，长按恒收起），
    # **底栏不再放独立收起键**。所以旧判据「每一栏都要有 hideKeyboard」已作废，
    # 换成「全文至少一处 hideKeyboard 出口 + 三角的条件分支在」。
    # 旧判据每次跑都报两个假 FAIL，会掩盖真问题（14:4x 清）。
    fold_exits = src.count("hideKeyboard")
    # 收紧：光有「candidates.length」不够（14:4x 用已知坏样本验出来的洞 —— 把分支
    # 条件改成 if (false) 后这两个串都还在，判据仍放行）。要求**某个 onClick 段里**
    # 同时出现「候选判断」「setExpanded」「hideKeyboard」。
    # 注意：全文可能有多个 onClick（候选键也有一个），所以逐个看，命中一个就算。
    smart_triangle = False
    for tri in re.finditer(r"\.onClick\(\(\)\s*=>\s*\{(.{0,800}?)\n\s*\}\)", src, re.S):
        seg = tri.group(1)
        if (("candidates.length" in seg) or ("preedit.length" in seg)) \
                and "hideKeyboard" in seg and "setExpanded" in seg:
            smart_triangle = True
            break
    add(checks, "折叠出口在候选栏右上角三角（智能双功能）", fold_exits >= 1 and smart_triangle,
        ("全文 hideKeyboard %d 处；三角 onClick 段内同时有候选判断、setExpanded 与 hideKeyboard"
         "（有候选展开网格／无候选收起键盘）⇒ 符合主人指示" % fold_exits)
        if (fold_exits >= 1 and smart_triangle) else
        ("没找到「三角 onClick = 候选判断 + setExpanded + hideKeyboard」这个形态（当前段内："
         "候选判断=%s、hideKeyboard=%s、setExpanded=%s）。"
         "主人 10-23 定的口径：一个三角两个功能 —— 有候选点它展开候选网格、无候选点它收起键盘、"
         "长按恒收起；底栏不放独立收起键。" % ("candidates.length" in seg, "hideKeyboard" in seg,
                                            "setExpanded" in seg)))
    for label, seg in rows:
        ws = weights(seg)
        # 底栏不再要求收起键；这里只报它有多少键、权重和多少，供布局参考
        add(checks, "底栏[%s]形态" % label, True,
            "并列 Row %d 个键 / layoutWeight 求和 %.1f（收起键不在这栏，按主人指示收敛到候选栏右上角三角）"
            % (len(ws), sum(ws)))

    # 功能键不能因为加键而被删
    for k in REQUIRED_KEYS:
        add(checks, "功能键未丢失:%s" % k, k in body, "底栏里应能 pressKey/releaseKey '%s'" % k)

    # 越界检查：底栏直接调面板 API
    bad = [api for api in FORBIDDEN_PANEL_API if api in body]
    add(checks, "底栏未直接操作面板 API", not bad,
        "越界调用: %s —— 只允许 keyboardController.hideKeyboard()" % bad if bad else "只通过 hideKeyboard()")

    # 候选栏 ▼ 老语义：结构随版本变化，提示级，不阻断
    add(checks, "候选栏 ▼ 仍在", ("chevron_down" in src and "hideKeyboard" in src),
        "全文 chevron_down %d 处 / hideKeyboard %d 处；候选栏折叠键语义=panel.hide 不销毁面板" %
        (src.count("chevron_down"), src.count("hideKeyboard")), sev=WARN)

    head = "自测模式（只判结构）"
    if self_built:
        head = "自建轮模式（只判结构，跳过交付判据）"
    if not selftest and not self_built:
        # 交付形式：没有记账行和字节数，我没有可比对的基准，构建装机都无意义
        age = time.time() - os.path.getmtime(kb_path)
        add(checks, "代码已静置 >=120s", age >= MTIME_MIN_AGE, "KeyboardIndex.ets mtime 距今 %.0fs" % age)
        # 09:2x 修：原来只查 KeyboardIndex.ets，于是 4debbe3 之后工作区还有 11 改 4 新
        # （含 KeyboardIndex 调用、但 HEAD 里不存在的 KeyboardController.hideKeyboard），
        # 这里仍打印「工作区状态: clean」——HEAD 根本编不过，这组字节无法从任何提交重建。
        # 交付字节取自工作区 ⇒ checkpoint 必须覆盖 entry/src 与 AppScope 的全部改动。
        dirty = git(["status", "--porcelain", "--", "entry/src", "AppScope"])
        dirty_lines = [ln for ln in dirty.splitlines() if ln.strip()]
        detail = "clean（entry/src、AppScope 无未提交改动）"
        if dirty_lines:
            detail = "%d 项未提交（前 8 项）: %s —— 交付字节取自工作区，HEAD 重建不出同一组字节；" \
                     "先把本轮改到的文件全部提交（含被调用方，如 KeyboardController.ets），再报交付" % (
                         len(dirty_lines), "; ".join(ln.strip() for ln in dirty_lines[:8]))
        add(checks, "已做 checkpoint 提交", not dirty_lines, "工作区状态: %s" % detail)
        head = git(["log", "--oneline", "-1"])
        rows, digits = delivery_ok()
        add(checks, "台账有待验收的 CodeArts 交付行", bool(rows),
            ("待验收交付: %s（%s）—— 该行字节数尚未被后面的行回抄，且在最新行往前 %d 小时内" % ("/".join(r[1] for r in rows), "+".join(r[0] for r in rows), FRESH_HOURS)) if rows else
            ("WIP/MAILBOX 里没有「CodeArts 署名 + 真实字节数 + 未被回抄」的行 ⇒ 本轮没有待验收交付。"
             "两类情况都会走到这里：他还没报，或我的验收行已经抄过他的字节数（那就不该再构建同一个 HAP）。"
             "我自己的指令里带的示例字节数一律不算他报的数；02:5x 起交付行不再要求位于台账末尾，"
             "但必须在最新行往前 %d 小时以内（03:0x 加的窗口：昨天已验收的旧行不许复活，复活旧行会让我装错包）。"
             "另外：交付行的时间戳要写成 2026-10-23 03:10 这种能被读出来的形式（「~22:35」这类算不了本轮）。"
             "如果他确实有一条超过 %d 小时没被我验收的交付，重写一条带时间戳的交付行就行" % (FRESH_HOURS, FRESH_HOURS)))
        add(checks, "交付行含 unsigned 字节数", bool(digits),
            ("他报的字节数: %s —— 独立构建后**只比 unsigned 文件的字节数**（不比 hash：HAP 的 ZIP 时间戳取构建时刻，跨构建不可能逐字节相同，见 `docs/BUILD.md` §2.1）" % ", ".join(digits)) if digits else
            ("没有待验收交付行，或那条行里没写真实字节数（需 >=6 位且不是示例 1234567，形如 28179829B 或 字节数 28179829）。"
             "没有可比对的基准我就不构建，避免装完发现版本对不上"))

        # M-143 / H-131: delivery byte counts should state the build origin.
        # WARN only, and only for rows inside the freshness window: historical
        # deliveries (10-21 etc.) predate the convention, naming them is noise.
        # 10:2x (H-157) 取值字段从 r[0]（文件名）改成整行文本，逻辑搬进 build_origin_unmarked()。
        unmarked = build_origin_unmarked(rows)
        add(checks, u"交付字节数标注了构建来源", not unmarked,
            (u"所有 CodeArts 交付行都写了构建来源（本机构建/同一工作区）—— 跨目录构建会差 271,577 B（H-131），"
             u"所以字节数只在同一台机器、同一工作区里比对（H-133 的前提）") if not unmarked else
            (u"这些 CodeArts 交付行报了字节数但没说明是哪台机器构建的：%s。"
             u"本机有 271,577 B CRLF 漂移，换目录/换机器构建出的 HAP 会小这么多；"
             u"请在后续交付行里写「unsigned 28,xxx,xxx B（本机构建）」（M-143）" % (u" | ".join(unmarked[:3]))),
            sev=WARN)

        # H-134：台账行的时间戳不得比本机时钟往前 —— 值守的并发闸门和 3 小时窗口都吃这个数
        now = now_local_epoch()
        ahead = []
        for path in (WIP, MAILBOX, PROGRESS):
            lns = [l for l in read(path).splitlines() if l.startswith("| ")]
            for ln_no, rid, mins in future_rows(lns[-15:], now):
                ahead.append("%s %s（第 %d 行）超前 %d 分钟" % (os.path.basename(path), rid or "-", ln_no, mins))
        add(checks, "台账时间戳未超前本机时钟", not ahead,
            "最近 15 行没有未来时间戳（本机时钟 %s）" % time.strftime("%Y-%m-%d %H:%M")
            if not ahead else
            "未来时间戳：%s ⇒ 值守的「最后一行距今不足 20 分钟就只读」会算出负龄，"
            "主会话其实已经静默了它仍可能只读，CodeArts 交付后要晚上十来分钟才有人动手；"
            "写法：落笔前先跑 date 取本机时钟，标签段照真实分钟写（H-134）" % "; ".join(ahead[:6]),
            sev=WARN)

    report(want_json, checks, head)
    return 0 if not [c for c in checks if c["sev"] == BLOCK and not c["ok"]] else 2


def report(want_json, checks, head):
    blocked = [c for c in checks if c["sev"] == BLOCK and not c["ok"]]
    warns = [c for c in checks if c["sev"] == WARN and not c["ok"]]
    if want_json:
        print(json.dumps({"head": head, "checks": checks, "blocking": len(blocked),
                          "warn": len(warns), "passed": not blocked}, ensure_ascii=False, indent=2))
        return
    print("== H-106 交付前自检 ==  %s" % head)
    for c in checks:
        tag = "[OK  ]" if c["ok"] else ("[FAIL]" if c["sev"] == BLOCK else "[warn]")
        print("  %s %-24s %s" % (tag, c["name"], c["detail"]))
    print("结论：%s（阻断 %d 项 / 提示 %d 项）" %
          ("BLOCK 全过，可以进入独立构建" if not blocked else "先补齐再报交付，不要装机", len(blocked), len(warns)))


if __name__ == "__main__":
    sys.exit(main())
