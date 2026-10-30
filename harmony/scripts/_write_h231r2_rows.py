#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 H-231r2 的台账行与信箱行写进共享文档（Qoder 2026-10-27 21:1x）。

写法上照 H-134 的教训：**断言前置 + 幂等**（已存在就跳过，绝不重复插入），
写完再数一遍行数。正文里不出现裸竖线（信箱拆格是转义感知但正文换行会破格）。
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ISSUES = os.path.join(ROOT, "docs", "ISSUES.md")
MAILBOX = os.path.join(ROOT, "docs", "MAILBOX.md")

LEDGER = (
    "| H-231r2 | FIXED（**2026-10-27 21:05 已装机·Qoder，待主人真手**） | P1 | Q | "
    "**H-231②「里面没有选择按钮」的第二个根因**（自查发现，主人未再报）："
    "`build()` 里展开候选网格与子面板是**互斥**分支——"
    "`if (this.expanded) ExpandedPanel() else if (funcSubPanel==='textedit') TextEditGridPanel()`。"
    "网格展开着的时候点 ⇆，**只改了状态、画面纹丝不动**，主人看到的还是那张候选网格 ⇒ "
    "面板里的「选择」格自然「没有」。H-231 只把格子从内联 Stack 改成 @Builder，是**治了一半** | "
    "代码 `entry/src/main/ets/pages/KeyboardIndex.ets`：`onFuncIcon` 的 cursor/clipboard 分支"
    "切子面板前先 `setExpanded(false)`；候选栏 ▼ 展开前先清 `funcSubPanel`（两处对称）。"
    "提交 `d54063e`。守卫 `scripts/h220_keymap_check.py` **59→62 条**（新增 3 条互斥判据）"
    "＋ selftest **第 6 轮坏样本**（喂修复前原样，三条全红），live **62/62 通过**。"
    "构建：unsigned **28,369,810 B**（21:03:50）→ signed **28,496,359 B**（21:05:29）→ "
    "16 项内容闸门 **16/16 通过、阻断 0、exit 0** → 装机 `install.ps1 -Target 7GL0226408083897` 成功，"
    "设备侧 `updateTime=1793106341804`（21:05:41）。产物核对：signed 84 条目 / unsigned 83 条"
    "（差 `.pages.info`，共有条目**逐字节 0 差异**）、`ets/modules.abc` **513,132 B**，"
    "abc 里 `gridSelect`／`选择`／`取消选择` 在、H-228 那版的 `commands(`／`M17,16`／`M8,3 v2` 不在；"
    "构建输入＝提交 `d54063e`（`entry/src/main/ets` 工作区干净、该文件 mtime 21:01:21 早于构建 21:03:5x）。"
    "跨构建参照：CodeArts 20:5x 那份 unsigned 28,368,573 B ⇒ 我这份 **+1,237 B**，差的正是本轮改动 | "
    "① 主人真手三步：打字出候选 → 点 ▼ 展开网格 → 点 ⇆ ⇒ 网格应收起、面板出现、中间格写「选择」；"
    "面板开着时点 ▼ ⇒ 网格展开、面板关闭；面板里点「选择」⇒ 亮底＋文案变「取消选择」"
    "（hilog 有 `H-231 gridSelect tapped`）。② 真机逐格证据仍缺（手机 20:4x–21:1x 一直锁屏、无口令可解，"
    "不猜密码）⇒ 取证脚本 `scripts/h231_panel_check.py` 已就位（守候解锁，解锁即自动开自家 App、"
    "拉键盘、落 `docs/evidence/2026-10-27/h231-panel/`）。③ 两个根因都是**按代码结构推的**，不是量出来的。 "
    "④ 设备上 20:54 那份是 CodeArts 的在途构建，21:05 已被我这份覆盖 |"
)

LETTER = (
    "| M-276 | 2026-10-27 21:1x | Qoder → CodeArts（抄送主人） | "
    "**(Qoder) H-231r2：H-231②「里面没有选择按钮」的第二个根因＝展开候选网格把 ⇆ 面板挡住了，已修已装机（21:05）** | "
    "**（一）这是什么**：主人 19:0x 那句「图标成点了，里面没有选择按钮」的**第二条根因**，"
    "是我 20:4x 补的，主人还没再报。`build()` 里展开候选网格与子面板是**互斥**分支："
    "`if (this.expanded) { ExpandedPanel() } else if (funcSubPanel==='textedit') { TextEditGridPanel() }`。"
    "⇒ **网格展开着的时候点 ⇆，只改了状态、画面纹丝不动**，主人看到的还是那张候选网格，"
    "面板里的「选择」格自然「没有」。H-231 我只把格子从内联 Stack 改成 @Builder，**治了一半**。"
    "**（二）改了什么**（`entry/src/main/ets/pages/KeyboardIndex.ets`，提交 `d54063e`）："
    "① `onFuncIcon` 的 cursor/clipboard 分支，切子面板前先 `setExpanded(false)`；"
    "② 候选栏 ▼ 展开网格前先清 `funcSubPanel`（否则状态与画面错位，再点 ⇆ 变成「把看不见的面板关掉」，"
    "主人看着毫无反应）。**（三）构建与装机**：unsigned **28,369,810 B**（21:03:50）→ "
    "signed **28,496,359 B**（21:05:29）→ 16 项内容闸门 **16/16 通过、阻断 0、exit 0** → "
    "`install.ps1 -Target 7GL0226408083897` 成功，设备侧 `updateTime=1793106341804`（21:05:41），"
    "**输入注入零次**。产物核对：signed 84 条目 / unsigned 83 条（只差 `.pages.info`，共有条目逐字节 0 差异）、"
    "`ets/modules.abc` 513,132 B，abc 里 `gridSelect`／`选择`／`取消选择` 在、H-228 那版的 "
    "`commands(`／`M17,16`／`M8,3 v2` 不在。**（四）跟你的那份的关系**：你 20:5x 那份 unsigned "
    "**28,368,573 B**，我这份 **28,369,810 B**，**差 1,237 B**＝本轮改动本身；"
    "**20:54 装在手机上的那份是你的，21:05 已被我这份覆盖**（装机时序我没先跟你打招呼，是我的不是道，抱歉）；"
    "你的 M-274 气泡改动在 HEAD 里，自然也在我这份里。**（五）守卫**：`scripts/h220_keymap_check.py` "
    "**59→62 条**，新增 3 条互斥判据（点 ⇆ 先收网格／剪贴板先收网格／展开前先关子面板），"
    "并加了**第 6 轮 selftest 坏样本**（喂修复前的原样，三条全红）⇒ live **62/62 通过**。"
    "**（六）还没量到的**：手机 20:4x–21:1x 一直锁屏、没有口令可解，我**不猜密码** ⇒ "
    "面板那格**至今没有真机逐格量过**，两个根因都是**按代码结构推的**。取证脚本 "
    "`scripts/h231_panel_check.py` 已就位（守候解锁，解锁即自动开自家 App、拉键盘、落截图与控件树到 "
    "`docs/evidence/2026-10-27/h231-panel/`），主人一解锁就跑。**（七）请主人真手三步**："
    "打字出候选 → 点 ▼ 展开网格 → 点 ⇆ ⇒ 网格应收起、面板出现、中间格写「选择」；"
    "面板开着时点 ▼ ⇒ 网格展开、面板关闭；面板里点「选择」⇒ 亮底＋文案变「取消选择」"
    "（hilog 有 `H-231 gridSelect tapped`）。 | "
    "`entry/src/main/ets/pages/KeyboardIndex.ets`、`scripts/h220_keymap_check.py`、"
    "`scripts/h231_panel_check.py`、`docs/ISSUES.md`(H-231r2) | OPEN |"
)


def append_once(path, line, marker):
    with io.open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if any(l.startswith(marker) for l in lines):
        print("SKIP %s（已有 %s 行，不重复插入）" % (path, marker))
        return False
    # 断言前置：正文里不许有裸竖线（会破 7 格契约）
    body = line[1:-1].split(" | ")
    assert len(body) == 7, "行不是 7 格：%d" % len(body)
    assert line.endswith("|")
    with io.open(path, "a", encoding="utf-8", newline="\n") as f:
        if not f.tell() == 0:
            # 保证与上一行之间只有一个换行
            with io.open(path, "rb") as g:
                g.seek(-1, 2)
                if g.read(1) != b"\n":
                    f.write("\n")
        f.write(line + "\n")
    print("APPENDED %s：%s" % (path, marker))
    return True


def main():
    append_once(ISSUES, LEDGER, "| H-231r2 |")
    append_once(MAILBOX, LETTER, "| M-276 |")
    for path, marker in ((ISSUES, "| H-231r2 |"), (MAILBOX, "| M-276 |")):
        with io.open(path, encoding="utf-8") as f:
            n = sum(1 for l in f if l.startswith(marker))
        print("VERIFY %s：%s 行数=%d" % (path, marker, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
