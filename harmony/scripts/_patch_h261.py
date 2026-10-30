# -*- coding: utf-8 -*-
"""H-261 台账落盘：ISSUES 行 + PROGRESS 行。锚点命中 !=1 即 FAIL。"""
import io, sys

R = r'F:\qoderwork\sansheng-ime-harmony'

def load(p):
    t = io.open(p, encoding='utf-8', newline='').read()
    nl = '\r\n' if '\r\n' in t else '\n'
    return t.replace('\r\n', '\n'), nl

def save(p, lines, nl):
    io.open(p, 'w', encoding='utf-8', newline='').write(nl.join(lines))

def one(lines, prefix, what):
    hits = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    if len(hits) != 1:
        print('SELFTEST FAIL 锚点 %s 命中 %d 次: %r' % (what, len(hits), prefix[:40])); sys.exit(1)
    return hits[0]

# ---- ISSUES：H-261 行 ----
H261 = (u'| H-261 | FIXED（**Qoder 10-28 16:4x 改完，待主人真手验**） | P1 | Q | '
        u'**退格单删／连删删掉的文字无法撤销**（主人原话「退格单删连删删除的文字，下滑反不回，下滑加上针对退格返回，'
        u'顶栏的返回和重做也不针对退格单删和连删」） | '
        u'根因：`onBackspace()` 编辑框删除走 `deleteEditor(1)` 但**不入撤销栈**；顶栏 `undoCommit/redoCommit` 只认 `commit` 记录。'
        u'修法（`KeyboardController.ets`）：删前用 `getForwardSync(1)` 取光标前 1 字（命名坑同 H-210：getForwardSync 才是光标前文）'
        u'记成 `clear` 记录（下滑 `undoLastAction` 本就只弹 `clear` ⇒ 自然可还原）；`undoCommit` 改收 `commit`＋`clear`（clear 走 insertText 还原）；'
        u'`redoCommit` 对 clear 走 deleteEditor 再删（与撤销对称）。守卫 `h261_backspace_undo_check.py` 4 条＋3 坏样本自测全过；'
        u'release 构建 unsigned 27,902,684 B（16:46）。 | '
        u'待主人真手：退格删字后**下滑应还原**、**顶栏撤销应还原**、**重做应再删**；三样都过转 VERIFIED |')
p = R + r'\docs\ISSUES.md'
t, nl = load(p); L = t.split('\n')
if any(l.startswith(u'| H-261 |') for l in L):
    print('ISSUES H-261 已存在，跳过')
else:
    i = one(L, u'| H-259 |', 'ISSUES H-259')
    L.insert(i + 1, H261); save(p, L, nl); print('ISSUES H-261 插入')

# ---- PROGRESS：⑲ 行（不引用 H-260，避免无行编号）----
ROW = (u'| ⑲ 10-28 16:4x | Qoder | 主人 | H-261：退格单删/连删删的字不可撤销——`onBackspace` 编辑框删除不入撤销栈、'
       u'顶栏 undo/redo 只认 commit。修：删前 `getForwardSync(1)` 取光标前字记成 clear（下滑 `undoLastAction` 自然还原）'
       u'＋`undoCommit` 收 clear＋`redoCommit` 对 clear 再删；守卫 `h261_backspace_undo_check.py` 4 条＋3 坏样本；'
       u'release 构建 unsigned **27,902,684 B**（16:46，含 CodeArts 在途「候选完整显示」6 行改动——他未提交，我没碰他的改动） | '
       u'待主人真手验（下滑还原／顶栏撤销还原／重做再删）；CodeArts 在途改动未提交，release 封包前需他先提交 |')
p = R + r'\docs\PROGRESS.md'
t, nl = load(p); L = t.split('\n')
if any(l.startswith(u'| ⑲ 10-28 16:4x') for l in L):
    print('PROGRESS ⑲ 已存在，跳过')
else:
    i = one(L, u'| ⑱ 10-28 15:1x', 'PROGRESS ⑱')
    n = len(ROW.split(u'|')) - 2
    assert n == 5, '格子数=%d' % n
    L.insert(i + 1, ROW); save(p, L, nl); print('PROGRESS ⑲ 插入（5 格）')
