-- abbrGloss_Filter.lua
-- 三生输入法（sansheng-ime）自研滤镜 · 2026-10-20
-- 作用：中文态打「流行固定英文缩写」的码（cpu / ppt / github / kpi …），
--       在第一条中文候选之后插入该缩写本体，并把中文释义放进 comment。
--       只插候选、只写自己的 comment，不动词库、不动别人插进来的候选、不删任何候选。
-- 数据：同目录 abbr_en.txt（码<TAB>词面<TAB>释义），由 rime-config/dicts/abbr-en-seed.txt 生成。
-- 开关：abbrEn（F4 / Ctrl+Shift 自选），关闭时本滤镜完全透明直通。
-- 铁律自检：候选条数只许多不许少；第 1 位仍是中文原候选；全程 pcall，出错直通不崩 coroutine。

-- 数据文件：本滤镜自己的 lua/abbr_en.txt（码<TAB>词面<TAB>释义）
local DATA_FILE = "abbr_en.txt"

-- 目录解析手法沿用 codeLookup_Filter.lua（本机 + 笔记本双实测那套），
-- 但判据换成「本滤镜的数据文件在不在」：谁的目录里真有 abbr_en.txt 就用谁，
-- 因此在沙箱里不会误读线上表，在线上也不会被空目录钉死。
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
	-- 本文件位于 <用户目录>/lua/abbrGloss_Filter.lua → 捕获含结尾斜杠的 lua/ 段
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
	-- 注意：这里刻意不写死任何本机安装路径（盘符 + Program Files 那种）。
	-- 第 1 条 luaDirFromSelf() 已在本机、笔记本与沙箱三处实测命中，
	-- 引擎 API 与工作目录兜底；出包里带绝对路径会害了装在别的盘的用户。
	return out
end

local dict = {}          -- code(小写) -> { text = 词面, gloss = 释义 }
local dictSize = 0

local function openDict()
	local cands = dirCandidates()
	for i = 1, #cands do
		-- 候选既可能是 <用户目录>/lua/，也可能是 <用户目录>/，两种拼法都试
		local fn = io.open(cands[i] .. DATA_FILE, "r")
		if fn then
			if os.getenv("ABBR_DIAG") then
				print("[abbrGloss] data from " .. cands[i])
			end
			return fn
		end
		fn = io.open(cands[i] .. "lua/" .. DATA_FILE, "r")
		if fn then
			if os.getenv("ABBR_DIAG") then
				print("[abbrGloss] data from " .. cands[i] .. "lua/")
			end
			return fn
		end
	end
	if os.getenv("ABBR_DIAG") then
		print("[abbrGloss] NO data file; candidates=" .. table.concat(cands, " | "))
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
	print("[abbrGloss] loaded=" .. tostring(loaded) .. " dictSize=" .. dictSize
		.. (loaded and "" or (" err=" .. tostring(loadErr))))
end

-- 是否是「中文候选」：UTF-8 三字节序列（U+3000~U+9FFF，含CJK基本层与扩展A）
-- 或四字节序列（U+20000 起的扩展 B/C/D…，词库里那批生僻字如 𦚵/𨒵 都在这儿）。
-- 不依赖 utf8 库；拉丁、数字、符号的字节都落不进这些区间。
local function hasCjk(s)
	if type(s) ~= "string" then
		return false
	end
	return s:find("[\227-\233]") ~= nil or s:find("[\240-\244]") ~= nil
end

local function passthrough(cands)
	for i = 1, #cands do
		yield(cands[i])
	end
end

-- 诊断开关：只在加载时读一次环境变量，避免每键都 os.getenv
local DIAG = false
pcall(function()
	DIAG = os.getenv("ABBR_DIAG") ~= nil
end)

-- 廉价闸门：这次输入到底命不命中缩写码。不命中就一个候选都不碰（不建表、不扫描），
-- 这是为了不把每键延迟抬起来 —— 命中才走上面的收表逻辑。
local function hitFor(ctx)
	if dictSize == 0 or not ctx then
		return nil
	end
	local code = ctx.input
	if type(code) ~= "string" then
		return nil
	end
	local n = #code
	if n < 2 or n > 12 then
		return nil
	end
	if not code:match("^[%a]+$") then
		return nil
	end
	if not ctx:get_option("abbrEn") then
		return nil
	end
	return dict[code:lower()], code:lower()
end

local function abbrGloss_Filter(input, env)
	local okGate, hit, code = pcall(function()
		return hitFor(env.engine.context)
	end)

	if not okGate or not hit then
		-- 直通分支：绝大多数按键走这里，原样流出去，不做任何表操作
		for cand in input:iter() do
			yield(cand)
		end
		return
	end

	-- 命中缩写码（只有整串输入正好等于某个缩写码时才到这里）
	local cands = {}
	local dup = false
	for cand in input:iter() do
		cands[#cands + 1] = cand
		if not dup and type(cand.text) == "string" and cand.text == hit.text then
			dup = true
		end
	end

	local pos, injected
	local okJob = pcall(function()
		if dup or #cands == 0 then
			return
		end
		-- 插在第一条中文候选之后；一条中文都没有时插到最前（该码本来就没有中文可让）
		pos = 1
		for i = 1, #cands do
			if hasCjk(cands[i].text) then
				pos = i + 1
				break
			end
		end
		local comment = hit.gloss ~= "" and ('「' .. hit.gloss .. '」') or ''
		injected = Candidate("word", cands[1].start, cands[1]._end, hit.text, comment)
		if DIAG then
			local parts = {}
			for i = 1, math.min(6, #cands) do
				parts[#parts + 1] = i .. ":" .. tostring(cands[i].text) .. (hasCjk(cands[i].text) and "(中)" or "(非)")
			end
			print("[abbrGloss] head " .. code .. " -> " .. table.concat(parts, " ")
				.. " || inject @" .. pos .. " n=" .. #cands)
		end
	end)

	-- 铁律：任何分支都必须把上游给的候选原样吐回去，只有算出插入点时才多塞一条
	if okJob and injected then
		for i = 1, #cands do
			if i == pos then
				yield(injected)
			end
			yield(cands[i])
		end
		if pos > #cands then
			yield(injected)
		end
		return
	end
	passthrough(cands)
end

return abbrGloss_Filter
