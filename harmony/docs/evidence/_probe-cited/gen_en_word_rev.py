# -*- coding: utf-8 -*-
"""生成「中文 → 英文本词」反查表 en_word_rev.tsv（Qoder 2026-10-29）

用途：码/拼音输入时把英文补进候选前三（qtal→猫，第2位出 cat；mao→猫 同理）。
选词规则（离线算好，运行时只做一次查表，避免滤镜里再解析 9.8 MB 词库）：
  ① 该词把中文放在译词第一位（first）优先；
  ② 其次看词典权重（en_word.dict.yaml 第三列，4=常用、3=次常用、2=生僻）；
  ③ 再取更短的词、再按字典序。
输出：zh<TAB>word，每个中文一条；行按中文排序。
只收权重≥3（常用/次常用）且中文长度≤4 的条目：宁可少补，不要补出 anagnorisis 这种生僻词。
"""
import io
import os

DATA = r'G:\RimeUser'
DICT = os.path.join(DATA, 'en_word.dict.yaml')
TRANS = os.path.join(DATA, 'en_word_trans.tsv')
GLOSS = os.path.join(DATA, 'en_word_gloss.tsv')
OUT = r'F:\workbuddywork\三生输入法\packaging\release\config\en_word_rev.tsv'

MIN_WEIGHT = 3
MAX_ZH = 4


def load_weights():
    w = {}
    with io.open(DICT, encoding='utf-8') as f:
        for line in f:
            if not line or line[0] in '#\n\t':
                continue
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 3:
                continue
            word, wt = parts[0], parts[2]
            try:
                w[word] = int(wt)
            except ValueError:
                pass
    return w


def main():
    weights = load_weights()
    best = {}

    def offer(zh, word, first):
        if not zh or '\t' in zh or len(zh) > MAX_ZH:
            return
        wt = weights.get(word, 0)
        if wt < MIN_WEIGHT:
            return
        key = (1 if first else 0, wt, -len(word), )
        cur = best.get(zh)
        if cur is None or key > cur[0] or (key == cur[0] and word < cur[1]):
            best[zh] = (key, word)

    with io.open(TRANS, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if '\t' not in line:
                continue
            word, trans = line.split('\t', 1)
            if not word.isalpha() or len(word) < 2:
                continue
            zs = [z for z in trans.split('|') if z]
            for i, zh in enumerate(zs):
                offer(zh, word, i == 0)

    # gloss 的首义项再补一遍（有些词 trans 表里没有但 gloss 有）
    with io.open(GLOSS, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if '\t' not in line:
                continue
            word, gloss = line.split('\t', 1)
            if not word.isalpha() or len(word) < 2:
                continue
            toks = gloss.split()
            if toks:
                offer(toks[0], word, True)

    lines = ['%s\t%s' % (zh, best[zh][1]) for zh in sorted(best)]
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    print('写出 %s：%d 条，%d B' % (OUT, len(lines), os.path.getsize(OUT)))
    for zh in ['猫', '山雀', '说', '是', '我', '的', '个', '你', '好', '中', '国', '戏', '秒', '马', '毛', '狗']:
        print(' ', zh, '->', best.get(zh, ('', ''))[1])


if __name__ == '__main__':
    main()
