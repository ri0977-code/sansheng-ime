--dateTime_filter.lua
--Copyright (C) 2023 yaoyuan.dou <douyaoyuan@126.com>
--本脚本主要用于提供一些与时间日期信息相关的处理服务

--引入支持模块，处理日期和时间信息
local dateTimeModuleEnable, dateTimeModule = pcall(require, 'dateTimeModule')
--引入 eventsList 模块，处理日期相关事件信息
local eventsListModuleEnable, eventsListModule = pcall(require, 'eventsListModule')
-- 导入log模块记录日志
local logEnable, log = pcall(require, "runLog")
if logEnable then
	log.writeLog('')
	log.writeLog('log from dateTime_filter.lua')
	log.writeLog('dateTimeModuleEnable:'..tostring(dateTimeModuleEnable))
	log.writeLog('eventsListModuleEnable:'..tostring(eventsListModuleEnable))
end

local jqListComming = dateTimeModule.jqListComming
local jqIdxByName = dateTimeModule.jqIdxByName
local jqInfoByTime = dateTimeModule.jqInfoByTime
local wInfoByTime = dateTimeModule.wInfoByTime
local timeDiff = dateTimeModule.timeDiff
local daysDiffName = dateTimeModule.daysDiffName
local dateInfoByTime = dateTimeModule.dateInfoByTime
local dateInfoByDaysOffset = dateTimeModule.dateInfoByDaysOffset
local timeInfoByTime = dateTimeModule.timeInfoByTime

--创建节气表
dateTimeModule.jqListBuild()

local getEventsByKw = eventsListModule.getEventsByKw
local getEventsByTime = eventsListModule.getEventsByTime

--最长的comment长度限制
local maxLenOfComment = 250

--加载农历信息
local lunarList,jqList,timeList
local thisLunar,thisJq,thisTime
local cands
local theCands
local candTxt_lower
local thisComment
local dateInfoList
local jqTime
local jqName
local eventsList
local thisEvent
local thisTxt
local wInfo
local timeBase
local timeReBase
local dateInfo

local function Filter(input, env)
	--获取dateTimeInfo开关状态
	local on = true --env.engine.context:get_option("dateTime")
	cands={}

	for cand in input:iter() do
		--抛出原选项
		if nil == cands[cand.text] then
			yield(cand)
			cands[cand.text]=true
		end
		if on then
			candTxt_lower = cand.text:lower()

			--时间选项整理
			if ({['time']=true,['时间']=true,['现在']=true,['now']=true,['此刻']=true,['此时']=true,['后缀']=true})[candTxt_lower] then
				--处理时间信息
				timeInfo = timeInfoByTime()
				--获取周序信息
				wInfo = wInfoByTime()
				--获取日期信息
				dateInfo = dateInfoByDaysOffset(0)

				theCands={}
				if ({['后缀']=true})[candTxt_lower] then
					table.insert(theCands,{dateInfo.YYYY_sb..dateInfo.MM_xb..dateInfo.DD_xb..wInfo.nameCN_1,timeInfo.timeLogo})
					table.insert(theCands,{dateInfo.YYYY_xb..dateInfo.MM..dateInfo.DD..timeInfo.hh_xb.."."..timeInfo.mm_xb,timeInfo.timeLogo})
				else
					if ({['现在']=true,['now']=true,['此刻']=true,['此时']=true})[candTxt_lower] then
						table.insert(theCands,{candTxt_lower.."("..dateInfo.date_YYYYMMDD_1.." "..timeInfo.time1..")",timeInfo.timeLogo})
					end
					--2025/03/25 16:02:33
					table.insert(theCands,{dateInfo.date_YYYYMMDD_1.." "..timeInfo.time1,timeInfo.timeLogo})
					--2025-03-25 16:02
					table.insert(theCands,{dateInfo.date_YYYYMMDD_2.." "..timeInfo.time2,timeInfo.timeLogo})
					--2025年3月25日 星期二 16点02分50秒
					table.insert(theCands,{dateInfo.date_YYYY_M_D_1.." "..wInfo.nameCN.." "..timeInfo.time3,timeInfo.timeLogo})
					--Tues. Mar. 25th 16:02:57, 2025
					table.insert(theCands,{wInfo.nameEN_short.." "..dateInfo.date_M_Dth.." "..timeInfo.time1.." "..dateInfo.YYYY,timeInfo.timeLogo})
				end

				--抛出选项
				for idx = 1, #theCands do
					thisTxt = theCands[idx][1]
					thisComment = theCands[idx][2]

					if nil == cands[thisTxt] then
						yield(Candidate("word", cand.start, cand._end, thisTxt, thisComment))
						cands[thisTxt] = true
					end
				end
			elseif ({['时辰']=true})[candTxt_lower] then
				local timeInfo = timeInfoByTime()
				theCands={}
				table.insert(theCands,{timeInfo.shiChen,timeInfo.timeLogo})

				for idx = 1, #theCands do
					thisTxt = theCands[idx][1]
					thisComment = theCands[idx][2]

					if nil == cands[thisTxt] then
						yield(Candidate("word", cand.start, cand._end, thisTxt, thisComment))
						cands[thisTxt] = true
					end
				end
			elseif ({['钟表']=true,['时钟']=true,['clock']=true,['表']=true})[candTxt_lower] then
				local timeInfo = timeInfoByTime()
				theCands={}
				table.insert(theCands,{timeInfo.timeLogo,'💡'})

				--抛出选项
				for idx = 1, #theCands do
					thisTxt = theCands[idx][1]
					thisComment = theCands[idx][2]

					if nil == cands[thisTxt] then
						yield(Candidate("word", cand.start, cand._end, thisTxt, thisComment))
						cands[thisTxt] = true
					end
				end
			elseif ({['date']=true,['日期']=true,['今天']=true,['今日']=true,['today']=true,['明天']=true,['明日']=true,['后天']=true,['昨天']=true,['前天']=true})[candTxt_lower] then
				--处理日期信息
				if ({['date']=true,['日期']=true,['今天']=true,['今日']=true,['today']=true})[candTxt_lower] then
					dateInfo = dateInfoByDaysOffset(0)
				elseif ({['明天']=true,['明日']=true})[candTxt_lower] then
					dateInfo = dateInfoByDaysOffset(1)
				elseif ({['后天']=true})[candTxt_lower] then
					dateInfo = dateInfoByDaysOffset(2)
				elseif ({['昨天']=true})[candTxt_lower] then
					dateInfo = dateInfoByDaysOffset(-1)
				elseif ({['前天']=true})[candTxt_lower] then
					dateInfo = dateInfoByDaysOffset(-2)
				end

				--获取周序信息
				wInfo = wInfoByTime(dateInfo.time)
				--获取今天的事件信息
				eventsList = getEventsByTime(dateInfo.time)
				--获取今天的24节气信息
				jqTime, jqName = jqInfoByTime(dateInfo.time)

				--如果今天有特殊事件，则合成事件的comment信息
				local eventsStr = ''
				for idx = 1, #eventsList do
					thisEvent = eventsList[idx]
					if '' ~= eventsStr then
						eventsStr = eventsStr..'\r[🔊]'..thisEvent.c3
					else
						eventsStr = '[🔊]'..thisEvent.c3
					end
				end

				theCands = {}
				if ({['今天']=true,['今日']=true,['today']=true,['明天']=true,['明日']=true,['后天']=true,['昨天']=true,['前天']=true})[candTxt_lower] then
					if ''~=eventsStr then
						table.insert(theCands,{candTxt_lower.."("..dateInfo.YYYY_sb.."/"..dateInfo.MM_xb.."."..dateInfo.DD_xb..")",eventsStr})
					else
						table.insert(theCands,{candTxt_lower.."("..dateInfo.YYYY_sb.."/"..dateInfo.MM_xb.."."..dateInfo.DD_xb..")",'💡'})
					end
					table.insert(theCands,{dateInfo.date_YYYYMMDD_1..' '..wInfo.nameCN,'💡'})
				else
					if ''~=eventsStr then
						table.insert(theCands,{dateInfo.date_YYYYMMDD_1..' '..wInfo.nameCN,eventsStr})
					else
						table.insert(theCands,{dateInfo.date_YYYYMMDD_1..' '..wInfo.nameCN,'💡'})
					end
				end

				table.insert(theCands,{dateInfo.date_M_Dth_YYYY_1,'💡'})
				table.insert(theCands,{dateInfo.YYYY_xb..dateInfo.MM..dateInfo.DD, '💡'})
				table.insert(theCands,{dateInfo.YYYY_sb.."/"..dateInfo.MM_xb.."."..dateInfo.DD_xb,'💡'})
				if jqTime>0 then
					table.insert(theCands,{dateInfo.lunarInfo.lunarDate_1,dateInfo.lunarInfo.jiJieLogo..jqName})
				else
					table.insert(theCands,{dateInfo.lunarInfo.lunarDate_4,dateInfo.lunarInfo.jiJieLogo})
				end

				--抛出选项
				for idx = 1, #theCands do
					thisTxt = theCands[idx][1]
					thisComment = theCands[idx][2]

					if nil == cands[thisTxt] then
						yield(Candidate("word", cand.start, cand._end, thisTxt, thisComment))
						cands[thisTxt] = true
					end
				end
			elseif ({['周日']=true,['周一']=true,['周二']=true,['周三']=true,['周四']=true,['周五']=true,['周六']=true})[candTxt_lower] then
				--获取今天的周信息
				timeBase = os.date('*t')
				wInfo = wInfoByTime()
				local wOffsetInput = ({['周日']=0,['周一']=1,['周二']=2,['周三']=3,['周四']=4,['周五']=5,['周六']=6})[candTxt_lower]

				--调整 base
				timeBase.day = timeBase.day + wOffsetInput - wInfo.offset2Sun
				wInfo = wInfoByTime(os.time(timeBase))
				jqTime, jqName = jqInfoByTime(os.time(timeBase))
				dateInfo = dateInfoByDaysOffset(wOffsetInput-tonumber(os.date('%w')))
				local daysDiff = daysDiffName(os.time(),os.time(timeBase))

				eventsList = getEventsByTime(os.time(timeBase))
				local eventsStr = ''
				for idx = 1, #eventsList do
					thisEvent = eventsList[idx]
					if '' ~= eventsStr then
						eventsStr = eventsStr..'\r[🔊]'..thisEvent.c3
					else
						eventsStr = '[🔊]'..thisEvent.c3
					end
				end

				local commentStr = ''
				if '今天'==daysDiff then
					commentStr = '[🚩]'
				elseif ''~=daysDiff then
					if os.time() < os.time(timeBase) then
						commentStr = '[👉'..daysDiff..']'
					else
						commentStr = '['..daysDiff..'👈]'
					end
				end

				if ''~=jqName then
					if ''==commentStr then
						commentStr = jqName
					else
						commentStr = commentStr..'\r'..jqName
					end
				end
				if ''~=eventsStr then
					if ''==commentStr then
						commentStr = eventsStr
					else
						commentStr = commentStr..'\r'..eventsStr
					end
				end

				dateInfoList = {dateInfo.date_YYYYMMDD_1,dateInfo.date_YYYYMMDD_2,dateInfo.date_M_Dth_YYYY_1,dateInfo.date_YYYYMMDD}
				for idx = 1, #dateInfoList do
					thisTxt = dateInfoList[idx]
					if nil == cands[thisTxt] then
						if 1==idx and ''~=commentStr then
							yield(Candidate("word", cand.start, cand._end, thisTxt, commentStr))
						else
							yield(Candidate("word", cand.start, cand._end, thisTxt, '💡'))
						end
						cands[thisTxt]=true
					end
				end
			elseif ({['lunar']=true,['农历']=true,['节气']=true})[candTxt_lower] then
				--处理农历信息
				lunarList,jqList,timeList = jqListComming()

				theCands={}

				for idx = 1, math.min(6,#lunarList) do
					thisJq = jqList[idx]
					thisTime = timeList[idx]

					dateInfo = dateInfoByTime(thisTime)
					thisLunar = dateInfo.lunarInfo.lunarDate_4

					if os.date("%Y/%m/%d",thisTime) == os.date("%Y/%m/%d") then
						thisJq = '🚩/'..dateInfo.lunarInfo.jiJieLogo..thisJq
					else
						local daysDiff = daysDiffName(os.time(),thisTime)
						if '' ~= daysDiff then
							if os.time() < thisTime then
								daysDiff = '[👉'..daysDiff..']'
							else
								daysDiff = '['..daysDiff..'👈]'
							end
						end

						thisLunar = dateInfo.lunarInfo.lunarDate_4..'('..thisJq..')'
						thisJq = dateInfo.lunarInfo.jiJieLogo..dateInfo.date_YYYYMMDD..daysDiff
					end
					table.insert(theCands,{thisLunar,thisJq})
				end

				--抛出选项
				for idx = 1, #theCands do
					thisTxt = theCands[idx][1]
					thisComment = theCands[idx][2]

					if nil == cands[thisTxt] then
						yield(Candidate("word", cand.start, cand._end, thisTxt, thisComment))
						cands[thisTxt] = true
					end
				end
			elseif ({['wx']=true,['周序']=true,['周数']=true})[candTxt_lower] then
				--处理周信息
				wInfo = wInfoByTime()

				theCands={}
				table.insert(theCands,{wInfo.xxWxx,'💡'})

				--抛出周序选项
				for idx = 1, #theCands do
					thisTxt = theCands[idx][1]
					thisComment = theCands[idx][2]

					if nil == cands[thisTxt] then
						yield(Candidate("word", cand.start, cand._end, thisTxt, thisComment))
						cands[thisTxt] = true
					end
				end
			elseif ({['本周']=true,['这周']=true,['上周']=true,['下周']=true})[candTxt_lower] then
				--处理周信息
				timeBase = os.date('*t')
				--对齐到周一
				timeBase.day = timeBase.day - os.date('%w') + 1
				if ({['上周']=true})[candTxt_lower] then
					timeBase.day = timeBase.day - 7
				elseif ({['下周']=true})[candTxt_lower] then
					timeBase.day = timeBase.day + 7
				end

				wInfo = wInfoByTime(os.time(timeBase))

				theCands={}
				if ({['本周']=true,['上周']=true,['下周']=true})[candTxt_lower] then
					table.insert(theCands,{candTxt_lower.."("..wInfo.xxWxx..")",'💡'})
				end
				table.insert(theCands,{wInfo.xxWxx,'💡'})

				for idx=0,6 do
					timeReBase = os.date('*t',os.time(timeBase))
					timeReBase.day = timeReBase.day + idx
					local daysDiff = daysDiffName(os.time(),os.time(timeReBase))

					--获取事件
					eventsList = getEventsByTime(os.time(timeReBase))
					--节取节气
					local jqT,jqN = jqInfoByTime(os.time(timeReBase))
					--日期信息
					dateInfo = dateInfoByTime(os.time(timeReBase))
					--周序信息
					wInfo = wInfoByTime(os.time(timeReBase))

					--如果存在节气，或者存在事件
					if ''~=jqN or 0<#eventsList then
						thisComment = ''
						local daysDiffInfo = os.date("%Y/%m/%d",os.time(timeReBase))
						if os.date("%Y/%m/%d") == os.date("%Y/%m/%d",os.time(timeReBase)) then
							daysDiffInfo = '[🚩]'
						elseif ''~=daysDiff and candTxt_lower~=daysDiff then
							--为了避免关键字与日期差异的信息冗余，增加条件 candTxt_lower~=daysDiff
							if os.time() < os.time(timeReBase) then
								daysDiffInfo = '[👉'..daysDiff..']'
							else
								daysDiffInfo = '['..daysDiff..'👈]'
							end
						end
						--如果节气存在
						if jqT>0 then
							if ''==thisComment then
								if ''~=daysDiffInfo then
									thisComment = dateInfo.lunarInfo.jiJieLogo..jqN..daysDiffInfo
									daysDiffInfo = ''
								else
									thisComment = dateInfo.lunarInfo.jiJieLogo..jqN
								end
							else
								if ''~=daysDiffInfo then
									thisComment = thisComment..'\r'..dateInfo.lunarInfo.jiJieLogo..jqN..daysDiffInfo
									daysDiffInfo = ''
								else
									thisComment = thisComment..'\r'..dateInfo.lunarInfo.jiJieLogo..jqN
								end
							end
						end
						--如果事件存在
						for idx = 1,#eventsList do
							thisEvent = eventsList[idx]
							if ''~=thisEvent.c3 and ''~=thisEvent.cycleType then
								if ''~=daysDiffInfo then
									if ''==thisComment then
										thisComment = '[🔊]'..thisEvent.c3..daysDiffInfo
									else
										thisComment = thisComment..'\r[🔊]'..thisEvent.c3..daysDiffInfo
									end
									daysDiffInfo = ''
								else
									if ''==thisComment then
										thisComment = '[🔊]'..thisEvent.c3
									else
										thisComment = thisComment..'\r[🔊]'..thisEvent.c3
									end
								end
							end
						end
						if ''==thisComment then
							thisComment = '💡'
						end
						table.insert(theCands,{dateInfo.date_YYYYMMDD_1..' '..wInfo.nameCN,thisComment})
					end
				end

				--抛出选项
				for idx = 1, #theCands do
					thisTxt = theCands[idx][1]
					thisComment = theCands[idx][2]

					if nil == cands[thisTxt] then
						yield(Candidate("word", cand.start, cand._end, thisTxt, thisComment))
						cands[thisTxt] = true
					end
				end
			elseif ({['week']=true,['星期']=true})[candTxt_lower] then
				--处理周信息
				wInfo = wInfoByTime()

				theCands={}
				table.insert(theCands,{wInfo.nameCN,'💡'})
				table.insert(theCands,{wInfo.nameEN,'💡'})
				table.insert(theCands,{wInfo.nameEN_short,'💡'})

				--抛出选项
				for idx = 1, #theCands do
					thisTxt = theCands[idx][1]
					thisComment = theCands[idx][2]

					if nil == cands[thisTxt] then
						yield(Candidate("word", cand.start, cand._end, thisTxt, thisComment))
						cands[thisTxt] = true
					end
				end
			elseif ({['本月']=true,['上月']=true,['下月']=true})[candTxt_lower] then
				--处理月份信息
				if ({['本月']=true})[candTxt_lower] then
					dateInfo = dateInfoByTime(os.time())
				elseif ({['上月']=true})[candTxt_lower] then
					dateInfo = dateInfoByDaysOffset(-os.date("%d")-1)
				elseif ({['下月']=true})[candTxt_lower] then
					dateInfo = dateInfoByDaysOffset(45-os.date("%d"))
				end

				theCands={}
				if ({['本月']=true,['上月']=true,['下月']=true})[candTxt_lower] then
					table.insert(theCands,{candTxt_lower.."("..dateInfo.date_yyMxx..")",'💡'})
				end
				table.insert(theCands,{dateInfo.date_yyMxx,'💡'})

				--抛出选项
				for idx = 1, #theCands do
					thisTxt = theCands[idx][1]
					thisComment = theCands[idx][2]

					if nil == cands[thisTxt] then
						yield(Candidate("word", cand.start, cand._end, thisTxt, thisComment))
						cands[thisTxt] = true
					end
				end
			elseif ({['今年']=true,['去年']=true,['明年']=true,['前年']=true,['后年']=true})[candTxt_lower] then
				if ({['今年']=true})[candTxt_lower] then
					dateInfo = dateInfoByTime(os.time({year = tonumber(os.date("%Y")), month = 5, day = 1, hour = 8, min = 0, sec = 0}))
				elseif ({['去年']=true})[candTxt_lower] then
					dateInfo = dateInfoByTime(os.time({year = tonumber(os.date("%Y"))-1, month = 5, day = 1, hour = 8, min = 0, sec = 0}))
				elseif ({['明年']=true})[candTxt_lower] then
					dateInfo = dateInfoByTime(os.time({year = tonumber(os.date("%Y"))+1, month = 5, day = 1, hour = 8, min = 0, sec = 0}))
				elseif ({['前年']=true})[candTxt_lower] then
					dateInfo = dateInfoByTime(os.time({year = tonumber(os.date("%Y"))-2, month = 5, day = 1, hour = 8, min = 0, sec = 0}))
				elseif ({['后年']=true})[candTxt_lower] then
					dateInfo = dateInfoByTime(os.time({year = tonumber(os.date("%Y"))+2, month = 5, day = 1, hour = 8, min = 0, sec = 0}))
				end

				theCands={}

				table.insert(theCands,{candTxt_lower.."("..dateInfo.YYYY..")",'💡'})
				table.insert(theCands,{dateInfo.lunarInfo.year_shengXiao..'年','💡'})
				table.insert(theCands,{dateInfo.lunarInfo.year_ganZhi..'年','💡'})
				table.insert(theCands,{dateInfo.lunarInfo.year_ganZhi.."("..dateInfo.lunarInfo.year_shengXiao..")"..'年','💡'})

				--抛出选项
				for idx = 1, #theCands do
					thisTxt = theCands[idx][1]
					thisComment = theCands[idx][2]

					if nil == cands[thisTxt] then
						yield(Candidate("word", cand.start, cand._end, thisTxt, thisComment))
						cands[thisTxt] = true
					end
				end
			elseif jqIdxByName(candTxt_lower)>0 then
				--查找指定的节气信息
				lunarList,jqList,timeList = jqListComming()

				local matchFlg = false
				local jqCnt = 0

				theCands={}
				for idx = 1, #jqList do
					thisLunar = lunarList[idx]
					thisJq = jqList[idx]
					thisTime = timeList[idx]
					wInfo = wInfoByTime(thisTime)
					dateInfo = dateInfoByTime(thisTime)

					if not matchFlg then
						matchFlg = (thisJq == candTxt_lower) or false
					end

					if matchFlg then
						local daysDiff = daysDiffName(os.time(),thisTime)

						if '今天' == daysDiff then
							thisJq = ' 🚩'..thisJq
						else
							if '' ~= daysDiff then
								if os.time() < thisTime then
									daysDiff = '[👉'..daysDiff..']'
								else
									daysDiff = '['..daysDiff..'👈]'
								end
							end
							thisLunar = thisLunar..'('..thisJq..')'
							thisJq = dateInfo.lunarInfo.jiJieLogo..os.date("%Y/%m/%d",thisTime)..daysDiff
						end

						--加入周信息
						thisLunar = thisLunar..' '..wInfo.nameCN

						if nil == cands[thisLunar] then
							table.insert(theCands,{thisLunar,thisJq})

							jqCnt = jqCnt + 1
						end
						if jqCnt >= 4 then
							break
						end
					end

				end

				--抛出选项
				for idx = 1, #theCands do
					thisTxt = theCands[idx][1]
					thisComment = theCands[idx][2]

					if nil == cands[thisTxt] then
						yield(Candidate("word", cand.start, cand._end, thisTxt, thisComment))
						cands[thisTxt] = true
					end
				end
			end

			do--事件选项整理
				local eventsList = getEventsByKw(candTxt_lower)
				if 0<#eventsList then
					local timeNow = os.date('*t')
					--校准到零点
					timeNow = os.time({year=timeNow.year,month=timeNow.month,day=timeNow.day,hour=0})
					for idx=1,#eventsList do
						local thisE = eventsList[idx]
						if thisE.time > timeNow then
							dateInfo = dateInfoByTime(thisE.time)
							wInfo = wInfoByTime(thisE.time)
							local tDiff = daysDiffName(thisE.time) or ''
							local thisComment = thisE.c3

							local thisCandTxt = dateInfo.date_YYYYMMDD_1..' '..wInfo.nameCN
							if nil==cands[thisCandTxt] and ''~= thisComment then
								if ''==tDiff then
									thisComment = '[👉]'..thisComment
								else
									if os.time() < thisE.time then
										thisComment = '[👉'..tDiff..']'..thisComment
									else
										thisComment = '['..tDiff..'👈]'..thisComment
									end
								end
								yield(Candidate("word", cand.start, cand._end, thisCandTxt, thisComment))

								cands[thisCandTxt]=true
							end
						end
					end
				end
			end
		end
	end
end

return Filter
