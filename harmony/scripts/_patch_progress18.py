# -*- coding: utf-8 -*-
"""修 PROGRESS ⑱：剔除被 CR 断坏的段，换成单行 5 格（行走脚本＋当场数格）。"""
import io, sys

p = r'F:\qoderwork\sansheng-ime-harmony\docs\PROGRESS.md'
t = io.open(p, encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in t else '\n'
L = t.replace('\r\n', '\n').split('\n')

# 先剔掉嵌入的裸 CR（把断行找回来）
joined = []
i = 0
while i < len(L):
    ln = L[i]
    if ln.startswith(u'| ⑱ 10-28 15:1x') and (u'\r' in ln or not ln.rstrip().endswith(u'|')):
        # 找到下一段是完整行尾的位置，合并回一行（原文里 \r 被 split 成了两段）
        j = i + 1
        while j < len(L) and not L[j].startswith(u'| ') and not L[j].startswith(u'#'):
            j += 1
        # L[i] 与 L[i+1..j-1] 其实是一行被 \n(原为\r) 切断；但 \n join 会丢字符顺序，
        # 直接弃掉坏段，重写整行（内容我全知道）。
        del L[i+1:j]
        L[i] = u'PLACEHOLDER'
    i += 1

ROW = (u'| ⑱ 10-28 15:1x | Qoder | 主人 | 合树提交（CodeArts 在途 H-239/H-240/H-257/H-258 '
       u'经逐文件审查＋安全扫描＝零权限零网络零新增声明入树，commit／信箱 M-310／HANDOFF 三处声明）'
       u'＋h190 判据换档六条新断言（负控 22/22）＋离线套 14/14 全绿＋`settings_effective_check.py --head` '
       u'12/12（H-251 闭）＋release 构建 unsigned **27,902,192 B**（15:11:33；17/17 内容闸门 --source 绿） | '
       u'就绪待主人：跑 release_build.ps1 的 `-SkipBuild` 通路输一次发布密码出上架 .app'
       u'（OWNER-ACTIONS 第 16 行；我不碰 sign 目录与任何密码） |')

hits = [k for k, l in enumerate(L) if l == u'PLACEHOLDER' or l.startswith(u'| ⑱ 10-28 15:1x')]
if len(hits) != 1:
    print('FAIL ⑱ 段命中 %d 处' % len(hits)); sys.exit(1)
L[hits[0]] = ROW
n = len([x for x in ROW.split(u'|')]) - 2
assert n == 5, '格子数=%d' % n
io.open(p, 'w', encoding='utf-8', newline='').write(nl.join(L))
print('PROGRESS ⑱ 修复，单行 5 格')
