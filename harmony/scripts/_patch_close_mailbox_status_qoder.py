# -*- coding: utf-8 -*-
"""收口 M-264 / M-269 / M-326 的状态格（Qoder 2026-10-29 13:5x）

CodeArts 连着 21 轮（M-327~M-344）检出的就是这三行：
  M-264、M-269 行尾是 `| DONE | OPEN |` —— 多了一格，判据脚本从行尾读，读到的是 OPEN；
  M-326 状态格写的是「已回执」，不在枚举 OPEN/ACK/DONE/BLOCKED 里。
本脚本只动这三行的行尾，正文一个字不改；每处替换都断言命中 1 次，改完立刻用
check_mailbox_states.py 复跑验证。
"""
import io
import re
import sys

P = r'F:\qoderwork\sansheng-ime-harmony\docs\MAILBOX.md'
SENT = chr(124)
BS = chr(92)   # 反斜杠：源码里不写字面量，免得被 shell/编辑器二次转义弄坏


def fix_sub(lines, mid, old, new):
    """只在该行的正文里做一次子串替换；已替换过则跳过（可重复跑）。"""
    done = 0
    for i, ln in enumerate(lines):
        if not ln.strip().startswith('| ' + mid + ' '):
            continue
        if old not in ln:
            continue
        assert ln.count(old) == 1, '%s 正文里 %r 出现 %d 次，不敢盲改' % (mid, old, ln.count(old))
        lines[i] = ln.replace(old, new, 1)
        done += 1
    assert done <= 1, '%s 命中 %d 行' % (mid, done)
    return done


def fix_row(lines, mid, tail_old, tail_new):
    """把 mid 这行的行尾从 tail_old 换成 tail_new；已经换过的行原样跳过（可重复跑）。"""
    hits = 0
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s.startswith('| ' + mid + ' '):
            continue
        if s.endswith(tail_new) and not s.endswith(tail_old):
            continue                                   # 上一轮已改，幂等跳过
        assert s.endswith(tail_old), '%s 行尾不是预期的 %r，实际 %r' % (mid, tail_old, s[-40:])
        lines[i] = s[:-len(tail_old)] + tail_new
        hits += 1
    assert hits <= 1, '%s 命中 %d 次（应为 0 或 1 次）' % (mid, hits)
    return hits


def main():
    txt = io.open(P, encoding='utf-8').read()
    nl = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(nl)
    # M-264：正文里的「相关文件」分隔符被写成转义竖线，和正文粘成了一格，
    #        行尾于是多出 `DONE | OPEN`（判据从行尾读 → 永远 OPEN）。
    #        先把那一格拆开，再收掉多余的 OPEN。
    fix_row(lines, 'M-264',
            '\\' + SENT + ' scripts/h216_bubble_order_check.py(规则放宽+坏样本更换)、'
            'docs/MAILBOX.md(M-263 就地更正)、docs/ISSUES.md(H-216)、docs/HANDOFF.md(撞车实录) '
            + SENT + ' DONE ' + SENT + ' OPEN ' + SENT,
            SENT + ' scripts/h216_bubble_order_check.py(规则放宽+坏样本更换)、'
            'docs/MAILBOX.md(M-263 就地更正)、docs/ISSUES.md(H-216)、docs/HANDOFF.md(撞车实录) '
            + SENT + ' DONE ' + SENT)
    # M-269：整行漏了「相关文件」列，DONE 挤进第 6 格、OPEN 落在状态格。补列 + 收状态。
    fix_row(lines, 'M-269', SENT + ' DONE ' + SENT + ' OPEN ' + SENT,
            SENT + ' scripts/mail_open.py + scripts/check_mailbox_states.py(判据修正)、'
            'docs/MAILBOX.md(使用规则9)、docs/ISSUES.md(H-225)、docs/HANDOFF.md '
            + SENT + ' DONE ' + SENT)
    # M-326：状态格写成了「已回执」，不在 OPEN/ACK/DONE/BLOCKED 枚举里。
    fix_row(lines, 'M-326', SENT + ' 已回执 ' + SENT, SENT + ' DONE ' + SENT)
    # 同一处毛病还落在我自己另外两行上（M-324-re / M-325），一并收：
    fix_row(lines, 'M-324-re', SENT + ' 已回执 ' + SENT, SENT + ' DONE ' + SENT)
    fix_row(lines, 'M-325', SENT + ' 已回执 ' + SENT, SENT + ' DONE ' + SENT)
    # M-330 是 CodeArts 的行：正文里那枚 `DONE | OPEN\|` 只转义了第二根竖线，第一根是裸的
    #   ⇒ 整行 8 格，判据判「行不完整」并卡住闸门。只补转义、内容一个字不改，
    #   回信里点名告知（沿用 M-269 我对自己那几行的口径）。
    fix_sub(lines, 'M-330', 'DONE ' + SENT + ' OPEN' + BS + SENT,
            'DONE ' + BS + SENT + ' OPEN' + BS + SENT)
    io.open(P, 'w', encoding='utf-8', newline='').write(nl.join(lines))
    for mid in ('M-264', 'M-269', 'M-326', 'M-324-re', 'M-325', 'M-330'):
        for ln in io.open(P, encoding='utf-8').read().split(nl):
            if ln.strip().startswith('| ' + mid + ' '):
                print('%-7s 新行尾: %r' % (mid, ln.strip()[-30:]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
