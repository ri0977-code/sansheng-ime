-- phraseReplace_Filter.lua
-- Copyright (C) 2023 yaoyuan.dou <douyaoyuan@126.com>
--[[
这个过滤器的主要作用是，对于候选项中命中的选项(OR 内容)，用其指定的内容来代替，如果没有指定，则使用 * 替换
由于这个过滤器会改变候选项的内容（主要是会减少候选项数量），所以请将这个过滤器放在其它过滤器的最前端使用
]]
local phraseReplaceModuleEnable, phraseReplaceModule = pcall(require, 'phraseReplaceModule')

local logEnable, log = pcall(require, "runLog")
if logEnable then
	log.writeLog('')
	log.writeLog('log from phraseReplace_Filter.lua')
	log.writeLog('phraseReplaceModuleEnable:'..tostring(phraseReplaceModuleEnable))
end

local function phraseReplace_Filter(input, env)
	--获取选项敏感词替换开关状态
	local on = env.engine.context:get_option("phraseReplace") or false
	
	--一个字典，用于暂存存在于候选词中的敏感词及其替换词
	local keyValDic = {}
	
	local candStart,candEnd
	
	for cand in input:iter() do
		candStart = cand.start
		candEnd = cand._end
		
		local candTxt = cand.text:gsub("%s","") or ""
		local candComment = cand.comment or ""
		
		--清空敏感词暂存字典
		keyValDic = {}
		
		--循环遍历每一个敏感词，以检查是否有某个敏感词存在于候选项中
		for k,v in pairs(phraseReplaceModule.dict) do
			if string.find(candTxt,k) then
				keyValDic[k] = v
			end
		end
		
		if next(keyValDic) then
			--如果存在至少一个敏感词，则不论是否进行了脱敏处理，都加上敏感标记 👙
			candComment = '👙'..candComment
			
			if on then
				--逐一替换到候选项中的敏感词
				for k,v in pairs(phraseReplaceModule.dict) do
					if '' == v then
						v = '*'
					end
					
					candTxt = string.gsub(candTxt, k, v)
				end
				
				yield(Candidate("word", cand.start, cand._end, candTxt, candComment))
			else
				--如果没有开启脱敏功能，则抛出原选项
				cand.comment = candComment
				yield(cand)
			end
		else
			--如果不存在敏感词，则抛出原选项
			yield(cand)
		end
	end
end

return phraseReplace_Filter
