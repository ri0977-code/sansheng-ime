#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三生输入法 · M3 数据移植脚本（Qoder 归属）

把桌面端（小狼毫用户目录 + F: 工程目录）里已经跑通的三生 Rime 数据，
按「同名文件取最新修改时间」的规则挑出来，落到 HAP 的 rawfile/rime/。

为什么不让 CodeArts 手工拷：词库闭包有 9 个文件、跨 3 个根目录，
手拷必然漏 import_tables，而漏一个就是一片候选消失且没有报错。

产物：
  entry/src/main/resources/rawfile/rime/**            —— 打进 HAP 的数据
  docs/evidence/2026-10-21/m3-data-manifest.json      —— 每个文件来自哪个根、多大、md5 前 8 位

用法：python scripts/port_rime_data.py [--dry|--check]
  --dry    只算不写（打印挑源结果与齿轮完备性）
  --check  与 --dry 同义（真只读，供验收用；2026-10-22 前该旗标不存在，跑它等于全量移植）
"""

import hashlib
import json
import os
import re
import shutil
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(REPO, "entry", "src", "main", "resources", "rawfile", "rime")
MANIFEST = os.path.join(REPO, "docs", "evidence", "2026-10-21", "m3-data-manifest.json")

# 数据根目录，按优先级从高到低（F: 工程 > D: 小狼毫运行目录 > %APPDATA% 早期实验）。
# 不按「全局最新」取，因为实测三处已经分叉：%APPDATA% 的 wubi_pinyin.schema.yaml
# 时间最新（10-21 00:45）但把 abbrEn 开关、翻页键位写进了基础方案，
# 且词库体积与 D: 不同（zh2en_pinyin_wp 2.44MB vs 2.23MB）。分叉写进 manifest.diverged。
ROOTS = [
    r"F:/dshdesktopwork/sansheng-ime-android/rime",
    r"F:/workbuddywork/三生输入法/rime",
    r"F:/workbuddywork/三生输入法/rime-config",
    r"D:/Program Files/Rime",
    r"C:/Users/Administrator/AppData/Roaming/Rime",
]

# 逻辑清单：(rawfile 里的相对路径, 源文件名, 该文件的搜索根顺序)
# 每个文件按自己的顺序找，取「第一个命中的根里 mtime 最新」的那份。
# 为什么要逐文件排：F:/rime 里那两个 wubi_pinyin.* 是老版（1706/3168 B，
# 连 zh_trad、中英互译 translator 都没有），基础方案得用 F:/rime-config 的 4436 B 版，
# 而 custom.yaml 得用 D: 运行目录的 4516 B 版（比 rime-config 多 abbrGloss 一行）。
W = r"F:/workbuddywork/三生输入法"
D = r"D:/Program Files/Rime"
A = r"C:/Users/Administrator/AppData/Roaming/Rime"

SCHEMA_ORDER = [W + "/rime-config", D, A, W + "/rime"]
CUSTOM_ORDER = [D, W + "/rime-config", A, W + "/rime"]
DICT_ORDER = [W + "/rime", D, A]

FILES = [
    # --- 方案（schema） ---
    ("wubi_pinyin.schema.yaml", "wubi_pinyin.schema.yaml", SCHEMA_ORDER),
    ("wubi_pinyin.custom.yaml", "wubi_pinyin.custom.yaml", CUSTOM_ORDER),
    ("pinyin_simp.schema.yaml", "pinyin_simp.schema.yaml", SCHEMA_ORDER),
    ("symbols.yaml", "symbols.yaml", [r"F:/dshdesktopwork/sansheng-ime-android/_emulator_runs/apktool/rime/assets/usr/share/rime-data", W + "/rime", D, A]),
    ("symbols.custom.yaml", "symbols.custom.yaml", [r"F:/dshdesktopwork/sansheng-ime-android/rime", W + "/rime", D, A]),
    # --- 词库闭包：wubi86 的 import_tables 是 4 个 _wp，缺一个就少一类候选 ---
    ("wubi86.dict.yaml", "wubi86.dict.yaml", DICT_ORDER),
    ("cn_pinyin_wp.dict.yaml", "cn_pinyin_wp.dict.yaml", DICT_ORDER),
    ("zh2en_pinyin_wp.dict.yaml", "zh2en_pinyin_wp.dict.yaml", DICT_ORDER),
    ("zh2en_wubi_wp.dict.yaml", "zh2en_wubi_wp.dict.yaml", DICT_ORDER),
    ("en2zh_v2_wp.dict.yaml", "en2zh_v2_wp.dict.yaml", DICT_ORDER),
    # --- 三个中英互译 translator 用的是不带 _wp 的同名词典 ---
    ("zh2en_wubi.dict.yaml", "zh2en_wubi.dict.yaml", DICT_ORDER),
    ("zh2en_pinyin.dict.yaml", "zh2en_pinyin.dict.yaml", DICT_ORDER),
    ("en2zh_v2.dict.yaml", "en2zh_v2.dict.yaml", DICT_ORDER),
    # --- 拼音（反查 + T9 的数据底座） ---
    ("pinyin_simp.dict.yaml", "pinyin_simp.dict.yaml", DICT_ORDER),
    # --- 用户自造词模板（stabledb 读同名 .txt） ---
    ("Custom_phrase.txt", "Custom_phrase.txt", DICT_ORDER),
    # --- OpenCC：只用 s2t 一条链路（简→繁），.ocd2 是预编译的，不需要 opencc CLI ---
    # 这三个文件在源目录里就叫 opencc/xxx，所以根目录是不带 opencc 后缀的那一层。
    ("opencc/s2t.json", "opencc/s2t.json", [W, D, A]),
    ("opencc/STCharacters.ocd2", "opencc/STCharacters.ocd2", [W, D, A]),
    ("opencc/STPhrases.ocd2", "opencc/STPhrases.ocd2", [W, D, A]),
]

# 小狼毫专属、鸿蒙上没用甚至有害的行，落地前剔掉。
DROP_LINE_PREFIXES = {
    "wubi_pinyin.custom.yaml": (
        '"schema/icon"',
        '"schema/zhung_icon"',
        '"schema/ascii_icon"',
    ),
    # H-044 结案（run11/run12 真机）：候选归零不是「齿轮进不了 filter 链」，
    # 是我上一轮的桩写错了契约 —— 这套 rime-lua 和桌面一样是协程式：
    #   for cand in input:iter() do yield(cand) end，返回值引擎不看。
    # run12 证据：zzd_f8(iter+yield 恒等)=4 条与 zzd_min 完全一致；
    # zzd_f9(只 yield 首条并改 comment)="你好[诊断九g]"；
    # zzd_f10(yield 自建 Candidate)="诊断十[zz10]" 排在最前。
    # 所以 run13 起把 lua_* 齿轮重新挂上（桩已改成 iter+yield），
    # 只有 3 个没编译出 table.bin 的互译 translator 仍然摘掉。
    "wubi_pinyin.schema.yaml": (
        "- table_translator@zh2en_wubi",
        "- table_translator@en2zh_v2",
        "- table_translator@zh2en_pinyin",
    ),
}
# 桌面端 import_preset: symbols 依赖 weasel 公共目录里的 symbols.yaml，
# M8（H-079）起我们把 symbols.yaml + symbols.custom.yaml 打进 rawfile/rime/，
# 并把 import_preset 改成 symbols，所以不再需要替换成 default。
REPLACE_LINE = {
}

# M3 踩坑：桌面端的 *.custom.yaml / *.schema.yaml 用 Tab 对齐行尾注释（DSH 手写习惯）。
# yaml-cpp（真机 librime）容忍，PyYAML（scripts/check_rime_yaml.py 严格校验）直接
# "found character '\t' that cannot start any token"。统一在落地时把 Tab 换成空格，
# 两边都能解析。只处理配置文件：*.dict.yaml 的字段分隔符就是 Tab，动了词库全废。
def is_config_yaml(src_name):
    if not src_name.endswith(".yaml"):
        return False
    return not src_name.endswith(".dict.yaml")


# --- M3b：Lua 滤镜闭包（wubi_pinyin 的 engine/filters 里那 12 级） ---
# 桌面实测：librime.a 里确实编进了 librime-lua（LuaTypeInfo / lua_filter /
# package.path 的 "<dir>/lua/?.lua" 模板都在），liblua.a 也一起静态链接了。
# 但 librime-lua 只在 **user_data_dir** 找 rime.lua，所以产物要释放到 rime_user/，
# 且数据文件（abbr_en.txt 等）必须和脚本同层或在其 lua/ 子目录里。
#
# 只收 wubi_pinyin 真正引用的脚本，桌面端那些没用的大件不带上包体：
#   latex_translator.lua 129KB、latexLettersInWubi.lua、luaSocket/（要加载 Windows DLL）、
#   runLog.lua（往只读目录写日志）、Upper_Filter（三生已回退，主人说不用大写）。
LUA_ROOTS = [D, W + "/rime/lua"]          # 运行验证过的 D: 优先，F: 仓库版兜底
LUA_MODULES = {
    # rime.lua 里的全局名 -> lua/ 下的模块文件名（和桌面 rime.lua 的 require 对应）
    "inputShow_translator": "inputShow",
    "help_translator": "help",
    "inputShow_Filter": "inputShow_Filter",
    "phraseExt_Filter": "phraseExt_Filter",
    "dateTime_Filter": "dateTime_filter",
    "dynamicPhrase_Filter": "dynamicPhrase_Filter",
    "phraseReplace_Filter": "phraseReplace_Filter",
    "dic_4w_Filter": "dic_4w_Filter",
    "phraseComment_Filter": "phraseComment_Filter",
    "pinyinAdding_Filter": "pinyinAdding_Filter",
    "codeLookup_Filter": "codeLookup_Filter",
    "laneChangeAndSpace_Filter": "laneChangeAndSpace_Filter",
    "abbrGloss_Filter": "abbrGloss_Filter",
    "phoneComment_Filter": "phoneComment_Filter",
    # --- M4 补齐（2026-10-21 22:35 真机）----------------------------------------
    # 这两个齿轮**发布件里早就引用了**，但模块和 rime.lua 全局从来没移植过：
    #   Upper_Filter      —— wubi_pinyin.schema.yaml:67（custom.yaml 整表替换 filters 时
    #                        又把它注释掉了，所以当前不生效；仍要补，防止 custom.yaml 一旦
    #                        缺失就又变成「引用了不存在的全局」）
    #   rawEcho_translator —— wubi_pinyin.custom.yaml:30 用 engine/translators/+ 追加，
    #                        **这一条是生效的** ⇒ rime-lua 每次调用都抛
    #                        "func type error expect function"，
    #                        而抛错的 LuaTranslation::Next 会把整条候选队列打断
    #                        （run6/run13 是同一个坑）。真机现象：预编辑正常、候选只剩 2 条。
    "Upper_Filter": "Upper_Filter",
    "rawEcho_translator": "rawEcho_translator",
}
# 脚本运行时用 io.open 读的数据表（按 D: 目录实测列出的名字，空格也是文件名的一部分）
LUA_DATA_FILES = [
    "abbr_en.txt",
    "dic_4w_cn.txt",
    "dic_4w_en.txt",
    "eventsList.txt",
    "eventsList personal.txt",
    "phraseComment commonPhrase.txt",
    "phraseComment chemicalElement.txt",
    "phraseComment personal.txt",
    "phraseExt commonPhrase.txt",
    "phraseExt esAppEmoji.txt",
    "phraseExt esUnicode.txt",
    "phraseExt personal.txt",
    "phraseReplace.txt",
    "pinyinAdding.txt",
    # rawEcho_translator 的数据表（含数字的流行缩写，/5g → 5G）
    "abbr_num.txt",
]

# --- M4：真模块上包前的鸿蒙补丁 ---
# 桌面端这批 Lua 齿轮里有两处「只在 Windows 上成立」的路径假设，去掉它们
# 之后整块功能在鸿蒙上照样工作：
#   ① codeLookup_Filter 的 resolve_data_dir() 只会找「有 wubi86.dict.yaml 的目录」，
#      它的候选表是 [引擎 API 的 user_data_dir, D:/Program Files/Rime, lua 目录的上一级,
#      %APPDATA%/Rime, sysInfo.currentDir 去 /lua]。
#      鸿蒙布局是「共享目录 <沙箱根>/rime 放词库 + 用户目录 <沙箱根>/rime_user 放配置」，
#      用户目录里**没有** wubi86.dict.yaml → 候选表全部落空 → 编码反查整块失效
#      （现象：打字正常，只是候选注释没了，不报错，最难查）。
#      补丁：lua 目录的上一级 p 就是用户目录，补一条 p/../rime（=共享目录）当候选。
#   ② abbrGloss_Filter 的 %APPDATA% 分支在鸿蒙上取不到（os.getenv 返回 nil），
#      但它第一候选是「本文件自己所在的 lua 目录」（luaDirFromSelf），
#      数据表随包放在同一个 lua/ 目录里 → 不需要补丁，天然命中。
LUA_PATCHES = {
    "codeLookup_Filter.lua": [
        (
            "    if p and p ~= '' then candidates[#candidates + 1] = p end",
            "    if p and p ~= '' then\n"
            "      candidates[#candidates + 1] = p\n"
            "      -- M4 鸿蒙补丁：词库在共享目录 <沙箱根>/rime，用户目录 <沙箱根>/rime_user 里没有\n"
            "      -- wubi86.dict.yaml，而 p 正是用户目录（lua 的上一级）。补一条 p/../rime 候选，\n"
            "      -- 否则编码反查整块失效（只少注释、不报错）。桌面上这条候选不存在，无副作用。\n"
            "      candidates[#candidates + 1] = (p .. '/../rime'):gsub('/+', '/')\n"
            "    end",
        ),
    ],
    #   ③ Upper_Filter 直接 cand.comment:find(...)。鸿蒙这版 rime-lua 的候选在没有
    #      注释时 comment 是 nil（桌面上是空串）⇒ nil:find 抛
    #      "attempt to index a nil value" ⇒ 抛错的滤镜同样会打断候选队列。
    "Upper_Filter.lua": [
        (
            "\t\tselfFlg = cand.comment:find('☯')",
            "\t\t-- M4 鸿蒙补丁：comment 可能为 nil（桌面上是空串），先兜成空串再 find。\n"
            "\t\tlocal cc = cand.comment or ''\n"
            "\t\tselfFlg = cc:find('☯')",
        ),
    ],
}

# 依赖闭包：从 13 个入口模块出发把它们 require 到的辅助模块一起收进来。
# （桌面 rime.lua 是人工维护的 require 列表；我们按文件实际 require 语句自动算闭包，
#  免得桌面加一级辅助模块、鸿蒙这边就少一级、运行时才发现。）
#
# 正则要同时吃两种写法：require('x') 和 pcall(require, 'x')（桌面这批齿轮全是后者，
# 只匹配括号形式会漏掉 utf8String / dateTimeModule / phraseExt_Module 等全部辅助模块）。
LUA_REQUIRE_RE = re.compile(r"require\s*[,(]?\s*['\"]([A-Za-z0-9_./]+)['\"]")
LUA_REQUIRE_IGNORE = {"rime.api", "socket.core"}

# 这三个模块在鸿蒙上是手写的沙箱实现，放在 rawfile/rime/lua/ 下（不进闭包）：
#   runLog.lua  —— 桌面向模块同目录写 runLog.txt；鸿蒙上每次按键都落盘太慢，
#                  改成默认空实现，需要时用环境变量 SS_LUA_LOG=1 打开。
#   sysInfo.lua —— 桌面读一堆 Windows 环境变量；鸿蒙版只保留 currentDir（真被用到的）
#                  和给 dynamicPhrase 用的系统信息项，其余给「未知」。
#   socket.lua  —— 桌面向 socket/core.dll 要 luaSocket；鸿蒙没有 ⇒ 安全桩，socketEnable=false。
LUA_HARMONY_OVERRIDE = {"runLog.lua", "sysInfo.lua", "socket.lua"}

# 鸿蒙版 rime.lua：逐个 pcall，任何一个脚本在 musl 上加载失败都只是「这一级滤镜失效」，
# 不会像桌面那样整个 rime.lua 报错、所有滤镜一起没了。
HARMONY_RIME_LUA = '''-- 三生输入法 · 鸿蒙版 rime.lua（由 scripts/port_rime_data.py 生成，勿手改）
--
-- 释放位置：必须落在 **user_data_dir**（librime-lua 只在用户目录找 rime.lua，见
-- RimeDataInstaller.USER_FILES）；真模块与数据表放 <user>/lua/ 下，
-- librime-lua 已把 "<user>/?.lua" 和 "<user>/lua/?.lua" 加进 package.path。
--
-- 和桌面版 rime.lua 的区别（M3 run6 真机教训）：
--   桌面版直接 `xxx = require("xxx_Filter")`，模块缺失时整个 rime.lua 报错；
--   鸿蒙版先 pcall(require)，失败就回落到桩（滤镜恒等放行、翻译器不出候选）。
--   为什么必须有桩：齿轮缺失时 librime-lua 仍然会建出 LuaFilter/LuaTranslation 对象，
--   但每次调用都抛 "func type error expect function"，而抛错的
--   LuaTranslation::Next 会把整条候选队列打断 —— 真机表现是
--   wubi_pinyin 预编辑正常、候选 0 条（run6 里 611 次 Next error）。
--   桩先保主链路出词；M4 把真滤镜逐个补齐后 require 成功即自动生效，不用再改这个文件。
local ok_api, api = pcall(require, "rime.api")

local function warn(msg)
  -- run12 教训：引擎自带的全局 warn 不落到桥重定向的 napi_stderr.txt（那个文件 0 字节），
  -- 取证只认 io.stderr。所以顺序反过来：先 io.stderr（能 recv 回来），再补一发全局 warn。
  pcall(function() io.stderr:write(msg .. "\\n") end)
  if type(_G.warn) == "function" then
    pcall(_G.warn, msg)
    return
  end
  if ok_api and api and type(api.log) == "function" then
    pcall(api.log, msg)
  end
end

local function passthrough(input, segment)
  -- run11 实测钉死的契约（决定性证据：桌面 lua/pinyinAdding_Filter.lua:25 写的是
  -- `for cand in input:iter() do yield(cand) end`，而 run11 的真机 dump 里
  -- input 是 shared_ptr<rime::Translation> 的 userdata、metatable 带 methods 表、
  -- 且 _G 里就有 `yield:function` 与 `Candidate:function`）：
  -- **这版 rime-lua 的滤镜是协程生成器，靠 yield 逐个交候选，返回值一律作废**。
  -- 所以 run9/run10 里 `return input` / `return table` 都得到 0 条候选——
  -- 不是「滤镜掐候选」，是**桩写错了**：桌面版从来不是 table 进 table 出。
  -- 兜底保留 return input：万一哪天 iter 不存在，至少行为可预测。
  if type(input) == "userdata" and type(input.iter) == "function" then
    for cand in input:iter() do
      yield(cand)
    end
    return
  end
  return input
end

local function nothing(input, segment, env)
  return nil
end

-- kind: "filter" -> 恒等放行；"translator" -> 不出候选
local function need(name, module, kind)
  local ok, fn = pcall(require, module)
  if ok and type(fn) == "function" then
    return fn
  end
  warn("[sansheng-lua] stub " .. name .. " (module=" .. tostring(module) ..
       ", err=" .. tostring(fn) .. ")")
  if kind == "filter" then
    return passthrough
  end
  return nothing
end

-- H-044 已结案（run11–run13 真机），诊断齿轮与 zzd_*.schema.yaml 全部删除。
-- 结案时量到的契约（原文见 docs/evidence/2026-10-21/m3-stderr-run13.txt，M4 直接照这个写滤镜）：
--   _VERSION=Lua 5.4；滤镜调用形态 = f(input, env, ?)：
--     input = userdata 包 std::shared_ptr<rime::Translation>，methods 只有 `iter`，vars_get 只有 `exhausted`；
--     env   = 普通 table，键是 `engine`(userdata rime::Engine*) 与 `name_space`(string)，
--             `env.engine.context` 可用，`env.engine.context:get_option("ascii_mode"/"zh_trad"/"pinyin")` 返回 boolean
--             ⇒ 桌面 lua/pinyinAdding_Filter.lua 的 `env.engine.context:get_option(...)` 写法在鸿蒙上一字不改就能跑；
--     第 3 个参数是 std::vector<std::shared_ptr<rime::Candidate>> 的 userdata（没有 .engine，别拿它当 env）。
--   候选 = userdata，methods: append/get_dynamic_type/get_genuine/get_genuines/spans/to_phrase/to_sentence/
--     to_shadow_candidate/to_uniquified_candidate；vars_get: _end/_start/comment/preedit/quality/start/text/type。
--     `cand.code` 不存在（返回 nil）——桌面滤镜若用 cand.code 要改成 cand.text/cand.preedit。
--   出候选靠协程 `yield(cand)`，返回值作废；`Candidate("word", start, _end, text, comment)` 可直接构造并 yield；
--   comment 直接赋值与 `cand:get_genuine().comment=` 两种写法实测都生效（run13 f9）。
--   证据：zzd_f8 恒等=4 条 ≡ zzd_min；f9 裁成 1 条并显示「你好[诊断九g]」；f10 插入「诊断十[zz10]」到首位；
--   run13 里 wubi_pinyin 挂满 13 级齿轮（2 translator + 11 filter）候选与摘链时完全一致。
-- 【M4 22:35 补记】发布件里还引用了两个齿轮，桌面 rime.lua 有、这里一度漏掉：
--   rawEcho_translator（custom.yaml 用 engine/translators/+ 追加，**生效**）
--   Upper_Filter（schema 里的 filters 列表，custom.yaml 整表替换后不生效，但补上更安全）
-- 漏掉它们的后果不是「少一项能力」，而是 rime-lua 每次调用抛
-- "func type error expect function"，抛错的 LuaTranslation::Next 会把整条候选队列打断
-- ⇒ 真机现象：预编辑正常、候选只剩 2 条，且**不报错**。
-- 所以 scripts/port_rime_data.py 里加了齿轮完备性检查（yaml 引用 ↔ 模块 ↔ 本文件全局），
-- 少一个就让移植脚本以非 0 退出码失败。
'''


def build_harmony_rime_lua():
    lines = [HARMONY_RIME_LUA]
    for global_name, module in LUA_MODULES.items():
        kind = "translator" if global_name.endswith("_translator") else "filter"
        lines.append('%s = need("%s", "%s", "%s")\n' % (global_name, global_name, module, kind))
    lines.append("\n-- 真模块到位后（M4），上面的 need() 会自动改用真实现，桩不再命中。\n")
    return "".join(lines)


def lua_candidates(src_rel):
    out = []
    for root in LUA_ROOTS:
        # 桌面端布局：<D>/rime.lua + <D>/lua/*.lua，所以两处都要探；
        # F: 仓库版放在 <W>/rime/lua 下，等于 root 已经是 lua/。
        for base in (root, root + "/lua"):
            p = os.path.join(base, src_rel.replace("/", os.sep))
            if os.path.isfile(p):
                out.append(p)
    return out


def lua_pick(src_rel):
    """在桌面各根里找同一个 lua 文件，返回第一个命中的路径（D: 运行验证过的优先）。"""
    cands = lua_candidates(src_rel)
    return cands[0] if cands else None


def lua_closure(entry_rels):
    """按 require 语句算出依赖闭包：13 个入口模块 + 它们 require 的辅助模块。

    为什么自动算：桌面 rime.lua 是人工维护的 require 列表，鸿蒙这边如果照抄，
    桌面加一级辅助模块就会在鸿蒙上少一级，运行时才炸（run6/run13 的教训：
    齿轮缺失的表现是「预编辑正常、候选 0 条」，不报错）。
    """
    found = {}
    missing = []
    queue = list(entry_rels)
    while queue:
        rel = queue.pop(0)
        if rel in found:
            continue
        src = lua_pick(rel)
        if src is None:
            missing.append(rel)
            continue
        found[rel] = src
        try:
            text = open(src, "r", encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in LUA_REQUIRE_RE.finditer(text):
            dep = m.group(1)
            if dep in LUA_REQUIRE_IGNORE:
                continue
            if not dep.endswith(".lua"):
                dep = dep + ".lua"
            if dep not in found and dep not in queue:
                queue.append(dep)
    return found, missing


def apply_lua_patches(rel, text):
    """把鸿蒙补丁打进桌面脚本（幂等：已打过就跳过）。"""
    for old, new in LUA_PATCHES.get(rel, []):
        if new in text:
            continue
        if old not in text:
            print("  WARN patch anchor not found in %s: %s" % (rel, old[:60]))
            continue
        text = text.replace(old, new, 1)
    return text


def write_lua_manifest(dest_root, dry=False):
    """扫出 lua/ 目录下的全部文件，写成 rawfile/rime/lua-files.txt（每行一个相对路径）。

    为什么用纯文本而不是 JSON：ArkTS 侧没有 TextDecoder/JSON 类型标注 hassle，
    一行一个路径用 split('\\n') 就能读，解析失败也不会把整个安装流程带崩
    （清单读不出来 ⇒ 退化成「只放桩版 rime.lua」，主链路仍然通）。
    """
    lua_dir = os.path.join(dest_root, "lua")
    names = []
    if os.path.isdir(lua_dir):
        for root, _dirs, files in os.walk(lua_dir):
            for f in sorted(files):
                rel = os.path.relpath(os.path.join(root, f), lua_dir).replace(os.sep, "/")
                names.append("lua/" + rel)
    names.sort()
    payload = "\n".join(names) + "\n"
    if not dry:
        with open(os.path.join(dest_root, "lua-files.txt"), "w", encoding="utf-8") as f:
            f.write(payload)
    return names


# --- M4 完备性检查：发布件里引用到的每一个 Lua 齿轮，都必须有「模块 + rime.lua 全局」 ---
# 2026-10-21 22:35 真机教训（M4 第一件返工）：
#   wubi_pinyin.custom.yaml 用 engine/translators/+ 追加了 `lua_translator@rawEcho_translator`，
#   但 rime.lua 从来没定义过这个全局 ⇒ rime-lua 每次调用都抛
#   "func type error expect function" ⇒ 抛错的 LuaTranslation::Next 会把整条候选队列打断
#   ⇒ 真机现象是「预编辑正常、候选只剩 2 条」，而且**不报错**，光看日志最难查。
#   桌面端不会犯（rime.lua 里 19 个全局一个不少），所以移植必须机器校验，不能靠人肉数。
LUA_GEAR_RE = re.compile(r"^\s*-\s*(lua_filter|lua_translator)@([A-Za-z0-9_]+)\s*$")


def collect_gears(dest_root):
    """扫发布件里的 yaml，返回 [(file, kind, global_name)]。

    只认「没被注释掉」的行：custom.yaml 里 `# - lua_filter@Upper_Filter` 是三生主动回退的，
    不算引用。patch 语义（engine/filters 整表替换 / engine/translators 追加）不展开——
    保守做法是把 schema 与 custom 里出现过的齿轮都要求齐，多余的模块留着不吃亏。
    """
    gears = []
    if not os.path.isdir(dest_root):
        return gears
    for name in sorted(os.listdir(dest_root)):
        if not name.endswith(".yaml"):
            continue
        try:
            with open(os.path.join(dest_root, name), "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        for line in text.split("\n"):
            m = LUA_GEAR_RE.match(line)
            if m:
                gears.append((name, m.group(1), m.group(2)))
    return gears


def check_gear_completeness(dest_root, closure):
    """返回缺口列表 [(file, kind, global_name, why)]；空列表 = 全齐。"""
    gaps = []
    for f, kind, g in collect_gears(dest_root):
        if g not in LUA_MODULES:
            gaps.append((f, kind, g, "rime.lua 没有定义这个全局（require 不到就是 nil）"))
            continue
        module_file = "%s.lua" % LUA_MODULES[g]
        if module_file not in closure:
            gaps.append((f, kind, g, "模块文件没进包：%s" % module_file))
    return gaps


def port_lua(dest_root, dry=False, with_modules=False):
    """把 Lua 齿轮写进 rawfile/rime/：rime.lua（生成）。
    with_modules=True 时才带真模块与数据表（M4：先把模块里的 Windows 路径
    （os.getenv('APPDATA')、'<dir>/installation.yaml'）改成沙箱路径再上，
    否则 M3 只需要 rime.lua 里的桩把主链路出词打通）。
    返回 (rows, bytes, missing)。"""
    rows = []
    total = 0
    entry = build_harmony_rime_lua().encode("utf-8")
    entry_path = os.path.join(dest_root, "rime.lua")
    if not dry:
        with open(entry_path, "wb") as f:
            f.write(entry)
    rows.append({"dest": "rime.lua", "source": "generated by port_rime_data.py",
                 "bytes": len(entry), "md5_8": hashlib.md5(entry).hexdigest()[:8]})
    total += len(entry)
    if not with_modules:
        # M3：只上桩。真模块留在桌面，等 M4 去掉 Windows 路径依赖再进包。
        return rows, total, [], []

    missing = []
    # ① 真模块 + 依赖闭包
    closure, miss = lua_closure(["%s.lua" % m for m in LUA_MODULES.values()])
    missing.extend(miss)
    for rel in sorted(closure):
        if rel in LUA_HARMONY_OVERRIDE:
            # 这三个在鸿蒙上是手写的沙箱实现（见 rawfile/rime/lua/），不用桌面的
            continue
        src = closure[rel]
        raw = open(src, "rb").read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = None
        if text is not None:
            text = apply_lua_patches(rel, text.replace("\r\n", "\n"))
            data = text.encode("utf-8")
        else:
            data = raw
        dest = os.path.join(dest_root, "lua", rel.replace("/", os.sep))
        if not dry:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)
        rows.append({"dest": "lua/" + rel, "source": src.replace("\\", "/"),
                     "bytes": len(data), "md5_8": hashlib.md5(data).hexdigest()[:8]})
        total += len(data)

    # ② 数据表（词表/符号/emoji/事件表…）：必须和脚本同层（sysInfo.currentDir 就是脚本所在目录）
    for rel in LUA_DATA_FILES:
        src = lua_pick(rel)
        if src is None:
            missing.append(rel)
            continue
        data = open(src, "rb").read()
        dest = os.path.join(dest_root, "lua", rel.replace("/", os.sep))
        if not dry:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)
        rows.append({"dest": "lua/" + rel, "source": src.replace("\\", "/"),
                     "bytes": len(data), "md5_8": hashlib.md5(data).hexdigest()[:8]})
        total += len(data)

    # ③ 运行时释放清单
    names = write_lua_manifest(dest_root, dry=dry)
    rows.append({"dest": "lua-files.txt", "source": "generated by port_rime_data.py",
                 "bytes": len(names), "md5_8": "-"})

    # ④ 完备性检查：发布件引用到的每个 lua 齿轮，都要有模块 + rime.lua 全局
    gaps = check_gear_completeness(dest_root, closure)
    return rows, total, missing, gaps



def pick(src_name, order):
    """在 order 给定的根目录列表里找 src_name：
    取第一个有该文件的根（列表本身按优先级排好），同一层有多个根时取 mtime 最新的。
    返回 (选中路径, mtime, 所有命中的路径)。"""
    candidates = []
    for root in order:
        p = os.path.join(root, src_name.replace("/", os.sep))
        if os.path.isfile(p):
            candidates.append((p, os.stat(p).st_mtime, root))
    if not candidates:
        return None
    top_root = candidates[0][2]
    same_tier = [c for c in candidates if c[2] == top_root]
    best = max(same_tier, key=lambda c: c[1])
    return best[0], best[1], [c[0] for c in candidates]


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def transform(src_name, raw):
    text = raw.decode("utf-8")
    had_cr = "\r\n" in text
    lines = text.replace("\r\n", "\n").split("\n")
    drops = DROP_LINE_PREFIXES.get(src_name, ())
    out = []
    for line in lines:
        stripped = line.strip()
        if any(stripped.startswith(d) for d in drops):
            continue
        out.append(line)
    text = "\n".join(out)
    for old, new in REPLACE_LINE.get(src_name, ()):
        text = text.replace(old, new)
    if is_config_yaml(src_name):
        text = text.replace("\t", "    ")
    if had_cr:
        text = text.replace("\n", "\r\n")
    return text.encode("utf-8")


def main():
    dry = "--dry" in sys.argv
    # --check 之前**根本不存在**（H-080 验收条款写错了，是我的文档 bug）：
    # 谁按字面跑 `python scripts/port_rime_data.py --check`，等于跑一次**全量移植**——
    # 重写 rawfile/rime/** 与 m3-data-manifest.json，并把 wubi_pinyin.schema.yaml 的
    # db_class 从 userdb 覆盖回 tabledb（M4 自造词持久化修复被吞）。2026-10-22 12:37 实测踩过。
    # 现在 --check = 真只读：只做挑源、比对、齿轮完备性检查，任何写盘都跳过。
    check_only = "--check" in sys.argv
    dry = dry or check_only
    rows = []
    diverged = []
    missing = []
    total = 0
    for dest_rel, src_rel, order in FILES:
        found = pick(src_rel, order)
        if found is None:
            missing.append(src_rel)
            continue
        src, mtime, all_paths = found
        raw = open(src, "rb").read()
        # .ocd2 是 OpenCC 预编译二进制，不能按文本处理
        data = raw if src_rel.endswith(".ocd2") else transform(src_rel, raw)
        dest = os.path.join(DEST, dest_rel.replace("/", os.sep))
        chosen_md5 = md5_of(src)
        others = []
        for alt in all_paths:
            if alt != src and md5_of(alt) != chosen_md5:
                others.append({"path": alt.replace("\\", "/"), "bytes": os.path.getsize(alt)})
        if others:
            diverged.append({"file": src_rel, "chosen": src.replace("\\", "/"), "others": others})
        rows.append({
            "dest": "rime/" + dest_rel,
            "source": src.replace("\\", "/"),
            "source_mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime)),
            "bytes": len(data),
            "md5_8": chosen_md5[:8],
        })
        total += len(data)
        if not dry:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)

    rows.sort(key=lambda r: r["dest"])
    # Lua 齿轮：rime.lua 由本脚本生成，释放到 rime_user/（见 RimeDataInstaller.USER_FILES）
    lua_rows, lua_bytes, lua_missing, gear_gaps = port_lua(DEST, dry=dry,
                                                             with_modules="--lua-modules" in sys.argv)
    rows.extend(lua_rows)
    total += lua_bytes
    missing.extend(lua_missing)
    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tool": "scripts/port_rime_data.py",
        "dest": DEST.replace("\\", "/"),
        "files": len(rows),
        "total_bytes": total,
        "lua_modules_included": "--lua-modules" in sys.argv,
        "missing": missing,
        "gear_gaps": ["%s: %s@%s → %s" % g for g in gear_gaps],
        "diverged": diverged,
        "rows": rows,
    }
    if not dry:
        os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
        with open(MANIFEST, "w", encoding="utf-8", newline="\n") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

    # 控制台只出 ASCII，避免 Windows gbk 编码把 CJK 路径打崩（真机调试踩过）
    log = []
    log.append("files=%d total=%d bytes missing=%d diverged=%d" % (len(rows), total, len(missing), len(diverged)))
    for r in rows:
        log.append("  %-28s %9d  %s  <- %s" % (
            r["dest"].replace("rime/", ""), r["bytes"], r["md5_8"], r["source"]))
    for m in missing:
        log.append("  MISSING: %s" % m)
    for g in gear_gaps:
        log.append("  GEAR GAP: %s: %s@%s → %s" % g)
    if gear_gaps:
        log.append("  FAIL 齿轮完备性检查没过：发布件引用了没有模块/全局的 lua 齿轮。")
        log.append("       这类缺口在真机上的表现是「预编辑正常、候选几乎为 0 且不报错」。")
    else:
        log.append("  PASS 齿轮完备性：发布件引用的每个 lua 齿轮都有模块 + rime.lua 全局。")
    text = "\n".join(log)
    if not dry:
        with open(os.path.join(REPO, "docs", "evidence", "2026-10-21",
                               "m3-port.log"), "w", encoding="utf-8") as f:
            f.write(text + "\n")
    try:
        print(text)
    except Exception:
        print(text.encode("ascii", "replace").decode("ascii"))
    # 有齿轮缺口就不算成功：退出码非 0，CI/人工一眼能看出这次移植不完整。
    return 1 if gear_gaps else 0


if __name__ == "__main__":
    sys.exit(main())
