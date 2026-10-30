import io, os

ROOT = r"F:\qoderwork\sansheng-ime-harmony"
EV = os.path.join(ROOT, "docs", "evidence", "2026-10-22")
WIP = os.path.join(ROOT, "docs", "WIP.md")

def read(p):
    with io.open(p, "r", encoding="utf-8") as f:
        return f.read()

def cells(s):
    s = s.strip()
    return len(s.strip("|").split("|"))

rows = read(WIP).split("\n")
hdr = max(i for i, l in enumerate(rows[:60]) if l.strip().startswith("| 编号"))
N = cells(rows[hdr])
assert N == 9, N

# 1) repair my own short rows (missing trailing 对方已读 cell)
fixed = []
for i, l in enumerate(rows):
    s = l.strip()
    if i > hdr and s.startswith("| W-") and s.endswith("|") and cells(s) == N - 1:
        assert "CodeArts" not in s.split("|")[3], "refusing to rewrite a peer row at " + str(i)
        rows[i] = s + " |"
        fixed.append(s.split("|")[1].strip())
print("repaired short rows:", fixed)

# 2) append W-082 (9 cells)
wip_row = read(os.path.join(EV, "tmp-wip-row.txt")).strip("\n")
assert "\n" not in wip_row
body = wip_row.strip("|").split("|")
assert len(body) == 8, len(body)
wip_row = wip_row + " 待读 |"          # 第 9 列：对方已读
assert cells(wip_row) == 9, cells(wip_row)
assert wip_row not in read(WIP)

idx = max(i for i, l in enumerate(rows) if l.strip())
assert rows[idx].strip().startswith("| W-081"), repr(rows[idx][:30])
assert cells(rows[idx]) == 9, cells(rows[idx])
rows.insert(idx + 1, wip_row)

with io.open(WIP, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(rows))
os.remove(os.path.join(EV, "tmp-wip-row.txt"))
os.remove(os.path.join(EV, "tmp-append.py"))
print("W-082 appended; temps removed")
