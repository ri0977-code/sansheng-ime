# -*- coding: utf-8 -*-
"""把 Qoder 的 v32 索引版 translator 放回打包树（默认试运行，--apply 才写盘）。

为什么要有这个脚本（H-129/H-250 口径）：
2026-10-29 14:29–14:48 这二十分钟里，CodeArts 连着三次改 `enWord_translator.lua` 与它的挂载行
（14:29:36 注释挂载 → 14:43:38 换成他自己的「排序＋二分」v31 → 14:48:10 换成 505 B 最小化实验桩）。
我这版 8,553 B 在 14:43:38 被他覆盖，**当时 M-348 他还没读到**。撞车的正确处理不是把对方改动 revert 回去，
而是：①他的两份改动我逐字归档、可随时恢复；②我那版停在打包树外的 patch 路径，带自检与一条命令可回；
③谁覆盖谁，写在信箱里，由做决定的人（此刻是拿着真机做消融实验的 CodeArts）来落。

它会做：
  · 试运行＝只报「树里现在是哪版（字节数／sha1／首行）」＋「将要写入什么」；
  · `--apply`＝先把树内当前文件逐字备份进 `_probe/rawfile-backups-20261029/`（带真实时间戳），
    再写入 patch 版，写完复核字节数与 sha1；
  · 幂等：树里已经是这版（sha1 相同）就直接退出，不重复写。
"""
import hashlib
import io
import os
import subprocess
import sys

ROOT = r'F:\qoderwork\sansheng-ime-harmony'
TARGET = os.path.join(ROOT, 'entry', 'src', 'main', 'resources', 'rawfile', 'rime', 'lua',
                      'enWord_translator.lua')
PATCH = os.path.join(ROOT, '_probe', 'patches-20261029',
                     'enWord_translator.lua.qoder-v32-indexed')
ARCHIVE = os.path.join(ROOT, '_probe', 'rawfile-backups-20261029')

EXPECT_SHA1 = '921bf7439e8d'   # 8,547 B；离线基准 122 个查询产出全等、每按键 0.007 ms


def sha1(b):
    return hashlib.sha1(b).hexdigest()[:12]


def describe(path):
    if not os.path.exists(path):
        return '（不存在）'
    d = open(path, 'rb').read()
    first = d.split(b'\r\n')[0].decode('utf-8', 'replace')
    second = (d.split(b'\r\n') + [b''])[1].decode('utf-8', 'replace')
    return '%s B  sha1 %s  首行「%s」次行「%s」' % (
        "{:,}".format(len(d)), sha1(d), first.strip(), second.strip()[:70])


def main():
    apply = '--apply' in sys.argv
    patch_bytes = open(PATCH, 'rb').read()
    if sha1(patch_bytes) != EXPECT_SHA1:
        print('FAIL patch 自身 sha1 变了：%s（应为 %s）——先确认改的是哪一份，再谈放回'
              % (sha1(patch_bytes), EXPECT_SHA1))
        return 1
    now = open(TARGET, 'rb').read() if os.path.exists(TARGET) else b''
    print('树内现在：', describe(TARGET))
    print('将要写入：', describe(PATCH))
    if sha1(now) == EXPECT_SHA1:
        print('SKIP 树内已经是这一版（幂等退出）')
        return 0
    if not apply:
        print('DRY-RUN 没写盘。确认要放回再加 --apply（会先把现在这份逐字备份，不删）')
        return 0
    stamp = subprocess.run(['date', '+%Y%m%d-%H%M%S'], capture_output=True, text=True).stdout.strip()
    bak = os.path.join(ARCHIVE, 'enWord_translator.lua.in-tree-before-v32apply-%s' % stamp)
    with open(bak, 'wb') as f:
        f.write(now)
    print('已备份树内当前这份 → %s（%s B）' % (os.path.relpath(bak, ROOT), "{:,}".format(len(now))))
    with open(TARGET, 'wb') as f:
        f.write(patch_bytes)
    after = open(TARGET, 'rb').read()
    if sha1(after) != EXPECT_SHA1:
        print('FAIL 写完复核不一致：%s' % describe(TARGET))
        return 1
    print('OK 已放回 v32 索引版：%s' % describe(TARGET))
    print('   复验：python _probe/bench_enword_translator_qoder.py %s %s'
          % (os.path.relpath(TARGET, ROOT),
             '_probe/rawfile-backups-20261029/enWord_translator.lua.bak-qoder-20261029-143x-before-bisect'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
