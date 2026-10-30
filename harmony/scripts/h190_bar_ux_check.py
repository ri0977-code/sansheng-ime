#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-188/H-189/H-190/H-192/H-199 候选栏交互闸门（Qoder，2026-10-26 11:2x）。

为什么写：这一轮几个改动全是**主人肉眼才看得见**的交互，离线套件里没有任何脚本能抓住回退：
  H-188 两个三角的中心必须和工具栏首/末枚图标同一条竖线（20vp / 94.4% 屏宽）；
  H-189 展开/收起要有过渡（barAlpha 淡出→换→淡入；网格展开 gridOpacity 淡入）；
  H-190 L1 只许显示 preedit，注释跟候选词同条目（安卓 CandidateItemUi 口径）；
  H-192 工具栏动作键不许自动收起（只有 ‹ / ▼ / ··· 才收起）；
  H-199 动画期间的去重必须读**目标态**、非动画调用必须**作废在途回调**
        （否则 80ms 内打字被吞，展开回调随后又把栏弹开 = 打字盖候选）。
`h165_bar_height_check.py` 只管高度预算，这些它一条都看不见——所以单独落一个静态闸门，
并给每个判据做负控：把源码改回旧写法，**必须变红**，否则本闸门无效。

用法：
    python scripts/h190_bar_ux_check.py             # 全绿 exit 0
    python scripts/h190_bar_ux_check.py --selftest   # 22 个负控必须全部变红（少一个＝锚点漂了，闸门白跑）
"""
import argparse
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "entry", "src", "main", "ets", "pages", "KeyboardIndex.ets")
CTRL = os.path.join(ROOT, "entry", "src", "main", "ets", "inputmethod", "KeyboardController.ets")
SCREEN_W = 360.0     # 设计基准屏宽（vp）；与 H-179 的 5.5% / 94.4% 口径一致


def extract_body(text, marker):
    i = text.index(marker)
    j = text.index("{", i)
    depth = 0
    for k in range(j, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return text[j + 1:k]
    raise SystemExit("括号不配平：%s" % marker)


def const_num(text, name):
    m = re.search(r"^const\s+%s\s*:\s*number\s*=\s*([0-9.]+)\s*;" % re.escape(name), text, re.M)
    if not m:
        raise SystemExit("找不到常量 %s" % name)
    return float(m.group(1))


def case_body(func_body, name):
    """取 switch 里某个 case 的 body。

    坑（2026-10-26 假红）：ArkTS 里相邻的 `case 'back':` / `case 'more':` 常共用同一段 body，
    所以不能取到「下一个 case 标签」为止——必须先跳过紧随其后的连续 case 标签，
    否则 back 会拿到空 body，误报「没收起」。
    """
    m = re.search(r"case\s+'%s'\s*:" % re.escape(name), func_body)
    if not m:
        return None
    rest = func_body[m.end():]
    while True:
        n = re.match(r"\s*case\s+'[^']+'\s*:", rest)
        if not n:
            break
        rest = rest[n.end():]
    n = re.search(r"\n\s*(case\s+'|default\s*:)", rest)
    return rest[:n.start()] if n else rest


def check(text):
    """返回 [(项, 是否通过, 说明)]。"""
    out = []
    body = extract_body(text, "CandidateBar() {")

    # ---- H-190：L1 只放 preedit；注释跟候选词同条目 ----
    # 判据必须锚到「整宽 L1」本身：横屏时 L2 行左侧也有一处 Text(this.preedit)（无 width 100%），
    # 只匹配 fontSize(12) 会被它顶替，负控造了坏样本仍全绿（2026-10-26 selftest 抓到的假绿）。
    l1_ok = re.search(
        r"Text\(this\.preedit\)\s*\n\s*\.fontSize\(12\)\s*\n\s*\.fontColor\(FG_HINT\)"
        r"\s*\n\s*\.maxLines\(1\)\s*\n\s*\.textOverflow\(\{ overflow: TextOverflow\.Ellipsis \}\)"
        r"\s*\n\s*\.width\('100%'\)",
        body) is not None
    out.append(("H-190 L1 只显示 preedit", l1_ok,
                "L1 的 Text(...) 必须正好是 this.preedit（候选注释不许混进字母行）"))
    out.append(("H-190 commentLine 已移除", "commentLine" not in text,
                "旧的「preedit · comment」整行方法必须删干净，防止有人再接回去"))
    out.append(("H-190 注释在候选条目内", body.count("this.candCommentText(cand)") >= 2,
                "L2 每条候选要有 candCommentText(cand)（估宽 + 渲染各一处）"))

    # ---- H-188：三角与工具栏首末枚同竖线 + 按下反馈 ----
    pad = const_num(text, "CAND_PAD_H")
    tri_left = const_num(text, "FUNC_TRI_LEFT_W")
    tri_w = const_num(text, "FUNC_TRI_WIDTH")
    m = re.search(r"\.padding\(\{ left: (\d+), right: (\d+), top: 2, bottom: 2 \}\)", body)
    tb_l, tb_r = (int(m.group(1)), int(m.group(2))) if m else (-1, -1)
    m2 = re.search(r"\.padding\(\{ left: CAND_PAD_H, right: (\d+) \}\)", body)
    row_r = int(m2.group(1)) if m2 else -1
    left_c = pad + tri_left / 2.0
    first_c = tb_l + tri_w / 2.0
    right_c = SCREEN_W - (row_r + tri_w / 2.0)
    last_c = SCREEN_W - (tb_r + tri_w / 2.0)
    out.append(("H-188 左 › 与工具栏 ‹ 同竖线", abs(left_c - first_c) < 0.01,
                "收起态 › 中心 %.1fvp ≠ 展开态 ‹ 中心 %.1fvp（差 %.1f）" %
                (left_c, first_c, left_c - first_c)))
    out.append(("H-188 右 ▼ 与工具栏 ▼ 同竖线", row_r == tb_r and abs(right_c - last_c) < 0.01,
                "候选行右内边距 %s / 工具栏右内边距 %s；右 ▼ 中心 %.1fvp ≠ %.1fvp" %
                (row_r, tb_r, right_c, last_c)))
    # H-201（主人 13:2x「三角给加了灰底，干吗？」）：三角**不许**有按压灰底——
    # 安卓实物无底色。判据从「必须有 pressed」反转为「必须没有」，负控也跟着反。
    out.append(("H-201 三角无按压灰底", body.count("stateStyles({ pressed: funcIconPressed })") == 0,
                "三角上发现 stateStyles 按压灰底——主人点名撤掉（安卓实物无底色，别加戏）"))

    # ---- H-189：展开/收起有过渡 ----
    out.append(("H-189 栏内容有 barAlpha 过渡", body.count(".opacity(this.barAlpha)") >= 3,
                "工具栏行 / L1 / L2 都要绑 barAlpha（淡出→换→淡入）"))
    try:
        setbar = extract_body(text, "private setFuncBar(open: boolean")
        trans_ok = ("animateTo" in setbar) and ("onFinish" in setbar) and ("this.barAlpha = 0" in setbar)
    except ValueError:
        setbar = ""
        trans_ok = False
    out.append(("H-189 setFuncBar 先淡出再换内容", trans_ok,
                "setFuncBar 必须 animateTo + onFinish：淡到 0 → 换 showFuncBar → 淡回 1"))
    try:
        setexp = extract_body(text, "private setExpanded(expanded: boolean)")
        grid_ok = ("gridOpacity = 0" in setexp) and ("animateTo" in setexp)
    except ValueError:
        grid_ok = False
    out.append(("H-189 网格展开有淡入", grid_ok,
                "setExpanded(true) 要 gridOpacity=0 + animateTo 淡入（H-168 同一通道）"))

    # ---- H-199：动画期间去重读目标态、非动画调用作废在途回调（CodeArts M-223 C①）----
    out.append(("H-199 target/gen 字段已声明",
                re.search(r"private\s+funcBarTarget\s*:\s*boolean\s*=", text) is not None and
                re.search(r"private\s+funcBarGen\s*:\s*number\s*=", text) is not None,
                "funcBarTarget / funcBarGen 缺一个就编译不过"))
    guard_ok = re.search(r"if\s*\(this\.funcBarTarget\s*===\s*open\)\s*\{\s*\n\s*return;",
                         setbar) is not None
    out.append(("H-199 去重读目标态不读旧值", guard_ok,
                "去重必须用 funcBarTarget；读 showFuncBar 会在展开动画的 80ms 内吞掉「打字即收起」"))
    fast = re.search(r"if\s*\(!animated\)\s*\{([\s\S]*?)\n {4}\}", setbar) if trans_ok else None
    fast_body = fast.group(1) if fast else ""
    p_gen = fast_body.find("funcBarGen++")
    p_show = fast_body.find("this.showFuncBar = open")
    order_ok = p_gen != -1 and p_show != -1 and p_gen < p_show
    out.append(("H-199 快路径先作废再改状态", order_ok,
                "!animated 分支必须先 ++funcBarGen 作废在途回调，再写 showFuncBar/barAlpha"))
    fin = re.search(r"onFinish:\s*\(\)\s*=>\s*\{([\s\S]*?)\n {4}\}", setbar) if trans_ok else None
    fin_body = fin.group(1) if fin else ""
    stale_ok = "gen !== this.funcBarGen" in fin_body and "return" in fin_body
    out.append(("H-199 过期回调自我作废", stale_ok,
                "onFinish 里必须先比代次，过期就 return，不许再套第二段动画把栏弹开"))

    # ---- H-192/H-184：动作键不收起；‹ 收起；`···` 是开关菜单（H-184 主人拍板「照安卓抄」）----
    fn = extract_body(text, "private onFuncIcon(action: string)")
    for act in ("undo", "redo", "cursor", "clipboard"):
        cb = case_body(fn, act)
        ok = cb is not None and "setFuncBar(" not in cb
        out.append(("H-192 %s 不自动收起" % act, ok,
                    "case '%s' 里发现 setFuncBar(——主人要求「操作还没完成，改成手动折叠」" % act))
    cb = case_body(fn, "back")
    ok = cb is not None and "setFuncBar(false)" in cb
    out.append(("H-192 back 仍然收起", ok,
                "case 'back'（‹）语义就是收起，必须保留 setFuncBar(false)"))
    cb = case_body(fn, "more")
    ok = cb is not None and "funcMenuOpen" in cb and "setFuncBar(" not in cb
    out.append(("H-184 more 打开开关菜单不收起", ok,
                "case 'more'（···）必须切 funcMenuOpen（安卓式弹层），不许只是收起——"
                "主人骂过「点开都是空的」"))

    # ---- H-201：展开钮只在空闲态显示（照安卓 ExpandButtonStateMachine）----
    out.append(("H-201 › 只在空闲态渲染",
                re.search(r"if \((this\.candidates\.length === 0 && this\.preedit\.length === 0)\) \{", body) is not None,
                "出候选后左上角 › 必须消失（安卓口径），否则挡候选——主人 13:2x 点名"))
    # ---- H-201/H-202/H-258：展开候选面板（ExpandedPanel）----
    # 口径换档 2026-10-28（Qoder 04:0x，接主人 14:0x 真手定稿的 H-258）：展开面板从
    # 「Grid 双列×3 行整屏硬翻」改成「List 单列左对齐连续滚动（EdgeEffect.Spring）＋
    # 上/下一页 scrollToIndex 步进」。主人原话：「滑动改成丝滑的那种」「双列不好看长注释
    # 会相互影响，改成单列」「居中显示不好看，改成左对齐」。
    # 原 H-201/H-202 的语义判据**照旧有效**（词＋右侧注释同一条、只截注释、剥掉编码段），
    # 只是锚点从 Grid 条目挪到 List 条目；「双列 / 3 行 / rowsTemplate」三条是排版口径，
    # 被主人新口径顶掉 ⇒ 换成「单列 / 左对齐 / Spring 连续滚动 / 翻页保留」四条。
    try:
        exp = extract_body(text, "ExpandedPanel() {")
    except ValueError:
        exp = ""
    out.append(("H-201 网格注释跟词右",
                "Row({ space: 4 })" in exp and
                not re.search(r"Text\(cand\.comment\)[\s\S]{0,200}Text\(cand\.text\)", exp),
                "展开条目必须是「词＋右侧灰小字注释」（安卓 CandidateItemUi），不许「码上词下」"))
    # H-202 真机返工（2026-10-26 19:3x）：注释文本改走 candCommentText()（剥掉 `[编码]` 段，
    # 只留拼音），所以判据不能只认字面量 `Text(cand.comment)`——否则我改了实现、判据还停在旧写法，
    # 就会红成「没实现」。两种写法都认，但**必须**仍然是「词 flexShrink(0) + 注释 layoutWeight(1)」。
    item_ok = ("Row({ space: 4 })" in exp
               and re.search(r"Text\(cand\.text\)[\s\S]{0,400}\.flexShrink\(0\)", exp) is not None
               and re.search(r"Text\((?:cand\.comment|this\.candCommentText\(cand\))\)"
                             r"[\s\S]{0,900}\.layoutWeight\(1\)", exp) is not None)
    out.append(("H-202 注释单独截断", item_ok,
                "展开条目：词 flexShrink(0)（不许被截），注释 layoutWeight(1)（要截只截注释）"))
    # 新判据：注释文本必须先剥掉 `[编码]` 段再显示（否则一格放不下必然 `…`，真机 a2_grid 已见）
    out.append(("H-202 注释剥掉编码段",
                re.search(r"candCommentText\(cand: RimeCandidate\)[\s\S]{0,900}match\(", text) is not None,
                "candCommentText 要剥掉行首 `[...]` 编码段（引擎 comment 是 `[fwaj] guihua` 两段，"
                "一格放不下 ⇒ 拼音被 … 截断，主人原话「注释显示不全」）"))
    # ---- H-258（主人 2026-10-28 定稿；CodeArts 落地；这里锁死口径防回退）----
    try:
        cols_body = extract_body(text, "private gridCols(): number {")
    except ValueError:
        cols_body = ""
    out.append(("H-258 展开单列", "return 1;" in cols_body,
                "gridCols() 必须恒 1（主人「双列长注释互相影响，改成单列」；回双列/四列＝红）"))
    out.append(("H-258 单列左对齐", ".justifyContent(FlexAlign.Start)" in exp,
                "条目行左对齐（主人「居中显示不好看，改成左对齐吧」，顶格与编码行同轴）"))
    out.append(("H-258 丝滑连续滚动", "List({ scroller: this.expandedListScroller" in exp
                and ".edgeEffect(EdgeEffect.Spring)" in exp
                and "Grid() {" not in exp,
                "展开面板＝List 连续滚动＋EdgeEffect.Spring（主人「滑动改成丝滑的那种」），回 Grid 硬翻＝红"))
    out.append(("H-258 翻页按钮保留", exp.count("expandedListScroller.scrollToIndex") >= 2,
                "上/下一页保留且走 scrollToIndex 步进（主人只点了滑动要丝滑，没让删按钮）"))

    # ---- H-203（主人 2026-10-26「不输入时顶栏太宽，安卓窄，打字时字母上去一行」）----
    try:
        idle_body = extract_body(text, "private barIdle(): boolean {")
    except ValueError:
        idle_body = ""
    out.append(("H-203 空闲态判据含 preedit/候选/工具栏",
                all(k in idle_body for k in ("this.showFuncBar", "this.candidates.length === 0",
                                             "this.preedit.length === 0")),
                "barIdle 必须＝无工具栏、无候选、无 preedit（照安卓 ExpandButtonStateMachine 的 Idle）"))
    try:
        barh_body = extract_body(text, "private candBarHeight(): number {")
    except ValueError:
        barh_body = ""
    # H-208（主人 2026-10-26 20:5x「怎么出候选键盘还往上跳上来，打完字又跳下去呢？哪个输入法
    # 键盘不是稳定的啊，一蹦一跳的像什么话」）：判据**反转**。
    # 旧口径要求「空闲 candBarHeight 返回 28、窗口跟着缩」——那正是键盘蹦跳的根因，已被主人否。
    # 新口径：栏容器恒 44vp（窗口不动），空闲时内容靠下（justifyContent FlexAlign.End）。
    out.append(("H-208 栏容器恒 44vp（窗口不跳）",
                re.search(r"if\s*\(this\.barIdle\(\)\)\s*\{\s*\n\s*return this\.candRowHeight\(\);", barh_body)
                is None and "return Math.max(this.barHeight" in barh_body,
                "candBarHeight 不许再因空闲缩成 candRowHeight()——栏高变化会让整块键盘上下跳"
                "（主人 2026-10-26 20:5x 点名的大问题）；空闲观感改在栏内靠下画"))
    # H-208「空闲靠下」判据已被 H-212 取代（贴顶 + 占位补白）
    out.append(("H-212 栏内容贴顶（非居中）",
                "justifyContent(FlexAlign.Start)" in text,
                "栏容器必须 FlexAlign.Start（L1/候选贴顶）；Center 会把候选行推到栏中间（主人骂的「分家」）"))
    out.append(("H-212 空闲态补 16vp 占位",
                re.search(r"Row\(\)\.height\(this\.commentRowHeight\(\)\)", text) is not None,
                "空闲态要在 L2 上方补一行 16vp 占位（Row().height(commentRowHeight())），让候选贴键区上沿（窄条）"))
    out.append(("H-208/H-213 菜单浮层在顶层 Stack（不被栏裁）",
                re.search(r"if \(this\.funcMenuOpen\).*?this\.FuncMenu\(\)", text, re.DOTALL) is not None and
                "position({ x: '36%', y: -" not in text,
                "H-213：FuncMenu 已移至 build() 顶层 Stack（与 LangMenu/LayoutMenu 并列），原负 y 定位已移除；"
                "不再被 CandidateBar 44vp 裁切"))
    out.append(("H-203 无 preedit 不渲染 L1",
                # H-241(Qoder 2026-10-28 03:2x) 更正：这一支的条件多了 `&& this.preeditShown`
                # （契约 §3-12「显示编码行」开关，关掉时改画同高空行）。**语义没变**——
                # 仍然是「preedit 为空就不画 L1」，只是判据跟着代码字面走（M-247 立的规矩：
                # 口径变了要连 checker 的提示语一起改，不然下一个人会以为代码回退了）。
                re.search(r"if \(this\.barHeight >= 40 && !this\.showFuncBar && this\.panelMode !== 'symbol' &&\s+this\.preedit\.length > 0 && this\.preeditShown\) \{",
                          body) is not None,
                "L1 行必须在 preedit 为空时不渲染（H-241 后＝`preedit.length > 0 && preeditShown`），否则空闲态仍被空字母行撑高 16vp"))

    # ---- H-203 续改（Qoder 2026-10-26）：栏画窄 ≠ 窗口变窄 ----
    # 第一版只在 candBarHeight() 里收窄、再补一块同高留白把键区按住，结果窗口高度一点没变，
    # 16vp 空白原样留在屏幕上——主人要的「不输入时窄 / 打字时字母上去一行」一条都没发生。
    # 判据：① UI 有把实际栏高报给控制器的入口；② 状态推送末尾真的调它；③ 不许再留补高块。
    # H-228(Qoder 2026-10-27 17:5x)：判据跟着代码口径走——符号页「增大显示空间」已改由
    # CandidateBar 容器 `.height(0)` 实现（`applyBarHeightVp(0)` 是空操作，被 `barVp > 0` 闸门吞掉，
    # CodeArts M-262 指出、我按根布局复核确认）。所以这里只要求**入口把 candBarHeight() 报上去**，
    # 不再要求写死符号页传 0（那条既无效又会被下一个人当成必须）。
    out.append(("H-203 栏高同步入口存在",
                re.search(r"private syncPanelBarHeight\(\): void \{[^}]*?"
                          r"keyboardController\.applyBarHeightVp\(this\.candBarHeight\(\)\);", text, re.S) is not None,
                "syncPanelBarHeight 必须把 candBarHeight() 报给 keyboardController.applyBarHeightVp()"
                "（符号页省空间走 CandidateBar 容器 height(0)，不走这条）"))
    try:
        li = text.index("keyboardController.setUiListener((s: KeyboardState) => {")
        lj = text.index("\n    });", li)
        listener = text[li:lj]
    except ValueError:
        listener = ""
    out.append(("H-203 状态推送末尾同步窗口", "this.syncPanelBarHeight();" in listener,
                "setUiListener 回调末尾必须 syncPanelBarHeight()——否则打字出候选后窗口不长，"
                "键区也不会「上去一行」"))
    out.append(("H-203 不留补高块", "this.barIdle() && this.barHeight >= 40" not in text,
                "build() 里不许再补 commentRowHeight() 留白——它会把窗口撑回 44vp，栏白收窄"))

    # ---- H-206（Qoder 2026-10-26 真机，主人「退格下滑会多恢复一遍」）----
    # 真机日志链：16:22:52.863 `bs_row longpress: clearAllContent`（删 120 字）→
    # 16:22:54.562 `bs_row swipe down: undoLastAction dy=83.7`（restore 120 字）。
    # 也就是下滑撤销先把自己刚做的清空撤销了，用户真正想撤的那次被吃掉。
    # 两道防线都必须钉住：① 滑动一开始就撤掉长按定时器；② 万一已经清了，手势动作前先还原。
    out.append(("H-206 本次按下是否已触发清空要记账",
                re.search(r"private bsClearAllFired: boolean = false;", text) is not None
                and text.count("this.bsClearAllFired = false;") >= 2,
                "字段要有，而且 Down 每次按下要重新记账（=false 至少出现两次：字段/Down + heal 内）"))
    rep = ""
    try:
        rep = extract_body(text, "private startBackspaceRepeat(): void {")
    except ValueError:
        pass
    out.append(("H-206 长按清空时置位标记",
                "this.bsClearAllFired = true;" in rep
                and rep.index("this.bsClearAllFired = true;") < rep.index("clearAllContent("),
                "定时器里必须**先置位再** clearAllContent()，否则手势无从知道自己刚清过"))
    out.append(("H-206 滑动一开始就撤掉长按定时器",
                re.search(r"if \(moved > 20 && this\.bsDelay >= 0\) \{\s*\n\s*clearTimeout\(this\.bsDelay\);",
                          text) is not None,
                "移动超过 20vp 就必须 clearTimeout(bsDelay)——不然滑到一半 500ms 长按先把内容清了"))
    out.append(("H-206 两个滑动手势都先还原",
                text.count("this.healAccidentalClearAll();") >= 2,
                "上滑清除与下滑撤销都要先 healAccidentalClearAll()，缺一个就还是「多恢复一遍」"))

    # ---- H-207（Qoder 2026-10-26 真机，主人「v 粘不上有提示了，点多少次也粘不上」）----
    # 真机日志 `AceSecurityComponent: security component has not registered` ×20+ ⇒ 安全控件
    # 从未注册 ⇒ 永远拿不到临时授权。官方错误码 2 的第 5/7/10 条（被遮挡、超出窗口、
    # 「父组件属性设置不当导致显示不完整」）都指向父节点：所以剪贴板这一支不许带 opacity 动画，
    # 也不许有上下 padding（展开动画期间 barAlpha=0，安全控件正是在那一帧挂载的）。
    clip_branch = ""
    try:
        ci = text.index("if (this.funcSubPanel === 'clipboard') {")
        cj = text.index("\n        } else {", ci)
        clip_branch = text[ci:cj]
    except ValueError:
        pass
    out.append(("H-207 剪贴板分支存在", clip_branch != "",
                "找不到 clipboard 子面板分支（`funcSubPanel === 'clipboard'`）"))
    out.append(("H-207 剪贴板分支不带 opacity", ".opacity(" not in clip_branch,
                "父节点带 `.opacity()` 会让安全控件在 alpha<1 的那帧注册失败（H-207 真机）"))
    out.append(("H-207 剪贴板分支不带上下 padding",
                re.search(r"\.padding\(\{[^}]*\b(top|bottom):", clip_branch) is None,
                "上下 padding 会从 44vp 预算里吃掉按钮高度；默认胶囊按钮约 40vp，吃掉就判「显示不完整」"))

    # ---- H-215（CodeArts M-251 ④：符号页顶栏换工具栏，增大符号区）----
    out.append(("H-215 符号页 CandidateBar 高度为0",
                re.search(r"this\.panelMode === 'symbol' \? 0 : this\.candBarHeight\(\)", text) is not None,
                "符号页时候选栏容器高度必须为0（标签行是顶栏，照安卓），省44vp给符号区"))
    out.append(("H-215 SymbolPanel 标签行存在",
                text.count("SYMBOL_CATEGORIES") >= 2,
                "SymbolPanel 必须保留分类标签行（SYMBOL_CATEGORIES 在常量定义+ForEach处各出现一次）"))
    out.append(("H-215 symbolRowItems 支持 row=4（7+6+6分配）",
                re.search(r"row === 3\).*?slice\(start \+ 7, start \+ 13\)", text, re.S) is not None
                and re.search(r"slice\(start \+ 13, start \+ 19\)", text) is not None,
                "symbolRowItems 必须支持 row=2/3/4 三行分配（7+6+6=19）"))
    out.append(("H-215 ListItem 有第4行符号行(sr4)",
                "sr4_" in text,
                "SymbolPanel ListItem 必须有第4行符号行（sr4_ 标识）"))
    out.append(("H-215 L1 候选行符号页不渲染",
                re.search(r"!this\.showFuncBar && this\.panelMode !== 'symbol' &&\s+this\.preedit\.length > 0", text, re.S) is not None,
                "L1 候选行条件必须含 `panelMode !== 'symbol'`，符号页时不渲染候选行"))
    out.append(("H-215 L2 候选行符号页不渲染",
                re.search(r"this\.showFuncBar \|\| this\.panelMode === 'symbol' \? Visibility\.None", text) is not None,
                "L2 候选行 visibility 必须含 `panelMode === 'symbol'`，符号页时不渲染候选行"))
    out.append(("H-215 onFuncIcon back 符号页回字母页",
                re.search(r"case 'back':[\s\S]{0,500}panelMode === 'symbol'[\s\S]{0,100}switchPanelMode\('qwerty'\)", text) is not None,
                "onFuncIcon back 分支在符号页时必须回字母页（switchPanelMode('qwerty')）"))

    # ---- H-215 ③：字母键下滑出大写（代码已在，验证存在）----
    out.append(("H-215 ③ 字母键下滑出大写代码存在",
                re.search(r"typeChar\(ch\.toUpperCase\(\)\)", text) is not None,
                "LetterKey onTouch 中必须有下滑出大写代码（typeChar(ch.toUpperCase())）"))
    return out


def check_ctrl(ctrl):
    """H-208（主人 2026-10-26 20:5x）：面板窗口高度**必须恒定**，不再跟 UI 栏高走。
    旧判据（H-203）要求 liveBarVp 取 uiBarVp——那正是键盘蹦跳的根因，已反转。"""
    out = []
    out.append(("H-208 控制器窗口高度恒定（不跟 UI 栏高）",
                re.search(r"const liveBarVp: number = barVp;", ctrl) is not None
                and "liveBarVp + rowVp * ROW_COUNT" in ctrl,
                "computePanelSize 的 liveBarVp 必须直接取方向预算 barVp（窗口恒定）；"
                "取 this.uiBarVp 就会随候选出没上下跳（主人骂的「一蹦一跳」）"))
    try:
        body = extract_body(ctrl, "applyBarHeightVp(barVp: number): void {")
    except ValueError:
        body = ""
    out.append(("H-203 控制器栏高同步入口",
                "this.uiBarVp = barVp" in body and "this.applyPanelSize()" in body,
                "applyBarHeightVp 必须记下 uiBarVp 并触发 applyPanelSize()，否则 resize 不会被调用"))
    out.append(("H-203 建面板后按首帧栏高定尺寸",
                re.search(r"await p\.setUiContent\(PANEL_PAGE\);[\s\S]{0,800}"
                          r"const live: PanelSize = this\.computePanelSize\(\);", ctrl) is not None,
                "setUiContent 之后要重算尺寸再 resize——面板页 aboutToAppear 刚报回空闲 28vp，"
                "用挂载前的 44vp 会把窗口撑回去"))

    # ---- H-205（Qoder 2026-10-26 真机，主人「你把顶栏输入和候选弄成一行了」）----
    # H-203 把**实时**栏高（空闲 28vp）当 `state.barHeight` 推回 UI，而 UI 里 `barHeight < 40`
    # 是 H-096 的**横屏判据** ⇒ 竖屏永久落进横屏分支：L1 与候选并排一行，
    # 且 candBarHeight()=max(24, 28-6)=24 再报回去形成反馈环，打字也回不到 44vp、窗口不长一行。
    # 结论：**窗口尺寸用实时值，UI 布局依据用方向预算（竖/横都 44vp）**，两者必须分开。
    out.append(("H-205 推给 UI 的 barHeight 是方向预算",
                re.search(r"barHeight:\s*this\.defaultBarVp", ctrl) is not None
                and re.search(r"barHeight:\s*this\.barVp", ctrl) is None,
                "notify() 必须送 this.defaultBarVp（44vp 预算）——送实时栏高会让竖屏落进 "
                "barHeight<40 的横屏分支（L1 并进候选行 + 反馈环把栏高压死）"))
    out.append(("H-205 PanelSize 带预算字段",
                re.search(r"struct PanelSize|interface PanelSize", ctrl) is not None
                and re.search(r"^\s*defaultBarVp: number;", ctrl, re.M) is not None
                and re.search(r"defaultBarVp:\s*barVp\s*$|defaultBarVp:\s*barVp\s*\n\s*\}", ctrl) is not None,
                "computePanelSize 要同时返回实时 barVp 与预算 defaultBarVp（=方向 barVp），缺一不可"))
    out.append(("H-205 预算随面板创建/刷新落地",
                ctrl.count("this.defaultBarVp = ") >= 3,
                "applyPanelSize 与 createPanel（size 与 setUiContent 后的 live）三处都要写回 "
                "this.defaultBarVp，否则横竖切换后 UI 拿到的还是旧方向预算"))
    return out


def report(items):
    bad = [x for x in items if not x[1]]
    for name, ok, hint in items:
        print("  [%s] %s%s" % ("绿" if ok else "红", name, "" if ok else "  —— " + hint))
    return bad


def selftest(text, ctrl):
    """每个负控都必须让至少一项变红，否则闸门无效。

    先验基线：基线本身不干净的话，「变红」可能来自旧红项，负控就白跑了。
    条目格式：(说明, 'ui'|'ctrl', 旧串, 新串) —— 'ctrl' 改的是 KeyboardController.ets。
    """
    base_bad = [x for x in (check(text) + check_ctrl(ctrl)) if not x[1]]
    if base_bad:
        print("SELFTEST FAIL: 基线本身有 %d 项红（%s），负控判据不干净" %
              (len(base_bad), "、".join(x[0] for x in base_bad)))
        return 1
    bads = [
        ("L1 混入候选注释", "ui", "Text(this.preedit)\n          .fontSize(12)",
         "Text(this.preedit + this.candCommentText(this.candidates[0]))\n          .fontSize(12)"),
        ("左 › 退回 36vp", "ui", "const FUNC_TRI_LEFT_W: number = 24;",
         "const FUNC_TRI_LEFT_W: number = 36;"),
        ("右 ▼ 退回 8vp 内边距", "ui", ".padding({ left: CAND_PAD_H, right: 2 })",
         ".padding({ left: CAND_PAD_H, right: 8 })"),
        ("undo 恢复自动收起", "ui", "      case 'undo':\n        keyboardController.undoCommit();\n        break;",
         "      case 'undo':\n        keyboardController.undoCommit();\n        this.setFuncBar(false);\n        break;"),
        ("setFuncBar 去掉 onFinish", "ui", "duration: 80, curve: Curve.EaseIn, onFinish: () => {",
         "duration: 80, curve: Curve.EaseIn, onEnd: () => {"),
        # H-199 三控：每一控对应主人骂过的那个现象（打字后工具栏自己弹开）
        ("H-199 去重退回读 showFuncBar", "ui", "if (this.funcBarTarget === open) {",
         "if (this.showFuncBar === open) {"),
        ("H-199 快路径不作废在途回调", "ui",
         "      this.funcBarGen++;             // 作废所有在途动画回调（打字不能被 80ms 前的展开回调覆盖）\n",
         ""),
        ("H-199 onFinish 不比代次", "ui",
         "      if (gen !== this.funcBarGen) {\n        return;                      // 已被打字/收起作废\n      }\n",
         ""),
        # H-201 三控：对应主人 13:2x 骂的三个点
        ("H-201 三角加回灰底", "ui",
         "          .rotate({ angle: 90 })\n          .width(FUNC_TRI_LEFT_W)",
         "          .rotate({ angle: 90 })\n          .stateStyles({ pressed: funcIconPressed })\n          .width(FUNC_TRI_LEFT_W)"),
        ("H-201 › 常驻不随空闲消失", "ui",
         "        if (this.candidates.length === 0 && this.preedit.length === 0) {",
         "        if (true) {"),
        ("H-184 more 退回收起", "ui",
         "        this.funcSubPanel = '';\n        this.funcMenuOpen = !this.funcMenuOpen;\n",
         "        this.funcSubPanel = '';\n        this.setFuncBar(false);\n"),
        # H-202/H-203 四控：对应主人 2026-10-26 第二条口信
        # 两控随 H-258 换锚（Qoder 2026-10-28 04:0x）：旧锚「return w >= 300 ? 2 : 1」与
        # 「gridRows return 3」都在主人 10-28 定稿（单列左对齐＋List 连续滚动）里退休了，
        # 命中 0 次＝负控白跑。现在盯的是**新口径**的回退形态：退回双列、退回居中。
        ("H-258 展开退回双列", "ui",
         "  private gridCols(): number {\n    // H-257(CodeArts): 单列居中——主人原话「改成单列居中吧」\n    return 1;",
         "  private gridCols(): number {\n    return 2;"),
        ("H-258 单列退回居中", "ui",
         "            .alignItems(VerticalAlign.Center)\n            .justifyContent(FlexAlign.Start)",
         "            .alignItems(VerticalAlign.Center)\n            .justifyContent(FlexAlign.Center)"),
        # H-203 两控退休（Qoder 2026-10-28 03:2x，自测连续报「锚点命中 0 次」＝这两控早已没跑）：
        #   · 「空闲态退回整栏」锚的是 `candBarHeight()` 空闲返回 28vp 那一版；
        #   · 「控制器忽略 UI 栏高」锚的是 `liveBarVp = uiBarVp …` 那一版。
        # 二者都被**主人 2026-10-26 20:5x 拍板**＋**H-208**顶掉了：窗口高度固定＝预算栏高＋4 行键，
        # 空闲「窄条」只在栏**内部**靠下画一行（`candBarHeight()` 恒 ≥ 行高和，控制器里就是
        # `const liveBarVp: number = barVp;`）。留着＝闸门自测永远红三条，真回退反而看不见。
        # 现在盯住的是活口径：`H-212 空闲态补 16vp 占位` ＋ `H-203 不留补高块`。
        ("H-203 L1 退回常驻", "ui",
         # H-241(Qoder 2026-10-28 03:2x)：条件里多了 `&& this.preeditShown`（契约 §3-12），
         # 锚点跟着改成**同一行**的字面——旧锚跨两行，count 掉到 0，负控等于没跑。
         "\n        this.preedit.length > 0 && this.preeditShown) {",
         "\n        this.preedit.length > 0) {"),
        ("H-203 删掉状态推送里的同步", "ui",
         "      this.syncPanelBarHeight();\n    });",
         "    });"),
        ("H-203 补高块回潮", "ui",
         "          this.CandidateBar()\n",
         "          this.CandidateBar()\n"
         "          if (this.barIdle() && this.barHeight >= 40) {\n"
         "            Row()\n"
         "              .height(this.commentRowHeight())\n"
         "          }\n"),
        # H-205/206/207 六控：对应主人 2026-10-26 16:5x 第三条口信（实测三条）
        ("H-205 把实时栏高推回 UI（顶栏与候选挤成一行）", "ctrl",
         "barHeight: this.defaultBarVp",
         "barHeight: this.barVp"),
        ("H-205 横竖切换后预算不刷新", "ctrl",
         "      this.defaultBarVp = live.defaultBarVp;\n",
         ""),
        ("H-206 长按清空不记账（下滑多恢复一遍）", "ui",
         "      this.bsClearAllFired = true;      // H-206：记下「这次清空发生在本次按下里」，供手势前还原\n",
         ""),
        ("H-206 滑动中不撤长按定时器", "ui",
         "              if (moved > 20 && this.bsDelay >= 0) {",
         "              if (moved > 500 && this.bsDelay >= 0) {"),
        ("H-206 下滑手势前不还原", "ui",
         "              this.healAccidentalClearAll();   // H-206：不先还原就会「多恢复一遍」\n",
         ""),
        ("H-207 剪贴板分支带回 opacity/padding", "ui",
         "          .padding({ left: 2, right: 2 })\n",
         "          .padding({ left: 2, right: 2, top: 2, bottom: 2 })\n          .opacity(this.barAlpha)\n"),
    ]
    fails = 0
    for name, target, old, new in bads:
        src = text if target == "ui" else ctrl
        if src.count(old) != 1:
            print("SELFTEST FAIL: 负控「%s」锚点命中 %d 次（应为 1），坏样本没造出来" %
                  (name, src.count(old)))
            fails += 1
            continue
        patched = src.replace(old, new, 1)
        items = (check(patched) + check_ctrl(ctrl)) if target == "ui" \
            else (check(text) + check_ctrl(patched))
        bad = [x for x in items if not x[1]]
        if bad:
            print("SELFTEST OK: 负控「%s」变红 %d 项（%s）" %
                  (name, len(bad), "、".join(x[0] for x in bad)))
        else:
            print("SELFTEST FAIL: 负控「%s」仍全绿 = 闸门无效" % name)
            fails += 1
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    text = open(SRC, encoding="utf-8").read()
    ctrl = open(CTRL, encoding="utf-8").read()
    if args.selftest:
        return 1 if selftest(text, ctrl) else 0
    bad = report(check(text) + check_ctrl(ctrl))
    if bad:
        print("\nFAIL: %d 项不满足（见上）" % len(bad))
        return 1
    print("\nPASS: H-188 三角对齐 / H-189 展开过渡 / H-190 字母行干净 / H-192 手动折叠 / "
          "H-199 动画去重 / H-202 词注同条只截注释 / H-258 展开单列左对齐连续滚动 / H-203 空闲栏窄且窗口跟缩 全部满足")
    return 0


if __name__ == "__main__":
    sys.exit(main())
