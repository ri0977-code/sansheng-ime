"""H-0xx 许可核对：枚举随包 rawfile，比对 NOTICE / rime README 是否声明。
产出 docs/evidence/<date>/rawfile-declaration-gap.txt 与 rawfile-inventory.json。
用法：python scripts/license_gap.py [YYYY-MM-DD]
"""
import io
import os
import sys
import json
import hashlib
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, 'entry', 'src', 'main', 'resources', 'rawfile')


def walk():
    rows = []
    for dp, dn, fn in os.walk(ROOT):
        dn.sort()
        for f in sorted(fn):
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, ROOT).replace(os.sep, '/')
            b = open(p, 'rb').read()
            rows.append((rel, len(b), hashlib.md5(b).hexdigest()[:16]))
    return rows


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else '2026-10-22'
    outdir = os.path.join(REPO, 'docs', 'evidence', day)
    os.makedirs(outdir, exist_ok=True)
    notice = io.open(os.path.join(REPO, 'NOTICE'), encoding='utf-8', errors='ignore').read()
    rd_path = os.path.join(ROOT, 'rime', 'README.md')
    rd = io.open(rd_path, encoding='utf-8', errors='ignore').read() if os.path.exists(rd_path) else ''
    lic_dir = os.path.join(REPO, 'LICENSES')
    lic_files = sorted(os.listdir(lic_dir)) if os.path.isdir(lic_dir) else []

    files = walk()
    declared, und = set(), []
    for rel, sz, mh in files:
        base = os.path.basename(rel)
        if base in notice or base in rd or rel in notice or rel in rd:
            declared.add(rel)
        else:
            und.append((rel, sz, mh))

    out = ['rawfile 文件总数 %d；NOTICE 或 rime/README 提到 %d；两处都未提到 %d'
           % (len(files), len(declared), len(und)),
           'LICENSES/ 目录许可全文文件 %d 个: %s' % (len(lic_files), ', '.join(lic_files)),
           '',
           '== 未在 NOTICE/rime README 出现的随包文件 ==']
    g = defaultdict(list)
    for rel, sz, mh in und:
        g[os.path.dirname(rel) or '.'].append((rel, sz, mh))
    for d in sorted(g):
        out.append('  [%s] %d 个' % (d, len(g[d])))
        for rel, sz, mh in sorted(g[d]):
            out.append('      %-50s %10d  %s' % (rel, sz, mh))
    out.append('')
    out.append('== 已提到（对照用）==')
    for rel in sorted(declared):
        out.append('      ' + rel)

    txt = os.path.join(outdir, 'rawfile-declaration-gap.txt')
    io.open(txt, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
    js = os.path.join(outdir, 'rawfile-inventory.json')
    json.dump([{'path': r, 'bytes': sz, 'md5_16': mh, 'declared': r in declared}
               for r, sz, mh in files],
              io.open(js, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
    print(out[0])
    print(out[1])
    print('wrote ' + txt)


if __name__ == '__main__':
    main()
