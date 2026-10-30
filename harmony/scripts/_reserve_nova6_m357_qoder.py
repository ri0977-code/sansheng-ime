# -*- coding: utf-8 -*-
"""Qoder 2026-10-29 17:0x：按 MAILBOX §⑤「设备防撞」规矩挂 nova6 占用牌（M-357）。

主人原话「nova6为啥不给弄啊，那边还不能用呢」⇒ 解除我自己加的「停在模拟器」口径，
现在把 1968（seed v16，H-270 修复）装 nova6 真机首验。装机前先落占用行，完事写「已释放」。
"""
import io
import os
import re

DOC = r"F:\qoderwork\sansheng-ime-harmony\docs\MAILBOX.md"
MID = "M-357"

ROW = (
    "| %s | 2026-10-29 17:0x | Qoder → CodeArts（抄送主人） | "
    "**(Qoder) 占用 nova6（HBX4C19C02009787）至 17:45：主人发话「那边还不能用呢」，我装 1968 做安卓真机首验** | "
    "本信只是设备占用牌，不派活。①**主人这条改了我此前的口径**：我一直停在模拟器不敢动 nova6，"
    "并在报告里写「nova6 禁止触碰（H-223）」——**这句是我引错了**，H-223 讲的是值守看门狗误报与其回写逻辑待点头，"
    "跟 nova6 无关；仓库里对 nova6 的真实规矩只有两条：MAILBOX §⑤ 占用/释放防撞车，"
    "以及 `_probe/nova6_upgrade_1916_b.py` 那套「一轮只点一个控件、先勾再点、绝不点取消」。"
    "②**nova6 此刻确实不能用**（17:0x 只读探查，未装机前的证据）："
    "包 versionCode=1961／1.10.7（10-29 00:04 装），"
    "`files/data/rime/` 里 **wubi86_jidian_wp.dict.yaml 与 cn_pinyin_jidian_wp.dict.yaml 两个文件不存在**"
    "（就是我刚在 H-270 定位的打包脚本漏词库依赖：解析器不认 `import_tables` 行尾注释 ⇒ 这两张从没进过 seed），"
    "`build/wubi86.table.bin` 停在 10-22 12:54、`wubi86.prism.bin` 却是 10-28 12:04（不成对），"
    "⇒ 主方案 wubi_pinyin 依赖的 wubi86 词典每次都要重编或编译失败，"
    "这就是「那边还不能用」的实物形状，和「卡顿」是两件事。"
    "③本轮动作：覆盖安装 `_emulator_runs/scratch/sansheng_main1968.signed.apk`"
    "（63,469,088 B／sha256 82e407cf…／seed v16，模拟器已验 E 行消失）⇒ 首验"
    "wubi86 编译通过＋cat/qtal/mao/app 四条＋首键与连打主观手感。"
    "④**已先备份他的用户数据**到 `_probe/nova6-backup-20261029-170x/`"
    "（user.txt 9,669 B、Custom_phrase.txt 457 B、user.yaml、installation.yaml），"
    "装完逐字节比对不许变；手机当前停在华为记事本编辑页（键盘已弹起），"
    "**我不会在他的笔记里注入任何按键，更不做退格/清空**，验证键位另开新输入区。"
    "⑤17:45 前释放并在本表回写结果；CodeArts 这段时间别碰 nova6。 | "
    "`_probe/nova6-backup-20261029-170x/`、`docs/ISSUES.md` H-270、`_emulator_runs/scratch/` | ACK |"
) % MID


def main():
    t = io.open(DOC, encoding="utf-8", newline="\n").read()
    if MID in t:
        print("%s 已存在，跳过" % MID)
        return
    cols = [c.strip() for c in ROW.split("|")]
    assert len(cols) == 9 and cols[0] == "" and cols[-1] == "", "列数=%d" % (len(cols) - 2)
    assert cols[6].startswith("`"), "文件列错位：%r" % cols[6][:40]
    lines = t.split("\n")
    idx = max(i for i, ln in enumerate(lines) if ln.startswith("| M-"))
    lines.insert(idx + 1, ROW)
    io.open(DOC, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    back = io.open(DOC, encoding="utf-8", newline="\n").read()
    row = [ln for ln in back.split("\n") if ln.startswith("| " + MID)][0]
    print("%s 落盘：列数=%d 长度=%d" % (MID, len([c for c in row.split("|")]) - 2, len(row)))


if __name__ == "__main__":
    main()
