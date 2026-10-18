-- phraseExt_Filter.lua
-- Copyright (C) 2023 yaoyuan.dou <douyaoyuan@126.com>
-- 这个滤镜的作用是，当候选项列表中出现对应的关键词时，将对应的增强词条追加到候选项列表中

local dbgFlg = false

local phraseExt_ModuleEnable, phraseExt_Module = pcall(require, 'phraseExt_Module')

local logEnable, log = pcall(require, "runLog")
if logEnable then
	log.writeLog('')
	log.writeLog('log from phraseExt_Filter.lua')
	log.writeLog('phraseExt_ModuleEnable:'..tostring(phraseExt_ModuleEnable))
end

local getPhraseList = phraseExt_Module.getPhraseList

--最长的comment长度限制
local maxLenOfComment = 250

--设置 dbg 开关
local function setDbg(dbgFlg)
	phraseExt_Module.setDbg(dbgFlg)
end

--过滤器
local function phraseExt_Filter(input, env)
	--获取选项增强开关状态
	local on = env.engine.context:get_option("phraseExt")
	--获取应用程序标记状态[由于飞书暂不支持文本转表情的输入，帮使用 and false 将其关闭]
	local feishuFlg = env.engine.context:get_option("feishuFlg") and false
	local wechatFlg = env.engine.context:get_option("wechatFlg") or false
	local qqFlg = env.engine.context:get_option("qqFlg") or false
	local dingdingFlg = env.engine.context:get_option("dingdingFlg") or false
	local minttyFlg = env.engine.context:get_option("minttyFlg") or false
	local cmdFlg = env.engine.context:get_option("cmdFlg") or false
	local pycharmFlg = env.engine.context:get_option("pycharmFlg") or false
	local vscodeFlg = env.engine.context:get_option("vscodeFlg") or false
	local markdownFlg = env.engine.context:get_option("markdown") or false
	local chromeFlg = env.engine.context:get_option("chromeFlg") or false
	local qianniuFlg = env.engine.context:get_option("qianniuFlg") or false
	local wangwangFlg = env.engine.context:get_option("wangwangFlg") or false
	
	-- 候选词组前缀与开关状态的对应字典
	local prefixSwitchsDict = {['git-']=minttyFlg or cmdFlg,
								['cmd-']=cmdFlg,
								['py-']=pycharmFlg or vscodeFlg,
								['md-']=markdownFlg,
								['chrome-']=chromeFlg}
	
	local matchedTxt = ''
	local esType = ''
	local esTxt = ''
	
	local cands={}
	local thisTxt
	
	for cand in input:iter() do
		--提交默认选项
		if nil == cands[cand.text] then
			yield(cand)
			cands[cand.text]=true
		end
		if on then
			local candTxt = cand.text:gsub("%s","") or ""
			
			if candTxt ~= "" then
				--获取增强选项
				local phraseList = getPhraseList(candTxt)
				if #phraseList > 0 then
					local idx
					for idx=1,#phraseList do
						thisTxt=phraseList[idx]
						
						if nil == cands[thisTxt] then
							cands[thisTxt]=true
							
							--第一个括号匹配app标记（例如：fs,wx,qq,dt），
							--第二个括号匹配表情表达式（例如：[赞]、[/hanx]）
							esType,esTxt = string.match(thisTxt,"^es(.+)%{(.+)%}$")
							
							if nil ~= esType then
								esType = string.lower(esType)

								--这是一个表情选项
								if feishuFlg and nil ~= string.find(esType,'fs') then
									--这是一个 feishu 表情，且当前在 feishu 中输入
									if nil ~= esTxt then
										yield(Candidate("word", cand.start, cand._end, esTxt, '😃'))
									end
								elseif wechatFlg and nil ~= string.find(esType,'wx') then
									--这是一个 wechat 表情，且当前在 wechat 中输入
									if nil ~= esTxt then
										yield(Candidate("word", cand.start, cand._end, esTxt, '😃'))
									end
								elseif qqFlg and nil ~= string.find(esType,'qq') then
									--这是一个 QQ 表情，且当前在 QQ 中输入
									if nil ~= esTxt then
										yield(Candidate("word", cand.start, cand._end, esTxt, '😃'))
									end
								elseif dingdingFlg and nil ~= string.find(esType,'dt') then
									--这是一个 dingtalk 表情，且当前在 钉钉 中输入
									if nil ~= esTxt then
										yield(Candidate("word", cand.start, cand._end, esTxt, '😃'))
									end
								elseif (qianniuFlg or wangwangFlg) and nil ~= string.find(esType,'qn') then
								--这是一个 千牛/旺旺 表情，且当前在 千牛工作台 或者在阿里旺旺 中输入
									if nil ~= esTxt then
										yield(Candidate("word", cand.start, cand._end, esTxt, '😃'))
									end
								end
							else
								--这不是一个表情选项，检察是否符合某一前缀规则
								local prefix = ''
								local prefixLen = 0
								local prefixFlg = false
								for k,v in pairs(prefixSwitchsDict) do
									if string.find(string.lower(thisTxt),'^'..k..'-') then
										prefix = k
										prefixLen = #k
										prefixFlg = v
										break
									end
								end
								
								if prefixLen > 0 then
									if prefixFlg then
										-- 修剪选项
										thisTxt = string.sub(thisTxt, 1 + prefixLen)
									else
										--清除 thisTxt 的内容
										thisTxt = ""
									end
								end
								
								if #thisTxt > 0 then
									-- 抛出选项
									yield(Candidate("word", cand.start, cand._end, thisTxt, '💡'))
								end
							end
						end
					end
				end
			end
		end
	end
end

return phraseExt_Filter
