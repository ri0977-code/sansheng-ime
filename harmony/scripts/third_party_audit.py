"""逐文件许可/来源对账：鸿蒙 rawfile vs 安卓 rime/ vs dyyRime vs 上游仓库。
只读。产出 docs/evidence/<date>/third-party-audit-data.md
用法：python scripts/third_party_audit.py [YYYY-MM-DD]
"""
import hashlib
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIME = os.path.join(REPO, 'entry', 'src', 'main', 'resources', 'rawfile', 'rime')
ANDROID = r'F:/dshdesktopwork/sansheng-ime-android/rime'
DYY = r'D:/IDM/dyyRime-master'
WUBI_LGPL = r'D:/IDM/rime-wubi-master/rime-wubi-master'
JIDIAN = r'D:/IDM/rime-wubi86-jidian-master'
OHMY = r'D:/IDM/oh-my-rime-main'


def md5(b):
    return hashlib.md5(b).hexdigest()[:16]


def digest_tree(root, normalize=False):
    """normalize=True：把 CRLF 折成 LF 再算摘要，用来识别「仅行尾差异的原样复制」"""
    idx = {}
    if not os.path.isdir(root):
        return idx
    for dp, dn, fn in os.walk(root):
        dn.sort()
        for f in sorted(fn):
            p = os.path.join(dp, f)
            try:
                b = open(p, 'rb').read()
            except Exception:
                continue
            if normalize:
                b = b.replace(b'\r\n', b'\n')
            idx.setdefault(md5(b), []).append((os.path.relpath(p, root).replace(os.sep, '/'), len(b)))
    return idx


def name_index(root):
    """basename -> [relpath, ...]（dyyRime 里同名文件可能有多份）"""
    idx = {}
    if not os.path.isdir(root):
        return idx
    for dp, dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            idx.setdefault(f, []).append(os.path.relpath(p, root).replace(os.sep, '/'))
    return idx


def same_role(rel, cands):
    """角色对齐：我们的文件在 lua/ 下，dyy 候选也必须在 lua/ 下；root 层同理。
    避免 README.md / Custom_phrase.txt 这类通用名造成假阳性。"""
    ours_lua = '/lua/' in '/' + rel
    hits = []
    for c in cands:
        cand_lua = '/lua/' in '/' + c
        if cand_lua == ours_lua:
            hits.append(c)
    return hits


def head(p, n=6):
    try:
        with io.open(p, encoding='utf-8-sig', errors='ignore') as fh:
            return [fh.readline().rstrip('\n') for _ in range(n)]
    except Exception:
        return []


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else '2026-10-22'
    outdir = os.path.join(REPO, 'docs', 'evidence', day)
    os.makedirs(outdir, exist_ok=True)
    dyy_idx = digest_tree(DYY)
    dyy_norm = digest_tree(DYY, normalize=True)
    and_idx = digest_tree(ANDROID)
    dyys = name_index(DYY)
    lgpl_idx = digest_tree(WUBI_LGPL)
    jd_idx = digest_tree(JIDIAN)
    ohmy_idx = digest_tree(OHMY)

    rows = []
    for dp, dn, fn in os.walk(RIME):
        dn.sort()
        for f in sorted(fn):
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, RIME).replace(os.sep, '/')
            b = open(p, 'rb').read()
            mh = md5(b)
            where = []
            mhn = md5(b.replace(b'\r\n', b'\n'))
            for tag, idx in (('安卓', and_idx), ('dyy原样', dyy_idx),
                             ('LGPL-wubi', lgpl_idx), ('jidian', jd_idx), ('oh-my-rime', ohmy_idx)):
                if mh in idx:
                    where.append('%s:%s' % (tag, idx[mh][0][0]))
            if not any(w.startswith('dyy原样') for w in where) and mhn in dyy_norm:
                where.append('dyy原样(仅行尾差异):%s' % dyy_norm[mhn][0][0])
                ds_flag = True
            dyy_cands = same_role(rel, dyys.get(f, []))
            dyy_hit = bool(dyy_cands)
            dyy_same = any(w.startswith('dyy原样') for w in where)
            if dyy_hit and not dyy_same:
                try:
                    # 行尾差异（dyy 检出是 CRLF、仓库里是 LF）会假性压低相似度 → 统一 splitlines
                    other = open(os.path.join(DYY, dyy_cands[0].replace('/', os.sep)),
                                 'rb').read().decode('utf-8', 'ignore').splitlines()
                    self_ = b.decode('utf-8', 'ignore').splitlines()
                    import difflib
                    ratio = difflib.SequenceMatcher(None, other, self_).ratio()
                    where.append('dyy同名已改(%s，行级相似 %.0f%%)' % (dyy_cands[0], ratio * 100))
                except Exception:
                    where.append('dyy同名已改(%s)' % dyy_cands[0])
            rows.append((rel, len(b), mh, where, dyy_hit, dyy_same))

    same_and = [r for r in rows if any(w.startswith('安卓') for w in r[3])]
    dyy_same = [r for r in rows if r[5]]
    dyy_diff = [r for r in rows if r[4] and not r[5]]
    orphan = [r for r in rows if not r[3] and not r[4]]

    out = []
    out.append('# 鸿蒙随包 rime 数据逐文件来源对账（%s）' % day)
    out.append('')
    out.append('方法：对 `rawfile/rime/**` 每个文件算 md5（前 16 位），与四组参照做**字节级**命中：')
    out.append('`F:/dshdesktopwork/sansheng-ime-android/rime`（主人安卓产品自己的数据根，76 文件）、')
    out.append('`D:/IDM/rime-wubi-master`（LGPL-3.0）、`D:/IDM/rime-wubi86-jidian-master`（Apache-2.0）、')
    out.append('`D:/IDM/oh-my-rime-main`（仓库 LICENSE = GPL-3.0）、`D:/IDM/dyyRime-master`（仓库**无 LICENSE**）；')
    out.append('另按**文件名**与 dyyRime 对照，区分「原样复制」与「同名但已改写」。')
    out.append('')
    out.append('| 分类 | 个数 | 说明 |')
    out.append('|---|---|---|')
    out.append('| 与安卓数据根字节相同 | %d | 主人已在安卓 1.10.1 分发同一份文件，来源责任与安卓一致 |' % len(same_and))
    out.append('| 与 dyyRime 同名字节相同 | %d | ⚠ 上游无 LICENSE（保留所有权利）|' % len(dyy_same))
    out.append('| dyyRime 有同名但内容已改 | %d | 衍生作品，主体版权仍归上游 |' % len(dyy_diff))
    out.append('| 四组参照与 dyyRime 都没有 | %d | 本项目自写，或来自未在本机留档的上游 |' % len(orphan))
    out.append('| 合计 | %d | |' % len(rows))
    out.append('')
    out.append('## 1) 全量对账表')
    out.append('')
    out.append('| 文件 | 字节 | md5 | 命中 |')
    out.append('|---|---|---|---|')
    for rel, sz, mh, where, dh, ds in rows:
        tag = list(where)
        out.append('| `%s` | %s | `%s` | %s |' % (rel, format(sz, ','), mh, '；'.join(tag) if tag else '—'))
    out.append('')
    out.append('## 2) 与无授权上游 `happyDom/dyyRime` 的关系清单')
    out.append('')
    out.append('（本表口径：字节命中 = 原样复制；同名不同字节 = 改写衍生；其余 = 与 dyy 无关）')
    out.append('')
    out.append('| 关系 | 个数 | 合计字节 | 文件 |')
    out.append('|---|---|---|---|')
    grp = [('原样复制', [r for r in rows if r[5]]),
           ('同名但已改写', [r for r in rows if r[4] and not r[5]]),
           ('无 dyy 同名文件', [r for r in rows if not r[4]])]
    for label, rs in grp:
        out.append('| %s | %d | %s | %s |' % (
            label, len(rs), format(sum(r[1] for r in rs), ','),
            ', '.join('`%s`' % r[0] for r in rs)))

    out.append('')
    out.append('')
    out.append('## 3) 关键文件文件头（看署名头是否到位）')
    for rel in ('wubi86.dict.yaml', 'symbols.yaml', 'symbols.custom.yaml', 'pinyin_simp.dict.yaml',
                'cn_pinyin_wp.dict.yaml', 'lua/abbrGloss_Filter.lua', 'lua/phoneComment_Filter.lua'):
        p = os.path.join(RIME, rel.replace('/', os.sep))
        out.append('')
        out.append('### `%s`' % rel)
        out.append('```')
        if os.path.exists(p):
            out.extend(head(p, 8))
        else:
            out.append('(不存在)')
        out.append('```')

    path = os.path.join(outdir, 'third-party-audit-data.md')
    io.open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
    print('total=%d same_android=%d dyy_same=%d dyy_modified=%d orphan=%d'
          % (len(rows), len(same_and), len(dyy_same), len(dyy_diff), len(orphan)))
    print('wrote ' + path)


if __name__ == '__main__':
    main()
