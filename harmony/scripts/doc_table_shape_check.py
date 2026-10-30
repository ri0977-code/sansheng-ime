#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文档表格形状守卫（H-250，Qoder 2026-10-28 07:2x）。

为什么必须有它（不是形式主义）：
  同一族病**第二次落地**。10-26 的 M-244「行被空行拆断缺两格」之后，我在 10-28 07:1x 用 Edit 往
  `docs/ISSUES.md` 的 H-242 行里插了一段**带换行**的文本 ⇒ 那一行被拆成 8 个物理行、列数 7→6、尾格丢失，
  台账读起来就是「状态格没了／判据丢了」。第一次的修复只是散文提醒，没有拦截 ⇒
  按 H-130/H-238 口径「只打 WARN、永远不阻断的检查＝没有」，这条守卫**默认 FAIL、退出码非零**。

判据（只查真正被机器与下一个人读的三张表）：
  ① `docs/ISSUES.md` 每张表块内所有行必须与该表表头同列数（现状＝7），
     且**不许断行**——以竖线开头却不以竖线结尾的行＝一条账被拆成两个物理行（后一行也一并报出）；
  ② `docs/MAILBOX.md` 的**每个表格块**都要自洽：块里有表头 ⇒ 行数＝表头列数；没有表头 ⇒ 以块内第一行为准；
     同样不许断行（M-254/M-257/M-261-re 三条已知缺「文件」列的走 `MAILBOX_ALLOW`，
     等主人点头改列口径＝H-223，不在本轮追改）。**H-253 修正**：H-250 原版只查 `## 消息表` 一节，
     而当天新消息全被追加在文件末尾 ⇒ 28 条没查过、M-298 被裸竖线拆成 12 格还报绿；
  ③ `docs/PROGRESS.md`「最近交接」表：只对带圈编号（①②…）的追加行要求 5 列
     （更早的历史行是 2–4 列旧形状，动它们＝越界）。

棘轮而非清洗：守卫上线**之前**就存在的违规登记在 `scripts/doc_table_shape_baseline.txt`
（一行一个 `表名:行首格:症状`）。这些行**不阻断**，也不许悄悄重写——逐条修＝逐条决定（H-129 口径）。
基线里的条目本次扫描没再命中 ⇒ 打印「可收缩 N 条」（不 FAIL），手动删掉那几行即完成交接。

用法：
  python scripts/doc_table_shape_check.py            # 真树对账，红＝退出码 1
  python scripts/doc_table_shape_check.py --selftest # 10 条断言：6 种坏形状判红（含 H-253 的两种真形状）
                                                     #   ＋基线放行＋真树 0 新增＋端到端（复制真树到临时
                                                     #   目录插坏行，必须判红且 rc=1）
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLIT = re.compile(r'(?<!\\)\|')          # 转义感知：正文里的 \| 不是分隔符（H-225 那一族）
# 已知的历史形状，不追改（改了就是动别人的账）
MAILBOX_ALLOW = {'M-254', 'M-257', 'M-261-re'}

BASELINE_FILE = os.path.join(ROOT, 'scripts', 'doc_table_shape_baseline.txt')


def load_baseline():
    ids = set()
    if os.path.exists(BASELINE_FILE):
        with io.open(BASELINE_FILE, encoding='utf-8') as f:
            for ln in f:
                ln = ln.strip()
                if ln and not ln.startswith('#'):
                    ids.add(ln)
    return ids


def cells(line):
    parts = SPLIT.split(line)
    inner = parts[1:-1]
    if not inner:                        # 行首有竖线但行尾没有＝断行/半行，本身已经是违规
        inner = [parts[1].strip() if len(parts) > 1 else '']
    return [c.strip() for c in inner]


def ncells(line):
    return len(SPLIT.split(line)) - 2


def row_id(line):
    c = cells(line)
    return c[0] if c else '?'


def key_id(rid):
    """基线键里的行首格：空白折成下划线并截断到 24 个字符。
    ISSUES/MAILBOX 里有些行的首格是一整段散文（例：`ISSUES.md:237` 那条 10-24 的复验注），
    不处理的话键里带空格、也没法手工删。折＋截断后同一行永远得到同一个键。"""
    return re.sub(r'\s+', '_', rid).strip()[:24]


def read_at(path):
    with io.open(path, encoding='utf-8') as f:
        return f.read().split('\n')


def read(path):
    return read_at(os.path.join(ROOT, path))


def _mark(key, detail, out):
    """违规分类：不在基线里＝新增（进 out['new']，FAIL）；在基线里＝命中（进 out['hit']，不阻断）。
    `new` 存的是 (键, 说明) 二元组——别拼成一个字符串再 split，键里可能带冒号。"""
    if key in out['base']:
        out['hit'].add(key)
    else:
        out['new'].append((key, detail))


def is_separator(line):
    return line.startswith('|---') or line.startswith('|:') or set(line) <= set('|-: ')


def check_issues(lines, out):
    """ISSUES.md：表块内列数与表头一致＋行不许断。返回 None，结果写进 out。"""
    expect = None
    for n, ln in enumerate(lines, 1):
        if is_separator(ln):
            continue
        if ln.startswith('|'):
            rid = row_id(ln)
            if not ln.rstrip().endswith('|'):
                _mark('ISSUES:%s:尾格丢失' % key_id(rid),
                      '行以竖线开头却不以竖线结尾＝断行/尾格丢失（首格=%s 行%d）' % (key_id(rid), n), out)
            c = ncells(ln)
            if expect is None:
                expect = c
            elif c != expect:
                _mark('ISSUES:%s:列%d' % (key_id(rid), c),
                      '列数=%d（本表表头=%d）首格=%s 行%d' % (c, expect, key_id(rid), n), out)
        elif ln.strip() and _is_continuation(lines, n):
            # 上一条是断行、这一条不以竖线开头＝同一条账被拆出去的后半截（真实事故就是这个形状）
            _mark('ISSUES:%s:续行' % key_id(row_id(lines[n - 2])),
                  '上一行以竖线开头却不以竖线结尾，本行是它的后半截（行%d）' % n, out)
        else:
            expect = None      # 表块结束


def _is_continuation(lines, n):
    """行 n（1-based）本身不是表格行，但上一行是「以竖线开头却不以竖线结尾」的断行 ⇒ 它是后半截。"""
    prev = lines[n - 2] if n >= 2 else ''
    return prev.startswith('|') and not prev.rstrip().endswith('|')


def check_mailbox(lines, out):
    """MAILBOX：**逐个表格块自校准列数**（H-253）。

    H-250 那版只查 `## 消息表` 那一节（`in_msgs` 一遇到下一个 `## ` 就关掉），可当天的
    M-270～M-298 全被追加在文件末尾（`## 当前看板` 之后）⇒ 这 28 条**一条都没被查过**：
    M-298 里两条**裸竖线**（`|wx - letterTouchDownX|` 的绝对值符号）把一行拆成 12 格，
    守卫照样打印「新增违规 0 条」——假绿比没查更坏（H-130/H-238 口径）。

    改法＝按**表格块**判，块内自校准：块里有表头分隔行 ⇒ 以表头列数为准；没有 ⇒ 以块内第一行为准。
    这样「消息表」7 列、上方看板 9 列、催办小表 2 列各按自己的表头，互不误伤；
    末尾那截没有表头的续行块也会被第一行校准，裸竖线造成的 12 格照样判红。
    """
    expect = None
    for n, ln in enumerate(lines, 1):
        if is_separator(ln):
            continue
        if ln.startswith('|'):
            rid = row_id(ln)
            c = ncells(ln)
            if expect is None:
                expect = c            # 块内第一行（表头或首条消息）＝本块口径
            if not ln.rstrip().endswith('|'):
                _mark('MAILBOX:%s:尾格丢失' % key_id(rid),
                      '行以竖线开头却不以竖线结尾＝断行/尾格丢失（首格=%s 行%d）' % (key_id(rid), n), out)
            if c != expect and rid not in MAILBOX_ALLOW:
                _mark('MAILBOX:%s:列%d' % (key_id(rid), c),
                      '列数=%d（本块口径=%d）首格=%s 行%d' % (c, expect, key_id(rid), n), out)
        elif ln.strip() and _is_continuation(lines, n):
            _mark('MAILBOX:%s:续行' % key_id(row_id(lines[n - 2])),
                  '上一行以竖线开头却不以竖线结尾，本行是它的后半截（行%d）' % n, out)
        else:
            expect = None             # 表块结束


def check_progress(lines, out):
    """只看带圈编号（①②…）的追加行：那些是本轮起的账，必须 5 列。"""
    for n, ln in enumerate(lines, 1):
        m = re.match(r'^\| ([①-⑳]+) ', ln)
        if not m:
            continue
        c = ncells(ln)
        if c == 5:
            continue
        _mark('PROGRESS:%s:列%d' % (m.group(1), c),
              '行列数=%d（最近交接表表头=5）行%d' % (c, n), out)


SCOPES = ((check_issues, 'docs/ISSUES.md'),
          (check_mailbox, 'docs/MAILBOX.md'),
          (check_progress, 'docs/PROGRESS.md'))


def scan(base=None):
    """扫真树：返回 (新增违规列表, 命中基线集合, 基线总数)。"""
    out = {'new': [], 'hit': set(), 'base': load_baseline() if base is None else base}
    for fn, path in SCOPES:
        fn(read(path), out)
    return out['new'], out['hit'], len(out['base'])


# ---- 自测：四类「看起来没问题、实际坏了」的形状必须全部被判红；真树必须无新增 ----
def selftest():
    ok = True
    cases = []

    issues_cols = ['| A | B | C | D | E | F | G |', '|---|---|---|---|---|---|---|',
                   '| H-1 | x | y | z | u | v | w |', '| H-2 | x | y | z | u | v |']
    issues_break = ['| A | B | C | D | E | F | G |', '|---|---|---|---|---|---|---|',
                    '| H-1 | x | y | z | u | v | w |',
                    '| H-2 | x | y | z | u | v 这段在行中被敲了回车',
                    '   拆成了两个物理行 |']
    mailbox_short = ['## 消息表', '| 编号 | 时间 | 收发 | 事项 | 正文 | 文件 | 状态 |',
                     '|---|---|---|---|---|---|---|',
                     '| M-9 | t | a→b | s | body | f | OPEN |',
                     '| M-10 | t | a→b | s | body | OPEN |']
    # H-253 的两个真形状：① 消息追在**别的章节**后面（旧版按 `## 消息表` 划范围 ⇒ 看不见）；
    # ② 正文里写绝对值 `|x - y|`（裸竖线）把一行拆成 12 格。
    mailbox_tail = ['## 当前看板', '',
                    '| M-20 | t | a→b | s | body | f | OPEN |',
                    '| M-21 | t | a→b | s | `!f && |wx - down| < 5vp` 时跳过 | f | ACK |']
    mailbox_break = ['## 消息表', '| 编号 | 时间 | 收发 | 事项 | 正文 | 文件 | 状态 |',
                     '|---|---|---|---|---|---|---|',
                     '| M-30 | t | a→b | s | 这条在行中被敲了回车',
                     '  拆成了两个物理行 | f | OPEN |']
    progress_short = ['| 日期 | 从 | 到 | 内容 | 状态 |', '|---|---|---|---|---|',
                      '| ⑨ 10-28 | Qoder | x | y |']

    empty = {'new': [], 'hit': set(), 'base': set()}
    out = dict(empty, new=[], hit=set())
    check_issues(issues_cols, out)
    cases.append(('issues-缺格', out['new'], True))
    out = dict(empty, new=[], hit=set())
    check_issues(issues_break, out)
    cases.append(('issues-断行', out['new'], True))
    out = dict(empty, new=[], hit=set())
    check_mailbox(mailbox_short, out)
    cases.append(('mailbox-缺格', out['new'], True))
    out = dict(empty, new=[], hit=set())
    check_mailbox(mailbox_tail, out)
    cases.append(('mailbox-尾部裸竖线', out['new'], True))
    out = dict(empty, new=[], hit=set())
    check_mailbox(mailbox_break, out)
    cases.append(('mailbox-断行', out['new'], True))
    out = dict(empty, new=[], hit=set())
    check_progress(progress_short, out)
    cases.append(('progress-缺格', out['new'], True))

    # 基线必须真的能放行：把 issues-缺格 的违规号写进 base，同一个样本就该变绿。
    key = 'ISSUES:%s:列6' % key_id(row_id(issues_cols[3]))
    out = {'new': [], 'hit': set(), 'base': {key}}
    check_issues(issues_cols, out)
    passed = (out['hit'] == {key})
    cases.append(('基线放行(应当绿)',
                  out['new'] + ([] if passed else [('基线未命中', 'hit=%s 期望=%s' % (sorted(out['hit']), key))]),
                  False))

    new_bad, _hit, total = scan()                  # 真树：对已提交基线跑，必须 0 新增
    cases.append(('真树新增违规=0', new_bad, False))

    # 端到端：把真树三张表复制到临时目录，**在表中间**插一条断行，守卫必须从磁盘读出来判红。
    # 只测内存里的解析函数＝测不到 read()/ROOT/基线加载这条通路（H-130「验证检查本身」）。
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix='h250-')
    saved_root = ROOT
    try:
        os.makedirs(os.path.join(tmp, 'docs'))
        for p in ('docs/ISSUES.md', 'docs/MAILBOX.md', 'docs/PROGRESS.md'):
            shutil.copyfile(os.path.join(saved_root, p), os.path.join(tmp, p))
        ip = os.path.join(tmp, 'docs/ISSUES.md')
        lines = read_at(ip)
        at = next((i for i, x in enumerate(lines) if x.startswith('| H-') and x.endswith('|')), None)
        if at is None:
            cases.append(('端到端-找不到锚点', [('锚点', 'ISSUES.md 里没有一条完整表格行')], True))
        else:
            # 真实事故的形状：一行账被回车拆成两个物理行，第二个不以竖线收尾
            bad_rows = ['| H-999 | a | b | c | d | e 这条是自测故意插的坏行',
                        '  f | g | 后半截 |']
            lines[at + 1:at + 1] = bad_rows
            with io.open(ip, 'w', encoding='utf-8', newline='\n') as f:
                f.write('\n'.join(lines) + '\n')
            globals()['ROOT'] = tmp
            found = [x for x in scan(set())[0] if x[0].startswith('ISSUES:H-999')]
            cases.append(('端到端-插坏行必红', found, True))
            # 退出码通路也要证明：坏树上 `run_check()` 必须返回 1（只打 WARN 的检查永远不会阻断＝没有）。
            rc = run_check(verbose=False)
            cases.append(('端到端-阻断rc=1(绿)',
                          [] if rc == 1 else [('rc', '实得 %d 期望 1（只打 WARN＝没有）' % rc)], False))
    finally:
        globals()['ROOT'] = saved_root
        shutil.rmtree(tmp, ignore_errors=True)

    for label, got, want_hit in cases:
        hit = bool(got)
        good = (hit == want_hit)
        ok = ok and good
        print('[selftest] %-18s 期望=%s 实得=%s %s%s'
              % (label, '红' if want_hit else '绿', '红' if hit else '绿',
                 'OK' if good else '<<< 判据失效',
                 ('  %s %s' % got[0])[:110] if got else ''))
    if not ok:
        print('H-250 自测失败 ⇒ 检查本身不可信，别信它的结论')
        return 1
    print('H-250/H-253 自测通过: 6 种坏形状全部判红（含「消息追在别的章节后面」与「正文裸竖线拆格」两种真形状）、'
          '基线放行生效、端到端（临时目录＋断行＋退出码 1）成立、真树新增违规 0（基线 %d 条在册）。' % total)
    return 0


def run_check(verbose=True):
    """真树对账：返回退出码（0＝无新增违规，1＝有）。拆出来是为了让自测能连**退出码通路**一起验。"""
    new_bad, hit, total = scan()
    shrinkable = total - len(hit)
    if verbose:
        for key, detail in new_bad:
            print('[FAIL] %s %s' % (key, detail))
        print('H-250 文档表格形状守卫: 新增违规 %d 条；基线在册 %d 条、本次命中 %d 条、可收缩 %d 条'
              '（ISSUES 7 列／MAILBOX 7 列／PROGRESS 追加行 5 列；MAILBOX_ALLOW 3 条等主人点头＝H-223）'
              % (len(new_bad), total, len(hit), shrinkable))
    if new_bad:
        if verbose:
            print('结论: 台账表格形状**回归**——要么是新写的行断行/缺格，要么是基线里的行被改坏后换了症状号。'
                  '改行走脚本＋当场数格，别用带换行的插入。')
        return 1
    if verbose:
        if shrinkable:
            print('提示: 基线里有 %d 条本次没再命中（已修好或已删行），可以逐条从 %s 里删掉。'
                  % (shrinkable, 'scripts/doc_table_shape_baseline.txt'))
        print('结论: 本轮没有新增形状违规（历史违规逐条决定，不整包重写）。')
    return 0


def main():
    if '--selftest' in sys.argv:
        return selftest()
    return run_check()


if __name__ == '__main__':
    sys.exit(main())
