# -*- coding: utf-8 -*-
"""HANDOFF 2026-10-30 02:2x 合并（Qoder，M-368 收口）。

按 H-139：活表三格各只留一个带时间戳段落；被合并掉的原文逐字归档到文件末尾附录。
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "docs", "HANDOFF.md")

NEW_UPD = (
    "| 最近更新 | **2026-10-30 02:2x（Qoder·主人「符号还是不行」→ 鸿蒙 9 个符号键全部一键直出）**："
    "①**根因一：CodeArts 的 h275 在真机上等于没改**（H-276）。librime 1.16.1 里 `prebuilt_dir` = "
    "`<shared>/build`、`staging_dir` = `<shared>_user/build`，编译出的 `*.schema.yaml`／`*.table.bin`／`*.prism.bin` "
    "和**已部署的 default.yaml** 全在 staging；`RimeDataInstaller.ensure()` 删的是 prebuilt ⇒ deployer 按时间戳判定"
    "「不必重编」，punctuator 一直是旧的。设备 hilog 原样：`prebuild=1 (508 ms) files=14`、`deploy=1 (78 ms) files=14`"
    "（78 ms＝全部跳过）。②**根因二：` 是另一个病**（H-277）。三个方案的 `recognizer/patterns/reverse_lookup` 是 "
    "`\"^`[a-z]*'?$\"`，单独按反引号会被吞成反查预编辑「`〔拼音〕」＋1 条空候选，桥的兜底条件（输入串没变才直出）"
    "因此永远不成立。③**改了三处**：`DATA_VERSION` → `h275b-punct-deploy`；清缓存改删 `rime_user/build`（真 staging，"
    "老的 `rime/build` 顺手留着删＝无害）；新增 `punctProbe()` 在早退／清理前／释放后各报一次**已部署的** default.yaml 的 "
    "`half_shape` 键数（沙箱 `files/` 用 hdc 读不到，只能应用自报）；`fanxing_napi.cpp` 在多字节面板字直出那条分支后面"
    "加同语义的 `key == \"`\"` 单字节直出，另加 `LogPunctState()` **只在被引擎吞掉时**打一行。"
    "CodeArts 的 `default.yaml` 一行没动（改法是对的）。④**真机证据**（本次装的包 unsigned 44,542,801 B／signed "
    "44,659,493 B）：`staging files_before=1` → `prebuild=1 (7506 ms)` → `deploy=1 (100 ms) files=14`，"
    "`deploy default=1 pinyin_simp=1 wubi_pinyin=1 sansheng_t9=1` 全 success；9 个键逐个 "
    "`punct key=… commit='<符号>' menu=0 num=0`；不看眼睛的端到端＝`uitest dumpLayout` 读三生自己的「试一试」输入框，"
    "正文里 9 个字符逐字落地、中间没有候选菜单。⑤**验收口径的坑**：`uitest uiInput click` 一次点击会连发 2–5 个键事件"
    "（一个 tap 打出 4–5 个反引号），是注入手段的毛病、不是产品行为，别拿点击数对账。 |"
)

NEW_BLOCK = (
    "| **当前阻断** | **2026-10-30 02:2x 刷新（Qoder）：符号这条只剩主人一只手**。"
    "①**M-368 引擎侧已证、手感待主人**：9 个符号键在已装包上逐键量到直出，但「按下去舒不舒服」只能他复验；"
    "他点完之前这条不写 VERIFIED。②**安卓两件老账没动**：14 张预编译 `build/*.bin` 打进 seed（消冷启动编译）、"
    "H-271 脚本强制 bump versionName。③**H-273 等主人一句话**：安卓 seed 里的五笔主词库比桌面发布输入包少一版"
    "（2,352,069 vs 2,488,821 B），我没自行替换。④**英文链 9 个文件（5,453,552 B）仍全 untracked**：M-350 归属"
    "CodeArts 未回，新克隆一次英文功能整条消失。⑤**CodeArts 侧**：M-369 已写明 h275 白改的原因和我改他文件的 3 处，"
    "请他别再动那条删除路径。 |"
)

NEW_WAIT = (
    "| **等主人** | **2026-10-30 02:2x 刷新（Qoder）：只剩一次手点**。①**在 `?123`→`全`→`英文` 页把这 9 个键各点一下**："
    "`'` `\"` `#` `$` `^` 反引号 `_` `[` `]`——每个都应**直接落进输入框**，不该弹候选栏、不该要空格。"
    "②反引号那个请单独点一次（它是另一个病，我刚修）；要是哪个还不出字，告诉我「哪个键、出没出候选」，我按 hilog 抓。"
    "③其余（安卓 14 张预编译 bin、H-271、英文链入库）都是我的活，不用你管。④这轮只装了一次 Mate 80、没注入按键、"
    "没动他的备忘录文字。 |"
)

lines = io.open(P, encoding="utf-8").read().split("\n")

# 活表只在「当前状态」段里；文末附录里也躺着历史同前缀行，不能算命中
end = [i for i, l in enumerate(lines) if l.startswith("## 文件归属")][0]


def find(prefix):
    hits = [i for i, l in enumerate(lines[:end]) if l.startswith(prefix)]
    if len(hits) != 1:
        sys.exit("%s 命中 %d 行（应为 1）" % (prefix, len(hits)))
    return hits[0]


i_upd = find("| 最近更新 |")
i_blk = find("| **当前阻断** |")
i_wait = find("| **等主人** |")
old = {"最近更新": lines[i_upd], "当前阻断": lines[i_blk], "等主人": lines[i_wait]}

for name, new in (("最近更新", NEW_UPD), ("当前阻断", NEW_BLOCK), ("等主人", NEW_WAIT)):
    assert "\n" not in new
    assert new.endswith(" |")
lines[i_upd] = NEW_UPD
lines[i_blk] = NEW_BLOCK
lines[i_wait] = NEW_WAIT

s = "\n".join(lines)
if not s.endswith("\n"):
    s += "\n"

s += (
    "\n### 2026-10-30 02:2x · Qoder（归档：本轮合并掉的「当前状态」三格原文＝18:4x 版）\n"
    "\n> 合并口径（H-139）：读首每格只留一个带时间戳段落，被合并掉的原文逐字留这里，一字不改。\n"
    "\n#### 旧「最近更新」格（2026-10-30 02:2x 合并 ⇒ 原文逐字留此）\n\n"
    + old["最近更新"] + "\n"
    "\n#### 旧「当前阻断」格（2026-10-30 02:2x 合并 ⇒ 原文逐字留此）\n\n"
    + old["当前阻断"] + "\n"
    "\n#### 旧「等主人」格（2026-10-30 02:2x 合并 ⇒ 原文逐字留此）\n\n"
    + old["等主人"] + "\n"
)

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("[ok] HANDOFF 三格已合并，旧原文归档到末尾（18:4x 版逐字）")
