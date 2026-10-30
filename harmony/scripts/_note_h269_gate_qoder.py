# -*- coding: utf-8 -*-
"""给 H-269 的「下一步」格补一条**提案**（不擅自动别人的闸门）（Qoder 15:0x）

内容：建议把 `scripts/h267_english_candidates_check.py` 挂进构建前置，作为「英文链不得交付
只回吐／无联想／无第二条中文的版本」的硬闸门；但它现在只是我手跑的独立检查，
`build.ps1` 与 `h106_precheck.py` 都没引用它（本轮实测 grep：只有文档与我的脚本提到）。
挂闸门会改变 CodeArts 的构建通路 ⇒ 需他或主人点头，我不自作主张。
幂等：该行已含本轮标记就跳过。
"""
import io
import os
import sys
import time

ROOT = r'F:\qoderwork\sansheng-ime-harmony'
ISSUES = os.path.join(ROOT, 'docs', 'ISSUES.md')
NOTE = ('【15:0x 补一条提案（需点头，我不擅自动别人的闸门）：把 `scripts/h267_english_candidates_check.py` '
        '挂进构建前置，硬拦「桶里本词缺失／发布清单没列翻译器与桶／代码是只回吐或砍掉联想的形状」这三类交付；'
        '本轮实测该守卫目前只是我手跑的独立检查，`build.ps1` 与 `h106_precheck.py` 里都没有引用它（全文 grep 只命中我的文档与脚本），'
        '所以现在谁也拦不住 ⇒ 挂上去会改 CodeArts 的构建通路，要他或主人点头我才动；不点头就维持「只报不拦」。】')


def main():
    txt = io.open(ISSUES, encoding='utf-8').read()
    lines = txt.split('\n')
    hit = [i for i, l in enumerate(lines) if l.startswith('| H-269 ')]
    if len(hit) != 1:
        print('FAIL H-269 行数=%d（应为 1）' % len(hit))
        return 1
    i = hit[0]
    parts = lines[i].split('|')
    if len(parts) - 2 != 7:
        print('FAIL H-269 是 %d 格，应为 7 格' % (len(parts) - 2))
        return 1
    if '15:0x 补一条提案' in parts[7]:
        print('H-269 已带本轮提案 ⇒ 跳过（幂等）')
        return 0
    parts[7] = parts[7].rstrip() + ' ' + NOTE + ' '
    new = '|'.join(parts)
    if len(new.split('|')) - 2 != 7:
        print('FAIL 追加后变 %d 格（文本里有裸竖线）' % (len(new.split('|')) - 2))
        return 1
    lines[i] = new
    io.open(ISSUES, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    print('已给 H-269 补提案（行 %d，+%d 字符，真实时钟 %s）' % (i + 1, len(NOTE), time.strftime('%H:%M')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
