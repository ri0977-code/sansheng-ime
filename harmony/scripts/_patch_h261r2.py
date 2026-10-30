# -*- coding: utf-8 -*-
"""H-261 台账补记：重做统一修复 + 新构建字节。锚点命中 !=1 即 FAIL。"""
import io, sys

R = r'F:\qoderwork\sansheng-ime-harmony'

def patch(path, pairs):
    t = io.open(path, encoding='utf-8', newline='').read()
    nl = '\r\n' if '\r\n' in t else '\n'
    s = t.replace('\r\n', '\n')
    for old, new in pairs:
        c = s.count(old)
        if c != 1:
            print('SELFTEST FAIL %s: 锚点命中 %d 次: %r' % (path, c, old[:50])); sys.exit(1)
        s = s.replace(old, new)
    io.open(path, 'w', encoding='utf-8', newline='').write(s.replace('\n', nl))
    print('OK', path)

patch(R + r'\docs\ISSUES.md', [(
    u'release 构建 unsigned 27,902,684 B（16:46）。',
    u'release 构建 unsigned 27,902,680 B（17:16）。**H-261r2 补修（主人 16:5x「重做只能重做一次，两个不统一」）**：'
    u'`insertText` 加 `recordUndo` 开关，撤销/重做把文字插回时传 `false`，避免 `pushUndo` 把 `redoStack` 清空 '
    u'⇒ 重做可连按、与撤销对称；守卫加 A5＋坏样本 4（5 断言＋4 坏样本全过）。')])

patch(R + r'\docs\PROGRESS.md', [(
    u'release 构建 unsigned **27,902,684 B**（16:46，含 CodeArts 在途「候选完整显示」6 行改动——他未提交，我没碰他的改动）',
    u'release 构建 unsigned **27,902,680 B**（17:16，含 CodeArts 在途「候选完整显示」6 行改动——他未提交，我没碰他的改动）；'
    u'16:5x 补修「重做只能一次」：`insertText` 加 recordUndo 开关，撤销/重做插回不清空 redoStack，与撤销对称')])
