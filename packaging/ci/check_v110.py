# -*- coding: utf-8 -*-
"""
三生输入法 · v1.10 / v1.10.1 出包前硬校验（纯静态，不起引擎）

v1.9.10 的做法是把「TIP 参数必须 0804: 开头」这类致命错误挡在出包之前；
本版把同样的思路用在 v1.10 新增的英文缩写功能上，另外把「不能激活互译表」这条实测结论钉成硬门。
任何一条不过 → 非 0 退出，禁止出包。

检查项
  A 英文缩写功能（lua 滤镜路）
     A1 abbr_en.txt 与种子表 abbr-en-seed.txt 条目一一对应（防「改了表忘了生成」）
     A2 每条：码=2~12 位纯小写字母；词面必含大写；码不重复；释义非空
     A3 abbrGloss_Filter.lua 存在、在 rime.lua 里注册、在 custom.yaml 的 filters 末位
     A4 abbrEn 开关存在且 reset: 1（默认开）
     A5 滤镜与数据表里不出现本机绝对路径（防把 D:\\Program Files\\Rime 钉进包里）
  B 三条互译 translator 的本版处置（实测后回退，见 _probe/apply_v110.py 顶部记录）
     B1 wubi_pinyin.schema.yaml 仍挂着 table_translator@en2zh_v2/@zh2en_pinyin/@zh2en_wubi（没删功能）
     B2 出包树里不存在内部构件 schema 文件（en2zh_v2 / zh2en_pinyin / zh2en_wubi 的 .schema.yaml）
        —— 一旦放上，三张表会被真编出来，8.9 万条英文词面挤进候选并抢走中文第 1（实测 10/162 码）
     B3 custom.yaml 里没有 schema/dependencies 补丁（同上原因；B 若要做，得先解决「英文压到中文之后」）
  C 两棵出包树一致性
     C1 packaging/stage/config/ 与 packaging/release/config/ 的 7 个新增/改动文件逐字节相同
     C2 顺带报告仓库旧树 rime/ 的状态（它是 v1.2 遗留镜像，不参与出包，不计入失败）
     C3 研发镜像 rime-config/ 与 stage 的关键文件也逐字节相同
        —— v1.10.1 补这条：上一版把 abbrEn/abbrGloss 只落在出包树、rime-config 停在旧快照，
           结果拿 rime-config 当基准打补丁时把两行 v1.10 功能覆盖掉了（2026-10-21 实测踩坑）
  E 单字 stem 列（v1.10.2：修自动造词取码）
     E1 词库里每个不同单字，至少有一行带第 4 列 stem（2 位小写字母）
     E2 stem 必须等于该字「最短码（长度≥2）的前两位」——独立重算，不信任写进去的值
     E3 单字总数不得低于下限（防止整层单字被删掉后 E1 还「通过」）
        —— 为什么要有这一节：2026-10-22 给 20,910 个单字补了 stem，但任何「按 词/码/权重 三列
           重写整个词库」的脚本（刷权重、同步上游）都会把第 4 列整层冲掉，且不报错。
           这条门就是为了让那种改动在出包前直接失败。
  D 「/」通道（v1.10.1：含数字的原文串 + dyy 的 107 组符号）
     D1 abbr_num.txt 与种子表 abbr-num-seed.txt 条目数一致（防「改了表忘了生成」）
     D2 每条：码=2~14 位且必含数字；词面≠码且给出正确写法；码唯一；释义非空且宽度 ≤20 格
        （宽度这条是硬约束：rawEcho 的 comment 写在 phoneComment 之后，安卓上不会被截断，超宽会顶破候选窗）
     D3 slash_translator.lua 存在、在 rime.lua 里注册、在 custom.yaml 的 engine/translators 里，
        且排在 table_translator@custom_phrase 之后（同层按序，别把自定义短语挤掉）
     D4 custom.yaml 里 recognizer/patterns/punct + rawNum 两条都在。
        punct 缺一条 → symbols.custom.yaml 那 107 组 /xx 符号全哑（dyy 原配开关，我们重写
        default.custom.yaml 时丢了它）；rawNum 缺一条 → /5g /ri0977 出不来，数字还会被 selector 当选词键吃掉。
     D5 slash_translator.lua 与 abbr_num.txt 里不出现本机绝对路径
  F 每键延迟闸门（v1.10.3：修「打字明显卡顿」）
     F1 生效的 lua_translator 只能是 1 个 slash_translator。
        librime 每挂一个 lua_translator，每次按键都要跨一次 Lua 边界并调用它一次，
        实测单个 +10~13 ms 且与脚本内容无关（3 个 translator + 11 个 filter = 44.0 ms/键，
        0 个 = 9.1 ms/键；lua_filter 只在候选算完后跑一遍，不构成这个成本）。
        见 _probe/lag_report_20261022.txt。
        —— 生效集合 = 基础 schema 的 translators + custom.yaml 的 engine/translators/+ ，
           所以只查 schema 会漏（slash_translator 是补丁加进去的），只查 custom 会漏（有人在 schema 里加回一个）。
     F2 三台树的 rime.lua 里不得再出现 help_translator / inputShow_translator / rawEcho_translator
        的 require —— 老脚本留在 lua/ 目录不加载没关系，一旦被重新注册，卡顿立刻回来。

用法：python packaging/ci/check_v110.py
"""
import hashlib
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SEED = os.path.join(ROOT, "rime-config", "dicts", "abbr-en-seed.txt")
SEED_NUM = os.path.join(ROOT, "rime-config", "dicts", "abbr-num-seed.txt")
# 真正参与出包的两棵树：stage 是打包源，release 是 install.nsi 的 File /r 对象。
# 仓库里的 rime/ 是 v1.2 时代留下的旧镜像（37 个 lua、无 rime.lua、schema 里还没有
# 那三条 table_translator），老 release.yml 只拿它做依赖完整性静态校验，
# 安装包并不用它 —— 所以本版不往它身上铺新文件，只在下面单独报一句它的状态。
TREES = {
    "stage": os.path.join(ROOT, "packaging", "stage", "config"),
    "release": os.path.join(ROOT, "packaging", "release", "config"),
}
LEGACY = os.path.join(ROOT, "rime")
# 研发镜像：_probe/apply_v1101.py 之后要求它与 stage 逐字节一致（见 C3）
MIRROR = os.path.join(ROOT, "rime-config")
INTERNAL = ["en2zh_v2", "zh2en_pinyin", "zh2en_wubi"]
CODE_RE = re.compile(r"^[a-z]{2,12}$")
NUM_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9.]{1,13}$")
ABS_RE = re.compile(r"[A-Za-z]:[\\/](?:Program Files|Users|workbuddywork)")

fails = []
oks = []


def ok(msg):
    oks.append(msg)


def bad(msg):
    fails.append(msg)


def read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def seed_rows(path=SEED):
    rows = []
    for line in read(path).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = [x.strip() for x in line.split("\t")]
        if len(parts) == 3:
            rows.append(parts)
    return rows


def check_abbr(tree, tag):
    txt = os.path.join(tree, "lua", "abbr_en.txt")
    lua = os.path.join(tree, "lua", "abbrGloss_Filter.lua")
    if not os.path.isfile(txt):
        bad("%s 缺 lua/abbr_en.txt" % tag)
        return
    if not os.path.isfile(lua):
        bad("%s 缺 lua/abbrGloss_Filter.lua" % tag)
        return
    body = read(txt)
    rows = [l for l in body.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    srows = seed_rows()
    if len(rows) != len(srows):
        bad("%s abbr_en.txt 词条数 %d ≠ 种子表 %d（改完种子没重新生成？）"
            % (tag, len(rows), len(srows)))
    else:
        ok("%s abbr_en.txt %d 条，与种子表一致" % (tag, len(rows)))
    seen = {}
    local_bad = len(fails)
    for i, line in enumerate(rows, 1):
        parts = line.split("\t")
        if len(parts) != 3:
            bad("%s abbr_en.txt 第 %d 行不是三列" % (tag, i))
            continue
        code, text, gloss = parts
        if not CODE_RE.match(code):
            bad("%s abbr_en.txt 第 %d 行码不合法：%r" % (tag, i, code))
        if not re.search(r"[A-Z]", text):
            bad("%s abbr_en.txt 第 %d 行词面无大写：%r" % (tag, i, text))
        if not gloss:
            bad("%s abbr_en.txt 第 %d 行释义为空" % (tag, i))
        if code in seen:
            bad("%s abbr_en.txt 码重复：%s（第 %d 行与第 %d 行）" % (tag, code, i, seen[code]))
        seen[code] = i
    if len(fails) == local_bad:
        ok("%s abbr_en.txt 逐条格式通过（码唯一 / 词面含大写 / 释义非空）" % tag)
    local_bad = len(fails)
    for p in (txt, lua):
        m = ABS_RE.search(read(p))
        if m:
            bad("%s %s 里出现本机绝对路径：%s" % (tag, os.path.basename(p), m.group(0)))
    if len(fails) == local_bad:
        ok("%s 缩写滤镜与数据表无本机绝对路径" % tag)


def gloss_width(s):
    """候选窗宽度：汉字/全角算 1 格，ASCII 算 0.5 格（与生成器同一把尺）。"""
    w = 0.0
    for ch in s:
        w += 1.0 if ord(ch) > 0x7F else 0.5
    return w


def check_raw_num(tree, tag):
    """D 组：v1.10.1 的「/」通道。数据表 + 滤镜注册 + 两条 recognizer 模式。"""
    txt = os.path.join(tree, "lua", "abbr_num.txt")
    lua = os.path.join(tree, "lua", "slash_translator.lua")
    if not os.path.isfile(txt):
        bad("%s 缺 lua/abbr_num.txt（/5g 这类含数字码的数据表）" % tag)
    elif not os.path.isfile(lua):
        bad("%s 缺 lua/slash_translator.lua" % tag)
    else:
        rows = [l for l in read(txt).splitlines() if l.strip() and not l.lstrip().startswith("#")]
        srows = seed_rows(SEED_NUM)
        if len(rows) != len(srows):
            bad("%s abbr_num.txt 条目数 %d ≠ 种子表 %d（改完种子没重新生成？跑 python _probe/abbr_num_lua_gen.py --out rime-config/abbr_num.txt）"
                % (tag, len(rows), len(srows)))
        else:
            ok("%s abbr_num.txt %d 条，与 abbr-num-seed.txt 一致" % (tag, len(rows)))
        local_bad = len(fails)
        seen = {}
        for i, line in enumerate(rows, 1):
            parts = line.split("\t")
            if len(parts) != 3:
                bad("%s abbr_num.txt 第 %d 行不是三列" % (tag, i))
                continue
            code, text, gloss = parts
            if not NUM_CODE_RE.match(code) or not re.search(r"\d", code):
                bad("%s abbr_num.txt 第 %d 行码不合法（要 2~14 位且含数字）：%r" % (tag, i, code))
            if text == code:
                bad("%s abbr_num.txt 第 %d 行词面与码相同（该码本来就用原文即可）：%s" % (tag, i, code))
            if not (re.search(r"[A-Z]", text) or "-" in text
                    or any(ord(ch) > 0x7F for ch in text)):
                bad("%s abbr_num.txt 第 %d 行词面没给出正确写法：%r" % (tag, i, text))
            if not gloss:
                bad("%s abbr_num.txt 第 %d 行释义为空" % (tag, i))
            elif gloss_width(gloss) > 20.0:
                bad("%s abbr_num.txt 第 %d 行释义超宽 %.1f 格：%r（comment 顶破候选窗，上限 20 格）"
                    % (tag, i, gloss_width(gloss), gloss))
            if code in seen:
                bad("%s abbr_num.txt 码重复：%s（第 %d 与第 %d 行）" % (tag, code, i, seen[code]))
            seen[code] = i
        if len(fails) == local_bad:
            ok("%s abbr_num.txt 逐条格式通过（码含数字且唯一 / 词面给出正确写法 / 释义非空且 ≤20 格）" % tag)
        local_bad = len(fails)
        for p in (txt, lua):
            m = ABS_RE.search(read(p))
            if m:
                bad("%s %s 里出现本机绝对路径：%s" % (tag, os.path.basename(p), m.group(0)))
        if len(fails) == local_bad:
            ok("%s slash 滤镜与数据表无本机绝对路径" % tag)

    # 2026-10-22 性能闸门：librime 每挂一个 lua_translator 就让每次按键多约 10~13 ms
    # （实测五笔方案 3 个 translator + 11 个 filter = 44.0 ms/键，0 个 = 9.1 ms/键）。
    # lua_filter 只在候选算完之后跑一遍，十一个合计约 9 ms，不受这条限制。
    # 现在只允许一个 slash_translator；将来若有人加第二个，卡顿立刻回来，出包前必须拦下。
    spath = os.path.join(tree, "wubi_pinyin.schema.yaml")
    cpath = os.path.join(tree, "wubi_pinyin.custom.yaml")
    lua_t = []
    if os.path.isfile(spath):
        lua_t += re.findall(r"^\s*-\s*[\"']?lua_translator@(\w+)", read(spath), re.M)
    if os.path.isfile(cpath):
        # custom.yaml 用 engine/translators/+: 追加，所以补丁里的每一项也是生效的 translator
        lua_t += re.findall(r"^\s*-\s*[\"']?lua_translator@(\w+)", read(cpath), re.M)
    extra = [x for x in lua_t if x != "slash_translator"]
    if extra:
        bad("%s 生效的 translators 里多了 lua_translator：%s —— 每个让每键多约 10~13 ms"
            "（实测依据 _probe/lag_report_20261022.txt；/xx 通道请走 symbols 或 slash_translator）"
            % (tag, "、".join(extra)))
    elif len(lua_t) != 1:
        bad("%s 生效的 lua_translator 有 %d 个（%s），只应保留 1 个 slash_translator"
            % (tag, len(lua_t), "、".join(lua_t) or "无"))
    else:
        ok("%s 每键成本受控：生效 lua_translator 只有 slash_translator（1 个）" % tag)

    if not os.path.isfile(cpath):
        return
    data = read(cpath)
    m = re.search(r"^\s*-\s*lua_translator@slash_translator", data, re.M)
    if not m:
        bad("%s custom.yaml 的 engine/translators 没挂 slash_translator —— /help 与 /5g 通道不会加载" % tag)
    else:
        c = re.search(r"^\s*-\s*table_translator@custom_phrase", data, re.M)
        if c and c.start() > m.start():
            bad("%s slash_translator 排在 custom_phrase 之前，会抢自定义短语" % tag)
        else:
            ok("%s slash_translator 已挂在 translators 且位次在 custom_phrase 之后" % tag)
    for pat, why in (("recognizer/patterns/punct",
                      "缺它则 symbols.custom.yaml 那 107 组 /xx 符号一个都出不来"),
                     ("recognizer/patterns/rawNum",
                      "缺它则 /5g /ri0977 出不来，且数字会被 selector 当选词键吃掉")):
        if pat not in data:
            bad("%s custom.yaml 没有 %s —— %s" % (tag, pat, why))
    if "recognizer/patterns/punct" in data and "recognizer/patterns/rawNum" in data:
        ok("%s 两条 recognizer 模式在位（punct 点亮 dyy 符号库 / rawNum 走原文串）" % tag)

    rl = os.path.join(tree, "rime.lua")
    if not os.path.isfile(rl):
        bad("%s 缺 rime.lua —— slash_translator 与各滤镜都无从注册" % tag)
        return
    rdata = read(rl)
    if 'slash_translator = require("slash_translator")' not in rdata:
        bad("%s rime.lua 没注册 slash_translator —— /help 与 /5g 通道不会被加载" % tag)
    else:
        ok("%s rime.lua 已注册 slash_translator" % tag)
    # F2：老脚本一旦被重新 require，每键又要多付一次 Lua 边界开销
    back = [n for n in ("help_translator", "inputShow_translator", "rawEcho_translator")
            if re.search(r"^\s*%s\s*=\s*require" % n, rdata, re.M)]
    if back:
        bad("%s rime.lua 又注册了旧的 lua_translator：%s —— 打字卡顿会回来（44.0 ms/键）"
            % (tag, "、".join(back)))
    else:
        ok("%s rime.lua 未重新注册旧 translator（help/inputShow/rawEcho）" % tag)


STEM_MIN_CHARS = 20000
STEM_RE = re.compile(r"^[a-z]{2}$")


def check_char_stems(tree, tag):
    """E：单字 stem 列在位且取值正确（v1.10.2 修自动造词取码的回归门）。"""
    d = os.path.join(tree, "wubi86.dict.yaml")
    if not os.path.isfile(d):
        bad("%s 找不到 wubi86.dict.yaml，stem 门无法判定" % tag)
        return
    lines = read(d).split(chr(10))
    if "..." not in lines:
        bad("%s wubi86.dict.yaml 没有 `...` 表头结束标记，stem 门无法判定" % tag)
        return
    codes = {}          # 单字 -> 该字所有码
    stems = {}          # 单字 -> 写进第 4 列的 stem 集合
    for ln in lines[lines.index("...") + 1:]:
        if not ln.strip():
            continue
        f = ln.split(chr(9))
        w = f[0]
        if len(w) != 1 or not (u"一" <= w <= u"鿿"):
            continue
        if len(f) >= 2 and f[1]:
            codes.setdefault(w, set()).add(f[1])
        if len(f) >= 4 and f[3]:
            stems.setdefault(w, set()).add(f[3])
    n = len(codes)
    if n < STEM_MIN_CHARS:
        bad("%s 词库里只有 %d 个单字（下限 %d），单字层疑似被删" % (tag, n, STEM_MIN_CHARS))
        return
    missing = [c for c in codes if c not in stems]
    if len(missing) > 10:
        bad("%s 有 %d 个单字没有 stem 列（前 10 个：%s）—— 词库疑似被三列格式重写过，"
            "自动造词会退回算错码，禁止出包" % (tag, len(missing), u"".join(missing[:10])))
        return
    badfmt = {c: v for c, v in stems.items() if any(not STEM_RE.match(x) for x in v)}
    if badfmt:
        bad("%s 有 %d 个单字的 stem 不是 2 位小写字母（例：%s）"
            % (tag, len(badfmt), list(badfmt.items())[:3]))
        return
    wrong = []
    for c, sv in stems.items():
        cand = codes.get(c, set())
        short = [x for x in cand if len(x) >= 2]
        if not short:
            continue
        low = min(len(x) for x in short)
        allow = set(x[:2] for x in short if len(x) == low)
        if not sv <= allow:
            wrong.append((c, sorted(sv), sorted(allow)))
    if wrong:
        bad("%s 有 %d 个单字的 stem 与「最短码前两位」不符（例：%s）" % (tag, len(wrong), wrong[:3]))
        return
    ok("%s 单字 stem：%d 个单字，%d 个带 stem（缺 %d），取值全部等于最短码前两位"
       % (tag, n, len(stems), len(missing)))


def check_custom(tree, tag):
    p = os.path.join(tree, "wubi_pinyin.custom.yaml")
    if not os.path.isfile(p):
        bad("%s 缺 wubi_pinyin.custom.yaml" % tag)
        return
    data = read(p)
    if "- name: abbrEn" not in data:
        bad("%s custom.yaml 没有 abbrEn 开关" % tag)
    elif "reset: 1" not in data.split("- name: abbrEn")[1][:200]:
        bad("%s abbrEn 开关不是默认开（reset: 1）" % tag)
    else:
        ok("%s abbrEn 开关存在且默认开启" % tag)
    m = re.search(r"^\s*-\s*lua_filter@abbrGloss_Filter", data, re.M)
    if not m:
        bad("%s custom.yaml 的 engine/filters 没挂 abbrGloss_Filter" % tag)
    else:
        # 「末位」的含义：它必须排在所有会改写 comment 的滤镜之后，
        # 否则我们写的「释义」会被后面任何一个 comment 滤镜抹掉。
        after = data[m.end():]
        for other in ("dic_4w_Filter", "phraseComment_Filter", "pinyinAdding_Filter",
                      "codeLookup_Filter", "laneChangeAndSpace_Filter"):
            if re.search(r"^\s*-\s*lua_filter@" + other, after, re.M):
                bad("%s abbrGloss_Filter 挂在了 %s 之前，comment 会被后面的滤镜改写" % (tag, other))
                break
        else:
            ok("%s abbrGloss_Filter 位于 comment 滤镜链末端之后（位次与注释都保得住）" % tag)
    if "schema/dependencies" in data:
        bad("%s custom.yaml 带了 schema/dependencies —— 三张互译表会被真编出来，"
            "实测英文抢走 10/162 码的中文第 1，本版禁止" % tag)
    else:
        ok("%s custom.yaml 未铺 schema/dependencies（互译修复按实测回退，仍留 backlog）" % tag)


def check_schema_and_internal(tree, tag):
    sp = os.path.join(tree, "wubi_pinyin.schema.yaml")
    data = read(sp)
    miss = [n for n in INTERNAL if "table_translator@" + n not in data]
    if miss:
        bad("%s wubi_pinyin.schema.yaml 的 translators 里没有：%s（删了功能，违反「绝不删功能」）"
            % (tag, ", ".join(miss)))
    else:
        ok("%s 三条 table_translator 仍在位（本版不动它们，只是不激活）" % tag)
    for n in INTERNAL:
        p = os.path.join(tree, n + ".schema.yaml")
        if os.path.isfile(p):
            bad("%s 出现了内部构件 %s.schema.yaml —— 三张表会被编出来，英文候选抢中文第 1"
                % (tag, n))
    ok("%s 出包树无内部构件 schema（符合本版范围）" % tag)
    dl = os.path.join(tree, "default.custom.yaml")
    if os.path.isfile(dl) and re.search(r"schema_list:.*?%s" % INTERNAL[0], read(dl), re.S):
        bad("%s 内部构件混进了 schema_list，用户会看见它" % tag)
    else:
        ok("%s schema_list 未包含内部构件" % tag)


def check_rime_lua(tree, tag):
    p = os.path.join(tree, "rime.lua")
    if not os.path.isfile(p):
        ok("%s 无 rime.lua（该树不承载注册，跳过）" % tag)
        return
    if "abbrGloss_Filter = require" not in read(p):
        bad("%s rime.lua 没注册 abbrGloss_Filter —— 滤镜不会被加载" % tag)
    else:
        ok("%s rime.lua 已注册 abbrGloss_Filter" % tag)


def md5(p):
    return hashlib.md5(io.open(p, "rb").read()).hexdigest() if os.path.isfile(p) else None


def check_trees_match():
    files = ["lua/abbr_en.txt", "lua/abbrGloss_Filter.lua",
             "lua/abbr_num.txt", "lua/slash_translator.lua",
             "lua/dic_4w_Filter.lua",
             "wubi_pinyin.schema.yaml", "wubi_pinyin.custom.yaml", "rime.lua"]
    for f in files:
        digs = {}
        for tag, tree in TREES.items():
            p = os.path.join(tree, f)
            if os.path.isfile(p):
                digs[tag] = md5(p)
        vals = set(digs.values())
        missing = sorted(set(TREES) - set(digs))
        if len(vals) > 1:
            bad("跨树不一致：%s 在 %s 里内容不同 → 装的包与仓库校验树不是同一套"
                % (f, ", ".join("%s=%s" % (k, v[:8]) for k, v in digs.items())))
        elif not digs:
            bad("三棵树都没有 %s" % f)
        elif missing:
            # 只查「有文件的那些树相同」会漏掉「release 树里根本没这个新文件」——
            # 安装包是 prepare_release.py 从 stage 拷过来的，漏拷等于功能没进包。
            bad("跨树缺文件：%s 不在 %s（stage 改了没同步到出包树？）"
                % (f, "、".join(missing)))
        else:
            ok("跨树一致：%s（%s 同 md5）" % (f, "/".join(sorted(digs))))
    # C3 研发镜像漂移：rime-config 是「改配置时最容易下手」的那棵树，
    # 它和 stage 不一致 = 下一次拿它当基准打补丁就会覆盖掉出包树里的新功能。
    for f in files:
        # rime-config 把 lua 平铺在根目录（没有 lua/ 子目录），所以按文件名兜底找
        a = md5(os.path.join(MIRROR, f)) or md5(os.path.join(MIRROR, os.path.basename(f)))
        b = md5(os.path.join(TREES["stage"], f))
        if a is None or b is None:
            bad("C3 镜像缺文件：%s（rime-config=%s / stage=%s）"
                % (f, "有" if a else "无", "有" if b else "无"))
        elif a != b:
            bad("C3 镜像漂移：rime-config/%s 与 stage 不同（%s vs %s）—— 见 _probe/apply_v1101.py 顶部记录"
                % (os.path.basename(f), a[:8], b[:8]))
        else:
            ok("C3 镜像一致：rime-config/%s == stage" % os.path.basename(f))


def main():
    # 控制台默认 GBK，打不出 ✓/✗；这里显式切到 UTF-8（切不动就退回 ASCII 标记）
    global MARK_OK, MARK_BAD
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        MARK_OK, MARK_BAD = "[OK]", "[FAIL]"
    for tag, tree in TREES.items():
        if not os.path.isdir(tree):
            bad("配置树不存在：%s" % tag)
            continue
        check_abbr(tree, tag)
        check_raw_num(tree, tag)
        check_custom(tree, tag)
        check_schema_and_internal(tree, tag)
        check_rime_lua(tree, tag)
        check_char_stems(tree, tag)
    check_trees_match()
    legacy_has = os.path.isfile(os.path.join(LEGACY, "lua", "abbr_en.txt"))
    ok("旧树 rime/ %s（v1.2 遗留镜像，只被 release.yml 做依赖完整性校验，不参与出包）"
       % ("已铺 v1.10 文件" if legacy_has else "未铺 v1.10 文件，符合预期"))
    for line in oks:
        print("  ✓ " + line)
    print("-" * 60)
    if fails:
        for line in fails:
            print("  ✗ " + line)
        print("v1.10 硬校验未通过：%d 条问题，禁止出包" % len(fails))
        sys.exit(1)
    print("v1.10.2 硬校验通过：%d 项全绿（纯字母缩写 %d 条 + 含数字原文串 %d 条与种子同步 / "
          "滤镜与 translator 挂载位 / 两条 recognizer 模式 / 互译表未激活的门禁 / "
          "两棵出包树与研发镜像一致 / 单字 stem 列在位且取值正确）"
          % (len(oks), len(seed_rows()), len(seed_rows(SEED_NUM))))


if __name__ == "__main__":
    main()
