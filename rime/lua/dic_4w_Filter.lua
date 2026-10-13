-- spaceAppending.lua
-- Copyright (C) 2023 yaoyuan.dou <douyaoyuan@126.com>
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

--最长的comment长度限制
local maxLenOfComment = 100

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
