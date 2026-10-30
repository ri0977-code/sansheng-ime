# -*- coding: utf-8 -*-
"""往 docs/ISSUES.md 追加 H-265 / H-266 两行（Qoder 2026-10-29 14:2x）

只追加，不改已有行；写盘前先按 7 格校验，格内一律不出现裸竖线。
备份：_probe/rawfile-backups-20261029/ISSUES.md.bak-qoder-20261029-1420-before-h265
"""
import io
import os
import re
import sys

ROOT = r'F:\qoderwork\sansheng-ime-harmony'
P = os.path.join(ROOT, 'docs', 'ISSUES.md')

ROWS = [
    "| H-265 | FIXED（**Qoder 10-29 14:1x：Windows 真机＋安卓模拟器 1967 已验；鸿蒙数据与 Lua 离线验完，待下一次构建装机**） | P1 | Q | **打 app 只剩五条英文联想、没有中文**（主人 10-29 原话「这个app对吗，后面都是联想，没有中文，看万能五笔的截图」，附两张截图：我们这边 appa／appy／appl／appo／apps 五条全英文；万能五笔 1.应用 2.蒙冤q 3.劳神y 4.禁寨f 5.app 6.劳军l）。这违反一条已定口径「一位二位，是给本义和翻译的」。根因两层：① 词库生成器 `gen_en_word.py` 的 `eligible()` 只收「全小写」和「首字母大写＋其余小写」两种写法，ECDICT 里**只有全大写形式**的缩写词（APP／CPU／OK／URL／TV／DNA…）一条都没进 `en_word.dict.yaml`，于是 gloss 表和鸿蒙分桶表也一起没有；② 滤镜场景1 的前提是「输入本身是库里有的英文单词」，app 不在库里 ⇒ 整条滤镜不接管 ⇒ 只剩 en_word translator 的前缀联想。三端各断在不同位置：Windows／安卓是「滤镜没接管」，鸿蒙是「桶里根本没这行」，且鸿蒙 `enWord_Filter` 因大 TSV 卡顿被注释（H-260 方向1，走 Lua translator＋`en_word_bucket.txt`），所以鸿蒙补滤镜没用，得补数据。 | **Windows／安卓**：滤镜 24,271 B（sha1 cc786d1adbdc）新增**场景1b**——纯字母、不在 gloss、但在 `en_word_trans.tsv` 的输入：第1条＝英文本词（注释「应用 yiet／yingyong」＋五笔反查），第2条＝中文译词，其余中文在前、英文联想仍≤5，且不排掉码感知。四份权威拷贝逐文件同字节（`G:/RimeUser/lua`、`packaging/release/config/lua`、安卓 `rime/lua`、鸿蒙 `rawfile/rime/lua`），各带 `.bak-20261029-1315-before-1b`。台架 `_probe/run_1b_regression.py` 16 条断言全过；真实 rime.dll 双会话台架验自调频（点一次「应用」即升到第1位）。安卓：`FirstRunSeeder` SEED_VERSION 15（`sansheng_seed_v15.done`，MARKERS 历史保留），APK 1967（63,084,064 B／sha256 d4d1c50f39e87618…／相对 1966 只差 `assets/sansheng_seed.zip`＋`classes3.dex`）装 emulator-5554 回归 cat／qtal／mao／app 全绿，logcat 见「older seed → v15 upgrade」，机内滤镜 24,271 B。**鸿蒙**：`scripts/_patch_bucket_add_abbrev_qoder.py`（默认试算、`--apply` 才写盘、写前自动备份、行尾保持原样、自检「原有 55792 行一行不少」）把 `en_word_trans.tsv` 有而桶里没有的 **75 个**缩写词按桶内字典序插进 `en_word_bucket.txt`（55,792→55,867 行；app／cpu／ok／url／tv／core／max…，释义口径与现有一致：第一个中文义项＋五笔/拼音码）；`_probe/verify_bucket_patch_qoder.py` 用 difflib 判 insert=75 delete=0 replace=0＝PASS。再往 `lua/enWord_translator.lua`（5,025→6,478 B）加**第二条中文候选**（取桶释义空格前的中文，不占 MAX_EN_CANDS 名额、不新读文件）；`_probe/run_harmony_translator_offline_qoder.py` 用 lupa 直接执行在用的这份 Lua＋补词后的这份桶：app→「app[应用 yiet／yingyong] 应用[app] apparent… 」、cpu→「cpu 中央处理器」、单字母 q 不出、联想≤5 ⇒ PASS。 | ①**Windows 还差主人一拍**：托盘「重新部署」（约 10 秒）——13:15 换的 24,271 B 滤镜还没进 `build/`，线上跑的是旧字节（`WeaselDeployer /deploy` 会弹方案选单模态且没写 build，已关窗没点确定，不改他的方案勾选）。②**鸿蒙待构建装机**：Mate 80（7GL0226408083897）`updateTime`＝10-29 14:10:04，装的是 14:09:51 那份 signed HAP 39,923,890 B——包内 `en_word_bucket.txt` sha1 与工作区一致（**补词已进手机**），但 `enWord_translator.lua` 还是 5,025 B 旧版（第二条中文候选未进包）⇒ 主人现在真手打 app 应能看到「app ＋注释 应用」，要看到第二条可选中文需再构建＋装一次；每次华为装机都要主人输密码，故与 H-260/H-263 那批改动并成一次再装。③14:18 结构闸门 `h106_precheck.py` 阻断 3 项（工作区 16 项未提交、无待验收 CodeArts 交付行、交付行无 unsigned 字节数），因此本轮**不构建**，等 CodeArts 把 14:0x 那批（`RimeDataInstaller.ets` DATA_VERSION→`h260-enword-translator-v29`、translator 性能改版、14:26 又动了 `sansheng_t9.schema.yaml`）在台账里署名报字节数。 |",
    "| H-266 | FIXED（**Qoder 10-29 14:2x：挪出打包树，包体少 5.8 MB**） | P2 | Q | **我把备份文件写在了会被打进 HAP 的目录里**（自查发现，非主人报）：改 `rawfile/rime/` 下的数据与 Lua 时按「先备份再改」的习惯就地留了 `.bak-*`，而 hvigor 把 `rawfile` 整棵树原样打进包里——14:09 那份 signed HAP 里就有 4 份桶备份（各 1,562,235 B）＋旧版滤镜备份＋`en_word.dict.yaml.bak-v23-full`，**白背 5.8 MB**（占包 14.5%）。同一目录里还有 3.9 MB 已经不再释放给用户的 TSV（CodeArts v29 把它们从 SHARED／USER 清单里移走，文件仍在 rawfile）也在打进去。 | `find entry/src/main/resources/rawfile -iname '*.bak*'` 现在为 0；六个备份全部移到仓外可读位置 `_probe/rawfile-backups-20261029/`（一个都没删，H-129）。已验证：移动前包内桶 sha1 与工作区一致，说明打包路径本来就是逐字节透传，问题只在「放进去」这一步。 | 下一次构建后按条目复核：`python -c` 列 HAP 里 `rawfile` 条目，凡 `.bak`／`.tmp` 一律判失败；顺带把这条加进 `check_app_content.py` 或 `_probe` 里的条目 diff，别只靠散文提醒（H-144 口径：散文式提醒不算修好）。TSV 是否从 rawfile 一并瘦身，属 CodeArts 归属区决定，逐条问、不自作主张删。 |",
]


def cells(line):
    if not line.startswith('|') or not line.endswith('|'):
        return None
    return len(re.split(r'(?<!\\)\|', line)) - 2


def main():
    for i, r in enumerate(ROWS):
        n = cells(r.rstrip('\n'))
        if n != 7:
            print('FAIL 第 %d 行是 %d 格，应为 7 格' % (i + 1, n))
            return 1
        if '\n' in r:
            print('FAIL 第 %d 行含换行' % (i + 1))
            return 1
    txt = io.open(P, encoding='utf-8').read()
    lines = txt.split('\n')
    ids = [l.split('|')[1].strip() for l in lines if l.startswith('| H-')]
    for r in ROWS:
        rid = r.split('|')[1].strip()
        if rid in ids:
            print('已存在 %s，跳过（幂等）' % rid)
            return 0
    # 追加在最后一条 | H- 行之后
    last = max(i for i, l in enumerate(lines) if l.startswith('| H-'))
    lines[last + 1:last + 1] = [r.rstrip('\n') for r in ROWS]
    io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    print('已追加 H-265／H-266 到第 %d 行之后；文件 %d 行' % (last + 1, len(lines)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
