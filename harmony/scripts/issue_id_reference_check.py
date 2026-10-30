#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-252(Qoder) 台账编号引用对账守卫（2026-10-28 08:1x）。

为什么有它：`H-227` 这个编号被 `HANDOFF.md`／`ISSUES.md`／`MAILBOX.md`／`SETTINGS-CONTRACT.md`
**四处当活单引用**（「三个点菜单补 5 个开关」），可 `docs/ISSUES.md` 里**从来没有过 `| H-227 |` 这一行**
（`git log -S'| H-227 |' -- docs/ISSUES.md` 命中 0 条）。后果不是难看，是**丢活**：
值守和 CodeArts 都按工单表派活，编号在四处被引用却在表里不存在 ⇒ 谁也没法把它当一条待办捡起，
它在 10-27 派给 CodeArts、他零回执，就这么飘了一整天。同一族病还有一次：H-248「台账状态列大面积过期」。

判据（红＝退出码 1，不是 WARN＝H-130/H-238 口径）：
  ① 凡在 `docs/*.md` 里被引用的 `H-编号`，`docs/ISSUES.md` 必须有以它为行首格的表行
     （`| H-241r2 |` 这种带后缀的行算 `H-241` 已有行）；
  ② **只查三层**：正文引用点算引用；`scripts/` 里的注释不算引用来源（守卫脚本自己会提编号，
     否则每次加判据都要补一张台账行，那是反向绑架）；
  ③ 台账里多出行、但全仓没人引用 ⇒ **不判**（新开单先写行再写正文是正常顺序）。

已知坏样本自测（`--selftest`）：往临时目录的真树副本里插一条「引用了不存在的编号」的行 ⇒ 必须判红
**且退出码 1**（端到端，同 H-250 那条口径：只测内存里的解析，测不到 read()/ROOT 这条通路）。

用法：
  python scripts/issue_id_reference_check.py            # 真树对账
  python scripts/issue_id_reference_check.py --selftest  # 已知坏样本
本条**不进内容闸门**（管的是文档，不是包；装机那一次主人要输密码，不该被台账笔误挡住＝H-250 同一口径），
但挡台账：写进 `docs/NIGHT-WATCH-V10.md` §3 第 4b 条那一串离线套里。
"""
import io
import os
import re
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = os.environ.get('SS_H252_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'docs')
ISSUES = os.path.join(DOCS, 'ISSUES.md')
ID = re.compile(r'\bH-(\d{3,4})\b')


def read(path):
    with io.open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def rows_in_issues():
    """ISSUES.md 里作为**行首格**出现过的编号（带 r 后缀的行归到主编号上）。"""
    have = set()
    for line in read(ISSUES).split('\n'):
        m = re.match(r'\|\s*H-(\d{3,4})\b', line)
        if m:
            have.add(m.group(1))
    return have


def references(exclude_issues_row_heads=True):
    """docs/*.md 里被引用过的编号 -> 引用处文件清单（证据目录 docs/evidence/** 不参与对账）。"""
    refs = {}
    for fn in sorted(os.listdir(DOCS)):
        if not fn.endswith('.md'):
            continue
        txt = read(os.path.join(DOCS, fn))
        for m in ID.finditer(txt):
            refs.setdefault(m.group(1), set()).add(fn)
    return refs


def scan():
    have = rows_in_issues()
    refs = references()
    missing = []
    for num in sorted(refs, key=lambda x: int(x)):
        if num not in have:
            where = ','.join(sorted(refs[num]))
            missing.append(('H-%s' % num, where))
    return missing, len(have), len(refs)


def run_check(verbose=True):
    missing, n_have, n_ref = scan()
    for num, where in missing:
        print('[FAIL] %s 在 %s 里被引用，但 docs/ISSUES.md 没有它的行' % (num, where))
    if verbose:
        print('H-252 台账编号引用对账: ISSUES 有行 %d 个编号；docs 被引用 %d 个；'
              '被引用却没有行的 %d 个' % (n_have, n_ref, len(missing)))
    if not missing and verbose:
        print('结论: 每个被引用的编号都有它自己的台账行（新开单先写行、后写正文，顺序不许反）。')
    return 1 if missing else 0


def selftest():
    """端到端三条断言。**不许把「真树当前干净」写进自测**——那是仓库状态不是守卫质量：
    真树真有缺行时自测会跟着红，反而把「守卫坏了」和「仓库有账没结」混成一句。所以：
      ① 副本与真树判定一致（证明 read()/ROOT 这条通路没坏）；
      ② 在副本里**删掉一个真实存在的编号行** ⇒ 必须判红（确定性坏样本，不依赖当前树）；
      ③ 在副本里插一条引用不存在编号的行 ⇒ 必须判红且 rc=1。"""
    import shutil
    import tempfile
    real_rc = run_check(verbose=False)
    tmp = tempfile.mkdtemp(prefix='h252-')
    saved = ROOT
    try:
        os.makedirs(os.path.join(tmp, 'docs'))
        for fn in os.listdir(DOCS):
            if fn.endswith('.md'):
                shutil.copyfile(os.path.join(DOCS, fn), os.path.join(tmp, 'docs', fn))
        globals()['DOCS'] = os.path.join(tmp, 'docs')
        globals()['ISSUES'] = os.path.join(globals()['DOCS'], 'ISSUES.md')
        copy_rc = run_check(verbose=False)
        cases = [('副本判定与真树一致', copy_rc, real_rc)]

        # ② 删掉 H-090 那一行（它必然在别处被引用 ⇒ 必红）
        p = globals()['ISSUES']
        orig = read(p)
        kept = [x for x in orig.split('\n') if not x.startswith('| H-090 ')]
        assert len(kept) < len(orig.split('\n')), '自测前提失效：副本里没有 H-090 行可删'
        with io.open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(kept))
        cases.append(('删掉一个真实编号行', run_check(verbose=False), 1))

        # ③ 复原 + 插一条引用 H-9001 的行
        with io.open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(orig)
        prog = os.path.join(globals()['DOCS'], 'PROGRESS.md')
        txt = read(prog).split('\n')
        txt.insert(0, '| ① 10-01 00:00 | Qoder | 自测插的坏行：引用 H-9001 这个不存在的编号 | x | y |')
        with io.open(prog, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(txt))
        cases.append(('插引用不存在的编号', run_check(verbose=False), 1))

        ok = True
        for label, rc, want in cases:
            good = (rc == want)
            ok = ok and good
            print('[selftest] %-20s 期望 rc=%d 实得 rc=%d %s'
                  % (label, want, rc, 'OK' if good else '<<< 判据失效'))
    finally:
        globals()['ROOT'] = saved
        globals()['DOCS'] = os.path.join(saved, 'docs')
        globals()['ISSUES'] = os.path.join(saved, 'docs', 'ISSUES.md')
        shutil.rmtree(tmp, ignore_errors=True)
    if not ok:
        print('H-252 自测失败 ⇒ 检查本身不可信，别信它的结论')
        return 1
    print('H-252 自测通过: 副本复现真树判定、删真行判红、插不存在编号判红且退出码 1。')
    return 0


def main():
    if '--selftest' in sys.argv:
        return selftest()
    return run_check()


if __name__ == '__main__':
    sys.exit(main())
