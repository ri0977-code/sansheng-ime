#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时脚本：给 h190_bar_ux_check.py 加 H-215 判据。"""
import re

PATH = "scripts/h190_bar_ux_check.py"
with open(PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 找到 "return out" 前面插入 H-215 判据
# 定位：H-207 剪贴板分支不带上下 padding 之后、return out 之前
marker = '                "上下 padding 会从 44vp 预算里吃掉按钮高度；默认胶囊按钮约 40vp，吃掉就判「显示不完整」"))\n    return out'

if marker not in content:
    # 尝试另一种匹配
    marker = '吃掉就判「显示不完整」"))\n    return out'
    if marker not in content:
        print("FAIL: marker not found")
        import sys
        sys.exit(1)

new_block = '''吃掉就判「显示不完整」"))

    # ---- H-215（CodeArts M-251 ④：符号页顶栏换工具栏，增大符号区）----
    out.append(("H-215 符号页 CandidateBar 自动显示工具栏",
                "this.panelMode === 'symbol'" in text and
                re.search(r"if \\(this\\.showFuncBar \\|\\| this\\.panelMode === 'symbol'\\)", text) is not None,
                "CandidateBar 条件必须含 `|| this.panelMode === 'symbol'`"))
    out.append(("H-215 SymbolPanel 无标签行",
                text.count("SYMBOL_CATEGORIES") <= 1,
                "SymbolPanel 不应再渲染标签行"))
    out.append(("H-215 symbolRowItems 支持 row=4",
                re.search(r"slice\\(start \\+ 7, start \\+ 13\\)", text) is not None
                and re.search(r"slice\\(start \\+ 13, start \\+ 19\\)", text) is not None,
                "symbolRowItems 必须支持 row=2/3/4 三行分配（7+6+6=19）"))
    out.append(("H-215 ListItem 有第4行符号行(sr4)",
                "sr4_" in text,
                "SymbolPanel ListItem 必须有第4行符号行"))
    out.append(("H-215 L1 候选行符号页不渲染",
                re.search(r"this\\.panelMode !== 'symbol'", text) is not None,
                "L1 候选行条件必须含 `panelMode !== 'symbol'`"))
    out.append(("H-215 L2 候选行符号页不渲染",
                re.search(r"panelMode === 'symbol' \\? Visibility\\.None", text) is not None,
                "L2 候选行 visibility 必须含 `panelMode === 'symbol'`"))
    out.append(("H-215 onFuncIcon back 符号页回字母页",
                re.search(r"panelMode === 'symbol'.*?switchPanelMode\\('qwerty'\\)", text, re.S) is not None,
                "onFuncIcon back 分支在符号页时必须回字母页"))
    out.append(("H-215 ③ 字母键下滑出大写代码存在",
                re.search(r"typeChar\\(ch\\.toUpperCase\\(\\)\\)", text) is not None,
                "LetterKey onTouch 中必须有下滑出大写代码"))
    return out'''

content = content.replace(marker, new_block)

with open(PATH, "w", encoding="utf-8") as f:
    f.write(content)
print("OK: h190 闸门加 H-215 判据")