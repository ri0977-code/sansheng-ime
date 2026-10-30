#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-220(Qoder) 键位语义守卫：防止 j/k/m/s/d/n 的口径在后续构建里被悄悄改回。

背景（为什么需要这条闸门）：
  2026-10-27 主人三轮定稿了这几个长按键的语义，而 `KeyboardIndex.ets` 是
  Qoder / CodeArts 同树并行编辑的文件（M-255 划界），一旦被旧基线覆盖，
  缺陷会以「又变回去了」的形式回到主人手上——每次都要他重新手测一遍。
  所以这里把口径写死成可离线跑的检查。

判据来源（主人原话）：
  · 「错了不是全首全尾，是行」      ⇒ s=行首 / d=行尾（全文首尾只留在 ⇆ 面板格子里）
  · 「安卓里面有个选择键，可以按方向选择文本」⇒ n=选择（扩选模式开关）
  · 「下移上移，互换位置」          ⇒ j=上移 / k=下移（**故意偏离**安卓参照表 nova6-ime-research.md:118）
  · 「长按m是删除右边的内容…和退格重复了」⇒ m=删光标**后**（Del），走 deleteBackwardSync
  · 真机教训（14:58 手测 range 恒为 x,40）⇒ 扩选主路径必须是宿主原生 selectByMovementSync，记账式只兜底
  · H-224（Qoder 16:0x 自查）⇒ 一次「定位光标」只做一次宿主写，且按 selectionModeOn 分支；
    四个定位入口不得再自己 `selectByRangeSync({x,x})`（那会把开着的选择抹掉）

用法：
  python scripts/h220_keymap_check.py            # 跑守卫，红=退出码 1
  python scripts/h220_keymap_check.py --selftest # 用一份「已知错误」样本验证检查本身会红

严重度：**开发期守卫，不进发布阻断闸门**（发布闸门是 check_app_content.py 的 16 条）。
红了不要装机，先 `git diff` 看是不是并行改动打架（M-255 口径）。
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'entry', 'src', 'main', 'ets', 'pages', 'KeyboardIndex.ets')
CTRL = os.path.join(ROOT, 'entry', 'src', 'main', 'ets', 'inputmethod', 'KeyboardController.ets')

# (说明, 文件, 必须出现的正则)
RULES = [
    ("s 角标=行首", PAGE, r"if \(ch === 's'\) \{\s*\n\s*return '行首';"),
    ("d 角标=行尾", PAGE, r"if \(ch === 'd'\) \{\s*\n\s*return '行尾';"),
    ("n 角标=选择", PAGE, r"if \(ch === 'n'\) \{\s*\n\s*return '选择';"),
    ("j 角标=上移", PAGE, r"if \(ch === 'j'\) \{\s*(?://[^\n]*\n\s*)*return '上移';"),
    ("k 角标=下移", PAGE, r"if \(ch === 'k'\) \{\s*\n\s*return '下移';"),
    ("m 角标=删除", PAGE, r"if \(ch === 'm'\) \{\s*(?://[^\n]*\n\s*)*return '删除';"),
    ("长按 s 走行首", PAGE, r"keyboardController\.moveCursorToLineStart\(\);"),
    ("长按 d 走行尾", PAGE, r"keyboardController\.moveCursorToLineEnd\(\);"),
    ("长按 n 开/关选择", PAGE, r"keyboardController\.toggleSelectionMode\(\);"),
    ("长按 j = 上移(1)", PAGE, r"\} else if \(ch === 'j'\) \{[^}]*?keyboardController\.moveEditorCursor\(1\);"),
    ("长按 k = 下移(2)", PAGE, r"\} else if \(ch === 'k'\) \{[^}]*?keyboardController\.moveEditorCursor\(2\);"),
    ("长按 m = 删光标后", PAGE, r"keyboardController\.deleteAfterCursor\(\);"),
    ("m 不得退回退格", PAGE, r"(?s)else if \(ch === 'm'\) \{.*?\} else if \(ch === 's'\)"),
    ("控制器有 deleteAfterCursor", CTRL, r"deleteAfterCursor\(\): void \{"),
    ("Del 走 deleteBackwardSync", CTRL, r"client\.deleteBackwardSync\(1\);"),
    ("扩选主路径=selectByMovementSync", CTRL, r"client\.selectByMovementSync\(\{ direction: direction as inputMethodEngine\.Direction \}\)"),
    # H-218r4：⇆ 面板高必须等于键区预算（4 行）。传 5 行 ⇒ 内容超 IME 窗口 236vp，末行「选择」被裁到窗口外。
    ("⇆ 面板高=4 行预算", PAGE, r"panelHeight: this\.rowHeight \* 4,"),
    # H-221（主人 2026-10-27 15:3x「hjkl 长按不撒手…连续执行，直到撒手」）：四个方向键长按后要起连发，
    # 连发必须有停（抬手/接管/销毁/新按下），否则「按一下 h 之后打字光标自己乱走」。
    ("h 连发(3)", PAGE, r"this\.startDirRepeat\(3, 'h'\);"),
    ("j 连发(1)", PAGE, r"this\.startDirRepeat\(1, 'j'\);"),
    ("k 连发(2)", PAGE, r"this\.startDirRepeat\(2, 'k'\);"),
    ("l 连发(4)", PAGE, r"this\.startDirRepeat\(4, 'l'\);"),
    ("连发用 setInterval+120ms 常量", PAGE, r"setInterval\(\(\) => \{\s*\n\s*keyboardController\.moveEditorCursor\(dir\);"),
    ("抬手停连发", PAGE, r"this\.letterHeld = false;\s*\n\s*this\.stopDirRepeat\(\);"),
    ("Cancel 停连发", PAGE, r"TouchType\.Cancel\) \{\s*\n\s*this\.releaseKey\(`letter_\$\{ch\}`\);\s*\n\s*this\.stopDirRepeat\(\);"),
    ("销毁停连发", PAGE, r"this\.stopBackspaceRepeat\(\);\s*\n\s*// H-221[\s\S]{0,80}?this\.stopDirRepeat\(\);"),
    # H-224（Qoder 2026-10-27 自查，主人未报）：四个「定位光标」入口原先各做两次宿主写
    # （先 {x,x} 收拢、再在开着「选择」时扩回去）。主人 14:58 手测证明宿主把每次
    # selectByRange 当成重新落选区 ⇒ 中间那次收拢会把选区抹掉。定论：一次分支写。
    # H-224/H-229（2026-10-27 18:2x 改口径）：定位分两条路——
    # ① 开着选择 ⇒ 非空区间一次 selectByRangeSync（H-224 主人真手验过）；
    # ② 关着选择 ⇒ **不许**用 selectByRangeSync 落位（零长度区间宿主一律不认，18:23 真机铁证），
    #    改走 moveCursorSync 逐步走（hjkl 连发用的同一个 API，真手验过有效）。
    # H-230（2026-10-27 18:3x，主人「开选择时行首行尾选的是前半文后半文不是一行」）：
    # 开选择落位要先用 `anchor`（行级移动=当前光标位 selCursor、全文级=selAnchor）再算 min/max，
    # 不许直接 Math.min(this.selAnchor, pos)（那会把选区跨回开选择时的那一行，选成半篇文）。
    ("H-230 开选择落位先取 anchor", CTRL, r"const anchor: number = lineMove \? this\.cursorIndex\(\) : this\.selAnchor;"),
    ("H-230 起点=min(anchor,pos)", CTRL, r"const start: number = Math\.min\(anchor, pos\);"),
    ("H-230 终点=max(anchor,pos)", CTRL, r"const end: number = Math\.max\(anchor, pos\);"),
    ("H-229 关选择走 moveCursorSync 逐步走", CTRL, r"this\.walkCursorTo\(pos\);"),
    ("H-229 逐步走用 moveCursorSync", CTRL, r"client\.moveCursorSync\(step\);"),
    ("H-229 逐步走有防呆上限", CTRL, r"guard < 4000"),
    ("H-229 每步回读、卡住就停", CTRL, r"if \(next === cur\) \{"),
    ("H-229 关选择时锚点跟到新位", CTRL,
     r"this\.walkCursorTo\(pos\);\s*\n\s*this\.selCursor = pos;\s*\n\s*this\.selAnchor = pos;"),
    # H-226（主人 2026-10-27 16:5x「sd只针对行，那么fg就有用了，应该是页首页尾…没异议就加上吧」）：
    # 鸿蒙拿不到宿主可视区域 ⇒ 没有「页」，落到全文首/尾（与 ⇆ 面板「全首」「全尾」同一动作）。
    # 角标用「文首/文末」而不写「页首/页尾」——写「页」是假承诺。
    ("f 角标=文首", PAGE, r"if \(ch === 'f'\) \{\s*(?://[^\n]*\n\s*)*return '文首';"),
    ("g 角标=文末", PAGE, r"if \(ch === 'g'\) \{\s*(?://[^\n]*\n\s*)*return '文末';"),
    ("长按 f 走全文首", PAGE, r"\} else if \(ch === 'f'\) \{[^}]*?keyboardController\.moveCursorToStart\(\);"),
    ("长按 g 走全文尾", PAGE, r"\} else if \(ch === 'g'\) \{[^}]*?keyboardController\.moveCursorToEnd\(\);"),
    ("f/g 归入编辑动作键（不弹泡）", PAGE, r"ch === 'f' \|\| ch === 'g';"),
]

# H-228（主人 2026-10-27 17:5x「文本编辑工具展开丑的一批，而且再次点击不能折叠，那个图标也不合适，
# 参考安卓那个图标吧」）：三条判据各自盯一个已修好的缺陷，防止后续构建被改回去。
PANELS = os.path.join(ROOT, 'entry', 'src', 'main', 'ets', 'components', 'ToolPanels.ets')
RULES_H228 = [
    # ① 图标最终定稿 = 系统符号 arrow_left_arrow_right（H-231，主人「图标成点了」）。
    #    H-228 那版按安卓 ic_cursor_move 用 Shape+Path 描形状，在 Mate 80 实机上**不渲染**
    #    （26vp 格子里只剩一个点），所以定稿退回系统符号。渲染不成点这件事只能靠真手验，
    #    但「不许再把 Shape+Path 塞回光标分支」可以离线盯死 ⇒ 见 FORBIDDEN_H231。
    ("H-231 光标图标用系统符号", PAGE,
     r"\} else if \(action === 'cursor'\) \{[\s\S]{0,400}?SymbolGlyph\(\$r\('sys\.symbol\.arrow_left_arrow_right'\)\)"),
    ("H-231 面板里有选择/取消格", PANELS, r"this\.gridSelect\(\)"),
    # 文案两种状态都带「选择」二字（开着时写「取消」，主人按「找选择按钮」找不到）。
    ("H-231 选择格文案含选择", PANELS, r"this\.selOn \? '取消选择' : '选择'"),
    # ② 再点一次要折叠：cursor 分支必须是三元开关，不许写成恒等赋值
    ("H-228 点光标图标是开关", PAGE,
     r"this\.funcSubPanel = this\.funcSubPanel === 'textedit' \? '' : 'textedit';"),
    # ③ 面板照安卓结构：左 3×3 簇 + 右操作列，且**不许再写死格子高度**（写死就会超窗裁末行）
    ("H-228 面板左簇权重 2.2", PANELS, r"\.layoutWeight\(2\.2\)"),
    ("H-228 面板右操作列权重 1", PANELS, r"\.layoutWeight\(1\)\s*\n\s*\.height\('100%'\)"),
    ("H-228 面板右列有退格(安卓 backspaceButton)", PANELS, r"sys\.symbol\.delete_left"),
]
RULES.extend(RULES_H228)


# H-231r2（Qoder 2026-10-27 21:0x）：H-231②「面板里没有选择按钮」的**第二个根因**——
# build() 里展开候选网格与子面板（textedit/clipboard）**互斥**：
#     if (this.expanded) { ExpandedPanel() } else if (funcSubPanel==='textedit') { TextEditGridPanel() }
# 网格展开着的时候点 ⇆，只改了状态、画面纹丝不动 ⇒ 主人看到的还是那张网格，
# 自然「里面没有选择按钮」。先前只把格子从内联 Stack 改成 @Builder 是**治了一半**。
RULES_H231R2 = [
    ("H-231r2 点光标图标先收展开网格", PAGE,
     r"case 'cursor':[\s\S]{0,900}?if \(this\.expanded\) \{\s*\n\s*this\.setExpanded\(false\);\s*\n\s*\}"),
    ("H-231r2 剪贴板面板先收展开网格", PAGE,
     r"case 'clipboard':[\s\S]{0,600}?if \(this\.expanded\) \{\s*\n\s*this\.setExpanded\(false\);\s*\n\s*\}"),
    # 反向也堵死：子面板开着时点 ▼ 展开网格，必须先关子面板，否则状态与画面错位
    # （再点 ⇆ 就变成「把看不见的面板关掉」，主人看着毫无反应）。
    ("H-231r2 展开网格前先关子面板", PAGE,
     r"if \(!this\.expanded && this\.funcSubPanel !== ''\) \{\s*\n\s*this\.funcSubPanel = '';"),
]
RULES.extend(RULES_H231R2)


# H-232（Qoder 2026-10-27 22:4x 真机实测）：⤶ 面板右列 5 格里**只有**「粘贴」这一枚还在用
# cellW/cellH —— 宽按 25% 算成 26.7vp、高按 cellH() 算成 35.2vp（cellH 少扣了外层 12vp padding），
# 系统粘贴徽章被拉成 95×123px 的椭圆，还比兄弟格（113px 行高）高出 10px 溢出行格（22:31 真机量到）。
# 修法＝与兄弟格同构：layoutWeight 均分 + height('100%')，宽度取「右列行高」⇒ 徽章成正圆。
RULES_H232 = [
    ("H-232 粘贴格宽度取右列行高", PANELS, r"\.width\(this\.rightCellW\(\)\)"),
    ("H-232 右列行高扣掉外层 padding 与列内间隙", PANELS,
     r"this\.panelHeight - 2 \* PANEL_PAD - \(RIGHT_CELLS - 1\) \* RIGHT_GAP\) / RIGHT_CELLS"),
    ("H-232 粘贴格与兄弟格同构（layoutWeight 均分）", PANELS,
     r"pasteCell\(\)\s*\{[\s\S]{0,700}?\.layoutWeight\(1\)"),
    ("H-232 粘贴徽章宽高同值（正方形⇒系统徽章成正圆）", PANELS,
     r"\.width\(this\.rightCellW\(\)\)\s*\n\s*\.height\(this\.rightCellW\(\)\)"),
    ("H-232 右列格数常量=5", PANELS, r"const RIGHT_CELLS: number = 5;"),
]
RULES.extend(RULES_H232)


# H-234/H-235/H-236（Qoder 2026-10-28 00:4x，主人 2026-10-27 深夜真手回话）：
#   「文本编辑折叠后，还显示灰色选中状态，没变回来」＝H-234（折叠 ⇆ 面板必须退出「选择」）
#   「上页下页怎么定义的，我看不出来」＝H-235（鸿蒙没有「页」，标签必须写实话「上5行/下5行」）
#   「复制还是个图标形式，全选，剪切都是文字」＝H-236（右列按安卓实物统一成文字）
RULES_H234_236 = [
    ("H-234 子面板折叠走单一出口（@Watch）", PAGE,
     r"@State @Watch\('onFuncSubPanelWatch'\) funcSubPanel"),
    ("H-234 折叠 textedit 时退出选择模式", PAGE,
     r"was === 'textedit' && this\.funcSubPanel === '' && this\.selMode"),
    ("H-234 退出选择复用 toggleSelectionMode（不造第二套）", PAGE,
     r"if \(was === 'textedit'[\s\S]{0,300}?keyboardController\.toggleSelectionMode\(\);"),
    ("H-235 面板上移格标签写「上5行」", PANELS, r"this\.gridWord\('上5行'"),
    ("H-235 面板下移格标签写「下5行」", PANELS, r"this\.gridWord\('下5行'"),
    ("H-236 右列「复制」是文字格", PANELS, r"this\.gridWord\('复制'"),
]
RULES.extend(RULES_H234_236)


# 「不得出现」规则：出现即红
FORBIDDEN = [
    ("m 长按不得再用 onBackspace", PAGE, r"\} else if \(ch === 'm'\) \{[^}]*?keyboardController\.onBackspace\(\);"),
    ("s 角标不得改回全文首", PAGE, r"if \(ch === 's'\) \{\s*\n\s*return '全首';"),
    ("⇆ 面板不得再传 5 行死高（会把末行裁出窗口）", PAGE, r"panelHeight: this\.rowHeight \* 5,"),
    ("d 角标不得改回全文尾", PAGE, r"if \(ch === 'd'\) \{\s*\n\s*return '全尾';"),
    # H-224：三个「自己收拢」的写法一旦回到定位入口，开着「选择」按 s/d 就又会取消选择。
    ("H-224 全首入口不得自己写 {0,0}", CTRL, r"client\.selectByRangeSync\(\{ start: 0, end: 0 \}\);"),
    ("H-224 全尾入口不得自己写 {end,end}", CTRL, r"client\.selectByRangeSync\(\{ start: end, end: end \}\);"),
    ("H-224 行首/行尾入口不得自己写 {pos,pos}", CTRL, r"client\.selectByRangeSync\(\{ start: pos, end: pos \}\);"),
    # H-229：18:23 那次「ssdfg 全失灵」的原样——关着选择用零长度区间落位（写一次/写两次都不生效，
    # 还会把后续定位带坏）。这条一旦回来，s/d/f/g 会再次集体不动。
    ("H-229 关选择不得退回零长度落位", CTRL,
     r"if \(!this\.selectionModeOn\) \{\s*\n\s*client\.selectByRangeSync\(\{ start: pos, end: pos \}\);"),
    ("H-229 不得在关选择分支补第二次同值写", CTRL, r"if \(start === end\) \{\s*\n\s*client\.selectByRangeSync"),
    # H-230（2026-10-27 18:3x 主人「开选择时行首行尾选的是前半文后半文不是一行」）：
    # 开选择落位若直接 Math.min(this.selAnchor, pos) 起选，行级移动会把选区跨回开选择的旧行
    # ⇒ 选成半篇文。必须先用 lineMove 决定 anchor（当前行=selCursor / 全文=selAnchor）。
    ("H-230 行级移动不得跨回旧 anchor", CTRL,
     r"if \(this\.selectionModeOn\) \{\s*\n[^}]*?const start: number = Math\.min\(this\.selAnchor, pos\);"),
]

FORBIDDEN_H228 = [
    # H-231（主人 2026-10-27 19:0x「图标成点了」）：H-228 用 Shape+Path 照 ic_cursor_move 描的
    # 左右三角＋I 型竖杠，在 Mate 80 的 26vp 功能图标格子里**整个不渲染**，只剩一个点。
    # 光标分支从此不许再出现 Shape()/Path()/commands()——形状近似但能渲染的系统符号才是正解。
    ("H-231 光标分支不得再用 Shape+Path（实机不渲染成点）",
     PAGE, r"\} else if \(action === 'cursor'\)[\s\S]{0,500}?(?:\b(?:Shape|Path)\(|commands\('M)"),
    # H-231：「选择」格必须是 gridSelect @Builder 的一枚兄弟格，不许再写回 Row 里的内联 Stack
    # （H-228 那版就是这样混排的，实机整排都在、偏偏中间这格看不见）。
    ("H-231 选择格不得写成内联 Stack", PANELS, r"Text\(this\.selOn \? '取消' : '选择'\)"),
    # 点光标图标不得再写成「永远置 textedit」（主人「再次点击不能折叠」的原缺陷）
    ("H-228 点光标图标不得恒置 textedit",
     PAGE, r"case 'cursor':[\s\S]{0,400}?this\.funcSubPanel = 'textedit';\s*\n\s*break;"),
    # 面板格子不许再写死高度（H-213/H-218r3 两次超窗事故的共同根因）。
    # 注意：单行模式（full=false）的 cellH 是**栏内**高度、不是键区预算，合法；
    # 所以只禁 full 模式那三枚新 builder（gridGlyph/gridWord/gridHold）里出现 cellH。
    ("H-228 full 网格不得写死 cellH 高度", PANELS,
     r"gridGlyph\(icon: Resource[\s\S]{0,300}?\.height\(this\.cellH\(\)\)"
     r"|gridWord\(label: string[\s\S]{0,300}?\.height\(this\.cellH\(\)\)"
     r"|gridHold\(dir: number\)[\s\S]{0,400}?\.height\(this\.cellH\(\)\)"),
]
FORBIDDEN.extend(FORBIDDEN_H228)

# H-232：粘贴格一旦退回 cellW/cellH，系统徽章立刻被拉成椭圆并溢出行格。
# 正则用「不跨过下一个 @Builder」限定在同一个 builder 体内，避免误伤单行旧位
# （pasteCellLegacy 仍按旧口径留用，H-129：证明、记录、留着）。
FORBIDDEN_H232 = [
    ("H-232 粘贴格不得再用 cellW（26.7×35.2vp 椭圆徽章）", PANELS,
     r"pasteCell\(\)(?:(?!@Builder)[\s\S]){0,600}?\.width\(this\.cellW\(\)\)"),
    ("H-232 粘贴格不得再用 cellH（高出右列行高 2.4vp）", PANELS,
     r"pasteCell\(\)(?:(?!@Builder)[\s\S]){0,600}?\.height\(this\.cellH\(\)\)"),
]
FORBIDDEN.extend(FORBIDDEN_H232)

# H-234/H-235/H-236 的「不得回退」三条：
#   @State funcSubPanel 一旦被摘掉 @Watch ⇒ 十处折叠点又没人管「选择」态（主人这次的原缺陷）；
#   full 面板里再出现 上页/下页 ⇒ 又是「页」这种鸿蒙给不出的假承诺（H-226 同款）；
#   「复制」再变回 gridGlyph(doc_filled_on_doc) ⇒ 右列文字/图标混排（主人原话「显得很另类」）。
# 注意单行旧位（editActions 里的 this.glyph($r('sys.symbol.doc_filled_on_doc'))）不在禁令内：
# 那一支 full=false 实机不可达，按 H-129「证明、记录、留着」。
FORBIDDEN_H234_236 = [
    ("H-234 子面板不得摘掉 @Watch（折叠退出选择会失效）", PAGE,
     r"@State funcSubPanel: string = '';"),
    ("H-235 full 面板不得再写「上页/下页」", PANELS, r"gridWord\('(?:上页|下页)'"),
    ("H-236 full 面板「复制」不得退回图标格", PANELS,
     r"gridGlyph\(\$r\('sys\.symbol\.doc_filled_on_doc'\)"),
]
FORBIDDEN.extend(FORBIDDEN_H234_236)

# H-238（Qoder 2026-10-28 01:2x，主人 01:0x 纠正：他报的「折叠后还是灰底选中状态」是**顶栏
# 文本编辑 ⇆ 图标**，不是键盘 n 键——我上一轮量错了对象）。真机复现（h238_toolbar_cursor_check.py）：
# 点 ⇆ 开面板后 ⇆ 盒底色停在按压色 #DCE2EC（656 px），再点 ⇆ 折叠后**还是** #DCE2EC。
# 根因＝按下态握在框架的 stateStyles(pressed) 状态机里，而 onClick 改 funcSubPanel 会让键区
# 整块换 builder，重渲染后 pressed 没复位。⇒ 按下态改由 @State 显式持有（本文件 M-049 键面同款通路）。
RULES_H238 = [
    ("H-238 顶栏图标按下态显式持有", PAGE, r"@State pressedFuncIcon: string = '';"),
    ("H-238 图标底色＝按下色优先、其次选中色", PAGE,
     # H-238r2（主人 01:2x「现在连选中都没有颜色了！」）：三层底色 按下色 > 选中色 > 透明。
     # 只写「按下有、抬手全没」的那一版（r1）会被这条判红——选中色必须由子面板开关算出来。
     r"\.backgroundColor\(this\.pressedFuncIcon === action \? FUNC_ICON_PRESSED\s*\n"
     r"\s*:\s*\(this\.funcIconOn\(action\) \? BG_ACTIVE : Color\.Transparent\)\)"),
    ("H-238r2 选中态由 funcSubPanel 算出（cursor=textedit）", PAGE,
     r"funcIconOn\(action: string\): boolean \{\s*\n\s*if \(action === 'cursor'\) \{\s*\n"
     r"\s*return this\.funcSubPanel === 'textedit';"),
    ("H-238r2 剪贴板图标同样有选中态", PAGE,
     r"if \(action === 'clipboard'\) \{\s*\n\s*return this\.funcSubPanel === 'clipboard';"),
    ("H-238 图标 Down 上色 / Up 清色", PAGE,
     # 不用「从 FuncIcon 往后数 N 字」的窗口——这个 builder 注释很长，加两行就会把窗口撑爆
     # （84/85 那次假红就是这么来的）。改成直接锚这段独有的 `ev` + pressedFuncIcon 组合。
     r"if \(ev\.type === TouchType\.Down\) \{\s*\n\s*this\.pressedFuncIcon = action;\s*\n\s*\}"
     r" else if \(ev\.type === TouchType\.Up \|\| ev\.type === TouchType\.Cancel\)"),
    ("H-238 onClick 兜底清按下态", PAGE,
     r"this\.onFuncIcon\(action\);\s*\n\s*this\.pressedFuncIcon = '';"),
]
RULES.extend(RULES_H238)

FORBIDDEN_H238 = [
    # 按压样式态一旦回到 FuncIcon，主人那句「折叠后还是灰底选中状态」立刻复发。
    # 窗口用「走到 funcIconOn 就停」限定在 builder 体内，不用固定字数（同上一条规则的原因）。
    ("H-238 FuncIcon 不得再挂按压样式态（抬手不复位）", PAGE,
     r"FuncIcon\(action: string\)(?:(?!private funcIconOn)[\s\S]){0,4000}?\.stateStyles\(\{ pressed"),
    # r1 那一版（按下有色、抬手全没）＝主人 01:2x 抓到的「连选中都没有颜色」，也算回退。
    ("H-238r2 底色不得只跟按下态走（会丢选中色）", PAGE,
     r"\.backgroundColor\(this\.pressedFuncIcon === action \? FUNC_ICON_PRESSED : Color\.Transparent\)"),
]
FORBIDDEN.extend(FORBIDDEN_H238)

# H-224 已知错误样本（--selftest 用）：改回「先收拢、后扩选」的两次写
BAD_CTRL_SAMPLE = """
  private afterCursorJump(pos: number): void {
    const client = this.inputClient;
    const start: number = this.selectionModeOn ? Math.min(this.selAnchor, pos) : pos;
    const end: number = this.selectionModeOn ? Math.max(this.selAnchor, pos) : pos;
    if (client) {
      try {
        client.selectByRangeSync({ start: start, end: end });
        if (start === end) {
          client.selectByRangeSync({ start: start, end: end });
        }
      } catch (e) { /* 只记账 */ }
    }
    if (!this.selectionModeOn) {
      this.selAnchor = pos;
    }
    this.selCursor = pos;
  }
  moveCursorToStart(): void {
      client.selectByRangeSync({ start: 0, end: 0 });
      this.afterCursorJump(0);
  }
  moveCursorToEnd(): void {
      client.selectByRangeSync({ start: end, end: end });
      this.afterCursorJump(end);
  }
  moveCursorToLineStart(): void {
      client.selectByRangeSync({ start: pos, end: pos });
      this.afterCursorJump(pos);
  }
"""

# 已知错误样本（--selftest 用）：j/k 未对调 + m 还是退格 + 面板传 5 行死高（会被裁）
BAD_SAMPLE = """
    if (ch === 'j') {
      return '下移';
    }
    if (ch === 'k') {
      return '上移';
    }
      panelHeight: this.rowHeight * 5,
          } else if (ch === 'm') {
            keyboardController.onBackspace();
          } else if (ch === 's') {
"""


# H-231r2 已知错误样本（--selftest 轮 6）：**修复前**的 cursor/clipboard 分支原样——
# 点 ⇆ 不收展开网格、点 ▼ 展开也不关子面板。这三条判据必须都报「缺」。
BAD_SAMPLE_H231R2 = """
      case 'cursor':
        // H-218r2（主人「文本编辑不在一行上，展开铺到键盘上，你没看安卓吗」）：
        // H-228(Qoder 2026-10-27 17:5x，主人「再次点击不能折叠」)：**改成开关**——
        this.funcSubPanel = this.funcSubPanel === 'textedit' ? '' : 'textedit';
        break;
      case 'clipboard':
        this.funcSubPanel = 'clipboard';
        break;
"""

# H-226 已知错误样本（--selftest 轮 3）：把 f/g 写成「页首/页尾」并让 f 长按不做事——
# 「页」是鸿蒙给不出的承诺（拿不到宿主可视区域），角标必须诚实写「文首/文末」。
BAD_SAMPLE_FG = """
    if (ch === 'f') {
      return '页首';
    }
    if (ch === 'g') {
      return '页尾';
    }
          } else if (ch === 'f') {
            this.editorActionDone = true;
          } else if (ch === 's') {
"""


# H-228/H-231 已知错误样本（--selftest 轮 4）：把已修好的事改回去——
# ① 光标图标退回 H-228 那版 Shape+Path 描形状（**实机不渲染，主人看到「成点了」**）；
# ② 面板里少了「选择/取消」格（没有它就无法开/关扩选，H-220 的功能根）。
# 两条必须各自命中。
BAD_SAMPLE_H228 = """
      } else if (action === 'cursor') {
        Shape() {
          Path().commands('M17,16 l4,-4 L17,8 Z')
        }
      } else {
        SymbolGlyph(this.funcIconSymbol(action))
      }
"""

BAD_PANELS_NOSEL = """
  @Builder
  TextEditPadFull() {
    Row({ space: 6 }) {
      Column({ space: 4 }) {
        Row({ space: 4 }) {
          this.gridWord('上页', () => {})
          this.gridWord('下页', () => {})
        }
      }
    }
  }
"""

BAD_PANELS_H228 = """
  @Builder
  gridWord(label: string, onTap: () => void) {
    Stack() {
      Text(label)
    }
    .width(this.cellW())
    .height(this.cellH())
  }
"""

BAD_SAMPLE_TOGGLE = """
      case 'cursor':
        this.funcSubPanel = 'textedit';
        break;
"""

# H-230 已知错误样本（--selftest 轮 5）：开选择落位直接以 selAnchor 起选
# （行级移动 s/d 会把选区跨回开选择时的旧行，选成「前半文/后半文」）。
# 正确写法必须先 `const anchor = lineMove ? selCursor : selAnchor` 再算 min/max。
BAD_CTRL_SAMPLE_H230 = """
  private afterCursorJump(pos: number, lineMove: boolean = false): void {
    const client = this.inputClient;
    if (this.selectionModeOn) {
      const start: number = Math.min(this.selAnchor, pos);
      const end: number = Math.max(this.selAnchor, pos);
      client.selectByRangeSync({ start: start, end: end });
      this.selCursor = pos;
      return;
    }
    this.walkCursorTo(pos);
    this.selCursor = pos;
    this.selAnchor = pos;
  }
"""

# H-232 已知错误样本（--selftest 轮 7）：粘贴格退回 **修复前** 的 cellW/cellH 写法——
# 宽 25%（26.7vp）、高 cellH()（35.2vp，少扣了外层 12vp padding）⇒ 真机上系统徽章被拉成
# 95×123px 椭圆并溢出行格。两条禁令必须红、两条新判据必须报「缺」。
BAD_PANELS_H232 = """
  @Builder
  pasteCell() {
    PasteButton({ icon: PasteIconStyle.LINES, text: PasteDescription.PASTE, buttonType: ButtonType.Capsule })
      .width(this.cellW())
      .height(this.cellH())
      .fontSize(12)
  }
"""

# H-235/H-236 已知错误样本（--selftest 轮 8）：**修复前**的 full 面板原样——
# 中间行写「上页/下页」（鸿蒙拿不到可视区域，「页」是假承诺），右列「复制」是图标格
# （主人 2026-10-27 深夜「复制还是个图标形式，全选，剪切都是文字」）。
BAD_PANELS_H235_236 = """
      Row({ space: 4 }) {
        this.gridWord('上页', () => {
          keyboardController.moveCursorPage(-5);
        })
        this.gridSelect()
        this.gridWord('下页', () => {
          keyboardController.moveCursorPage(5);
        })
      }
      Column({ space: 4 }) {
        this.gridWord('全选', () => {})
        this.gridWord('剪切', () => {})
        this.gridGlyph($r('sys.symbol.doc_filled_on_doc'), () => {
          keyboardController.copyThenCollapse();
        })
        this.pasteCell()
      }
"""

# H-234 已知错误样本（--selftest 轮 8）：**修复前**的状态声明——funcSubPanel 没有 @Watch，
# 十处 `funcSubPanel = ''` 折叠点没有一处退出「选择」⇒ 主人「折叠后还显示灰色选中状态，没变回来」。
BAD_PAGE_H234 = """
  @State funcSubPanel: string = '';
      case 'cursor':
        if (this.expanded) {
          this.setExpanded(false);
        }
        this.funcSubPanel = this.funcSubPanel === 'textedit' ? '' : 'textedit';
        break;
"""

# H-238 已知错误样本（--selftest 轮 9）：**修复前**的 FuncIcon 原样——按压反馈挂在框架的
# 按压样式态上、没有任何显式清态。真机上点 ⇆ 开面板后灰底不恢复，再点 ⇆ 折叠后还是不恢复
# （主人 2026-10-28 01:0x「我说是顶栏的，文本编辑，折叠后还是灰底选中状态」）。
# 四条判据必须报「缺」、一条禁令必须报「禁」。
BAD_PAGE_H238 = """
  @Builder
  FuncIcon(action: string) {
    Stack() {
      SymbolGlyph(this.funcIconSymbol(action))
    }
    .width(FUNC_ICON_SIZE + 16)
    .height(this.funcIconBox())
    .borderRadius(RADIUS_SM)
    .stateStyles({ pressed: funcIconPressed })
    .onClick(() => {
      this.onFuncIcon(action);
    })
  }
"""

# H-238r2 已知错误样本（--selftest 轮 9b）：**我 r1 那一版**——按下有色、抬手后什么都不留，
# 面板开着时 ⇆ 也没有选中色（主人 01:2x 一眼看出「现在连选中都没有颜色了！」）。
# 这条样本必须让两条 r2 判据报「缺」，否则守卫只挡住了「灰底不退」，挡不住「把选中色一起砍掉」。
BAD_PAGE_H238_R1 = """
  @Builder
  FuncIcon(action: string) {
    Stack() {
      SymbolGlyph(this.funcIconSymbol(action))
    }
    .width(FUNC_ICON_SIZE + 16)
    .height(this.funcIconBox())
    .borderRadius(RADIUS_SM)
    .backgroundColor(this.pressedFuncIcon === action ? FUNC_ICON_PRESSED : Color.Transparent)
    .onTouch((ev: TouchEvent) => {
      if (ev.type === TouchType.Down) {
        this.pressedFuncIcon = action;
      } else if (ev.type === TouchType.Up || ev.type === TouchType.Cancel) {
        if (this.pressedFuncIcon === action) {
          this.pressedFuncIcon = '';
        }
      }
    })
    .onClick(() => {
      this.onFuncIcon(action);
      this.pressedFuncIcon = '';
    })
  }
"""


def read(path):
    return io.open(path, encoding='utf-8').read()


def run(page_text, ctrl_text, panels_text=None):
    """返回 (通过数, 失败列表)。H-228 起多一个文件（ToolPanels.ets）；
    不传时退回读磁盘，免得每处调用都要改。"""
    if panels_text is None:
        panels_text = read(PANELS)
    texts = {PAGE: page_text, CTRL: ctrl_text, PANELS: panels_text}
    fails = []
    passed = 0
    for name, path, pat in RULES:
        if re.search(pat, texts[path]):
            passed += 1
        else:
            fails.append('缺: %s' % name)
    for name, path, pat in FORBIDDEN:
        if re.search(pat, texts[path]):
            fails.append('禁: %s' % name)
        else:
            passed += 1
    return passed, fails


def main():
    selftest = '--selftest' in sys.argv[1:]
    if selftest:
        # 轮 1：把坏页面样本当成页面文本、好样本给控制器 ⇒ 必须红（证明检查真的会拦）
        passed, fails = run(BAD_SAMPLE, read(CTRL))
        hit = [f for f in fails if f.startswith('缺: j 角标') or f.startswith('缺: k 角标')
               or f.startswith('禁: m 长按') or f.startswith('禁: ⇆ 面板')]
        if len(hit) < 4:
            print('SELFTEST FAIL：键面侧检查失效，命中=%s' % hit)
            return 1
        # 轮 2：好页面 + 坏控制器（18:23 那次「ssdfg 全失灵」的原样：关着选择用零长度区间落位、
        # 四个入口各自再收拢一次）⇒ H-224/H-229 的「缺」与「禁」都要红
        p2, f2 = run(read(PAGE), BAD_CTRL_SAMPLE)
        hit2 = [f for f in f2 if 'H-224' in f or 'H-229' in f]
        if len(hit2) < 7:
            print('SELFTEST FAIL：H-229 零长度落位检查失效，命中=%s' % hit2)
            return 1
        # 轮 3：好控制器 + 坏页面（f/g 写成「页首/页尾」且 f 长按不做事）⇒ 四条 f/g 判据必须红
        p3, f3 = run(BAD_SAMPLE_FG, read(CTRL))
        hit3 = [f for f in f3 if f.startswith('缺: f ') or f.startswith('缺: g ')
                or f.startswith('缺: 长按 f') or f.startswith('缺: 长按 g')]
        if len(hit3) < 4:
            print('SELFTEST FAIL：H-226 f/g 检查失效，命中=%s' % hit3)
            return 1
        # 轮 4：H-228/H-231 各喂一个真实坏样本（图标退回 Shape+Path / 恒置 textedit /
        # 格子写死高度 / 面板缺「选择」格）。四条必须各自命中。
        p4, f4 = run(BAD_SAMPLE_H228, read(CTRL), read(PANELS))
        hit4 = [f for f in f4 if 'H-231' in f and 'H-231r2' not in f]
        p5, f5 = run(BAD_SAMPLE_TOGGLE, read(CTRL), read(PANELS))
        hit5 = [f for f in f5 if 'H-228 点光标图标不得恒置' in f]
        p6, f6 = run(read(PAGE), read(CTRL), BAD_PANELS_H228)
        hit6 = [f for f in f6 if 'H-228 full 网格不得写死' in f]
        p8, f8 = run(read(PAGE), read(CTRL), BAD_PANELS_NOSEL)
        hit8 = [f for f in f8 if '面板里有选择/取消格' in f]
        if not (hit4 and hit5 and hit6 and hit8):
            print('SELFTEST FAIL：H-228/H-231 检查失效，命中=%s/%s/%s/%s' % (hit4, hit5, hit6, hit8))
            return 1
        # 轮 5：好页面 + 坏控制器（H-230 旧写法：开选择直接 Math.min(selAnchor,pos) 起选）
        # ⇒ 三条 H-230 判据（先取 anchor / min(anchor) / max(anchor)）必须红，且
        #    那条「行级移动不得跨回旧 anchor」的禁令也必须红。
        p7, f7 = run(read(PAGE), BAD_CTRL_SAMPLE_H230)
        hit7 = [f for f in f7 if 'H-230' in f]
        if len(hit7) < 4:
            print('SELFTEST FAIL：H-230 行级跨行检查失效，命中=%s' % hit7)
            return 1
        # 轮 6：H-231r2——喂「修复前」的 cursor/clipboard 分支原样（点 ⇆ 不收展开网格、
        # 点 ▼ 展开也不关子面板）⇒ 三条互斥判据必须全报「缺」。
        p9, f9 = run(BAD_SAMPLE_H231R2, read(CTRL), read(PANELS))
        hit9 = [f for f in f9 if 'H-231r2' in f]
        if len(hit9) < 3:
            print('SELFTEST FAIL：H-231r2 展开网格互斥检查失效，命中=%s' % hit9)
            return 1
        # 轮 7：H-232——喂「修复前」的粘贴格（cellW/cellH）⇒ 两条禁令必须红、两条新判据必须报「缺」。
        p10, f10 = run(read(PAGE), read(CTRL), BAD_PANELS_H232)
        hit10 = [f for f in f10 if 'H-232' in f]
        if len(hit10) < 4:
            print('SELFTEST FAIL：H-232 粘贴格尺寸检查失效，命中=%s' % hit10)
            return 1
        # 轮 8：H-234/H-235/H-236（主人 2026-10-27 深夜真手回话的三件）——
        # ① 喂「修复前」的 full 面板（上页/下页 + 复制是图标格）⇒ 两条禁令红、三条判据报「缺」；
        # ② 喂「修复前」的状态声明（funcSubPanel 没有 @Watch）⇒ 禁令红、三条 H-234 判据报「缺」。
        p11, f11 = run(read(PAGE), read(CTRL), BAD_PANELS_H235_236)
        hit11 = [f for f in f11 if 'H-235' in f or 'H-236' in f]
        p12, f12 = run(BAD_PAGE_H234, read(CTRL), read(PANELS))
        hit12 = [f for f in f12 if 'H-234' in f]
        if len(hit11) < 5 or len(hit12) < 4:
            print('SELFTEST FAIL：H-234/235/236 检查失效，面板侧=%s 页面侧=%s' % (hit11, hit12))
            return 1
        # 轮 9：H-238（主人 01:0x 纠正后的真正对象＝顶栏 ⇆ 图标）——喂「修复前」的 FuncIcon
        # （按压反馈挂在框架按压样式态、无显式清态）⇒ 四条判据报「缺」+ 一条禁令报「禁」。
        p13, f13 = run(BAD_PAGE_H238, read(CTRL), read(PANELS))
        hit13 = [f for f in f13 if 'H-238' in f]
        if len(hit13) < 5:
            print('SELFTEST FAIL：H-238 顶栏图标按下态检查失效，命中=%s' % hit13)
            return 1
        # 轮 9b：喂**我自己 r1 那一版**（按下有色、选中无色）⇒ 三条 r2 判据必须报「缺」。
        # 这一轮是主人用眼睛抓出来的回归，守卫必须也能独立抓住它。
        p14, f14 = run(BAD_PAGE_H238_R1, read(CTRL), read(PANELS))
        hit14 = [f for f in f14 if 'H-238' in f]
        if len(hit14) < 3:
            print('SELFTEST FAIL：H-238r2 选中色检查失效（r1 坏样本没被拦下）：命中=%s' % hit14)
            return 1
        print('SELFTEST OK：已知错误样本被拦下（键面侧 %d 条 / H-224 侧 %d 条 / H-226 侧 %d 条'
              ' / H-228+H-231 侧 %d 条：图标%d 折叠%d 死高%d 缺选择%d / H-230 侧 %d 条'
              ' / H-231r2 侧 %d 条 / H-232 侧 %d 条 / H-234 侧 %d 条 / H-235+H-236 侧 %d 条'
              ' / H-238 侧 %d+%d 条）'
              % (len(hit), len(hit2), len(hit3),
                 len(hit4) + len(hit5) + len(hit6) + len(hit8),
                 len(hit4), len(hit5), len(hit6), len(hit8), len(hit7), len(hit9), len(hit10),
                 len(hit12), len(hit11), len(hit13), len(hit14)))
        return 0
    passed, fails = run(read(PAGE), read(CTRL))
    total = passed + len(fails)
    for f in fails:
        print('[FAIL] %s（H-220 口径被改动，先 git diff 再动手）' % f)
    print('H-220 键位守卫: %d/%d 通过' % (passed, total))
    if fails:
        return 1
    print('结论: j=上移 / k=下移 / m=删光标后(Del) / s=行首 / d=行尾 / n=选择 全部在位。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
