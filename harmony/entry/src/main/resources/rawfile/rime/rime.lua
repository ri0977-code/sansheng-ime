-- 三生输入法 · 鸿蒙版 rime.lua（由 scripts/port_rime_data.py 生成，勿手改）
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
  pcall(function() io.stderr:write(msg .. "\n") end)
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
inputShow_translator = need("inputShow_translator", "inputShow", "translator")
help_translator = need("help_translator", "help", "translator")
inputShow_Filter = need("inputShow_Filter", "inputShow_Filter", "filter")
phraseExt_Filter = need("phraseExt_Filter", "phraseExt_Filter", "filter")
dateTime_Filter = need("dateTime_Filter", "dateTime_filter", "filter")
dynamicPhrase_Filter = need("dynamicPhrase_Filter", "dynamicPhrase_Filter", "filter")
phraseReplace_Filter = need("phraseReplace_Filter", "phraseReplace_Filter", "filter")
dic_4w_Filter = need("dic_4w_Filter", "dic_4w_Filter", "filter")
phraseComment_Filter = need("phraseComment_Filter", "phraseComment_Filter", "filter")
pinyinAdding_Filter = need("pinyinAdding_Filter", "pinyinAdding_Filter", "filter")
codeLookup_Filter = need("codeLookup_Filter", "codeLookup_Filter", "filter")
laneChangeAndSpace_Filter = need("laneChangeAndSpace_Filter", "laneChangeAndSpace_Filter", "filter")
abbrGloss_Filter = need("abbrGloss_Filter", "abbrGloss_Filter", "filter")
phoneComment_Filter = need("phoneComment_Filter", "phoneComment_Filter", "filter")
Upper_Filter = need("Upper_Filter", "Upper_Filter", "filter")
-- enWord_Filter = need("enWord_Filter", "enWord_Filter", "filter")  -- H-260(CodeArts): v38 注释——filter 方案也卡，换 table_translator
-- H-272（Qoder 2026-10-29 18:3x）恢复这一行：v38 说的「filter 也卡」是 v3.2 的毛病——
-- 它每个输入窗口都把 gloss/trans/codes 三张表（3.5 MB）整表读进 Lua，本机 load 中位 241.2 ms，
-- 安卓真机 CPU 慢 3.6 倍 ⇒ 一个窗口约 868 ms。v3.3 改成「按首字母只读一段」：
-- 读 en_word_ltr_idx.tsv 的字节偏移，seek+read 只取按键首字母那一桶（最大 158 KB），
-- 本机 17.6 ms load + 5.1 ms 首键。索引缺/坏/首字符非字母一律退回整表读＝旧行为，一条功能不少。
-- 等价性证据：18 场景 × 三版本输出逐字节一致（安卓 _probe/h272-bucket-eq-cost-20261029.txt）。
enWord_Filter = need("enWord_Filter", "enWord_Filter", "filter")

rawEcho_translator = need("rawEcho_translator", "rawEcho_translator", "translator")
enWord_translator = need("enWord_translator", "enWord_translator", "translator")  -- H-260(CodeArts): 英文单词 Lua translator（方向1）

-- 真模块到位后（M4），上面的 need() 会自动改用真实现，桩不再命中。
