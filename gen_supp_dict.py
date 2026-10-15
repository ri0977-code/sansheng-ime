# -*- coding: utf-8 -*-
"""
生成 Rime 五笔词通补充词典 wubi_citong.dict.yaml
从 cn_pinyin_wp.dict.yaml 中挑出「wubi86 未收录的多字词(2~4字)」，
按标准五笔组词规则算出正确组词码，登记进去，使这些词可单码打出。
同时做碰撞检查：若算出的码已被 wubi86 中「另一个词」占用，则跳过，避免制造歧义。
"""
import os

RIME = r"D:/Program Files/Rime"
WUBI = os.path.join(RIME, "wubi86.dict.yaml")
PINYIN = os.path.join(RIME, "cn_pinyin_wp.dict.yaml")
OUT = os.path.join(RIME, "wubi_citong.dict.yaml")

CJK = []
def is_cjk(ch):
    b = ord(ch)
    return (0x3400 <= b <= 0x4DBF) or (0x4E00 <= b <= 0x9FFF) or (0xF900 <= b <= 0xFAFF)

def parse_dict(path):
    """返回 (text2shortest_code, code2text)"""
    t2c = {}
    c2t = {}
    in_data = False
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("---"):
                in_data = False
            elif line.startswith("..."):
                in_data = True
            elif in_data and line and not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) < 2:
                    continue
                text, code = parts[0], parts[1]
                if not text or not code:
                    continue
                if len(text) > 12:
                    continue
                # 最短码优先
                cur = t2c.get(text)
                if cur is None or len(code) < len(cur):
                    t2c[text] = code
                # code->text（碰撞用，取第一个）
                if code not in c2t:
                    c2t[code] = text
    return t2c, c2t

def first_n(code, n):
    return code[:n] if code else ""

def group_code(word, t2c):
    codes = [t2c.get(c) for c in word]
    if any(c is None for c in codes):
        return None
    L = len(word)
    if L == 2:
        gc = first_n(codes[0], 2) + first_n(codes[1], 2)
    elif L == 3:
        gc = first_n(codes[0], 2) + first_n(codes[1], 1) + first_n(codes[2], 2)
    elif L == 4:
        gc = codes[0][:1] + codes[1][:1] + codes[2][:1] + codes[3][:1]
    elif L > 4:
        gc = codes[0][:1] + codes[1][:1] + codes[2][:1] + codes[-1][:2]
    else:
        return None
    if len(gc) < 2:
        return None
    return gc

print("解析 wubi86 ...")
wubi_t2c, wubi_c2t = parse_dict(WUBI)
print("  wubi 词条(去重):", len(wubi_t2c))

print("解析 cn_pinyin_wp ...")
pin_t2c, _ = parse_dict(PINYIN)
print("  pinyin 词条(去重):", len(pin_t2c))

out_lines = []
out_lines.append("---")
out_lines.append("name: wubi_citong")
out_lines.append('version: "2.1"')
out_lines.append("sort: by_weight")
out_lines.append("import_tables: []")
out_lines.append("columns:")
out_lines.append("  - text")
out_lines.append("  - code")
out_lines.append("  - weight")
out_lines.append("  - stem")
out_lines.append("encoder:")
out_lines.append("  exclude_patterns:")
out_lines.append("    - '^z.*'")
out_lines.append("...")
out_lines.append("")

added = 0
skipped_in_wubi = 0
skipped_no_code = 0
skipped_collision = 0
skipped_noncjk = 0

# 种子词：用户明确要单码打出的词。允许与 wubi86 已有码撞车（共存），并给高权重排在前面。
SEED = {
    "海洋生物": ("iitt", 200000000),
}

# 先处理种子词（绕过碰撞检查，但避免与自身已收录重复）
for text, (gc, w) in SEED.items():
    if text in wubi_t2c:
        skipped_in_wubi += 1
        continue
    out_lines.append(f"{text}\t{gc}\t{w}\t")
    added += 1
    print(f"  种子: {text} -> {gc} (weight={w})")

for text, py in pin_t2c.items():
    L = len(text)
    if L < 2 or L > 4:
        continue
    if not all(is_cjk(c) for c in text):
        skipped_noncjk += 1
        continue
    if text in SEED:
        continue
    if text in wubi_t2c:
        skipped_in_wubi += 1
        continue
    gc = group_code(text, wubi_t2c)
    if gc is None:
        skipped_no_code += 1
        continue
    # 碰撞检查：码已被 wubi86 中别的词占用
    owner = wubi_c2t.get(gc)
    if owner is not None and owner != text:
        skipped_collision += 1
        continue
    weight = 100000  # 统一给一个中等权重，保证可打出但不喧宾夺主
    out_lines.append(f"{text}\t{gc}\t{weight}\t")
    added += 1

with open(OUT, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(out_lines) + "\n")

print("生成完成:", OUT)
print("  新增词条:", added)
print("  跳过(已在wubi86):", skipped_in_wubi)
print("  跳过(缺单字码):", skipped_no_code)
print("  跳过(码碰撞):", skipped_collision)
print("  跳过(含非CJK):", skipped_noncjk)

# 抽样展示几个
import random
random.seed(7)
sample = [l for l in out_lines if l and not l.startswith(("-", ".", "#")) and "\t" in l]
print("抽样(含海洋生物应为 iitt):")
for l in sample:
    if any(w in l for w in ["海洋生物","你好","春夏秋冬","打印机","中华人民共和国","苹果","中国","人民"]):
        print("  ", l)
