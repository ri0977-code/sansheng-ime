# -*- coding: utf-8 -*-
"""给 H-268 那行的「证据/下一步」格补一句指针（Qoder 15:0x）

原因：H-268 写于 14:51，里面「树内＝505 B 消融桩」当时是真的；14:57:36 CodeArts 又写了 v33
（只精确匹配、砍掉前缀联想），那是**新的、性质不同的**回归（删功能而不是留桩），单独开在 H-269。
只读 H-268 的人不该按「桩」去处置 ⇒ 在同格内加一句带时间戳的指针，原文一字不删。
幂等：该行已含本轮标记就跳过。
"""
import io
import os
import re
import sys
import time

ROOT = r'F:\qoderwork\sansheng-ime-harmony'
ISSUES = os.path.join(ROOT, 'docs', 'ISSUES.md')
NOTE = ('【15:0x 指针（Qoder）：本行 14:51 写的「树内＝505 B 消融桩」当时为真，现已推进到第三版——'
        'CodeArts 14:57:36 的 v33（3,886 B／sha1 773275948dce）＝只做精确匹配、整条砍掉前缀联想，'
        '台架实测 `ap`／`mao` 0 条、`app` 只剩 1 条带注释的英文、无第二条可选中文（122 个前缀查询 115 条与基线不同）。'
        '这条删功能的回归单独开在 **H-269**，A／B 两条可测的中间做法写在那里；'
        '他的 v31／消融桩／v33 三版逐字归档 `_probe/rawfile-backups-20261029/`（新增 '
        '`enWord_translator.lua.peer-v33-20261029-145736`），我这侧仍不覆盖这个文件。】')


def main():
    txt = io.open(ISSUES, encoding='utf-8').read()
    lines = txt.split('\n')
    hit = [i for i, l in enumerate(lines) if l.startswith('| H-268 ')]
    if len(hit) != 1:
        print('FAIL H-268 行数=%d（应为 1）' % len(hit))
        return 1
    i = hit[0]
    parts = lines[i].split('|')
    if len(parts) - 2 != 7:
        print('FAIL H-268 是 %d 格，应为 7 格' % (len(parts) - 2))
        return 1
    if '15:0x 指针' in parts[7]:
        print('H-268 已带本轮指针 ⇒ 跳过（幂等）')
        return 0
    parts[7] = parts[7].rstrip() + ' ' + NOTE + ' '
    new = '|'.join(parts)
    if len(new.split('|')) - 2 != 7:
        print('FAIL 追加后变 %d 格（指针里有裸竖线）' % (len(new.split('|')) - 2))
        return 1
    lines[i] = new
    io.open(ISSUES, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    print('已给 H-268 补指针（行 %d，+%d 字符，真实时钟 %s）'
          % (i + 1, len(NOTE), time.strftime('%H:%M')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
