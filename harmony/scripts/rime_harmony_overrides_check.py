#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-222(Qoder) 鸿蒙专用词库配置守卫：防止 `port_rime_data.py` 把桌面端配置盖进鸿蒙包。

为什么需要这条闸门（事故实录，**第二次**）：
  `scripts/port_rime_data.py` 的活儿是「从桌面三端（W=F:/workbuddywork/三生输入法/rime、
  D=D:/Program Files/Rime、A=%APPDATA%/Rime）按同名取最新，写进
  `entry/src/main/resources/rawfile/rime/`」。也就是说：它一跑，鸿蒙包里那些
  **故意和桌面不一样**的行就会被桌面板覆盖掉。桌面端那些差异不是随手改的，每一条都是
  主人在真机上拍过的口径。

  · 第一次 2026-10-22 12:37：有人按字面跑 `port_rime_data.py`（那时 `--check` 旗标
    根本不存在）⇒ 全量移植，`db_class` 从 userdb 被覆盖回 tabledb（M4 自造词持久化修复被吞）。
    当时的处置是「在脚本里写注释 + 加真只读的 --check」。
  · 第二次 2026-10-27 15:27:17~18：**注释没能拦住第二次**。一次非 dry 运行重写
    rawfile/rime/** 与 `docs/evidence/2026-10-21/m3-data-manifest.json`
    （`generated_at: 2026-10-27 15:27:18`，total_bytes 20,528,604 → 15,049,369），代价：
      1) `engine/translators` 里 `script_translator@pinyin` 被桌面的 `lua_translator@slash_translator`
         顶掉 ⇒ **26 键拼音整句/逐字候选没了**（H-089）；
      2) `punctuator/import_preset` 回到 `symbols`，并把 `symbols.yaml`＋`symbols.custom.yaml`
         （上游、许可不可再分发）放回 rawfile ⇒ **D-020 提审阻断项复活**；
      3) `lua_filter@phoneComment_Filter` 被换回桌面 `laneChangeAndSpace_Filter`
         （M-235：150 字符上限＋`<br>` 真换行，手机上把一个候选撑成 3 行）；
      4) `translator/db_class` 又回到 `tabledb`（M4：鸿蒙 IME 进程常驻、无 finalize ⇒
         user.txt 永远只有表头，自造词/自调频跨会话全丢）；
      5) `zh2en_pinyin.dict.yaml` 从 2,163,401 B 的全量表变成 440 B 的 import_tables 壳
         （数据仍在 `zh2en_pinyin_wp.dict.yaml`，功能不一定坏，但**没人批准过这次替换**）；
     发布闸门 `check_app_content.py` 当场 13/16（3 条阻断红），unsigned HAP
     28,443,643 → 26,235,679 B（少 2.2 MB 就是上面第 5 条）。

判据（1~4 阻断，5 只报不拦）：
  1. `wubi_pinyin.custom.yaml` 里有 `script_translator@pinyin`
  2. `wubi_pinyin.custom.yaml` 里 `import_preset: default`，且没有 `import_preset: symbols`
  3. `wubi_pinyin.custom.yaml` 里过滤器是 `phoneComment_Filter`，且没有 `laneChangeAndSpace_Filter`
  4. `wubi_pinyin.schema.yaml` 里 `db_class: userdb`，且没有 `db_class: tabledb`
  5. rawfile/rime 下没有 `symbols.yaml` / `symbols.custom.yaml`（D-020）
  WARN：`zh2en_pinyin.dict.yaml` < 1 MB ⇒ 提示被换成了 import 壳，需主人点头才接受（不阻断）

用法：
  python scripts/rime_harmony_overrides_check.py            # 跑守卫，红=退出码 1
  python scripts/rime_harmony_overrides_check.py --selftest  # 用 15:27 那份真实坏数据验证会红

严重度：**开发期守卫，不进发布阻断闸门**（发布闸门仍是 `check_app_content.py` 的 16 条；
这里 1~4 与它有重叠，作用是「构建前一眼看出词库被盖了」，而闸门要到打包后才报）。
**跑过 `port_rime_data.py`（任何不带 --dry/--check 的调用）之后必须跑它。**
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIME = os.path.join(ROOT, 'entry', 'src', 'main', 'resources', 'rawfile', 'rime')
CUSTOM = os.path.join(RIME, 'wubi_pinyin.custom.yaml')
SCHEMA = os.path.join(RIME, 'wubi_pinyin.schema.yaml')
ZH2EN = os.path.join(RIME, 'zh2en_pinyin.dict.yaml')

# (说明, 文件, 必须出现的正则) —— 阻断项
RULES = [
    ("26 键拼音翻译器在（H-089/M5）", CUSTOM, r"-\s*script_translator@pinyin"),
    ("punctuator 指 default（D-020）", CUSTOM, r"import_preset:\s*default"),
    ("手机版截断滤镜在位（M-235）", CUSTOM, r"-\s*lua_filter@phoneComment_Filter"),
    ("用户词典走 userdb（M4）", SCHEMA, r"db_class:\s*userdb"),
]

# 「不得出现」——阻断项
FORBIDDEN = [
    ("不得有 import_preset: symbols", CUSTOM, r"import_preset:\s*symbols"),
    ("不得退回桌面截断滤镜", CUSTOM, r"-\s*lua_filter@laneChangeAndSpace_Filter"),
    ("不得退回 tabledb", SCHEMA, r"db_class:\s*tabledb"),
]

# rawfile 里不允许存在的上游符号文件（D-020，许可不可再分发）
BANNED_FILES = ['symbols.yaml', 'symbols.custom.yaml']

# 只报不拦：中→英拼音主表被换成 import_tables 壳（桌面拆分版）。
# 数据本身还在 zh2en_pinyin_wp.dict.yaml，功能未必坏，但这属于「词库被替换」，
# 要主人点头才能接受 ⇒ WARN，不影响退出码。
WARN_MIN_BYTES = 1024 * 1024

# 已知错误样本（--selftest 用）：就是 2026-10-27 15:27 那次覆盖后的真实形态
BAD_CUSTOM = """  engine/translators/+:
    - table_translator@custom_phrase
    - lua_translator@slash_translator
  engine/filters:
    - lua_filter@laneChangeAndSpace_Filter
  recognizer/patterns/punct: "^/([0-9]0?|[A-Za-z]+)$"
  punctuator:
    import_preset: symbols
"""
BAD_SCHEMA = """engine:
  translators:
    - table_translator
translator:
  enable_user_dict: true
  db_class: tabledb
"""
BAD_ZH2EN = """# 【拆分版】供 table_translator@zh2en_pinyin 挂载
---
name: zh2en_pinyin
import_tables:
  - zh2en_pinyin_wp
...
"""


def read(path):
    return io.open(path, encoding='utf-8', errors='replace').read()


def run(custom_text, schema_text, zh2en_bytes, rime_listing):
    """返回 (通过数, 阻断失败, 警告列表)。"""
    texts = {CUSTOM: custom_text, SCHEMA: schema_text}
    fails = []
    warns = []
    passed = 0
    for name, path, pat in RULES:
        if re.search(pat, texts[path]):
            passed += 1
        else:
            fails.append('缺: %s' % name)
    for name, path, pat in FORBIDDEN:
        if re.search(pat, texts[path]):
            fails.append('禁: %s' % name)
        else:
            passed += 1
    for fn in BANNED_FILES:
        if fn in rime_listing:
            fails.append('禁: rawfile/rime 里有上游 %s（D-020 提审阻断）' % fn)
        else:
            passed += 1
    if zh2en_bytes < WARN_MIN_BYTES:
        warns.append('WARN: zh2en_pinyin.dict.yaml 只有 %d B ⇒ 被换成了 import_tables 壳'
                     '（原全量表 2,163,401 B）。数据仍在 zh2en_pinyin_wp.dict.yaml，'
                     '但这是词库替换，需主人点头。' % zh2en_bytes)
    return passed, fails, warns


def main():
    selftest = '--selftest' in sys.argv[1:]
    if selftest:
        passed, fails, warns = run(BAD_CUSTOM, BAD_SCHEMA, len(BAD_ZH2EN.encode('utf-8')),
                                   BANNED_FILES[:])
        must_hit = ['缺: 26 键拼音翻译器在（H-089/M5）',
                    '禁: 不得有 import_preset: symbols',
                    '禁: 不得退回桌面截断滤镜',
                    '禁: 不得退回 tabledb',
                    '禁: rawfile/rime 里有上游 symbols.yaml（D-020 提审阻断）']
        hit = [m for m in must_hit if m in fails]
        if len(hit) == len(must_hit) and warns:
            print('SELFTEST OK：15:27 那份坏数据被拦下（阻断命中 %d/%d，总失败 %d 条，WARN %d 条）'
                  % (len(hit), len(must_hit), len(fails), len(warns)))
            return 0
        print('SELFTEST FAIL：检查本身失效，命中=%s / fails=%s / warns=%s' % (hit, fails, warns))
        return 1
    custom_text = read(CUSTOM)
    schema_text = read(SCHEMA)
    zh2en_bytes = os.path.getsize(ZH2EN) if os.path.exists(ZH2EN) else 0
    listing = sorted(os.listdir(RIME))
    passed, fails, warns = run(custom_text, schema_text, zh2en_bytes, listing)
    total = passed + len(fails)
    for w in warns:
        print('[WARN] %s' % w)
    for f in fails:
        print('[FAIL] %s ← 词库配置被 port_rime_data.py 盖掉了' % f)
    print('鸿蒙词库口径守卫: %d/%d 通过（阻断项）' % (passed, total))
    if fails:
        print('结论: **别装机**。15:27 那次的处置见 docs/evidence/2026-10-27/h222-rime-port-overwrite/，'
              '恢复方法＝从 HEAD 还原 4 个文件 + 把 symbols*.yaml 请出 rawfile。')
        return 1
    print('结论: script_translator@pinyin / import_preset: default / phoneComment_Filter / '
          'db_class: userdb 四条鸿蒙专用口径全在位，rawfile 无上游符号文件。')
    if warns:
        print('（上面 WARN 不计入阻断，退出码仍是 0。）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
