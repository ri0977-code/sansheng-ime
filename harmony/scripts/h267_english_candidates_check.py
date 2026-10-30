#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-267 英文候选链守卫（Qoder，2026-10-29 14:5x）

为什么写（H-250/H-238 口径：第二次犯同一件事 ⇒ 散文不算修好，必须有拦截）：
英文候选这条链在鸿蒙上是**三样东西凑齐才成立**的——桶数据、Lua 文件、custom.yaml 挂载。
这几天它坏过三种不同的样子，每次都只被人眼看见其中一种：
  · 数据缺词（`app/cpu/ok/url` 全不在表里 ⇒ 打 app 只有联想）＝H-265；
  · 代码退化成整桶线扫（每按键上万次比较 ⇒ 打字卡，CodeArts 因此把它注释掉）＝H-267；
  · 挂载被人整条注释（功能直接没了，但文件与数据都还在，肉眼看不出）＝今天 14:29:36 实际发生。
所以这支守卫同时查三层，并且**明确不替 CodeArts 决定挂不挂**：挂载状态只报告，
只有「挂了但文件不在」这种自相矛盾才拦。

查什么：
  ① 桶数据在 rawfile 里，且关键缩写词在位（app／cpu／ok／url／tv／dna／vip／pvc／sos／atm）；
  ② `lua-files.txt` 把 `enWord_translator.lua` 与 `en_word_bucket.txt` 都列进发布清单
     （漏一个 ⇒ 装机的手机上没有文件，代码写得再对也不出词）；
  ③ 翻译器用的是索引（exact／idx2／idx3），旧的「整桶扫两遍」（`for i = 1, #bucket`）不许回来；
  ④ **联想顺序＝表内原顺序**这条不变量：不许在加载时对桶做 `table.sort`
     （我 14:3x 先写了「排序＋二分」，基准当场判红：`appl` 首条联想从 apple 变成 applaud，
      92/122 条查询产出变了 ⇒ 那是改行为不是改性能）；
  ⑤ custom.yaml 的挂载行状态（在／被注释／没有）只报告，不算违规。

用法：
    python scripts/h267_english_candidates_check.py            # 查真树
    python scripts/h267_english_candidates_check.py --selftest  # 正控＋四种坏形状
退出码：0＝通过；1＝违规（拦构建／拦交付用）。
"""
from __future__ import annotations

import io
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

RIME = os.path.join('entry', 'src', 'main', 'resources', 'rawfile', 'rime')
BUCKET = os.path.join(RIME, 'lua', 'en_word_bucket.txt')
TRANSLATOR = os.path.join(RIME, 'lua', 'enWord_translator.lua')
LUA_FILES = os.path.join(RIME, 'lua-files.txt')
CUSTOM = os.path.join(RIME, 'wubi_pinyin.custom.yaml')

KEY_WORDS = ['app', 'cpu', 'ok', 'url', 'tv', 'dna', 'vip', 'pvc', 'sos', 'atm']


def read(path):
    with io.open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def check(root=ROOT):
    bad = []
    notes = []
    p = lambda *a: os.path.join(root, *a)

    # ① 桶数据
    if not os.path.exists(p(BUCKET)):
        bad.append('桶文件不在：%s' % BUCKET)
    else:
        txt = read(p(BUCKET))
        missing = []
        for w in KEY_WORDS:
            if not re.search(r'^[a-z]\t%s\t' % re.escape(w), txt, re.M | re.I):
                missing.append(w)
        if missing:
            bad.append('桶里缺关键缩写词 %d 个：%s（打这些词就只有联想、没有本词）'
                       % (len(missing), ' '.join(missing)))
        else:
            notes.append('桶内关键缩写词全在位（%d 个抽检）' % len(KEY_WORDS))

    # ② 发布清单
    if not os.path.exists(p(LUA_FILES)):
        bad.append('发布清单不在：%s' % LUA_FILES)
    else:
        lst = read(p(LUA_FILES))
        # 按行解析并剔掉注释行：早先用「子串在不在」判，把 `#lua/en_word_bucket.txt`
        # 这种注释掉的行也算成已发布 ⇒ 自测当场抓到（负控不红＝守卫是假的）。
        listed = set()
        for line in lst.splitlines():
            s = line.strip()
            if not s or s.startswith('#'):
                continue
            listed.add(s.replace('\\', '/'))
        missing_list = [need for need in ('lua/enWord_translator.lua', 'lua/en_word_bucket.txt')
                        if need not in listed]
        for need in missing_list:
            bad.append('发布清单没列 %s ⇒ 手机上不会有这个文件' % need)
        if not missing_list:
            notes.append('发布清单列了翻译器与桶数据')

    # ③④ 翻译器代码形状
    if not os.path.exists(p(TRANSLATOR)):
        bad.append('翻译器不在：%s' % TRANSLATOR)
    else:
        src = read(p(TRANSLATOR))
        for name in ('exact', 'idx2', 'idx3'):
            if not re.search(r'\blocal\s+%s\s*=' % name, src):
                bad.append('翻译器缺索引 %s ⇒ 前缀查询仍在扫桶（H-267 的卡顿根因）' % name)
        if re.search(r'for\s+i\s*=\s*1\s*,\s*#bucket', src):
            bad.append('翻译器里又出现整桶线扫（for i = 1, #bucket）')
        if re.search(r'table\.sort', src):
            bad.append('翻译器对桶做了 table.sort ⇒ 联想顺序不再等于表内原顺序（改行为，不是改性能）')
        if '#input < 2' not in src.replace('  ', ' '):
            bad.append('翻译器丢了「单字母不出英文」的闸（判据 ①）')
        if 'MAX_EN_CANDS' not in src:
            bad.append('翻译器丢了英文联想限额（判据 ④）')

    # ⑤ 挂载状态：只报告
    if os.path.exists(p(CUSTOM)):
        cu = read(p(CUSTOM))
        mounted = re.search(r'^\s*-\s*lua_translator@enWord_translator', cu, re.M)
        commented = re.search(r'^\s*#\s*-\s*lua_translator@enWord_translator', cu, re.M)
        if mounted:
            notes.append('挂载：已挂 lua_translator@enWord_translator')
        elif commented:
            notes.append('挂载：**当前是注释状态**（v30 暂禁用）⇒ 手机上不会出英文候选；'
                         '挂不挂由 CodeArts 决定，本守卫不拦')
        else:
            notes.append('挂载：custom.yaml 里找不到这一行（既没挂也没注释）')
    return bad, notes


def run(root=ROOT):
    bad, notes = check(root)
    for n in notes:
        print('INFO %s' % n)
    if bad:
        for b in bad:
            print('FAIL ' + b)
        print('结论：英文候选链不通（rc=1）')
        return 1
    print('结论：桶数据＋发布清单＋索引式翻译器三层都在位（rc=0）')
    return 0


# ------------------------------------------------------------------ 自测

def selftest():
    ok = True

    def report(name, passed, detail=''):
        nonlocal ok
        ok = ok and passed
        print('%s %-44s %s' % ('PASS' if passed else 'FAIL', name, detail))

    good = tempfile.mkdtemp(prefix='h267-good-')
    try:
        # 用真树的一份等价副本当「已知好样本」＝正控（H-250 口径）
        for rel in (BUCKET, TRANSLATOR, LUA_FILES, CUSTOM):
            d = os.path.join(good, rel)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copyfile(os.path.join(ROOT, rel), d)
        bad, notes = check(good)
        report('正控:真树形状副本', bad == [], '；'.join(notes)[:110])

        def mutate(rel, fn):
            d = os.path.join(good, rel)
            s = io.open(d, encoding='utf-8').read()
            io.open(d, 'w', encoding='utf-8', newline='\n').write(fn(s))

        # 坏形状 1：桶里把 app 那行删掉（＝H-265 的原始症状）
        mutate(BUCKET, lambda s: re.sub(r'^a\tapp\t.*\n', '', s, flags=re.M | re.I))
        b1, _ = check(good)
        report('负控:桶缺 app', any('缺关键缩写词' in x and 'app' in x for x in b1), str(b1)[:90])
        mutate(BUCKET, lambda s: s)

        def restore_bucket():
            shutil.copyfile(os.path.join(ROOT, BUCKET), os.path.join(good, BUCKET))
        restore_bucket()

        # 坏形状 2：发布清单少桶（手机上没数据）
        mutate(LUA_FILES, lambda s: s.replace('lua/en_word_bucket.txt', '#lua/en_word_bucket.txt'))
        b2, _ = check(good)
        report('负控:清单没列桶', any('发布清单没列' in x for x in b2), str(b2)[:90])
        shutil.copyfile(os.path.join(ROOT, LUA_FILES), os.path.join(good, LUA_FILES))

        # 坏形状 3：索引被换回整桶线扫（H-267 的卡顿）
        mutate(TRANSLATOR, lambda s: s.replace('local idx3 = {}', 'local idx3 = {}\nfor i = 1, #bucket do end -- bad'))
        b3, _ = check(good)
        report('负控:出现整桶线扫', any('整桶线扫' in x for x in b3), str(b3)[:90])

        # 坏形状 4：加回 table.sort（我差点提交的那版：改了联想顺序＝改行为）
        mutate(TRANSLATOR, lambda s: s.replace('local nrows = 0', 'local nrows = 0\n  -- table.sort(b, byWord)'))
        b4, _ = check(good)
        report('负控:桶被排序', any('table.sort' in x for x in b4), str(b4)[-90:])
        shutil.copyfile(os.path.join(ROOT, TRANSLATOR), os.path.join(good, TRANSLATOR))

        # 恢复后必须重新放行（证明不是恒红，H-259 那类模型病）
        b5, _ = check(good)
        report('正控:改回原样再放行', b5 == [], str(b5)[:90])
    finally:
        shutil.rmtree(good, ignore_errors=True)

    print('自测结论：%s' % ('全部通过' if ok else '有断言失败'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(selftest() if '--selftest' in sys.argv else run())
