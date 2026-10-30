#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-194 / M-221-B 组件契约闸门（Qoder，2026-10-26 11:4x；H-204 改口径 2026-10-26 17:2x）。

为什么要先写：光标面板／剪贴板面板归 CodeArts（`entry/src/main/ets/components/ToolPanels.ets`），
集成归我。等他把文件丢过来再临时想判据，就会漏掉最容易漏的那几条——高度写死、
把「历史」做成假按钮、悄悄申请权限。所以契约在派单里写死了，这里把同一份契约变成可执行的检查：

  ① 两个 @Component 都在：`CursorPad`、`ClipboardPad`；
  ② 整层高度**由外部传入**（`candBarHeight()` 竖屏 44vp / 横屏 24vp），组件内不许写死数字高度
     —— 这条是 H-170/H-179⑤ 那一类真机事故的根：行级高度闸门看不见行内子节点，写死必然溢出压键；
  ③ 光标四向都调 `moveEditorCursor(1上/2下/3左/4右)`，按住连续要有节流（≈120ms 一步）；
  ④ **H-204 改口径**：粘贴必须走系统安全控件 `PasteButton`，在 onClick 里判
     `PasteButtonOnClickResult.SUCCESS` 后调 `keyboardController.pasteClipboardText(cb)`。
     旧的「让宿主编辑框 `sendExtendAction(PASTE)`」已被主人实测否掉（「粘贴没反应」——
     宿主常常没实现 handleExtendAction），退回它一律判红。
  ⑤ **H-204 改口径**：为什么必须点系统按钮，要写成**界面上看得见的说明文字**（永久一行），
     不许只在注释里、也不许只靠一次性 toast；同时**不许**把 PasteButton 自定义成
     小字号/透明/裁剪——安全控件样式不合规会导致授权直接失败（官方约束）。
  ⑥ 不许自己申请权限（`requestPermissionsFromUser` 一律不过；包内权限由内容闸门 ⑧ 另判）。
  ⑦ **H-207 新增（Qoder 2026-10-26 真机）**：onClick 必须收第三参 `error?: BusinessError<void>`
     并把 `result`/`err` 一起写进 console.info。真机「点多少次也粘不上」时，安全控件的失败
     分三类（1=系统内部错误、2=样式不合规、根本没注册＝`security component has not registered`），
     没有这条日志就只能猜；同时 BusinessError 必须显式导入（ArkTS 无全局 BusinessError）。

文件还没到（A/B 未交付）时本闸门打 SKIP、exit 0——不假装通过，也不阻塞别的闸门。

用法：
    python scripts/h194_toolpanels_check.py             # 文件未到 → SKIP；到了 → 逐项判据
    python scripts/h194_toolpanels_check.py --selftest  # 好样本全绿 + 坏样本必须各自变红
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
COMP = os.path.join(ROOT, "entry", "src", "main", "ets", "components", "ToolPanels.ets")

# 只扫组件内部：从 struct 名到它的最后一个右花括号（粗按「下一个 struct/@Component」切）
def strip_comments(text):
    """去掉注释后再判「有没有调某个 API」——注释里写「我们没调 requestPermissionsFromUser」
    是好注释，不该被闸门当成违规（H-185 教训：判据与被判的东西别共用同一个盲点）。"""
    t = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return "\n".join(re.sub(r"//.*$", "", ln) for ln in t.splitlines())


def struct_body(text, name):
    m = re.search(r"struct\s+%s\b" % re.escape(name), text)
    if not m:
        return None
    seg = text[m.end():]
    n = re.search(r"\n\s*(?:@Component|export\s+struct|struct\s+)", seg)
    return seg[:n.start()] if n else seg


def check(text):
    """返回 [(判据, 是否通过, 不过时说什么)]。"""
    out = []
    cursor = struct_body(text, "CursorPad")
    clip = struct_body(text, "ClipboardPad")
    out.append(("CursorPad 组件存在", cursor is not None,
                "找不到 `struct CursorPad`——派单 B① 要求导出这个 @Component"))
    out.append(("ClipboardPad 组件存在", clip is not None,
                "找不到 `struct ClipboardPad`——派单 B② 要求导出这个 @Component"))

    # ② 高度由外部传入（注意：`height` 这个 prop 名会和 `CustomComponent.height` 撞，
    #    编译直接红，所以组件里必须换个名收高度——契约只认「有个 @Prop 数字在收高度」，
    #    不认字面量 `height`。已交付的 ToolPanels 用 `barHeight`）。
    height_prop = re.search(r"@Prop\s+\w+\s*:\s*number", text) is not None and \
                  re.search(r"\.height\(\s*this\.\w+", text) is not None
    out.append(("高度是外部传入的 prop", height_prop,
                "整层高度必须由外部传入（`@Prop` 数字接收），组件内不许自有固定高度"))
    hard = []
    for nm, body in (("CursorPad", cursor), ("ClipboardPad", clip)):
        if not body:
            continue
        for m in re.finditer(r"\.height\(\s*(\d+(?:\.\d+)?)\s*\)", body):
            hard.append("%s .height(%s)" % (nm, m.group(1)))
    out.append(("组件内没有写死的高度", not hard,
                "写死高度 %s —— 竖屏 44vp、横屏只有 24vp，写死就会溢出压键（H-170/H-179⑤ 同类）"
                % ("、".join(hard[:4]) or "无")))

    # ③ 光标四向 + 节流
    # 判据 2026-10-26 12:1x 修（假红）：原写法只认 `moveEditorCursor(1)` 直调，CodeArts 的
    # ToolPanels 走 `startRepeat(dir)` 再在定时器里调，语义完全正确却被判「四向无」。
    # 现在按**图标 → 方向号配对**判：每枚 up/down/left/right 图标的作用域里，第一个
    # startRepeat/moveEditorCursor 参数必须是 1/2/3/4 中对应的那个（这也拦得住左右反接）。
    out.append(("光标走 moveEditorCursor", "moveEditorCursor(" in text,
                "没看到 `moveEditorCursor(`——应调既有 KeyboardController 方法，别自己调 API"))
    want = (("up", 1, "上"), ("down", 2, "下"), ("left", 3, "左"), ("right", 4, "右"))
    sites = [(m.start(), m.group(1), m.end()) for m in re.finditer(
        r"SymbolGlyph\(\$r\('sys\.symbol\.([a-z0-9_]+)'\)", text)]
    missing = []
    for kw, num, label in want:
        hit = False
        for i, (pos, name, scan_from) in enumerate(sites):
            if kw not in name:
                continue
            end = sites[i + 1][0] if i + 1 < len(sites) else len(text)
            seg = text[pos:end]
            d = re.search(r"(?:startRepeat|moveEditorCursor)\(\s*(\d)\s*\)", seg)
            if d and int(d.group(1)) == num:
                hit = True
                break
        if not hit:
            missing.append("%s(%d)" % (label, num))
    out.append(("四向图标--方向号都配对", not missing,
                "缺/错配：%s（上=1 下=2 左=3 右=4；图标域内第一个 startRepeat/moveEditorCursor 必须对上）"
                % ("、".join(missing) or "无")))
    out.append(("按住连续有 ~120ms 节流", re.search(r"\b120\b", text) is not None,
                "没看到 120（ms）——派单写的是按住 120ms 一步；别的值也可以，但要在注释里写明并同步派单"))

    # ④ 粘贴（H-204 改口径 2026-10-26 17:2x）
    # 旧判据是「走 sendEditorAction(PASTE)，让宿主自己贴」——主人真机实测「粘贴没反应」：
    # 宿主常常没实现 handleExtendAction，而应用级输入法又**不许**直接读剪贴板（华为官方答复），
    # 系统给的唯一合规通道是安全控件 PasteButton（点一下＝对这次读取临时授权）。
    clip_code = strip_comments(clip) if clip else ""
    out.append(("粘贴走系统 PasteButton", "PasteButton(" in clip_code,
                "ClipboardPad 必须用安全控件 `PasteButton(`——自定义按钮读不到剪贴板，"
                "走宿主 sendEditorAction(PASTE) 主人实测没反应"))
    out.append(("没有退回宿主 PASTE", "sendEditorAction(" not in clip_code,
                "ClipboardPad 里又出现 `sendEditorAction(`：宿主不实现 PASTE 时就是静默死按钮（H-204 已否）"))
    out.append(("点击结果判 SUCCESS",
                re.search(r"PasteButtonOnClickResult\.SUCCESS", clip_code) is not None,
                "必须在 onClick 里判 `result === PasteButtonOnClickResult.SUCCESS`，"
                "没授权还要给用户可见反馈"))
    out.append(("授权回调内立刻读剪贴板", "pasteClipboardText(" in clip_code,
                "临时授权只在 onClick 回调期间有效，必须当场调 "
                "`keyboardController.pasteClipboardText(...)`，拖到回调外会 201 被拒"))

    # ⑤ 说明写成界面文字 + 安全控件样式合规（H-204）
    # 关键词只认「授权/剪贴板」：光写一个「粘贴」按钮名不算说明（负控验证过：
    # 把说明撤成 Text('粘贴') 必须变红，否则这条判据形同虚设）。
    out.append(("为什么必须点它，写在界面上",
                re.search(r"Text\(\s*['\"][^'\"]*(授权|剪贴板)", clip_code) is not None,
                "面板里要有一行**永久可见**的说明（用户随时看得到为什么要点系统按钮）；"
                "只在注释里或只弹一次性 toast，用户会以为坏了"))
    pb_pos = clip_code.find("PasteButton(")
    # 说明行找「行首的 Text(」——`pasteClipboardText(` 里也含子串 "Text("，用 find("Text(") 会切早，
    # 把按钮链上的自定义样式全漏掉（2026-10-26 selftest 抓到这条负控原本是哑的）。
    nxt = re.search(r"\n\s*Text\(", clip_code[pb_pos:]) if pb_pos >= 0 else None
    pb_chain = clip_code[pb_pos:pb_pos + nxt.start()] if (pb_pos >= 0 and nxt) else clip_code[pb_pos:]
    style_bad = [p for p in (".fontSize(", ".fontColor(", ".backgroundColor(",
                             ".opacity(", ".borderRadius(", ".clip(", ".width(", ".height(")
                 if p in pb_chain]
    out.append(("PasteButton 未被自定义样式", pb_pos >= 0 and not style_bad,
                "安全控件改样式（字号/图标过小、透明、被裁剪、尺寸过大）会直接判授权失败 "
                "SecurityComponentCheckFail——保持系统默认样式，别加戏 %s"
                % ("、".join(style_bad) or "")))

    # ⑥ 不自己申请权限（先剥注释：说明「不申请」的注释不算违规）
    out.append(("没有申请权限", "requestPermissionsFromUser" not in strip_comments(text),
                "组件里出现了 `requestPermissionsFromUser`——包内权限必须保持恰为 ['VIBRATE']"
                "（内容闸门 ⑧），任何新权限一律不过"))

    # ⑦ H-207（Qoder 2026-10-26 真机）：授权失败必须**留下可判别的证据**。
    # 主人「v粘不上有提示了，点多少次也粘不上」——光有 toast 不够：安全控件的失败分三类
    # （1=系统内部错误 / 2=样式不合规 / 根本没注册上，真机日志是 `security component has not
    # registered`），只有把 result 和 error.code 一起打进日志，下一轮装机才能一次定位。
    out.append(("授权结果连错误码一起进日志",
                re.search(r"console\.info\([^\n]*result=[^\n]*err", clip_code) is not None
                and re.search(r"error\?:\s*BusinessError<void>", clip_code) is not None,
                "onClick 必须收第三参 `error?: BusinessError<void>` 并把 result/err 打进 "
                "console.info——否则「粘不上」只能靠猜（H-207）"))
    out.append(("BusinessError 已导入",
                re.search(r"import\s*\{[^}]*BusinessError[^}]*\}\s*from", text) is not None
                or "BusinessError" not in clip_code,
                "ArkTS 没有全局 BusinessError（不像 TS），用到就得从 @kit.BasicServicesKit 导入，"
                "否则编译红"))
    return out


def report(items):
    bad = [x for x in items if not x[1]]
    for name, ok, hint in items:
        print("  [%s] %s%s" % ("绿" if ok else "红", name, "" if ok else "  —— " + hint))
    return bad


GOOD = """
import { keyboardController } from '../inputmethod/KeyboardController';
import { BusinessError } from '@kit.BasicServicesKit';

@Component
export struct CursorPad {
  @Prop barHeight: number = 44;
  private timerId: number = -1;
  private HOLD_STEP_MS: number = 120;

  build() {
    Row() {
      SymbolGlyph($r('sys.symbol.arrow_up')).onClick(() => keyboardController.moveEditorCursor(1))
      SymbolGlyph($r('sys.symbol.arrow_down')).onClick(() => keyboardController.moveEditorCursor(2))
      SymbolGlyph($r('sys.symbol.arrow_left')).onClick(() => keyboardController.moveEditorCursor(3))
      SymbolGlyph($r('sys.symbol.arrow_right')).onClick(() => keyboardController.moveEditorCursor(4))
    }
    .width('100%')
    .height(this.barHeight)
  }
}

@Component
export struct ClipboardPad {
  @Prop barHeight: number = 44;

  build() {
    Row({ space: 8 }) {
      PasteButton({ icon: PasteIconStyle.LINES, text: PasteDescription.PASTE })
        .onClick((event: ClickEvent, result: PasteButtonOnClickResult, error?: BusinessError<void>) => {
          console.info(`H-194 click result=${result} err=${error === undefined ? 'none' : error.code}`);
          if (result !== PasteButtonOnClickResult.SUCCESS) {
            promptAction.showToast({ message: '系统没有授权读取剪贴板，请再点一次' });
            return;
          }
          keyboardController.pasteClipboardText((ok: boolean, msg: string) => { });
        })
      Text('点「粘贴」＝系统临时授权读一次当前剪贴板')
        .fontSize(11)
        .layoutWeight(1)
    }
    .width('100%')
    .height(this.barHeight)
  }
}
"""


def selftest(text):
    """好样本必须全绿；每个坏样本必须各自变红（否则闸门无效）。"""
    fails = 0
    bad = report(check(GOOD))
    if bad:
        print("SELFTEST FAIL: 好样本竟然有 %d 项红（%s）——判据本身写错了" % (len(bad), bad[0][0]))
        fails += 1
    else:
        print("SELFTEST OK: 好样本 %d 项全绿" % len(check(GOOD)))

    cases = [
        ("高度写死", ".height(this.barHeight)\n  }\n}\n\n@Component\nexport struct ClipboardPad",
         ".height(44)\n  }\n}\n\n@Component\nexport struct ClipboardPad"),
        ("自己申请权限", "  private HOLD_STEP_MS: number = 120;\n",
         "  private HOLD_STEP_MS: number = 120;\n"
         "  private async ask() { await abilityAccessCtrl.createAtManager().requestPermissionsFromUser(getContext(this)); }\n"),
        ("左右接反", "moveEditorCursor(3))", "moveEditorCursor(4))"),
        # H-204 四控：每一控对应主人骂过的那个现象
        ("粘贴退回宿主 PASTE（「粘贴没反应」）",
         "      PasteButton({ icon: PasteIconStyle.LINES, text: PasteDescription.PASTE })\n"
         "        .onClick((event: ClickEvent, result: PasteButtonOnClickResult, error?: BusinessError<void>) => {\n"
         "          console.info(`H-194 click result=${result} err=${error === undefined ? 'none' : error.code}`);\n"
         "          if (result !== PasteButtonOnClickResult.SUCCESS) {\n"
         "            promptAction.showToast({ message: '系统没有授权读取剪贴板，请再点一次' });\n"
         "            return;\n"
         "          }\n"
         "          keyboardController.pasteClipboardText((ok: boolean, msg: string) => { });\n"
         "        })\n",
         "      Button('粘贴').onClick(() => keyboardController.sendEditorAction(inputMethodEngine.ExtendAction.PASTE))\n"),
        ("不判授权结果（点了没反应也不说）",
         "          if (result !== PasteButtonOnClickResult.SUCCESS) {\n"
         "            promptAction.showToast({ message: '系统没有授权读取剪贴板，请再点一次' });\n"
         "            return;\n"
         "          }\n", ""),
        ("说明只写在注释里",
         "      Text('点「粘贴」＝系统临时授权读一次当前剪贴板')",
         "      // 点「粘贴」＝系统临时授权读一次当前剪贴板\n      Text('粘贴')"),
        ("给安全控件加自定义样式（授权会失败）",
         "          keyboardController.pasteClipboardText((ok: boolean, msg: string) => { });\n        })\n",
         "          keyboardController.pasteClipboardText((ok: boolean, msg: string) => { });\n        })\n"
         "        .fontSize(11)\n        .opacity(0.6)\n"),
        # H-207 两控：主人「点多少次也粘上了吗？为什么粘不上」当时只能靠猜
        ("授权失败不留证据（只能猜）",
         "          console.info(`H-194 click result=${result} err=${error === undefined ? 'none' : error.code}`);\n",
         ""),
        ("证据里不收 error 参数（分不清 1/2/没注册）",
         "error?: BusinessError<void>",
         "error: PasteButtonOnClickResult"),
    ]
    for name, old, new in cases:
        if GOOD.count(old) != 1:
            print("SELFTEST FAIL: 负控「%s」锚点命中 %d 次（应为 1），坏样本没造出来"
                  % (name, GOOD.count(old)))
            fails += 1
            continue
        b = report(check(GOOD.replace(old, new, 1)))
        if b:
            print("SELFTEST OK: 负控「%s」变红 %d 项（例：%s）" % (name, len(b), b[0][0]))
        else:
            print("SELFTEST FAIL: 负控「%s」仍全绿 = 闸门无效" % name)
            fails += 1
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return 1 if selftest(GOOD) else 0
    if not os.path.exists(COMP):
        print("SKIP: %s 还没交付（M-221 B：组件归 CodeArts）。本闸门不假装通过。" % COMP)
        return 0
    text = open(COMP, encoding="utf-8").read()
    items = check(text)
    bad = report(items)
    if bad:
        print("\nFAIL: %d 项不满足（见上）" % len(bad))
        return 1
    print("\nPASS: ToolPanels 契约 %d 项全部满足" % len(items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
