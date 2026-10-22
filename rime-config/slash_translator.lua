-- slash_translator.lua
-- 三生输入法（sansheng-ime）自研 translator · 2026-10-22
--
-- 它是 help_translator 与 rawEcho_translator 的合并体，**不是新功能**，目的是消掉每键开销。
--
-- 为什么要合并（实测，见 _probe/lag_report_20261022.txt）：
--   librime 每挂一个 lua_translator，就要在**每次按键**时跨一次 Lua 边界并调用它一次，
--   这个固定开销约 10 ms/键，与脚本本身干多重活无关（三个脚本加起来只有几百行查表）。
--   实测五笔方案 wubi_pinyin：
--     三个 lua_translator + 11 个 lua_filter   → 平均 44.0 ms/键
--     零个 lua_translator + 11 个 lua_filter   → 平均  9.7 ms/键
--   十一个 lua_filter 只占约 9 ms（它们在候选算完之后才跑一遍），
--   而三个 lua_translator 合计要 34 ms。**问题出在 translator 的数量上，不在滤镜。**
--   inputShow_translator 的功能与 inputShow_Filter 完全重复（同表 candsWillBeShown，
--   Filter 第 221-233 行自己生成候选），已直接删除、零功能损失。
--   剩下两个必须保留功能（/help 与 /5g 通道），所以合并成一个，只付一次开销。
--
-- 合并后的行为（与合并前逐条一致）：
--   /help      → 14 条分类速查（带圈汉字/数字、符号/记号、数学、方块、…）
--   help       → lua 版本 + 特殊符号 + latexLetters
--   /5g        → 5G「第五代移动通信」（查 abbr_num.txt 给正确写法与释义）
--   /pm2.5     → PM2.5「细颗粒物浓度指标」
--   /ri0977    → ri0977（原文）/ RI0977（大写）
--   纯字母（/cpu /szq /123）→ 一律不碰，留给符号库和词库。
--
-- 铁律：全程 pcall；数据表加载失败也要能把原文吐出来，不许让候选列表变空。

local MAX_CODE = 14
local SAFE = "^[%w._+-]+$"	-- %w=字母数字；. _ + - 原样放行（- 在类尾才是字面量）

-- ---------------- /help 速查表 ----------------
local HELP_MENU = {
  "带圈汉字/数字/字母/注音-->/hzq/szq/zmq/zy",
  "符号/记号/箭头/雪花/表情-->/fh/jh/jt/xh/bq",
  "数学/数字名/音乐/分数/电脑-->/sx/szm/yy/fs/dn",
  "方块/麻将/象棋/色子/扑克-->/fk/mj/xq/sz/pk",
  "单位/货币/偏旁-->/dw/hb/pp",
  "标点/下标/竖标点-->/bd/xb/bdz",
  "希腊字符/大写-->/xl/xld",
  "罗马数字/大写-->/lm/lmd",
  "天干/地支/干支-->/tg/dz/gz",
  "八卦-->/bg/bgm/txj",
  "星座/名-->/xz/xzm/seg",
  "节气/天气-->/jq/tq",
  "数字/字母-->/123/abc...",
  "状态/推荐/进度/对错-->/zt/tj/jd/dc",
}

-- ---------------- abbr_num.txt 词典（与 rawEcho 同源） ----------------
local DATA_FILE = "abbr_num.txt"

local function luaDirFromSelf()
  local ok, info = pcall(function()
    return debug.getinfo(1, "S")
  end)
  if not ok or not info or not info.source then
    return nil
  end
  local src = tostring(info.source)
  if src:sub(1, 1) ~= "@" then
    return nil
  end
  src = src:gsub("\\", "/"):sub(2)
  return src:match("^(.-/lua/)[^/]+$")
end

local function dirCandidates()
  local out = {}
  local function add(d)
    if type(d) == "string" and d ~= "" then
      out[#out + 1] = d
    end
  end
  add(luaDirFromSelf())
  local okApi, api = pcall(function()
    return rime.get_api()
  end)
  if okApi and api then
    local okDd, dd = pcall(api.get_user_data_dir, api)
    if okDd and dd and tostring(dd) ~= "" then
      add(tostring(dd):gsub("\\", "/") .. "/")
    end
  end
  add("./")
  local okAd, appdata = pcall(os.getenv, "APPDATA")
  if okAd and appdata and appdata ~= "" then
    add(appdata:gsub("\\", "/") .. "/Rime/")
  end
  return out
end

local dict = {}
local dictSize = 0

local function openDict()
  local cands = dirCandidates()
  for i = 1, #cands do
    local d = cands[i]
    local fn = io.open(d .. DATA_FILE, "r")
    if fn then
      return fn
    end
    fn = io.open(d .. "lua/" .. DATA_FILE, "r")
    if fn then
      return fn
    end
  end
  return nil
end

local function loadDict()
  local fn = openDict()
  if not fn then
    return
  end
  for line in fn:lines() do
    if line and #line > 0 and not line:match("^%s*#") then
      local code, text, gloss = line:match("^(%S+)\t([^\t]+)\t([^\t]*)$")
      if code and text then
        local key = code:lower()
        if not dict[key] then
          dictSize = dictSize + 1
        end
        dict[key] = { text = text, gloss = gloss or "" }
      end
    end
  end
  fn:close()
end

local loaded, loadErr = pcall(loadDict)
if not loaded then
  dict, dictSize = {}, 0
end
if os.getenv("ABBR_DIAG") then
  print("[slash] loaded=" .. tostring(loaded) .. " dictSize=" .. dictSize
    .. (loaded and "" or (" err=" .. tostring(loadErr))))
end

-- 「/ 开头、含数字、字符集安全」的串才归本通道；纯字母交给符号库/词库
local function rawBody(input)
  if type(input) ~= "string" or input:sub(1, 1) ~= "/" then
    return nil
  end
  local body = input:sub(2)
  local n = #body
  if n < 2 or n > MAX_CODE then
    return nil
  end
  if not body:match(SAFE) then
    return nil
  end
  if not body:match("%d") then	-- 纯字母不抢
    return nil
  end
  if body:match("/+") then		-- /10/21 这类日期串不接
    return nil
  end
  return body
end

local function translator(input, seg)
  local start, stop = seg.start, seg._end

  -- 1) /help：分类速查
  if input == "/help" then
    for i = 1, #HELP_MENU do
      yield(Candidate("help", start, stop, HELP_MENU[i], " "))
    end
    return
  end

  -- 2) help：Lua 版本 + 入口提示
  if input == "help" then
    yield(Candidate("help", start, stop, "lua version: ".._VERSION, " "))
    yield(Candidate("help", start, stop, "特殊符号-->/help", " "))
    yield(Candidate("help", start, stop, "latexLetters-->uzalph", " "))
    return
  end

  -- 3) /5g 这类含数字的原文串
  local ok, body = pcall(rawBody, input)
  if not ok or not body then
    return
  end
  local hit = dict[body:lower()]
  local emitted = {}
  local function once(t)
    for i = 1, #emitted do
      if emitted[i] == t then
        return false
      end
    end
    emitted[#emitted + 1] = t
    return true
  end
  if hit and once(hit.text) then
    local comment = hit.gloss ~= "" and ('「' .. hit.gloss .. '」') or ''
    yield(Candidate("word", start, stop, hit.text, comment))
  end
  if once(body) then
    yield(Candidate("word", start, stop, body, " 原文"))
  end
  local up = body:upper()
  if once(up) then
    yield(Candidate("word", start, stop, up, " 大写"))
  end
end

return translator