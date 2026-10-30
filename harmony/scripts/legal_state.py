#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""读取 uitest dumpLayout 的 JSON，输出 LegalPage 关键状态（Web src + 首个标题）。
用法: python scripts/legal_state.py <layout.json> <out.txt>
结果写文件（UTF-8），避免 Windows GBK 控制台乱码。"""
import json
import sys


def collect(path):
    d = json.load(open(path, encoding='utf-8'))
    web = []
    heads = []

    def walk(n):
        a = n.get('attributes', {}) or {}
        t = a.get('type', '')
        if t == 'Web':
            web.append(a.get('text', ''))
        if t == 'heading':
            heads.append((a.get('text', ''), a.get('bounds', '')))
        for c in (n.get('children') or []):
            walk(c)
    walk(d)
    return web, heads


def main():
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    web, heads = collect(src)
    lines = ['WEB: ' + (' | '.join(web) if web else 'NONE')]
    for h in heads[:2]:
        lines.append('H: %s  %s' % (h[0], h[1]))
    text = '\n'.join(lines) + '\n'
    if dst:
        open(dst, 'a', encoding='utf-8', newline='\n').write(text + '---\n')
    else:
        sys.stdout.buffer.write(text.encode('utf-8'))


main()
