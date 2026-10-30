#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成鸿蒙版符号/emoji 分类数据（H-057 / M-046 契约）。

输入（桌面三生数据，只读）：
  D:/Program Files/Rime/symbols.custom.yaml   107 组 /xx 符号表
  D:/Program Files/Rime/lua/phraseExt esUnicode.txt / esAppEmoji.txt   emoji 词条
输出：
  entry/src/main/resources/rawfile/symbols/symbols.json

契约（与 KeyboardIndex.ets 冻结）：
  {"version": "...", "groups": [{"id": "common", "label": "常用", "items": ["，", "。"]}]}

约定：
- id 稳定、全局唯一，UI 状态按 id 记；id 不随顺序变化。
- items 每项是一个按钮内容（单字符 / emoji 序列）。
- 先放 5 个核心组（与 UI fallback 的 id 对齐），再放表情，最后放桌面版 107 组。
- 同一组内去重、保持原顺序；空组丢弃。
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP_RIME = Path(r"D:/Program Files/Rime")
OUT = ROOT / "entry/src/main/resources/rawfile/symbols/symbols.json"
VERSION = "2026-10-22"

# 核心 5 组：id 与 KeyboardIndex.ets 的 FALLBACK_SYMBOL_GROUPS 保持一致，
# 这样数据到位前后 UI 状态（activeSymbolGroupId）不会跳。
CORE_GROUPS = [
    {
        "id": "common",
        "label": "常用",
        "items": list("，。？！、；：“”‘’（）【】《》「」『』…—～·￥＄％＃＠＆＊＋－＝／＼｜"),
    },
    {
        "id": "math",
        "label": "数学",
        "items": list("＋－×÷＝≠≈≤≥±∞√∛∑∏∫∬∂∆∇∈∉⊂⊃∪∩∧∨¬∀∃∵∴∠⊥∥∽≌≡°′″％‰π²³ⁿ½¼¾"),
    },
    {
        "id": "currency",
        "label": "货币",
        "items": list("￥＄€£¥¢₩₽₹₺₴₫₱₪₡₦₲₵₭₮₸₼₾₿¤"),
    },
    {
        "id": "arrow",
        "label": "箭头",
        "items": list("←→↑↓↔↕⇐⇒⇑⇓⇔⇕↖↗↘↙↺↻⟲⟳⤴⤵⬅➡⬆⬇"),
    },
    {
        "id": "english",
        "label": "英文",
        "items": list("~`!@#$^&*()-_=+[]{}\\|;:'\",.<>/?") + list("abcdefghijklmnopqrstuvwxyz"),
    },
]

# 107 组的中文标签。按桌面 symbols.custom.yaml 的 /xx 助记码给名；
# 查不到的组统一显示 "符号 xx"，不臆造语义。
LABELS = {
    "zt": "状态", "tj": "好评", "jd": "进度", "dc": "勾选",
    "lm": "罗马小写", "lmd": "罗马大写",
    "szd": "点号数字", "szk": "括号数字", "szm": "苏州码子",
    "szq": "圆圈数字", "szz": "中文数字", "hzq": "圆圈汉字", "hzk": "括号汉字",
    "fs": "分数", "gz": "干支", "xzm": "星座",
    "sb": "上标", "xb": "下标",
    "an": "方形字母", "jq": "节气", "bs": "部首",
    "yf": "月份", "mj": "麻将", "rq": "日期", "sj": "时刻", "bgm": "八卦", "zb": "钟表",
    "o": "o 变体", "u": "u 变体", "v": "ü 变体",
    "al": "α", "be": "β", "ga": "γ", "de": "δ", "ep": "ε", "ze": "ζ",
    "et": "θ", "the": "θ", "io": "ι", "ka": "κ", "la": "λ", "mu": "μ", "nu": "ν",
    "xi": "ξ", "om": "ω", "pi": "π", "rh": "ρ", "si": "σ", "ta": "τ", "tau": "τ",
    "up": "υ", "ph": "φ", "phi": "φ", "ch": "χ", "chi": "χ", "ps": "ψ", "psi": "ψ",
}
for letter in "abcdefghijklmnopqrstuvwxyz":
    LABELS[f"xb{letter}"] = f"下标 {letter}"
    letter = letter.upper()
    LABELS[f"sb{letter.lower()}"] = f"上标 {letter.lower()}"


def parse_symbol_groups(text: str):
    """从 symbols.custom.yaml 的 punctuator/symbols/+ 段落解析 (code, items[])。"""
    m = re.search(r"punctuator/symbols/\+:(.*?)(?:\n  [A-Za-z_]+/|\Z)", text, re.S)
    body = m.group(1) if m else text
    out = []
    seen = {}
    for line in body.splitlines():
        mm = re.match(r'^    "?([^":\s]+)"?:\s*\[(.*)\]\s*$', line)
        if not mm:
            continue
        code = mm.group(1).lstrip("/")
        items = re.findall(r'"([^"]*)"', mm.group(2))
        items = [s for s in items if s]
        if not items:
            continue
        if code in seen:
            # YAML 里 /om 出现两次（omicron/omega），合并而不是覆盖
            seen[code].extend(items)
        else:
            seen[code] = list(items)
            out.append(code)
    return [(code, seen[code]) for code in out]


EMOJI_MAX_CP = 8  # 一个按钮塞 8 个码点以内的 emoji（含 ZWJ 组合/肤色）


def is_emoji_like(s: str) -> bool:
    if not s or len(s) > EMOJI_MAX_CP * 3:
        return False
    if any(ch.isspace() for ch in s):
        return False
    has_emoji = False
    for ch in s:
        cp = ord(ch)
        if (0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF
                or 0x2300 <= cp <= 0x23FF or 0x2B00 <= cp <= 0x2BFF
                or cp in (0xFE0F, 0x200D)):
            has_emoji = True
        elif cp < 0x2000 or unicodedata.category(ch).startswith("C"):
            return False
    return has_emoji and len(s) <= 24


def load_emoji(path: Path):
    out = []
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        token = parts[-1].strip()
        if is_emoji_like(token):
            out.append(token)
    return out


def dedupe(items):
    seen, out = set(), []
    for it in items:
        if it and it not in seen:
            seen.add(it)
            out.append(it)
    return out


def build():
    groups = [dict(g, items=dedupe(g["items"])) for g in CORE_GROUPS]

    emoji = []
    for name in ("phraseExt esUnicode.txt", "phraseExt esAppEmoji.txt"):
        emoji.extend(load_emoji(DESKTOP_RIME / "lua" / name))
    emoji = dedupe(emoji)
    chunk = 120
    for i in range(0, len(emoji), chunk):
        part = i // chunk
        groups.append({
            "id": "emoji" if part == 0 else f"emoji_{part + 1}",
            "label": "表情" if part == 0 else f"表情 {part + 1}",
            "items": emoji[i:i + chunk],
        })

    sym_path = DESKTOP_RIME / "symbols.custom.yaml"
    if sym_path.exists():
        for code, items in parse_symbol_groups(sym_path.read_text(encoding="utf-8", errors="replace")):
            items = dedupe(items)
            if not items:
                continue
            groups.append({
                "id": f"r_{code}",
                "label": LABELS.get(code, f"符号 {code}"),
                "items": items,
            })
    else:
        print(f"warn: {sym_path} not found, only core+emoji groups", file=sys.stderr)

    data = {"version": VERSION, "groups": groups}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    total = sum(len(g["items"]) for g in groups)
    print(f"wrote {OUT} groups={len(groups)} items={total} emoji={len(emoji)} bytes={OUT.stat().st_size}")


if __name__ == "__main__":
    build()
