-- spaceAppending.lua
-- Copyright (C) 2023 yaoyuan.dou <douyaoyuan@126.com>
-- 三生改动（v1.10.1 · 2026-10-21）：中英对照在源头按「义项个数」截断，见 trimGlosses 上方说明。
local dic_4wEnable, dic_4w = pcall(require, 'dic_4w')
local utf8StringEnable, utf8String = pcall(require, 'utf8String')

local logEnable, log = pcall(require, "runLog")
if logEnable then
	log.writeLog('')
	log.writeLog('log from dic_4w_Filter.lua')
	log.writeLog('dic_4wEnable:'..tostring(dic_4wEnable))
	log.writeLog('utf8StringEnable:'..tostring(utf8StringEnable))
end

local getVal = dic_4w.getVal

-- 中英对照最多给几个义项。
-- 这里上游原来写的是 local maxLenOfComment = 100，但整个文件从没引用过它，是死代码；
-- 于是整条释义被原样贴进注释：「完成」14 个义项 205 列、「适当」39 个义项 581 列，
-- 最后由链尾 laneChangeAndSpace_Filter 按 150 个字符硬砍，砍出 fulfillment(n... 这种断词。
-- 本机 1920x1080、注释 14pt 雅黑下，150 个半角约 1.4K 像素，一条注释占掉屏宽的 3/4。
-- 留前 3 项后：最长注释 156 列降到 67 列，候选数与排名不变（沙箱 16 码实测）。
-- 只有值里含竖线的条目会被截（cn 到 en 表 25510 条中的 33%）；en 到 cn 表不含竖线，逐字不变。
local maxGlossCount = 3

-- 按竖线切义项，超出 maxGlossCount 的丢掉，末尾补省略号
local function trimGlosses(s)
	if not s or s == "" then return s end
	if not s:find("|") then return s end
	local parts = {}
	for p in (s:gsub(";+%s*$", "")):gmatch("[^|]+") do
		parts[#parts + 1] = p
	end
	if #parts <= maxGlossCount then return s end
	local kept = {}
	for i = 1, maxGlossCount do kept[i] = parts[i] end
	return table.concat(kept, "|") .. "…"
end

local function dic_4w_Filter(input, env)
	--获取中英对照开关状态
	local on = env.engine.context:get_option("encnDic")
	
	for cand in input:iter() do
		if on then
			local candTxt = cand.text:gsub("%s","") or ""
			local thisComment = cand.comment
			
			if candTxt ~= "" then
				--获取字典释义
				thisComment = getVal(candTxt)
				if nil == thisComment then
					thisComment = cand.comment
				else
					--只在查到中英对照释义时截断；查不到就原样保留上一条滤镜的注释
					thisComment = trimGlosses(thisComment)
				end
				if cand.comment ~= "" then
					if thisComment ~= cand.comment then
						if utf8.len(cand.comment) < 5 then
							if '💡'==cand.comment then
								thisComment = cand.comment..thisComment
							else
								thisComment = cand.comment..'✔'..thisComment
							end
						else
							thisComment = cand.comment..'<br>'..thisComment
						end
					end
				end
			end
			cand:get_genuine().comment = thisComment
		end
		yield(cand)
	end
end

return dic_4w_Filter
