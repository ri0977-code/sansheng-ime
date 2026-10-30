# -*- coding: utf-8 -*-
"""H-270 行重写（Qoder 2026-10-29 15:5x）。前一版落盘变成 5 格，这里用 7 格常量覆盖第 310 行并校验。"""
import io
import os
import re

ROOT = r'F:\qoderwork\sansheng-ime-harmony'
ISS = os.path.join(ROOT, 'docs', 'ISSUES.md')

H270 = ('| H-270 | OPEN | P1 | A | '
        '**安卓 build-android-qoder.py 解析 import_tables 只认「- 名字」后光秃秃换行的行，'
        'wubi86.dict.yaml 第 9/10 行带行尾注释（#A13）⇒ cn_pinyin_jidian_wp.dict.yaml 从没进过 seed ⇒ '
        '手机 librime 每次启动都报 source file .../cn_pinyin_jidian_wp.dict.yaml does not exist、'
        "dictionary 'wubi86' failed to compile，五笔主词典用着 10-27 的残表；加上 seed 里 0 张预编译表"
        '（build/*.bin 全缺），每次安装都从头编译 13.7 万行 wubi86 等 ⇒ 冷启动巨慢**。'
        '这是主人点名「安卓也卡」「安卓你一点没弄」里我能实打实量到的第一条根因（之前只做了滤镜同步/seed/APK，从没量过卡顿）。 | '
        'emulator-5554 logcat 10-29 07:32 含上述两条 E 行；冷启动时间线 07:32:15.724 proc 起 → 21.961 fcitx5 Finishing startup（6,237 ms）'
        '→ 34.383 addon rime loaded → 35.2 表就绪（19.5 s）；wubi86.dict.yaml:9/10 行 import_tables 带 # 注释；'
        'build-android-qoder.py:81 的 import_tables 正则只吃无注释行。 | '
        'Qoder 已修解析器（行尾注释照常吃，build-android-qoder.py:81 注释里写清 H-270 根因）＋ SEED_VERSION 15→16（FirstRunSeeder.java 注释同），'
        '重建 seed（87→88 文件，含该表，11,570,529 B）＋ APK 1968（63,469,088 B，自检 8/8 PASS），'
        '装模拟器后该 E 行消失、cn_pinyin_jidian_wp.dict.yaml 落到 rime/（07:43:22，972,458 B）；'
        '剩余 = 把 14 张 build/*.bin 打进 seed（学鸿蒙，消冷启动编译），给 CodeArts 的 M-355 ④ 已说。 |')


def main():
    if len(H270.split('|')) - 2 != 7:
        print('FAIL 常量不是 7 格:', len(H270.split('|')) - 2)
        return 1
    lines = io.open(ISS, encoding='utf-8').read().split('\n')
    repl = False
    for i, l in enumerate(lines):
        if re.match(r'^\|\s*H-270\s*\|', l):
            lines[i] = H270
            repl = True
            print('覆盖第 %d 行；写盘前格数 %d' % (i, len(H270.split('|')) - 2))
            break
    if not repl:
        print('没找到 H-270，中止')
        return 1
    io.open(ISS, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    # 回读校验
    for l in io.open(ISS, encoding='utf-8').read().split('\n'):
        if re.match(r'^\|\s*H-270\s*\|', l):
            print('回读格数', len(l.split('|')) - 2)
            break
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
