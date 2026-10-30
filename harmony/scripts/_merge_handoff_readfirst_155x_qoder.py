# -*- coding: utf-8 -*-
"""合并 HANDOFF「当前状态」读首三格到 15:5x（Qoder 2026-10-29 15:5x）

规则（H-139）：读首每格只留一个带时间戳的段落；被合并掉的原文逐字进文末附录。
本脚本：① 把 14:5x 版三格原格文逐字搬到文末新附录块；② 用 15:5x 更正段落替换。
更正的三件事（主人本轮纠的）：Windows 部署本可我自己跑；平台说混（安卓也卡）；
安卓我没「一点没弄」（已做＋挖到并修了 wubi86 编译失败真 bug）；鸿蒙 v35/v36 把短词和联想删没了、手机此刻装的 v36 是空函数。
备份：_probe/rawfile-backups-20261029/HANDOFF.md.bak-qoder-20261029-155x-before-readfirst
幂等：文末已存在本轮附录块就只报「已归档过」。
"""
import io
import os
import shutil
import sys
import time

ROOT = r'F:\qoderwork\sansheng-ime-harmony'
P = os.path.join(ROOT, 'docs', 'HANDOFF.md')
BAK = os.path.join(ROOT, '_probe', 'rawfile-backups-20261029',
                   'HANDOFF.md.bak-qoder-20261029-155x-before-readfirst')
MARK = '### 2026-10-29 15:5x · Qoder（归档：本轮合并掉的「当前状态」三格原文＝15:1x/14:5x 版）'

KEYS = ['最近更新', '当前阻断', '等主人']

NEW = {
    '最近更新': (
        "**2026-10-29 15:5x（Qoder·主人纠四点＋卡顿真因量出来了＋安卓真 bug 已修＋给 CodeArts 可执行解法）**："
        "①**平台说混我认**：安卓也卡、鸿蒙也卡，不是只有鸿蒙。②**Windows 部署那步我认错**："
        "`WeaselDeployer.exe` 在 `D:\\Program Files\\Rime\\weasel-0.17.4`，进程也在那，我之前写「只能你点重新部署」是错的；"
        "我用同一份 24,271 B 滤镜（用户目录 sha1 cc786d1a…＝引擎读的那份）在本机真 librime 上跑，`app` 出来就是"
        "「1.app（注释 应用 application）2.应用」——和你屏幕一致，今后这步我自己做。③**卡顿真因量出来了**（同一份真 Lua 5.4＋同一份 1,508,284 B 桶，"
        "`_probe/krun_cost_qoder.py` 可复跑）：每键 0.005-1.740 ms（一帧 16 ms 预算内）⇒ 删联想省不到 2 ms，根因在「冷启动重部署」"
        "（鸿蒙真机 15:37:19.391→21.271 引擎就绪＝1,880 ms，其中 prebuild 298 ms、deploy 66 ms；H-263 那条）＋"
        "「每个输入窗口新建 Lua VM 把整张表读一遍」（桌面 68-82 ms；安卓读三张 TSV 3,108,920 B／118,680 行＝245-291 ms）。"
        "④**安卓我没「一点没弄」，但确实没量过卡顿——今天量了并挖到真 bug**：打包脚本 `build-android-qoder.py` 解析 `import_tables` 不认带行尾注释的行"
        "⇒ `cn_pinyin_jidian_wp.dict.yaml` 从没进过 seed ⇒ 手机 librime 每次启动报 `dictionary 'wubi86' failed to compile`（emulator-5554 logcat 07:32 实证）。"
        "已修解析器＋SEED_VERSION 15→16，重建 seed（87→88 文件，含该表，11,570,529 B）＋APK 1968（63,469,088 B，自检 8/8 PASS），"
        "装模拟器后该 E 行消失（H-270）。⑤**给 CodeArts 的可执行解法写在 M-355（抄送你表面）**：门限改「桶里有没有词」而非长度、"
        "恢复 1 位本词/2 位中文译词/联想≤5、读表按首字母分桶、安卓补漏掉的表＋把预编译表打进 seed、真机取证命令＋判据阈值都给了。"
        "⑥**一条提醒**：他 15:24:49 写 v35（3,294 B，砍前缀联想＋#input<5 门槛）、15:35:58 写 v36（380 B 空函数＝消融探针），"
        "手机 15:37:19 装的是 v36 ⇒ 此刻手机打 app 什么都没有（只有 Windows 是好的），请别在真机上装这种消融桩。"
        "⑨**值守代码与那条 cron 一行没动**；nova6 禁止触碰（H-223）。"
    ),
    '当前阻断': (
        "**2026-10-29 15:5x 刷新（Qoder）：阻断在交付手续＋一个口径回归，不在代码查找**。"
        "①**「Windows 部署只能你点」不成立**：`WeaselDeployer.exe` 在 `D:\\Program Files\\Rime\\weasel-0.17.4`，服务也可重启，"
        "我之前那句「只能你点」是错的（已在本行更正，前一句不删，H-139）。②**安卓 wubi86 编译失败已修（H-270）**："
        "打包脚本 `import_tables` 解析漏了带注释的行 ⇒ `cn_pinyin_jidian_wp.dict.yaml` 从没进 seed ⇒ 手机每次 `dictionary 'wubi86' failed to compile`；"
        "已修解析器＋SEED_VERSION 15→16，seed 含该表（87→88 文件）＋APK 1968（63,469,088 B，自检 8/8 PASS），模拟器 E 行已消失；"
        "剩余＝把 14 张 `build/*.bin` 打进 seed（学鸿蒙）以消冷启动编译。③**鸿蒙 v35/v36 口径回归（H-269）**："
        "v34/v35 的「#input<5 门槛」把 app/cpu/ok/url/tv/cat 全打成 0 条、删掉全部前缀联想，离线台架现量 v35＝12 FAIL；"
        "v36（手机此刻装的）是空函数 ⇒ 此刻手机英文候选全空（只有 Windows 好）；等 CodeArts 回 M-355 定版"
        "（A=保联想降条数／B=联想交回 schema 链，两条都须 1 位本词+2 位中文）。④**英文链 9 文件仍 untracked**（M-350 待他定 A/B 归属）。"
        "⑤进度阻断清零：CodeArts 今晚持续在写这棵树，不是零回执。"
    ),
    '等主人': (
        "**2026-10-29 15:5x 刷新（Qoder）：两拍都不用你输密码，且有一处要你挡一下**。"
        "**① Windows 那步我自己能做**：`WeaselDeployer.exe` 在 `D:\\Program Files\\Rime\\weasel-0.17.4`，下次我直接重启服务/触发部署自证，不麻烦你点（我之前说「只能你点」是错的，已更正）。"
        "**② 安卓我没「一点没弄」**：已做滤镜 24,271 B 同字节、反查表、seed v15、APK 1967、模拟器 cat/qtal/mao/app 四条绿；"
        "今天又挖到并修了 wubi86 编译失败真 bug（H-270，seed v16/APK 1968）。但安卓真机我还没装、nova6 禁止触碰（H-223），等你点头我再装真机验。"
        "**③ 鸿蒙待 CodeArts 回 M-355 定版后，我一次构建装机验 app→应用（别让输两次密码）**；"
        "**④ 一件要你挡的**：他 15:37 装在手机上的 v36 是英文 translator 空函数 ⇒ 此刻手机打英文什么都没有，"
        "只有 Windows 是好的；别在真机上验收这种消融桩，也别让我按它装机。⑤其余旧等验项（H-261 退格撤销三下、九键五枚置灰、H-264 已确认）见 ISSUES，本轮未新增。"
    ),
}


def split_row(line):
    if not line.startswith('|') or not line.endswith('|'):
        return None, None
    cells = line[1:-1].split('|')
    return cells[0].strip().strip('*').strip(), cells


def main():
    txt = io.open(P, encoding='utf-8').read()
    if MARK in txt:
        print('本轮附录已存在 ⇒ 不重复归档（幂等退出）')
        return 0
    lines = txt.split('\n')
    archived = {}
    for key in KEYS:
        for i, l in enumerate(lines[:60]):
            name, cells = split_row(l)
            if name == key and cells and len(cells) == 2:
                archived[key] = (i, l)
                break
        if key not in archived:
            print('FAIL 没找到「%s」格（应为 2 列行）' % key)
            return 1
    if not os.path.exists(BAK):
        shutil.copy2(P, BAK)
        print('已备份 HANDOFF ⇒ %s（%d B）' % (os.path.basename(BAK), os.path.getsize(BAK)))
    block = ['', MARK, '',
             '> 合并口径（H-139）：读首每格只留一个带时间戳的段落，被合并掉的原文逐字留这里，一字不改。', '']
    for key in KEYS:
        block.append('#### 旧「%s」格（2026-10-29 15:5x 合并 ⇒ 原文逐字留此）' % key)
        block.append('')
        block.append(archived[key][1])
        block.append('')
    for key in KEYS:
        i, old = archived[key]
        _, cells = split_row(old)
        new = '|' + cells[0] + '| ' + NEW[key] + ' |'
        if '|' in NEW[key]:
            print('FAIL 新格文里有裸竖线：%s' % key)
            return 1
        lines[i] = new
    lines.extend(block)
    io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    print('已替换三格（行 %s）并归档原文；文件 %d 行（真实时钟 %s）'
          % (','.join(str(archived[k][0] + 1) for k in KEYS), len(lines), time.strftime('%H:%M')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
