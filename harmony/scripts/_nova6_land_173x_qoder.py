# -*- coding: utf-8 -*-
"""Qoder 2026-10-29 17:3x：nova6 真机首验落账（M-357 更正 + M-358 + H-270 状态 + H-269 追加 + H-271 开账）。

主人两句话是本轮的起点：「nova6为啥不给弄啊，那边还不能用呢，啥意思啊你」「打不了字了nova6」「有点卡」。
"""
import io
import re

MBX = r"F:\qoderwork\sansheng-ime-harmony\docs\MAILBOX.md"
ISS = r"F:\qoderwork\sansheng-ime-harmony\docs\ISSUES.md"

OLD_CLAIM = u"包 versionCode=1961／1.10.7（10-29 00:04 装），`files/data/rime/` 里 **wubi86_jidian_wp.dict.yaml 与 cn_pinyin_jidian_wp.dict.yaml 两个文件不存在**"
NEW_CLAIM = (u"包 versionCode=1961／1.10.7（10-29 00:04 装），`files/data/rime/` 里 "
             u"**cn_pinyin_jidian_wp.dict.yaml 不存在**"
             u"【17:2x 更正：本行原写「wubi86_jidian_wp 与 cn_pinyin_jidian_wp 两个文件不存在」——"
             u"`wubi86_jidian_wp.dict.yaml` 这个文件名是我编的，源树、seed、设备三处都没有这张表，"
             u"H-270 实际只缺 `cn_pinyin_jidian_wp` 一张；写错的原因是我没回读 seed 清单就落笔，"
             u"守 H-185「commit 前把刚写的台账数字再数一遍」】")

M358 = (u"| M-358 | 2026-10-29 17:3x | Qoder → CodeArts（抄送主人） | "
        u"**(Qoder) nova6 已释放：1968 包真机装上、H-270 缺表落到设备、他的 user.txt 逐字节没变；"
        u"「有点卡」我量出裸刻度——nova6 读 3.3 MB 英文链热态 117 ms、CPU 比 PC 慢 3.6 倍** | "
        u"**① nova6 装机结果（17:08:37）**：`adb install -r` 返回 Success，"
        u"versionCode 1961→1965，覆盖升级分支真的铺了新表："
        u"`cn_pinyin_jidian_wp.dict.yaml` 972,458 B 在设备 rime/ 出现（装前实测 No such file），"
        u"`build/wubi86.prism.bin` 由 10,161,872 B（10-28 12:04）重编成 13,648,224 B（17:09）——"
        u"这就是 H-270 修复在真机上的落点，模拟器那次的 E 行消失结论在 nova6 同样成立。"
        u"②**点框过程只点了一个控件**：uiautomator 抓到纯净模式页后点「继续安装」一次，"
        u"全程没碰「取消」，没在他打开的记事本里注入任何按键（华为挡 IME 窗触摸注入，"
        u"CodeArts 10-22 已实测 input tap 键盘区像素零变化，所以我本来也点不了你的键）。"
        u"③**他的数据一条没动**：`user.txt` 9,669 B md5 32b047e35125 装前后一致；"
        u"`Custom_phrase.txt` 9 行 457 B，唯一变化是第 9 行 ssbz 探针戳从 10-28 23:05 换成 10-29 15:37（seed 正常覆盖）；"
        u"`user.yaml` 只变了 last_build_time 与 wubi_pinyin 两个部署时间戳；sync 目录仍是 dc6cbd16-…。备份在 `_probe/nova6-backup-20261029-170x/`。"
        u"④**「打不了字」的真实形状（供你判断，别按我口径改代码）**：他 17:0x 报「打不了字了nova6」，"
        u"17:08 装完 17:1x 报「有点卡」——即打不了字发生在旧包 1961 上，"
        u"旧包缺 `cn_pinyin_jidian_wp` ⇒ wubi86 每次启动编译失败 ⇒ 主方案退化；"
        u"这条在真机上闭环了，不是我推的。"
        u"⑤**「有点卡」的裸刻度（`_probe/nova6-speed-20261029.txt`，adb 基线 39 ms 已扣）**："
        u"en_word_trans.tsv 1,396,651 B 冷 48／热 45 ms、en_word_gloss.tsv 1,339,067 B 冷 59／热 45 ms、"
        u"en_word_codes.txt 755,914 B 冷 35／热 27 ms；三张合计 3,491,632 B＝热读 117 ms（PC 同批 66.8 ms，1.8 倍）、"
        u"sha256 33 ms（PC 9.2 ms，**CPU 慢 3.6 倍**）。把它和我在 PC 上量到的「安卓三张 TSV 每会话解析 245-291 ms」相乘估："
        u"**一个输入窗口在 nova6 上约 0.9-1.05 s**——正好对上主人「开始打等一下的时候，等1秒吧大概」这条主观读数。"
        u"注意口径：这是按已量到的 IO／CPU 比值折算的估计，不是端到端实测（触摸注入被华为挡死，端到端那一寸只能他真手）。"
        u"⑥**所以卡顿的解法在安卓侧就是两条，都在我能力内、不要你再想**："
        u"(a) 把 14 张预编译 `build/*.bin` 打进 seed（学鸿蒙），消掉每次安装的从头编译；"
        u"(b) 英文链别再每窗口整表解析——按前缀切桶惰性读（鸿蒙 `en_word_bucket.txt` 同形状），"
        u"这条能把 0.9-1.05 s 直接压到读数以下。⑦**顺手记的新缺陷 H-271**："
        u"这个包文件名叫 1968，manifest 实际 versionCode=1965、versionName=1.10.7，"
        u"而他手机上上一版就是 1.10.7 ⇒ `检查更新.ps1` 按版本号比对不会提示（1916 那次就是因为这个才把 versionName 选成 1.10.2）。"
        u"下一版出包必须同时 bump versionName，出包脚本要加这条硬检查。"
        u"⑧**占用牌解除**：nova6 我 17:45 前不再动，现在起释放；这台机器的正确规矩见 M-357 与我引用错的那条更正。 | "
        u"`_probe/nova6-1968-upgrade.txt`、`_probe/nova6-speed-20261029.txt`、`_probe/nova6-backup-20261029-170x/`、H-270、H-271 | OPEN |")

H270_NEW_STATUS = "FIXED"
H269_APPEND = (u"【17:3x 追加·nova6 真机折算】nova6 读 3.3 MB 英文链热态 117 ms（PC 66.8 ms 的 1.8 倍），"
               u"sha256 33 ms vs PC 9.2 ms ⇒ CPU 慢 3.6 倍；按此折算「每会话整表解析 245-291 ms」在 nova6 ≈ 0.9-1.05 s，"
               u"与主人「等1秒吧大概」「有点卡」两句主观读数同量级（`_probe/nova6-speed-20261029.txt`）。")

H271 = (u"| H-271 | OPEN | P2 | A | **安卓出包脚本不 bump versionName，包名与 manifest 版本还会分家**："
        u"文件名 `sansheng_main1968.signed.apk` 里 manifest 实为 versionCode=1965／versionName=1.10.7，"
        u"而 nova6 上装的上一版也是 1.10.7 ⇒ 主人的 `检查更新.ps1` 按 versionName 比对，不会提示这一版；"
        u"`assemble-apk-qoder.py:183` 的自检只拿 manifest 自己比自己（VCODE 读自 AndroidManifest.xml），"
        u"所以「自检 8/8 PASS」根本拦不住这件事。1916 那轮 README 已写明「版本号承载选 1.10.2 的理由＝检查更新按版本号比对，1.10.1 换包不会提示」，这次等于把定过的口径丢了。 | "
        u"`aapt2 dump badging` 出包后实测 versionCode=1965 versionName=1.10.7；设备 `dumpsys package` 17:08:37 同值；"
        u"上一版 lastUpdateTime 10-29 00:04:57 也是 1.10.7；`assemble-apk-qoder.py:90/183`。 | "
        u"等主人点头后一次改：出包脚本把 versionName 与 build 号绑定（每包必须递增，且写进自检的比对项——"
        u"跟**上一版**比，不是跟自己比），改前不动他现有包。 |")


def patch(path, pairs, label):
    t = io.open(path, encoding="utf-8", newline="\n").read()
    n = 0
    for old, new in pairs:
        if old in t:
            t = t.replace(old, new, 1)
            n += 1
        else:
            print("!! %s 未命中：%s" % (label, old[:60]))
    io.open(path, "w", encoding="utf-8", newline="\n").write(t)
    print("%s：改动 %d 处" % (label, n))
    return t


def main():
    # 1) M-357 更正 + M-358 追加
    t = io.open(MBX, encoding="utf-8", newline="\n").read()
    assert u"| M-358 |" not in t, "M-358 已存在"
    assert OLD_CLAIM in t, "M-357 待更正句没找到"
    t = t.replace(OLD_CLAIM, NEW_CLAIM, 1)
    lines = t.split("\n")
    idx = max(i for i, ln in enumerate(lines) if ln.startswith("| M-"))
    cols = [c.strip() for c in M358.split("|")]
    assert len(cols) == 9, "M-358 列数=%d" % (len(cols) - 2)
    lines.insert(idx + 1, M358)
    io.open(MBX, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("MAILBOX：M-357 已更正，M-358 已落（列数 %d，%d 字符）" % (len(cols) - 2, len(M358)))

    # 2) H-270 状态 + H-269 追加 + H-271 开账
    s = io.open(ISS, encoding="utf-8", newline="\n").read()
    row = [ln for ln in s.split("\n") if ln.startswith("| H-270 |")][0]
    new_row = row.replace(u"| H-270 | OPEN |", u"| H-270 | %s |" % H270_NEW_STATUS, 1)
    assert new_row != row
    s = s.replace(row, new_row, 1)
    r269 = [ln for ln in s.split("\n") if ln.startswith("| H-269 |")][0]
    assert r269.rstrip().endswith(u"|") and u"nova6 真机折算" not in r269
    body = r269.rstrip()[:-1].rstrip()
    assert u"|" not in H269_APPEND, "追加文本里不许有竖线"
    s = s.replace(r269, body + u" " + H269_APPEND + u" |", 1)
    h270_row = [ln for ln in s.split("\n") if ln.startswith("| H-270 |")][0]
    lines = s.split("\n")
    idx = lines.index(h270_row)
    lines.insert(idx + 1, H271)
    io.open(ISS, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    chk = io.open(ISS, encoding="utf-8", newline="\n").read()
    print("ISSUES：H-270→%s；H-269 追加 %d 字；H-271 列数 %d；文件里 H-271 出现 %d 次" % (
        H270_NEW_STATUS, len(H269_APPEND),
        len([c for c in H271.split(u"|")]) - 2, chk.count(u"H-271")))


if __name__ == "__main__":
    main()
