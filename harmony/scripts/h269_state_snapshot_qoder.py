# -*- coding: utf-8 -*-
"""写台账/写信之前先量的「现状快照」（Qoder 15:0x，H-269 同族的**拦截式**修法）

为什么建这个：2026-10-29 这一小时里我连着写错两次现状——
①14:58 的信里写「树内＝505 B 消融桩」，其实 14:57:36 已被换成 v33；
②15:01 的读首里写「手机仍跑 14:10:04 那份」，其实 14:58:29 已经装过一次（装的是含 v33 的包）。
两次都不是判断错，是**没重测**（H-222 同族：引用记忆里的数字＝散文式修复）。
所以从现在起：凡要落「字节数／时间戳／在位版本」这类数字，先跑这一支，照抄它的输出，别抄记忆。

它只做四件只读的事：
  ① 工作区英文链三件套（translator／桶／挂载行）的字节数＋sha1＋mtime＋挂载状态；
  ② 本地最新 unsigned／signed HAP 的字节数＋sha1＋mtime，并从 **HAP 里**再读一次 translator／桶；
  ③ 设备（Mate 80）当前包的 versionCode／installTime／updateTime（真机读数，不猜）；
  ④ 台账闸门与两条守卫的当前退出码。
不写任何文件，不改任何东西；退出码恒 0（除 hdc 不可用会给 WARN），因为它不是判据而是**取数**。

用法：
    python scripts/h269_state_snapshot_qoder.py            # 全部四项
    python scripts/h269_state_snapshot_qoder.py --no-device # 手机没插/不想碰 hdc 时
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUA_DIR = os.path.join(ROOT, 'entry', 'src', 'main', 'resources', 'rawfile', 'rime', 'lua')
CUSTOM = os.path.join(ROOT, 'entry', 'src', 'main', 'resources', 'rawfile', 'rime', 'wubi_pinyin.custom.yaml')
HAP_DIR = os.path.join(ROOT, 'entry', 'build', 'default', 'outputs', 'default')
HDC = r'D:\DevTools\DevEco\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe'
DEVICE = '7GL0226408083897'
BUNDLE = 'com.sansheng.ime'

TARGETS = ['enWord_translator.lua', 'en_word_bucket.txt', 'enWord_Filter.lua']


def fmt(p):
    d = io.open(p, 'rb').read()
    return '%d B／sha1 %s／mtime %s' % (
        len(d), hashlib.sha1(d).hexdigest()[:12],
        time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(p))))


def mount_state():
    """从 custom.yaml 里读英文 translator 的挂载状态：返回 (状态词, 行号, 原文)。"""
    lines = io.open(CUSTOM, encoding='utf-8').read().split('\n')
    for i, l in enumerate(lines):
        if 'lua_translator@enWord_translator' in l:
            s = l.strip()
            if s.startswith('#'):
                return ('已注释（不出英文候选）', i + 1, s)
            return ('已挂载', i + 1, s)
    return ('树里没有这一行', 0, '')


def hap_info():
    out = []
    for name in ('entry-default-unsigned.hap', 'entry-default-signed.hap'):
        p = os.path.join(HAP_DIR, name)
        if not os.path.exists(p):
            out.append('  %s：不存在' % name)
            continue
        d = io.open(p, 'rb').read()
        row = '  %s：%d B／sha1 %s／mtime %s' % (
            name, len(d), hashlib.sha1(d).hexdigest()[:12],
            time.strftime('%m-%d %H:%M:%S', time.localtime(os.path.getmtime(p))))
        try:
            z = zipfile.ZipFile(p)
            row += '／条目 %d' % len(z.namelist())
            for key in ('resources/rawfile/rime/lua/enWord_translator.lua',
                        'resources/rawfile/rime/lua/en_word_bucket.txt'):
                if key in z.namelist():
                    b = z.read(key)
                    row += '\n      包内 %s＝%d B／sha1 %s' % (
                        os.path.basename(key), len(b), hashlib.sha1(b).hexdigest()[:12])
            baks = [n for n in z.namelist()
                    if re.search(r'\.(bak|orig)(?:$|[-.])|副本|~', n)]
            row += '／备份残留 %d 条' % len(baks)
        except zipfile.BadZipFile:
            row += '／读不到 zip'
        out.append(row)
    return '\n'.join(out)


def device_info():
    if not os.path.exists(HDC):
        return '  WARN hdc 不在 %s（换路径或用 --no-device）' % HDC
    try:
        r = subprocess.run([HDC, '-t', DEVICE, 'shell', 'bm dump -n ' + BUNDLE],
                           capture_output=True, text=True, timeout=40,
                           encoding='utf-8', errors='replace')
    except Exception as e:  # noqa: BLE001 - 取数工具不许抛
        return '  WARN hdc 调用失败：%s' % e
    txt = r.stdout or ''
    if not txt.strip():
        return '  WARN bm dump 无输出（设备没插／未授权）：%s' % (r.stderr or '').strip()[:160]
    # `bm dump -n <bundle>` 的首行是 “<bundle>:”，JSON 从第一个左花括号开始（真机实测形状）
    brace = txt.find('{')
    if brace < 0:
        return '  WARN bm dump 输出里没有 JSON：%s' % txt.strip()[:160]
    try:
        obj = json.loads(txt[brace:])
    except ValueError as e:
        return '  WARN bm dump 不是合法 JSON（%s）：%s' % (e, txt[brace:brace + 120].replace('\n', ' '))
    def ts(v):
        return '%d＝%s' % (v, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(v / 1000.0)))
    return '\n'.join([
        '  设备 %s／bundle %s（真机读数）：' % (DEVICE, BUNDLE),
        '    versionCode＝%s' % obj.get('versionCode'),
        '    installTime＝%s' % ts(obj.get('installTime', 0)),
        '    updateTime＝%s  ← 「手机上现在跑的是哪一次装机」只看这个' % ts(obj.get('updateTime', 0)),
    ])


def guard(name):
    p = os.path.join(ROOT, 'scripts', name)
    r = subprocess.run([sys.executable, p], capture_output=True, text=True, timeout=300,
                       encoding='utf-8', errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    tail = [l for l in (r.stdout or '').splitlines() if l.strip()]
    return '  %s ⇒ rc=%s ｜ %s' % (name, r.returncode, tail[-1] if tail else '（无输出）')


def main():
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    print('== 现状快照（只读，写信/写台账前照抄这里，别抄记忆）==  本机时钟 %s' % now)
    print('① 工作区英文链：')
    for f in TARGETS:
        p = os.path.join(LUA_DIR, f)
        print('  %s＝%s' % (f, fmt(p) if os.path.exists(p) else '不存在'))
    st, ln, raw = mount_state()
    print('  挂载（`wubi_pinyin.custom.yaml:%d`）＝%s ｜ 原文：%s' % (ln, st, raw[:70]))
    print('② 本地产物：')
    print(hap_info())
    if '--no-device' in sys.argv:
        print('③ 设备：跳过（--no-device）')
    else:
        print('③ 设备：')
        print(device_info())
    print('④ 闸门与守卫：')
    for g in ('h266_package_hygiene_check.py', 'h267_english_candidates_check.py'):
        print(guard(g))
    print(guard('doc_table_shape_check.py'))
    print('用法提醒：本脚本不是判据（不参与阻断），它只保证「落笔的数字是刚刚量出来的」（H-134／H-222）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
