# -*- coding: utf-8 -*-
"""就地更正 PROGRESS ㉓ 行里漏掉的占位符（Qoder 2026-10-29 14:5x）

事实：`_write_progress_23_qoder.py` 的 ROW 是字符串拼接出来的，我在行首写了
`真实时钟＝`date` %s` 却只对 print 做了 `% NOW` ⇒ 落盘的行里字面留着 `%s`，
台账上一条没有时间（H-134 要的就是「落笔前先 date 并把真实时钟写进行」）。
该行写入时刻由 `docs/PROGRESS.md` 的 mtime 量到＝**14:45:30**。

改法：只把 `%s` 换成 `14:45:30` 并留一句更注（不改任何一个别的字），
幂等：行内已无 `%s` 就跳过。
"""
import io
import os
import sys

P = r'F:\qoderwork\sansheng-ime-harmony\docs\PROGRESS.md'
OLD = '真实时钟＝`date` %s；'
NEW = ('真实时钟＝`date` 14:45:30＝本文件 mtime，写入脚本漏了 `% NOW`  ⇒ '
       '行里字面落了 `%s`，14:52 由 `scripts/_fix_progress_23_placeholder_qoder.py` 就地补号并留此注；')


def main():
    txt = io.open(P, encoding='utf-8').read()
    lines = txt.split('\n')
    hit = [i for i, l in enumerate(lines) if l.startswith('| ㉓ 10-29 14:4x')]
    if len(hit) != 1:
        print('FAIL ㉓ 行数=%d（应为 1）' % len(hit))
        return 1
    i = hit[0]
    if OLD not in lines[i]:
        print('㉓ 行已无占位符 ⇒ 跳过（幂等）；当前该行 %d 字符' % len(lines[i]))
        return 0
    fixed = lines[i].replace(OLD, NEW, 1)
    lines[i] = fixed
    if fixed.count('|') != 6:
        print('FAIL 更正后竖线数 %d，应为 6（5 格）' % fixed.count('|'))
        return 1
    io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    print('已更正 ㉓（行 %d，%d→%d 字符，占位符已换成真实时钟 14:45:30）'
          % (i + 1, len(txt.split('\n')[i]), len(fixed)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
