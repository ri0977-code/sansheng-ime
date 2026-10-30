-- rawEcho_translator.lua
-- 三生输入法（sansheng-ime）自研 translator · 2026-10-21（v1.10.1）
--
-- 要解决的问题：中文态下「字母里夹数字」的串打不出来。
--   打 ri 之后按 0 会被当选词键吃掉；按左 Shift 进西文态能接上数字，但这时空格
--   变成字面字符、不上屏。根因是五笔 speller 的字母表里没有数字，不是谁配错了。
--
-- 做法：走「/」通道。/ 本来就是我们这套配置（dyy 系）里的符号开关，
--   recognizer 里加一条含数字的模式，数字就会被 recognizer 提前接管
--   （它排在 selector 之前），整串留在组合里；本 translator 再把它变成候选：
--     /5g      → 5G「第五代移动通信」        ← 查 abbr_num.txt 给正确写法与释义
--     /ri0977  → ri0977（原文）/ RI0977（大写）← 表里没有就原样给出
--   空格直接上屏第 1 候选，不用 Shift、不用回车。
--
-- 数据：同目录 abbr_num.txt（码<TAB>词面<TAB>释义），
--   由 rime-config/dicts/abbr-num-seed.txt 经 _probe/abbr_num_lua_gen.py 生成。
-- 边界：只接管「以 / 开头、含数字、字符集安全」的串；纯字母（/cpu /help /szq）
--   一律不碰，留给符号库和词库。开关 abbrEn 与本文件无关。
-- 铁律：全程 pcall；数据表加载失败也要能把原文吐出来，不许让候选列表变空。

local DATA_FILE = "abbr_num.txt"
local MAX_CODE = 14
-- 允许 字母数字 与 . _ + - 。
-- 注意：这条以前写成 "^[%w%.%_%+%-%]+$"，Lua 5.1 在字符类里把 %- 之后的 ] 当逃掉了，
-- 直接报 malformed pattern (missing ']')；pcall 把它吞了，结果就是「/5g 一条候选都没有」。
-- 2026-10-21 出包树沙箱实测（dbg_ab.py）定位，改回「- 放类尾」的写法。
local SAFE = "^[%w._+-]+$"	-- %w=字母数字；. _ + - 原样放行（- 在类尾才是字面量）

-- 目录解析手法与 abbrGloss_Filter.lua 完全一致（本机 + 笔记本 + 沙箱三处实测命中）
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
	print("[rawEcho] loaded=" .. tostring(loaded) .. " dictSize=" .. dictSize
		.. (loaded and "" or (" err=" .. tostring(loadErr))))
end

-- 这次的输入到底该不该由本通道接管
local function bodyOf(input)
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
	if not body:match("%d") then	-- 纯字母交给符号库 / 词库，不抢
		return nil
	end
	if body:match("/+") then		-- 里面还带斜杠的不接（/10/21 这类日期串）
		return nil
	end
	return body
end

local function rawEcho(input, seg)
	local ok, body = pcall(bodyOf, input)
	if not ok or not body then
		return
	end
	local start, stop = seg.start, seg._end
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
	-- 1) 表里命中：给正确写法 + 释义
	if hit and once(hit.text) then
		local comment = hit.gloss ~= "" and ('「' .. hit.gloss .. '」') or ''
		yield(Candidate("word", start, stop, hit.text, comment))
	end
	-- 2) 原样（用户要的就是这串字符本身时选这条）
	if once(body) then
		yield(Candidate("word", start, stop, body, " 原文"))
	end
	-- 3) 全大写形态（5g → 5G 这类表里没收的）
	local up = body:upper()
	if once(up) then
		yield(Candidate("word", start, stop, up, " 大写"))
	end
end

return rawEcho
