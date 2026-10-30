# -*- coding: utf-8 -*-
"""往 docs/PROGRESS.md 追加一行 ㉒（Qoder 2026-10-29 14:2x，app 三端补完）
列口径＝日期 | 从 | 到 | 内容 | 状态（5 格）；幂等：已有 ㉒ 就跳过。"""
import io
import os
import sys

P = r'F:\qoderwork\sansheng-ime-harmony\docs\PROGRESS.md'
ROW = ('| ㉒ 10-29 14:2x（真实时钟＝`date` 14:22；**零构建、零签名、零装机、零注入；'
       '只补数据＋改 Lua＋离线验＋记台账**） | Qoder | CodeArts＋主人 | '
       '**主人报的「打 app 后面都是联想，没有中文」三端补完（H-265）**。根因是我们自己的词库生成口径：'
       '`gen_en_word.py` 的 `eligible()` 只收全小写与首字母大写两种写法 ⇒ ECDICT 里只有全大写形式的缩写词'
       '（APP／CPU／OK／URL／TV／DNA…）从没进过 `en_word.dict.yaml`，gloss 表和鸿蒙分桶表一起缺，'
       '而滤镜场景1 又要求「输入本身在库里」才接管 ⇒ app 完全不接管。'
       'Windows／安卓＝滤镜 24,271 B 新增**场景1b**（1 英文本词＋注释与反查码、2 中文译词、其余中文在前、联想仍≤5、码感知不排），'
       '16 条断言＋真实 rime.dll 双会话（点一次「应用」即升第1位）；安卓 seed v15／APK 1967 模拟器四条全绿。'
       '鸿蒙＝**断在数据不在滤镜**：`_patch_bucket_add_abbrev_qoder.py` 按桶内字典序插进 75 个缺词'
       '（55,792→55,867 行，difflib 判 insert=75 delete=0 replace=0，原有一行不少），'
       '`enWord_translator.lua` 5,025→6,478 B 加第二条中文候选（用桶里已有释义，不新读文件、不占联想名额，'
       '改在 CodeArts 14:07:56 那版之后、他的性能重排保留），用 lupa **真跑这份 Lua＋这份桶**离线判 PASS。'
       '自查纠两条：`.bak-*` 就地留在 rawfile 被 hvigor 打进 HAP 白背 5.8 MB（H-266，已挪出、一个没删）；'
       'M-264／M-269 状态列已回收 DONE ⇒ CodeArts 那 22 封「仍 OPEN」是旧副本检出，M-346 请他停追加并落笔前先 `date`'
       '（他的信超前本机约 10 小时，值守「20 分钟内只读」会算出负龄）。'
       'Mate 80 现跑 14:10:04 那份（signed 39,923,890 B：补词已进手机，第二条中文未进包）；'
       '14:18 `h106_precheck.py` 阻断 3 项 ⇒ **本轮不构建不装机**。 | '
       '待主人一拍（Windows 托盘重新部署约 10 秒）；鸿蒙待 CodeArts 报交付行后一次装机 |')


def main():
    if ROW.count('|') != 6:
        print('FAIL 竖线数 %d，应为 6（5 格）' % ROW.count('|'))
        return 1
    txt = io.open(P, encoding='utf-8').read()
    if '㉒ 10-29 14:2x' in txt:
        print('已存在 ㉒，跳过（幂等）')
        return 0
    body = txt.rstrip('\n') + '\n' + ROW + '\n'
    io.open(P, 'w', encoding='utf-8', newline='\n').write(body)
    print('已追加 ㉒（%d 字符）' % len(ROW))
    return 0


if __name__ == '__main__':
    sys.exit(main())
