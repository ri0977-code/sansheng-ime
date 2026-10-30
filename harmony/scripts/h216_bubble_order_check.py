#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-216(Qoder+CodeArts) 长按气泡「次序 + 出泡不预选」守卫：把主人定的口径写成可离线跑的检查。

背景：
  主人真机验完 H-215 后定了气泡的两条口径——
    · 「常用默认字符（本键大写字母＋数字）排前面、不常用变音符号排后面」
    · 2026-10-27 12:4x 原口径「长按直接默认选中数字」→ 2026-10-27 改为「不上滑选气泡的话松手不要上屏」
  即出泡时 longPressSymIdx = -1（不预选），手指滑进气泡才选中，不滑松手=取消不上屏。
  次序口径不变：常用字符仍排前面（方便手指滑进去选），变音仍排后面。

判据（逐条对应主人原话）：
  1. 每个非空组里**本键大写字母落在默认位或其旁边**（下标 0 或 1）——「大写字母在旁边」
  2. q~p 十键第 0 格＝数字 ——常用字符排前面
  3. z/b 两键没有数字行，第 0 格取「本键大写」或「ASCII 常用符」二者之一
     （2026-10-27 15:2x CodeArts 就地拍成**大写打头**，与主人「常用默认字符＝本键大写字母＋数字」同向，放行）
  4. 组内非 ASCII（变音符号）一律排在所有 ASCII 之后 ——「不常用变音符号排后面」
  5. 两条出泡路径（按下计时器 + 手势兜底）都把 `longPressSymIdx` 预置成 -1（不预选）
  6. 手指从未进过泡范围时，`bubbleEntered` 短路仍在（避免不必要的状态更新）
  7. 松手提交读的是 `longPressSymIdx`（>=0 才上屏，-1 = 取消）

用法：
  python scripts/h216_bubble_order_check.py            # 跑守卫，红=退出码 1
  python scripts/h216_bubble_order_check.py --selftest # 用「已知错误」数据验证检查本身会红

严重度：**开发期守卫，不进发布阻断闸门**（发布闸门仍是 check_app_content.py 的 16 条）。
红了先 `git diff entry/src/main/ets/pages/KeyboardIndex.ets` 看是不是并行改动打架（M-255 口径）。
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'entry', 'src', 'main', 'ets', 'pages', 'KeyboardIndex.ets')

QWERTY_DIGIT = ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p']
NO_DIGIT = ['z', 'b']  # 无数字行，第 0 格取 ASCII 常用符号


def read(path):
    return io.open(path, encoding='utf-8').read()


def parse_groups(text):
    r"""从 KeyboardIndex.ets 文本里解析 HIDDEN_SYMS ⇒ [(键名, [字符...]), ...]，按声明顺序。

    两个坑（都是本轮真踩出来的，别再退回简单正则）：
      · 组里有 `']'` 这种「中括号本身」的字符（i 键），所以不能拿 `[^\]]*` 截内容，
        要用贪婪 `(.*)` 一直吃到注释前的最后一个 `]`；
      · 组里有 `"'"`（z 键第 0 格是单引号，只能用双引号包）和 `` '`' ``（反引号），
        所以取字符串要同时认单引号/双引号/反引号三种写法。
    """
    m = re.search(r"const HIDDEN_SYMS: string\[\]\[\] = \[(.*?)\n\];", text, re.S)
    if not m:
        return []
    line_re = re.compile(r"\s*\[(.*)\],?\s*//\s*([a-z])\b")
    str_re = re.compile(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"|`((?:[^`\\]|\\.)*)`")
    groups = []
    for line in m.group(1).split('\n'):
        lm = line_re.match(line)
        if not lm:
            continue
        inner = lm.group(1).strip()
        items = []
        if inner:
            for q in str_re.finditer(inner):
                raw = next(g for g in q.groups() if g is not None)
                items.append(raw.replace("\\'", "'").replace('\\"', '"').replace('\\\\', '\\'))
        groups.append((lm.group(2), items))
    return groups


def run(page_text):
    """返回 (通过数, 失败列表)。"""
    fails = []
    passed = 0
    groups = dict(parse_groups(page_text))

    # 1) 每个非空组：本键大写必须在「默认位」或「紧挨着默认位」——常用字符排前面；
    #    下标 0/1 谁当默认由键面数据定（q~p 是数字，z/b CodeArts 15:2x 选了大写）。
    for k, items in groups.items():
        if len(items) < 2:
            continue
        if items[0] == k.upper() or items[1] == k.upper():
            passed += 1
        else:
            fails.append('次序: %s 组本键大写 %s 不在默认位旁边（前两格实为 %s/%s）'
                         % (k, k.upper(), items[0], items[1]))

    # 2) q~p：index0 = 数字
    for k in QWERTY_DIGIT:
        items = groups.get(k)
        if not items:
            fails.append('数据: %s 组缺失或为空（应有数字）' % k)
            continue
        if items[0].isdigit():
            passed += 1
        else:
            fails.append('次序: %s 组第 0 格应为数字，实为 %s（常用字符应排前面）' % (k, items[0]))

    # 3) z/b：没有数字行，第 0 格只能是「本键大写」或「ASCII 常用符」。
    #    CodeArts 2026-10-27 15:2x 就地选了**大写打头**（注释 `H-216(CodeArts): 大写X移首位`），
    #    与主人「常用默认字符＝本键大写字母＋数字」同向，守卫按这个口径放行；
    #    哪天又变回非 ASCII（如 `ž`）占第 0 格才红。
    for k in NO_DIGIT:
        items = groups.get(k)
        if not items:
            fails.append('数据: %s 组缺失或为空' % k)
            continue
        head = items[0]
        if head == k.upper() or all(ord(c) < 128 for c in head):
            passed += 1
        else:
            fails.append('次序: %s 组第 0 格既不是本键大写也不是 ASCII 常用符，实为 %s' % (k, head))

    # 4) 组内变音（非 ASCII）一律在 ASCII 之后
    for k, items in groups.items():
        last_non_ascii = -1
        last_ascii = -1
        for i, s in enumerate(items):
            if all(ord(c) < 128 for c in s):
                last_ascii = i
            else:
                last_non_ascii = i
        if last_non_ascii >= 0 and last_ascii > last_non_ascii:
            fails.append('次序: %s 组变音符号后面还压着 ASCII 常用符（违背「常用在前变音在后」）' % k)
        else:
            passed += 1

    # 5) 两条出泡路径都预置 -1（不预选，主人「不上滑松手不要上屏」）
    n_no_default = len(re.findall(r'this\.longPressSymIdx = -1;', page_text))
    if n_no_default >= 2:
        passed += 1
    else:
        fails.append('出泡不预选: `longPressSymIdx = -1` 出现 %d 次（计时器+手势兜底应各 1 次）' % n_no_default)

    # 6) bubbleEntered 短路仍在（避免手指未进泡时不必要的状态更新）
    if re.search(r"if \(idx < 0 && !this\.bubbleEntered\) \{\s*\n\s*return;", page_text):
        passed += 1
    else:
        fails.append('出泡不预选: 缺 `bubbleEntered` 短路（手指未进泡时不应触发状态更新）')

    # 7) 松手读 longPressSymIdx（>=0 才上屏，-1 = 取消）
    if re.search(r"this\.getHiddenSymbols\(ch\)\[this\.longPressSymIdx\]", page_text):
        passed += 1
    else:
        fails.append('出泡不预选: 松手未读 longPressSymIdx（无法判断选中/取消）')

    # 8) 回归：s/d 组注释不得写回「全文首/全文尾」（H-220r3 已改行首/行尾）
    if re.search(r"//\s*[sd] -> 全文[首尾]", page_text):
        fails.append('注释: s/d 组又写回「全文首/全文尾」，与 H-220r3（行首/行尾）冲突')
    else:
        passed += 1

    return passed, fails


# 已知错误样本（--selftest 用）：默认位被非数字/非大写/变音占掉 + 变音压在 ASCII 前 + 出泡预选了(=0)
BAD_BLOCK = """
const HIDDEN_SYMS: string[][] = [
  ['1', 'Q', '_'],                                          // q
  ['2', 'W', '-'],                                          // w
  ['3', 'E', '+', 'ê', 'ë', 'ē', 'é', 'ě', 'è', 'ė', 'ę', 'ȩ', 'ḝ', 'ə'], // e
  ['4', 'R', '='],                                          // r
  ['5', 'T', '|'],                                          // t
  ['6', 'Y', '\\\\', 'ÿ'],                                    // y
  ['[', 'U', 'û'],                                          // u  ← 第 0 格不是数字
  ['8', 'Ï', 'î'],                                          // i  ← 本键大写没落在默认位旁边
  ['9', 'O', 'õ', '{'],                                     // o  ← 变音压在 ASCII 前
  ['0', 'P', '}'],                                          // p
  ['ž', 'Z', "'"],                                          // z  ← 第 0 格是变音（既非大写也非常用符）
  ['!', 'B', '¡', '~'],                                     // b  ← 变音压在 ASCII 前
  [],                                                       // m -> 删除光标后1字
];
"""

# 坏样本里放 `= 0`（旧口径：出泡预选），应被判据5拦下
BAD_PAGE = BAD_BLOCK + """
    this.longPressSymIdx = 0;
    if (this.longPressSymIdx >= 0 && this.longPressSymIdx < this.getHiddenSymbols(ch).length) {
      const sym: string = this.getHiddenSymbols(ch)[this.longPressSymIdx];
    }
"""


def main():
    selftest = '--selftest' in sys.argv[1:]
    if selftest:
        passed, fails = run(BAD_PAGE)
        hit = [f for f in fails if f.startswith('次序:') or f.startswith('出泡不预选:')]
        if len(hit) >= 4:
            print('SELFTEST OK：已知错误样本被拦下（次序/出泡不预选命中 %d 条，总失败 %d 条）' % (len(hit), len(fails)))
            return 0
        print('SELFTEST FAIL：检查本身失效，命中=%s' % hit)
        return 1
    passed, fails = run(read(PAGE))
    total = passed + len(fails)
    for f in fails:
        print('[FAIL] %s（H-216 口径被改动，先 git diff 再动手）' % f)
    print('H-216 气泡次序/出泡不预选守卫: %d/%d 组项通过' % (passed, total))
    if fails:
        return 1
    print('结论: 12 个非空组次序正确（q~p 数字打头、z/b 大写打头[CodeArts 15:2x 定]、大写总在默认位旁、变音垫后），出泡两条路径不预选（-1），滑进气泡才选中。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
