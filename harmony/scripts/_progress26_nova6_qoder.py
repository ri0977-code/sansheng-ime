# -*- coding: utf-8 -*-
"""Qoder 2026-10-29 17:3x：PROGRESS 追加行 ㉖（nova6 真机一轮，5 列）。"""
import io

P = r"F:\qoderwork\sansheng-ime-harmony\docs\PROGRESS.md"
ROW = (u"| ㉖ 10-29 17:3x（真实时钟＝`date` 17:31；**本轮有真机覆盖安装，且只装一次**） | Qoder | CodeArts＋主人 | "
       u"**主人三句话把 nova6 这条路打开了：「nova6为啥不给弄啊，那边还不能用呢」→"
       u"「打不了字了nova6」→「有点卡」**。①我先认一条引用错误：我一直按「nova6 禁止触碰（H-223）」停手，"
       u"回查 H-223 讲的是值守看门狗误报与其回写逻辑等点头，与 nova6 无关；"
       u"仓库里对 nova6 的真实规矩只有 MAILBOX §⑤ 占用／释放防撞＋一台手机一次会话只装一次，"
       u"两条本轮都照办了（占用牌 M-357、17:08 装一次、M-358 释放）。"
       u"②**nova6 装前确实不能用**（只读探查）：包 1961／1.10.7，"
       u"`files/data/rime/` 里 `cn_pinyin_jidian_wp.dict.yaml` 不存在（＝H-270 那张从没进 seed 的表），"
       u"`build/wubi86.table.bin` 停在 10-22 12:54 而 prism 是 10-28 12:04（不成对）⇒ "
       u"主方案依赖的五笔词典每次重编／编译失败，这与他「打不了字」同一形状。"
       u"③**17:08:37 覆盖安装 1968 包 Success**（1961→1965），只点了一个控件"
       u"（纯净模式页「继续安装」，全程没碰「取消」，没在他打开的记事本里注入按键）；"
       u"装后 `cn_pinyin_jidian_wp.dict.yaml` 972,458 B 落到设备、"
       u"`build/wubi86.prism.bin` 重编为 13,648,224 B（17:09）⇒ H-270 在真机闭环，状态转 FIXED。"
       u"④**他的数据一条没动**：`user.txt` 9,669 B md5 装前后一致；"
       u"`Custom_phrase.txt` 9 行 457 B 只有 ssbz 探针戳换了时间戳；`user.yaml` 只变两个部署时间；"
       u"sync 目录仍 dc6cbd16-…；备份 `_probe/nova6-backup-20261029-170x/`。"
       u"⑤**「有点卡」量出裸刻度**（`_probe/nova6-speed-20261029.txt`，已扣 adb 基线 39 ms）："
       u"三张英文表合计 3,491,632 B，设备热读 117 ms（PC 66.8 ms 的 1.8 倍）、"
       u"sha256 33 ms（PC 9.2 ms ⇒ **CPU 慢 3.6 倍**）；把 PC 量到的「每会话整表解析 245-291 ms」按此折算 "
       u"**nova6 ≈ 0.9-1.05 s**，与主人「等1秒吧大概」同量级——"
       u"口径写死：这是折算估计，不是端到端实测（华为挡 IME 窗触摸注入，CodeArts 10-22 实测过像素零变化）。"
       u"⑥新开 **H-271**（P2）：这包文件名叫 1968、manifest 实为 versionCode=1965／versionName=1.10.7，"
       u"而他手机上上一版就是 1.10.7 ⇒ `检查更新.ps1` 按版本号比对不会提示；"
       u"出包自检只拿 manifest 自己比自己拦不住，1916 那轮 README 定过的口径这次丢了。"
       u"⑦更正一处我自己的落笔错误：M-357 原写「缺 wubi86_jidian_wp 与 cn_pinyin_jidian_wp 两张表」，"
       u"其中 `wubi86_jidian_wp.dict.yaml` 是我编的文件名（源树／seed／设备三处都没有），"
       u"实际只缺 `cn_pinyin_jidian_wp` 一张，已在 M-357 原行内逐字更正。 | "
       u"已发 M-358（H-270 FIXED／H-271 开账／H-269 追加真机折算） |")


def main():
    t = io.open(P, encoding="utf-8", newline="\n").read()
    if u"| ㉖ " in t:
        print(u"㉖ 已存在")
        return
    cols = [c for c in ROW.split(u"|")]
    assert len(cols) == 7 and cols[0] == u"" and cols[-1] == u"", u"列数=%d" % (len(cols) - 2)
    lines = t.split("\n")
    idx = max(i for i, ln in enumerate(lines) if ln.startswith(u"| ㉕ "))
    lines.insert(idx + 1, ROW)
    io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    back = io.open(P, encoding="utf-8", newline="\n").read()
    row = [ln for ln in back.split("\n") if ln.startswith(u"| ㉖ ")][0]
    print(u"㉖ 落盘：列数=%d 长度=%d 行数=%d" % (len(row.split(u"|")) - 2, len(row), back.count("\n") + 1))


if __name__ == "__main__":
    main()
