# -*- coding: utf-8 -*-
# H-279(Qoder): 选一条「全新词」做真机对照，证明造词链不是只对 tgtf/行不行 生效。
# 判定口径（三条同时成立才算「干净的全新词」）：
#   ① 该词在 rawfile/rime 下所有 *.dict.yaml（含 import_tables 递归展开）里都不作为词条出现
#      ⇒ 任何命中只可能来自 encoder 造词，不可能来自词库；
#   ② 三个字的 reverse 全码（第 4 列 stem）都在，否则 UnityTableEncoder 推不出码
#      （这正是 H-279 的根因列）；
#   ③ 按 encoder 三字规则 AaBaCaCb（wubi86.dict.yaml:44-45）算出期望码，且该码不以 z 开头
#      （encoder/exclude_patterns 排除 ^z.*$）。
import glob
import os
import sys

RIME = os.path.join("entry", "src", "main", "resources", "rawfile", "rime")

CANDIDATES = [
    "行不行", "好不好", "对不对", "能不能", "是不是", "有没有",
    "三生梦", "码海行", "词库全", "自造词", "造得出", "记得住",
    "吃了吗", "去哪儿", "来得及", "说不清", "做得到", "靠得住",
    "打天下", "输入法", "键盘声", "老手写", "新词表",
    "行得通", "说得对", "看得清", "听得进", "写得顺",
]

CACHE = {}


def load(name):
    """Return (words: dict text->[codes], stems: dict text->full code, imports: [names])."""
    path = os.path.join(RIME, name + ".dict.yaml")
    if not os.path.exists(path):
        return None
    if path in CACHE:
        return CACHE[path]
    raw = open(path, "rb").read().decode("utf-8")
    lines = raw.split("\n")
    end = None
    for i, l in enumerate(lines):
        if l.strip() == "...":
            end = i
            break
    if end is None:
        raise SystemExit("[FAIL] %s 没有 header 结束符 '...'，统计口径不成立" % path)
    header = lines[:end]
    body = lines[end + 1:]
    imports = []
    in_imports = False
    for l in header:
        s = l.strip()
        if s.startswith("import_tables:"):
            in_imports = True
            continue
        if in_imports:
            if not s:
                continue
            if s.startswith("#") and not l.startswith("  -"):
                # 纯注释行：可能带在 '- name  # 注释' 之后，继续
                pass
            if s.startswith("- "):
                item = s[2:].split("#")[0].strip()
                if item:
                    imports.append(item)
                continue
            if not l.startswith(" "):
                in_imports = False
    words = {}
    stems = {}
    n_entries = 0
    for l in body:
        if not l.strip() or l.startswith("#"):
            continue
        parts = l.split("\t")
        if len(parts) < 2:
            continue
        w, code = parts[0], parts[1]
        stem = parts[3].strip() if len(parts) >= 4 else ""
        words.setdefault(w, []).append(code)
        n_entries += 1
        if stem:
            stems[w] = stem
    CACHE[path] = (words, stems, imports, n_entries, os.path.getsize(path))
    return CACHE[path]


def expand(name, seen=None):
    seen = seen if seen is not None else set()
    got = load(name)
    if got is None:
        return {}, {}, 0
    words, stems, imports, n, _sz = got
    seen.add(name)
    total = n
    all_words = {}
    for w, cs in words.items():
        all_words.setdefault(w, []).extend(cs)
    all_stems = dict(stems)
    for imp in imports:
        if imp in seen:
            continue
        iw, ist, tn = expand(imp, seen)
        total += tn
        for w, cs in iw.items():
            all_words.setdefault(w, []).extend(cs)
        for w, st in ist.items():
            all_stems.setdefault(w, st)
    return all_words, all_stems, total


def main():
    names = sorted(os.path.basename(p)[: -len(".dict.yaml")]
                   for p in glob.glob(os.path.join(RIME, "*.dict.yaml")))
    print("rawfile/rime 下 *.dict.yaml 共 %d 个：%s" % (len(names), ", ".join(names)))
    all_words = {}
    per_table = {}
    for n in names:
        w, _s, cnt = expand(n, set())
        per_table[n] = (w, cnt)
        for t in w:
            all_words.setdefault(t, set()).add(n)
    print("展开后去重词条数：%d" % len(all_words))

    _wubi_words, wubi_stems, wubi_total = expand("wubi86", set())
    print("wubi86 自身含 stem（reverse 全码）的字/词数：%d ／ 展开词条 %d" % (len(wubi_stems), wubi_total))
    print()

    ok = []
    for cand in CANDIDATES:
        chars = list(cand)
        if len(chars) != 3:
            continue
        missing = [c for c in chars if c not in wubi_stems]
        full = [wubi_stems.get(c, "") for c in chars]
        hit_tables = sorted(all_words.get(cand, []))
        code = ""
        if not missing:
            code = full[0][:1] + full[1][:1] + full[2][:2]
        clean = (not missing) and (not hit_tables) and code and not code.startswith("z")
        print("%-6s 期望码=%-6s 缺stem=%-4s 存在于词库=%-28s %s"
              % (cand, code or "-", ",".join(missing) or "-",
                 ",".join(hit_tables) or "-",
                 "CLEAN-NEW-WORD" if clean else ""))
        if clean:
            ok.append((cand, code, [wubi_stems[c] for c in chars]))

    print()
    print("可选「全新词」（不在任何词库里且三字 stem 齐全）：")
    for cand, code, stems in ok:
        print("  %s  ->  %s   逐字全码 %s" % (cand, code, " / ".join(stems)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
