"""安卓 1.10.1 发布 APK 的 rime-data 与鸿蒙随包 rawfile/rime 逐文件对账。
只读。产出 docs/evidence/<date>/apk-data-parity.md
用法：python scripts/apk_parity.py [YYYY-MM-DD]
"""
import hashlib
import io
import os
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIME = os.path.join(REPO, 'entry', 'src', 'main', 'resources', 'rawfile', 'rime')
APKS = [
    r'F:/dshdesktopwork/sansheng-ime-android/_backup_ascii_rename_20261021/'
    r'发布-安卓-1.10.1-20261021/2-Rime插件-0.1.3-arm64.apk',
    r'F:/dshdesktopwork/sansheng-ime-android/_backup_ascii_rename_20261021/'
    r'发布-安卓-1.10.1-20261021/1-三生输入法-1.10.1-android.apk',
]
PREFIX = 'assets/usr/share/rime-data/'


def md5(b):
    return hashlib.md5(b).hexdigest()[:16]


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else '2026-10-22'
    outdir = os.path.join(REPO, 'docs', 'evidence', day)
    os.makedirs(outdir, exist_ok=True)

    apk = {}
    for a in APKS:
        if not os.path.exists(a):
            continue
        z = zipfile.ZipFile(a)
        for n in z.namelist():
            if n.startswith(PREFIX):
                b = z.read(n)
                apk[n[len(PREFIX):]] = (len(b), md5(b), os.path.basename(a))

    ours = {}
    for dp, dn, fn in os.walk(RIME):
        dn.sort()
        for f in sorted(fn):
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, RIME).replace(os.sep, '/')
            b = open(p, 'rb').read()
            ours[rel] = (len(b), md5(b))

    lines = []
    lines.append('# 安卓发布 APK rime-data 与鸿蒙随包数据逐文件对账（%s）' % day)
    lines.append('')
    lines.append('- 只读比对；摘要统一用 **md5 前 16 位**（此前散在记录里的 `6d089695…`、`ea929515…` 是 sha256 前 16 位，两套值不能互比）。')
    lines.append('- 安卓基准包：`2-Rime插件-0.1.3-arm64.apk`（发布 1.10.1，内含 `%s`）。' % PREFIX)
    lines.append('- 鸿蒙随包：`entry/src/main/resources/rawfile/rime/`（工作区未提交状态，CodeArts 12:10 记录在案）。')
    lines.append('')
    same, diff, only_h = [], [], []
    for name, (sz, mh, src) in sorted(apk.items()):
        if name in ours:
            if ours[name][1] == mh:
                same.append((name, sz))
            else:
                diff.append((name, sz, mh, ours[name][0], ours[name][1]))
    for name in sorted(ours):
        if name not in apk:
            only_h.append((name, ours[name][0], ours[name][1]))

    lines.append('## 1) 与安卓 APK 字节相同：%d 个' % len(same))
    for n, sz in same:
        lines.append('  - `%s` %s B' % (n, format(sz, ',')))
    lines.append('')
    lines.append('## 2) 同名但内容不同：%d 个' % len(diff))
    if diff:
        lines.append('| 文件 | 安卓 B / md5 | 鸿蒙 B / md5 |')
        lines.append('|---|---|---|')
        for n, sz, mh, osz, omh in diff:
            lines.append('| `%s` | %s / `%s` | %s / `%s` |' % (n, format(sz, ','), mh, format(osz, ','), omh))
    else:
        lines.append('  （无）')
    lines.append('')
    lines.append('## 3) 只在鸿蒙随包里出现：%d 个' % len(only_h))
    for n, sz, mh in only_h:
        lines.append('  - `%s` %s B `%s`' % (n, format(sz, ','), mh))
    lines.append('')
    lines.append('## 4) APK rime-data 全清单（%d 个）' % len(apk))
    for n, (sz, mh, src) in sorted(apk.items()):
        lines.append('  - `%s` %s B `%s`' % (n, format(sz, ','), mh))

    path = os.path.join(outdir, 'apk-data-parity.md')
    io.open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    print('same=%d diff=%d only_harmony=%d apk_total=%d' % (len(same), len(diff), len(only_h), len(apk)))
    print('wrote ' + path)


if __name__ == '__main__':
    main()
