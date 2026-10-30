# -*- coding: utf-8 -*-
"""只读校验：鸿蒙 en_word_bucket.txt 补词后是否「只多 75 行、一行不少、行尾不变」
（Qoder 2026-10-29 14:0x，H-265）"""
import difflib
import io
import os
import sys

BUCKET = r'F:\qoderwork\sansheng-ime-harmony\entry\src\main\resources\rawfile\rime\lua\en_word_bucket.txt'
BAK = sys.argv[1] if len(sys.argv) > 1 else BUCKET + '.bak-qoder-20261029-1404'


def rows(path):
    raw = open(path, 'rb').read()
    crlf = raw.count(b'\r\n')
    nl = '\r\n' if crlf * 2 >= raw.count(b'\n') else '\n'
    body = raw.decode('utf-8').split(nl)
    if body and body[-1] == '':
        body.pop()
    return raw, nl, body


def main():
    o_raw, o_nl, o_rows = rows(BAK)
    n_raw, n_nl, n_rows = rows(BUCKET)
    print('备份 %d B / %d 行 / 行尾 %r' % (len(o_raw), len(o_rows), o_nl))
    print('现文件 %d B / %d 行 / 行尾 %r' % (len(n_raw), len(n_rows), n_nl))
    ok = True
    if o_nl != n_nl:
        print('FAIL 行尾被改写'); ok = False
    o_words = set(r.split('\t')[1].lower() for r in o_rows if len(r.split('\t')) >= 2)
    n_words = set(r.split('\t')[1].lower() for r in n_rows if len(r.split('\t')) >= 2)
    lost = o_words - n_words
    print('丢词（应为 0）：%d %s' % (len(lost), sorted(lost)[:10]))
    if lost:
        ok = False
    print('新增词：%d' % len(n_words - o_words))
    # 用 difflib 确认真的只有插入，没有替换/删除
    sm = difflib.SequenceMatcher(None, o_rows, n_rows, autojunk=False)
    ins = dele = repl = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'insert':
            ins += j2 - j1
        elif tag == 'delete':
            dele += i2 - i1
        elif tag == 'replace':
            repl += max(i2 - i1, j2 - j1)
    print('difflib：insert=%d delete=%d replace=%d' % (ins, dele, repl))
    if dele or repl:
        print('FAIL 有删除或改写'); ok = False
    # 抽查关键缩写词，并核对桶内字典序位置
    for probe in ('app', 'cpu', 'ok', 'url', 'tv', 'core', 'max'):
        hits = [r for r in n_rows if r.split('\t')[1:2] == [probe]]
        print('   %-5s -> %s' % (probe, hits[0].replace('\t', ' | ') if hits else '（缺）'))
    a_idx = [i for i, r in enumerate(n_rows) if r.split('\t')[0] == 'a']
    a_words = [r.split('\t')[1] for r in (n_rows[i] for i in a_idx)]
    print('   a 桶 %d 行，字典序未被打乱：%s' % (len(a_words), a_words == sorted(a_words)))
    print('结论：%s' % ('PASS' if ok else 'FAIL'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
