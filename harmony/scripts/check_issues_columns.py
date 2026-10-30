#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ISSUES.md 行列数自检（H-233 守卫）。

**为什么要有这个闸门**：`docs/ISSUES.md` 的表头是 7 列
（ID｜状态｜优先级｜归属｜问题｜证据 / 位置｜下一步），但 2026-10-27 22:5x 实测有
**32 行**的格子数不是 7（多为 8：末尾多挂了一格「【…真机取证】」）。
Markdown 渲染按表头列数截断 ⇒ **多出来的最后一格被整格吞掉**，
主人看表就看不到那些验收/取证内容，而且 git diff 里明明写着 ⇒ 极难察觉。

用法：
    python scripts/check_issues_columns.py            # 审计当前 ISSUES.md（现为 WARN 级）
    python scripts/check_issues_columns.py --strict   # 有破表行就 exit 1（H-233 收口后启用）
    python scripts/check_issues_columns.py --selftest # 用已知坏样本证明判据本身有效

判据（与渲染器一致）：
    ① 行必须以竖线开头（否则根本不是表格行）；
    ② 按**未被转义**的竖线切出的格数必须 **等于表头列数**（本表 7）；
       行尾有没有竖线都行（Markdown 两种都渲染成同样的格数）；
    ③ 转义竖线 `\\|` 算格内内容，不劈格——所以拆格器也必须认这个转义，
       否则会把「写对了的行」误判成破表（这个误判真出现过一次，已修）。
"""
import io
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ISSUES = os.path.join(ROOT, 'docs', 'ISSUES.md')
EXPECTED_COLS = 7


def split_row(s):
    """按未转义的竖线切一行表格。返回 cells 列表。"""
    body = s[1:]
    if body.rstrip().endswith('|'):
        body = body.rstrip()[:-1]
    cells, cur, i = [], '', 0
    while i < len(body):
        ch = body[i]
        if ch == '\\' and i + 1 < len(body) and body[i + 1] == '|':
            cur += '|'
            i += 2
            continue
        if ch == '|':
            cells.append(cur.strip())
            cur = ''
            i += 1
            continue
        cur += ch
        i += 1
    cells.append(cur.strip())
    return cells


def audit(path):
    """返回 (rows_total, bad_list)。bad_list 每项＝(行号, ID, 格数, 原因)。"""
    bad = []
    total = 0
    with io.open(path, encoding='utf-8') as f:
        for lineno, line in enumerate(f.read().split('\n'), 1):
            s = line.strip()
            if not s.startswith('| H-'):
                continue
            total += 1
            if not s.startswith('|'):
                bad.append((lineno, s[:14], -1, '行首不是竖线（不是表格行）'))
                continue
            cells = split_row(s)
            if len(cells) != EXPECTED_COLS:
                bad.append((lineno, cells[0], len(cells),
                            '格数 %d ≠ 表头 %d ⇒ 渲染时末格被吞' % (len(cells), EXPECTED_COLS)))
    return total, bad


def selftest():
    """已知坏样本必须报红；已知好样本必须判过。"""
    good = '| H-001 | FIXED | P1 | Q | 问题 | 证据 | 下一步 |'
    good_no_tail = '| H-001 | FIXED | P1 | Q | 问题 | 证据 | 下一步'      # 行尾没竖线也合法
    good_escaped = '| H-001 | FIXED | P1 | Q | 含 \\| 转义 | 证据 | 下一步 |'
    bad_more = '| H-002 | FIXED | P1 | Q | 问题 | 证据 | 下一步 | 追加的真机取证段 |'
    bad_few = '| H-003 | FIXED | P1 | Q | 问题 | 证据 |'
    cases = (('多一格', bad_more, True), ('少一格', bad_few, True),
             ('正好 7 格', good, False), ('行尾无竖线但 7 格', good_no_tail, False),
             ('格内转义竖线', good_escaped, False))
    for name, sample, want_bad in cases:
        cells = split_row(sample)
        flagged = len(cells) != EXPECTED_COLS
        if flagged != want_bad:
            print('SELFTEST FAIL：%s 样本判据与预期不符（期望报红=%s，实际=%s，格数=%d）'
                  % (name, want_bad, flagged, len(cells)))
            return 1
    print('SELFTEST OK：多一格／少一格被拦下；正好 7 格、行尾无竖线、格内转义竖线三种合法写法判过'
          '（判据本身有效）')
    return 0


def main():
    if '--selftest' in sys.argv[1:]:
        return selftest()
    strict = '--strict' in sys.argv[1:]
    total, bad = audit(ISSUES)
    print('ISSUES 行列数自检：共 %d 个 H- 行，表头 %d 列' % (total, EXPECTED_COLS))
    if not bad:
        print('[PASS] 所有行都是 %d 格' % EXPECTED_COLS)
        return 0
    for lineno, rid, n, reason in bad:
        print('[FAIL] 第 %d 行 %s：%s' % (lineno, rid, reason))
    print('破表行 %d 个（H-233 已登记）' % len(bad))
    if strict:
        print('结论：FAIL（--strict）')
        return 1
    print('结论：WARN（H-233 未收口前不阻断；收口后改用 --strict 进闸门）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
