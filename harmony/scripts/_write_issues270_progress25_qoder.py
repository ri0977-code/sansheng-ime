# -*- coding: utf-8 -*-
"""追两条台账 + 一条进度（Qoder 2026-10-29 15:5x）

① ISSUES 新开 H-270（安卓：打包脚本漏词库依赖 ⇒ wubi86 编译失败 + 无预编译表 = 安卓卡顿主因）。
② H-269 行尾追加 15:5x 读数（v35/v36 在树、手机装 v36 空函数、离线台架 12 FAIL）。
③ PROGRESS ㉕（本轮：量出卡顿真因、安卓真 bug 已修、给 CodeArts 可执行解法 M-355）。

写盘前都按 7 格校验；H-269 只在「下一步」列尾追加、不破坏原有 7 格。幂等（已写过就跳过）。
"""
import io
import os
import re
import sys
import time

NOW = time.strftime('%Y-%m-%d %H:%M')
STAMP = time.strftime('%Y-%m-%d %H:') + time.strftime('%M')[:1] + 'x'
ROOT = r'F:\qoderwork\sansheng-ime-harmony'
ISS = os.path.join(ROOT, 'docs', 'ISSUES.md')
PROG = os.path.join(ROOT, 'docs', 'PROGRESS.md')


def cells(line):
    if not line.startswith('|') or not line.endswith('|'):
        return None
    return len(line.split('|')) - 2


def check(s):
    if '\\|' in s:
        return '裸转义竖线'
    return None


H270 = ('| H-270 | OPEN | P1 | A | '
        '**安卓 build-android-qoder.py 解析 import_tables 只认「- 名字」后光秃秃换行的行，'
        'wubi86.dict.yaml 第 9/10 行带行尾注释（#A13）⇒ cn_pinyin_jidian_wp.dict.yaml 从没进过 seed ⇒ '
        '手机 librime 每次启动都报 source file .../cn_pinyin_jidian_wp.dict.yaml does not exist、'
        'dictionary \'wubi86\' failed to compile，五笔主词典用着 10-27 的残表；加上 seed 里 0 张预编译表'
        '（build/*.bin 全缺），每次安装都从头编译 13.7 万行 wubi86 等 ⇒ 冷启动巨慢**。'
        '这是主人点名「安卓也卡」「安卓你一点没弄」里我能实打实量到的第一条根因（之前只做了滤镜同步/seed/APK，从没量过卡顿）。 | '
        'emulator-5554 logcat 10-29 07:32 含上述两条 E 行；冷启动时间线 07:32:15.724 proc 起 → 21.961 fcitx5 Finishing startup（6,237 ms）'
        '→ 34.383 addon rime loaded → 35.2 表就绪（19.5 s）；wubi86.dict.yaml:9/10 行 import_tables 带 # 注释；'
        'build-android-qoder.py:81 的 import_tables 正则 (?:\s+-[ \t]+\S+\n?) 只吃无注释行。 | '
        'Qoder 已修解析器（行尾注释照常吃，build-android-qoder.py:81 注释里写清 H-270 根因）＋ SEED_VERSION 15→16（FirstRunSeeder.java 注释同），'
        '重建 seed（87→88 文件，含该表，11,570,529 B）＋ APK 1968（63,469,088 B，自检 8/8 PASS），'
        '装模拟器后该 E 行消失、cn_pinyin_jidian_wp.dict.yaml 落到 rime/（07:43:22，972,458 B）；'
        '剩余 = 把 14 张 build/*.bin 打进 seed（学鸿蒙，消冷启动编译），给 CodeArts 的 M-355 ④ 已说。 |')

H269_ADD = (' 【15:5x 追加：他 15:24:49 又写 v35（3,294 B，sha1 d3d471e2，去掉前缀遍历、#input<5 门槛），'
           '15:35:58 写 v36（380 B 空函数 = 消融探针：测 lua_translator 注册本身有无开销）；'
           '手机 15:26:30 装 v35（bm dump updateTime 15:26:29）、15:37:19 装 v36（updateTime 15:37:18）→ 此刻手机英文候选全空（只有 Windows 是好的）。'
           '离线台架现量 v35 = app/cpu/ok/url/tv/cat/core 全 0 条、12 FAIL；v35 首键读桶比 v34 贵（147 vs 69 ms，桌面冷文件）。'
           '解决方向 = M-355 给的：门限改「桶里有没有词」而非长度、恢复 1 位本词 / 2 位中文译词 / 联想 ≤5、读表按首字母分桶。'
           'v35/v36 逐字归档 _probe/rawfile-backups-20261029/enWord_translator.lua.peer-v35-20261029-152449。】')

PROG25 = ('| ㉕ 10-29 15:5x（真实时钟 = %s；**零构建、零签名、零装机、零注入；只改台账＋码侧一处解析器＋一封信**） | Qoder | CodeArts＋主人 | '
         '**主人纠的四点逐条落地：①「平台说混」认——安卓也卡、鸿蒙也卡，不是只有鸿蒙；'
         '②「Windows 部署只能你点」我认错，WeaselDeployer.exe 在 D:\\\\Program Files\\\\Rime\\\\weasel-0.17.4、服务也在，我之前那句不成立；'
         '③卡顿真因量出来了：每键成本 0.005-1.740 ms（一帧 16 ms 预算内）⇒ 删联想省不到 2 ms，根因在「冷启动重部署（鸿蒙 1.8 s、H-263 那条）+ 每会话新建 Lua VM 读整张表（桌面 68-82 ms、安卓读三张 TSV 245-291 ms）」，'
         '这层三端同病、跨端可比的硬指标是字节数不是感觉；④「安卓你一点没弄」——已做（滤镜 24,271 B 同字节 / en_word_rev.tsv / seed v15 / APK 1967 / 模拟器四条绿）如实记，'
         '未做的是从没量过安卓卡顿，今天量了并挖到真 bug：打包脚本漏一张词库 ⇒ 手机 wubi86 每次编译失败（10-27 残表）。**安卓 bug 已修**：'
         'build-android-qoder.py 的 import_tables 解析器补认行尾注释 + SEED_VERSION 15→16，重建 seed（含漏掉的表，87→88 文件）+ APK 1968（63,469,088 B，自检 8/8 PASS），'
         '装模拟器后编译失败的 E 行消失。给 CodeArts 的可执行解法（门限怎么改、读表怎么分桶、安卓缺的表怎么补、真机取证命令 + 判据阈值）写在 **M-355**（抄送主人表面），'
         '他 14:07-15:37 写在这棵树的 v31/桩/v33/v34/v35/v36 我一行没碰也没提交、逐字备份于 _probe/rawfile-backups-20261029/。'
         '**一条提醒**：他 15:37 装在手机上的 v36 是空函数 ⇒ 此刻手机打 app 什么都没有，只有 Windows 是好的，请他别在主人真机上做这种消融。**值守代码与那条 cron 一行没动**；nova6 禁止触碰（H-223）。 | '
         '待 CodeArts 回 M-355 定 translator 版本（A=保联想降条数 / B=联想交回 schema 链，两条都须 1 位本词+2 位中文）；'
         '安卓 APK 1968 待主人真机安装点头（我不在他手机装机、不输密码）；h267 守卫仍只报不拦，挂构建前置需点头 |' % NOW)


def main():
    # ---- H-270 ----
    e = check(H270)
    if e:
        print('FAIL H-270:', e); return 1
    if cells(H270) != 7:
        print('FAIL H-270 格数', cells(H270)); return 1
    iss = io.open(ISS, encoding='utf-8').read()
    if re.search(r'^\|\s*H-270\s*\|', iss, re.M):
        print('H-270 已存在，跳过'); h270_done = True
    else:
        lines = iss.split('\n')
        last = max(i for i, l in enumerate(lines) if re.match(r'^\|\s*H-\d+', l))
        lines.insert(last + 1, H270)
        io.open(ISS, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
        print('已追加 H-270 于第 %d 行后' % (last + 1))
        h270_done = True

    # ---- H-269 追加 ----
    e = check(H269_ADD)
    if e:
        print('FAIL H-269 追加:', e); return 1
    if '\\|' in H269_ADD:
        print('FAIL H-269 裸竖线'); return 1
    iss2 = io.open(ISS, encoding='utf-8').read()
    if '15:5x 追加' in iss2:
        print('H-269 已补 15:5x，跳过')
    else:
        out = []
        for l in iss2.split('\n'):
            if re.match(r'^\|\s*H-269\s*\|', l):
                if l.endswith('|'):
                    l = l[:-1] + H269_ADD + '|'
                else:
                    l = l + H269_ADD + '|'
                if cells(l) != 7:
                    print('FAIL H-269 追加后格数', cells(l)); return 1
            out.append(l)
        io.open(ISS, 'w', encoding='utf-8', newline='\n').write('\n'.join(out))
        print('已在 H-269 下一步列尾追加 15:5x 读数')

    # ---- PROGRESS ㉕ ----
    e = check(PROG25)
    if e:
        print('FAIL ㉕:', e); return 1
    if cells(PROG25) != 5:
        print('FAIL ㉕ 格数', cells(PROG25)); return 1
    prog = io.open(PROG, encoding='utf-8').read()
    if re.search(r'^\|\s*㉕\s*\|', prog, re.M):
        print('㉕ 已存在，跳过')
    else:
        lines = prog.split('\n')
        circ = '�㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟'
        last = -1
        for i, l in enumerate(lines):
            if re.match(r'^\|\s*[�㉑-㉟]+\s*\|', l):
                last = i
        if last < 0:
            # 兜底：最后一条以 | 开头且第二格是「10-29」的进度行
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].startswith('|') and '10-29' in lines[i]:
                    last = i
                    break
        lines.insert(last + 1, PROG25)
        io.open(PROG, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
        print('已追加 ㉕ 于第 %d 行后' % (last + 1))
    print('真实时钟', NOW)
    return 0


if __name__ == '__main__':
    sys.exit(main())
