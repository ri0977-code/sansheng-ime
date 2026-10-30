# -*- coding: utf-8 -*-
"""补齐鸿蒙分桶表里缺的英文词（Qoder 2026-10-29 14:1x，H-265 鸿蒙侧）

背景：`lua/en_word_bucket.txt`（55,792 行）是从 `en_word_gloss.tsv` 导的，
而 gloss 表只覆盖 `en_word.dict.yaml` 里的词；那份词库由 gen_en_word.py 生成，
它的 eligible() 只收「全小写」和「首字母大写 + 其余小写」两种写法 —— ECDICT 里
只有全大写形式的缩写词（APP / CPU / OK / URL / TV / DNA …）一条都没进库。
后果：Windows 和安卓靠 enWord_Filter 的场景1b 兜住了（运行时直查
`en_word_trans.tsv` 现造两条中文候选），鸿蒙这条链是 Lua translator（H-260 方向1），
它只认桶，桶里没有就是没有 —— 打 app 在鸿蒙上连一条英文候选都不出。

数据核对（2026-10-29 14:1x 实测）：
    en_word_gloss.tsv  55,792 键  —— 与桶键集完全相同（桶 - gloss = 0）
    en_word_trans.tsv  40,626 键  —— 其中 75 个键不在桶里，就是这批全大写缩写词
所以本次只补这 75 个词，补齐后鸿蒙与 Windows/安卓「能出译词的英文集合」一致。

做法（最小改动）：
  ① 只【插入】缺失的词，一行都不删、已有行相对顺序不变；
  ② 插入位置按首字母桶内字典序落到该桶正确偏移，保证短前缀（ap→app）也能排进前几条；
  ③ 释义列沿用现有桶行口径：第一个中文义项 + 「五笔码/拼音码」（桶内现有行均无「|」）；
  ④ 词频列填 3（这批词没进过 dict.yaml，不冒充 4 级词库频率）。
产物：先备份 `.bak-qoder-<stamp>`，再写新文件，打印前后行数/字节与补进去的 75 行。

用法：默认试算（不写盘）；`--apply` 才落文件。
"""
import io
import os
import re
import shutil
import sys
import time

RIME = r'F:\qoderwork\sansheng-ime-harmony\entry\src\main\resources\rawfile\rime'
BUCKET = os.path.join(RIME, 'lua', 'en_word_bucket.txt')
TRANS = os.path.join(RIME, 'en_word_trans.tsv')
# 码表优先用仓内 rawfile 的副本，保证换机也能重跑；仓内没有再退回安装目录
WUBI_CANDIDATES = [os.path.join(RIME, 'wubi86.dict.yaml'),
                   r'D:\Program Files\Rime\wubi86.dict.yaml']
PINYIN_CANDIDATES = [os.path.join(RIME, 'cn_pinyin_wp.dict.yaml'),
                     r'D:\Program Files\Rime\cn_pinyin_wp.dict.yaml']
WORD_RE = re.compile(r'^[a-z]+$')
STAMP = time.strftime('%Y%m%d-%H%M')
PROBES = ('app', 'cpu', 'ok', 'url', 'tv', 'dna', 'ai', 'codearts')


def first_existing(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def load_codes(path, store):
    """中文词 -> 码（首条即可），用来拼「释义」列。"""
    if not path:
        return 0
    n = 0
    body = False
    for line in io.open(path, encoding='utf-8'):
        line = line.rstrip('\r\n')
        if line == '...':
            body = True
            continue
        if not body or not line or line[0] == '#' or line == '---':
            continue
        p = line.split('\t')
        if len(p) >= 2 and p[0] and p[1] and p[0] not in store:
            store[p[0]] = p[1]
            n += 1
    return n


def main():
    wb, pb = {}, {}
    wp = first_existing(WUBI_CANDIDATES)
    pp = first_existing(PINYIN_CANDIDATES)
    print('五笔码表：%s（%d 条）  拼音码表：%s（%d 条）'
          % (wp, load_codes(wp, wb), pp, load_codes(pp, pb)))

    lines = []
    have = set()
    raw = open(BUCKET, 'rb').read()
    # 保持原文件行尾（本表历史是 CRLF）：只插 75 行，绝不顺手把 5.5 万行改写一遍
    crlf = raw.count(b'\r\n')
    newline = '\r\n' if crlf * 2 >= raw.count(b'\n') else '\n'
    for line in raw.decode('utf-8').split(newline):
        s = line.rstrip('\r\n')
        if not s:
            continue
        lines.append(s)
        p = s.split('\t')
        if len(p) >= 2:
            have.add(p[1].lower())
    print('桶现状：%d 行 / %d 个词 / %d B（行尾 %r）'
          % (len(lines), len(have), os.path.getsize(BUCKET), newline))

    # 译词表口径：英文<TAB>中文1|中文2|...（全大写缩写词的规范小写形式都在这张表里）
    trans = {}
    for line in io.open(TRANS, encoding='utf-8'):
        p = line.rstrip('\r\n').split('\t')
        if len(p) < 2:
            continue
        en = p[0].strip().lower()
        zh = p[1].strip()
        if not WORD_RE.match(en) or len(en) < 2 or not zh:
            continue
        if en not in trans:
            trans[en] = zh.split('|')[0].strip()
    print('译词表：%d 个英文键' % len(trans))

    missing = sorted(w for w in trans if w not in have)
    # 按首字母分组（保持桶字母块的原有先后），组内按字典序插进正确偏移；
    # 已有行的相对顺序一行都不动。
    letter_order = []
    groups = {}
    for s in lines:
        p = s.split('\t')
        letter = p[0] if p else ''
        if letter not in groups:
            groups[letter] = []
            letter_order.append(letter)
        groups[letter].append(s)

    out = []
    added = []
    for en in missing:
        zh = trans[en]
        wc, pc = wb.get(zh, ''), pb.get(zh, '')
        gloss = zh if not (wc and pc) else '%s %s/%s' % (zh, wc, pc)
        row = '%s\t%s\t%d\t%s' % (en[0], en, 3, gloss)
        added.append(row)
        letter = en[0]
        group = groups.setdefault(letter, [])
        if letter not in letter_order:
            letter_order.append(letter)
        pos = len(group)
        for i, s in enumerate(group):
            w = (s.split('\t') + [''])[1].lower()
            if w > en:
                pos = i
                break
        group.insert(pos, row)
    for letter in letter_order:
        out.extend(groups[letter])
    print('补的词：%d 个，写盘后 %d 行' % (len(added), len(out)))
    for probe in PROBES:
        hit = [a for a in added if a.split('\t')[1] == probe]
        got = [s for s in out if s.split('\t')[1].lower() == probe]
        print('   %-8s -> %s' % (probe, hit[0] if hit else (got[0] if got else '（仍缺）')))
    if len(added) <= 120:
        for a in added:
            print('   + ' + a.replace('\t', ' | '))

    # 自检：原有行必须一行不少、同一字母桶内相对顺序不变
    from collections import Counter
    lost = Counter(lines) - Counter(out)
    if lost or len(out) != len(lines) + len(added):
        print('自检失败：丢行 %s / 行数 %d（应 %d）'
              % (list(lost.items())[:5], len(out), len(lines) + len(added)))
        return 1
    print('自检通过：原有 %d 行全部保留，只多了 %d 行' % (len(lines), len(added)))

    if '--apply' not in sys.argv:
        print('（试算模式，未写盘；加 --apply 才落文件）')
        return 0

    bak = BUCKET + '.bak-qoder-' + STAMP
    shutil.copyfile(BUCKET, bak)
    with io.open(BUCKET, 'w', encoding='utf-8', newline='') as f:
        f.write(newline.join(out) + newline)
    print('已写盘：%d B / %d 行（备份 %s）'
          % (os.path.getsize(BUCKET), len(out), os.path.basename(bak)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
