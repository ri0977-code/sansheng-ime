--dateTimeModule.lua
--Copyright (C) 2023 yaoyuan.dou <douyaoyuan@126.com>
--该模块主要提供一些当前的时间和日期的相关信息
local M={}
local dbgFlg = false

--引入农历计算模块
local lunarEnable, lunar = pcall(require, 'lunarModule')

-- 导入log模块记录日志
local logEnable, log = pcall(require, "runLog")
if logEnable then
	log.writeLog('')
	log.writeLog('log from dateTimeModule.lua')
	log.writeLog('lunarEnable:'..tostring(lunarEnable))
end

--设置 dbg 开关
local function setDbg(flg)
	flg = flg or dbgFlg

	dbgFlg = flg
	if lunarEnable then
		lunar.setDbg(flg)
	end
	if logEnable then
		log.setDbg(flg)
	end

	print('dateTimeModule dbgFlg is '..tostring(dbgFlg))
end

local wNames_CN = {'星期日','星期一','星期二','星期三','星期四','星期五','星期六'}
local wNames_EN = {'Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'}
local wNames_Short = {'Sun.','Mon.','Tues.','Wed.','Thur.','Fri.','Sat.'}
local mName_EN = {'January','February','March','April','May','June','July','August','September','October','November','December'}
local mName_Short = {'Jan.','Feb.','Mar.','Apr.','May.','Jun.','Jul.','Aug.','Sep.','Oct.','Nov.','Dec.'}
local numSymbals = {'st','nd','rd','th'}
local timeLogos = {['0000']='🕛',['0030']='🕧',['0100']='🕐',['0130']='🕜',['0200']='🕑',['0230']='🕝',['0300']='🕒',['0330']='🕞',['0400']='🕓',['0430']='🕟',['0500']='🕔',['0530']='🕠',['0600']='🕕',['0630']='🕡',['0700']='🕖',['0730']='🕢',['0800']='🕗',['0830']='🕣',['0900']='🕘',['0930']='🕤',['1000']='🕙',['1030']='🕥',['1100']='🕚',['1130']='🕦',['1200']='🕛',['1230']='🕧',['1300']='🕐',['1330']='🕜',['1400']='🕑',['1430']='🕝',['1500']='🕒',['1530']='🕞',['1600']='🕓',['1630']='🕟',['1700']='🕔',['1730']='🕠',['1800']='🕕',['1830']='🕡',['1900']='🕖',['1930']='🕢',['2000']='🕗',['2030']='🕣',['2100']='🕘',['2130']='🕤',['2200']='🕙',['2230']='🕥',['2300']='🕚',['2330']='🕦',['2400']='🕛'}
local diZhi = {"子","丑","寅","卯","辰","巳","午", "未","申","酉","戌","亥"}

local function numSymbal(num)
	if num > 4 then
		return numSymbals[4]
	else
		return numSymbals[num]
	end
end

--获取timeLogo 
local function timeLogo(t)
	t = t or os.time()
	local timeNow = os.time()
	if type(t) == type(timeNow) then
		timeNow = t
	end
	local hourValue = os.date("%H",timeNow)
	local minValue=tonumber(os.date("%M",timeNow))

	if 15 < minValue and minValue < 45 then
		return timeLogos[string.format("%02d30",hourValue)]
	elseif 15 > minValue then
		return timeLogos[string.format("%02d00",hourValue)]
	else
		return timeLogos[string.format("%02d00",hourValue+1)]
	end
end

--[[提供一个timeInfo的时间结构，定义如下
timeInfo.time: 以秒为单位的时间戳
timeInfo.hh_sb: ¹²小时值
timeInfo.hh_xb: ₁₂小时值
timeInfo.mm_sb: ⁴⁵分钟值
timeInfo.mm_xb: ₄₈分钟值
timeInfo.ss_sb: ⁰⁸秒钟值
timeInfo.ss_xb: ₅₈秒钟值
timeInfo.shiChen：时辰
timeInfo.time1：22:47:12
timeInfo.time2：22:47
timeInfo.time3：22点47分16秒
timeInfo.timeLogo: 时间对应的钟表符号
]]
local function timeInfoByTime(t)
	t = t or os.time()
	local tBase=os.time()
	if type(t)==type(tBase) then
		tBase = t
	end

	local timeInfo = {}
	timeInfo.time = tBase
	--¹²小时值
	timeInfo.hh_sb = os.date("%H",baseTime):gsub("%d",{["1"]="¹",["2"]="²",["3"]="³",["4"]="⁴",["5"]="⁵",["6"]="⁶",["7"]="⁷",["8"]="⁸",["9"]="⁹",["0"]="⁰"})
	--₁₂小时值
	timeInfo.hh_xb = os.date("%H",baseTime):gsub("%d",{["1"]="₁",["2"]="₂",["3"]="₃",["4"]="₄",["5"]="₅",["6"]="₆",["7"]="₇",["8"]="₈",["9"]="₉",["0"]="₀"})
	--⁴⁵分钟值
	timeInfo.mm_sb = os.date("%M",baseTime):gsub("%d",{["1"]="¹",["2"]="²",["3"]="³",["4"]="⁴",["5"]="⁵",["6"]="⁶",["7"]="⁷",["8"]="⁸",["9"]="⁹",["0"]="⁰"})
	--₄₈分钟值
	timeInfo.mm_xb = os.date("%M",baseTime):gsub("%d",{["1"]="₁",["2"]="₂",["3"]="₃",["4"]="₄",["5"]="₅",["6"]="₆",["7"]="₇",["8"]="₈",["9"]="₉",["0"]="₀"})
	--⁰⁸秒钟值
	timeInfo.ss_sb = os.date("%S",baseTime):gsub("%d",{["1"]="¹",["2"]="²",["3"]="³",["4"]="⁴",["5"]="⁵",["6"]="⁶",["7"]="⁷",["8"]="⁸",["9"]="⁹",["0"]="⁰"})
	--₅₈秒钟值
	timeInfo.ss_xb = os.date("%S",baseTime):gsub("%d",{["1"]="₁",["2"]="₂",["3"]="₃",["4"]="₄",["5"]="₅",["6"]="₆",["7"]="₇",["8"]="₈",["9"]="₉",["0"]="₀"})

	timeInfo.shiChen = ''
	timeInfo.time1 = os.date("%H:%M:%S",tBase)
	timeInfo.time2 = os.date("%H:%M",tBase)
	timeInfo.time3 = os.date("%H点%M分%S秒",tBase)

	local h = tonumber(os.date('%H',tBase))
	h = math.floor((h + 1)/2)+1
	timeInfo.shiChen = (diZhi[h] or diZhi[1])..'时'

	timeInfo.timeLogo = timeLogo(tBase)

	return timeInfo
end

--[[根据时间返回日期信息，一个日期信息结构如下
dateInfo.time：日期的时间值
dateInfo.YYYY：日期的年份值
dateInfo.MM：日期的月份值
dateInfo.DD：日期的日期值
dateInfo.y：日期的年份值（数字）
dateInfo.m：日期的月份值（数字）
dateInfo.d：日期的日期值（数字）
dateInfo.YYYY_sb：²⁰²⁵日期的年份值
dateInfo.YYYY_xb：₂₀₂₅日期的年份值
dateInfo.MM_sb：⁰³日期的月份值
dateInfo.MM_xb：₀₃日期的月份值
dateInfo.DD_sb：²⁸日期的日期值
dateInfo.DD_xb：₂₈日期的日期值
dateInfo.date_YYYYMMDD_1：2022/05/09
dateInfo.date_MMDD_1：05/09
dateInfo.date_YYYYMMDD_2：2022-05-09
dateInfo.date_YYYYMMDD_3：2022_05_09
dateInfo.date_MMDD_2：05-09
dateInfo.date_YYYY_MM_DD_1：2022年05月09日
dateInfo.date_YYYY_M_D_1：2022年5月9日
dateInfo.date_M_D_1：5月9日
dateInfo.date_M_Dth：Mar.09th
dateInfo.date_M_Dth_YYYY：Mar. 09th, 2022
dateInfo.date_M_Dth_YYYY_2：May 09th, 2022
dateInfo.date10：二〇二二年五月九日
dateInfo.date_yyMxx：23M04
dateInfo.date_YYYYMMDD：20230412
dateInfo.lunarInfo: 一个lunar的结构体
]]
local function dateInfoByTime(t)
	t = t or os.time()
	local baseTime = os.time()
	if type(t) == type(baseTime) then
		baseTime = t
	end

	--处理年份信息
	local yN=tonumber(os.date("%Y",baseTime))
	local yN_1=''
	yN_1=os.date("%Y",baseTime):gsub("%d",{["1"]="一",["2"]="二",["3"]="三",["4"]="四",["5"]="五",["6"]="六",["7"]="七",["8"]="八",["9"]="九",["0"]="〇"})
	local yInfo={yN_1.."年"}

	--处理月份信息
	local mN=tonumber(os.date("%m",baseTime))
	local mN_1=''
	mN_1=os.date("%m",baseTime):gsub("%d",{["1"]="一",["2"]="二",["3"]="三",["4"]="四",["5"]="五",["6"]="六",["7"]="七",["8"]="八",["9"]="九",["0"]=""})
	if mN == 10 then
		mN_1 = '十'
	elseif mN == 11 then
		mN_1 = '十一'
	elseif mN == 12 then
		mN_1 = '十二'
	end
	local mInfo={mName_EN[mN],mName_Short[mN],mN_1..'月'}

	--处理日期信息
	local dN=tonumber(os.date("%d",baseTime))
	local dN_1=''
	dN_1=os.date("%d",baseTime):gsub("%d",{["1"]="一",["2"]="二",["3"]="三",["4"]="四",["5"]="五",["6"]="六",["7"]="七",["8"]="八",["9"]="九",["0"]=""})
	if dN > 19 then
		dN_1 = string.sub(dN_1,1,3).."十"..string.sub(dN_1,4,#dN_1)
	elseif dN > 9 then
		dN_1="十"..string.sub(dN_1,4,#dN_1)
	end
	dN_1 = dN_1..'日'
	local dInfo={os.date("%d",baseTime)..numSymbal(dN),dN_1}

	local dateInfo = {}
	dateInfo.time = baseTime
	dateInfo.YYYY = os.date("%Y",baseTime)
	dateInfo.MM = os.date("%m",baseTime)
	dateInfo.DD = os.date("%d",baseTime)
	dateInfo.y = yN
	dateInfo.m = mN
	dateInfo.d = dN
	--²⁰²⁵日期的年份值
	dateInfo.YYYY_sb = os.date("%Y",baseTime):gsub("%d",{["1"]="¹",["2"]="²",["3"]="³",["4"]="⁴",["5"]="⁵",["6"]="⁶",["7"]="⁷",["8"]="⁸",["9"]="⁹",["0"]="⁰"})
	--₂₀₂₅日期的年份值
	dateInfo.YYYY_xb = os.date("%Y",baseTime):gsub("%d",{["1"]="₁",["2"]="₂",["3"]="₃",["4"]="₄",["5"]="₅",["6"]="₆",["7"]="₇",["8"]="₈",["9"]="₉",["0"]="₀"})
	--⁰³日期的月份值
	dateInfo.MM_sb = os.date("%m",baseTime):gsub("%d",{["1"]="¹",["2"]="²",["3"]="³",["4"]="⁴",["5"]="⁵",["6"]="⁶",["7"]="⁷",["8"]="⁸",["9"]="⁹",["0"]="⁰"})
	--₀₃日期的月份值
	dateInfo.MM_xb = os.date("%m",baseTime):gsub("%d",{["1"]="₁",["2"]="₂",["3"]="₃",["4"]="₄",["5"]="₅",["6"]="₆",["7"]="₇",["8"]="₈",["9"]="₉",["0"]="₀"})
	--²⁸日期的日期值
	dateInfo.DD_sb = os.date("%d",baseTime):gsub("%d",{["1"]="¹",["2"]="²",["3"]="³",["4"]="⁴",["5"]="⁵",["6"]="⁶",["7"]="⁷",["8"]="⁸",["9"]="⁹",["0"]="⁰"})
	--₂₈日期的日期值
	dateInfo.DD_xb = os.date("%d",baseTime):gsub("%d",{["1"]="₁",["2"]="₂",["3"]="₃",["4"]="₄",["5"]="₅",["6"]="₆",["7"]="₇",["8"]="₈",["9"]="₉",["0"]="₀"})

	--合成 dateInfo 信息
	--2022/05/09
	dateInfo.date_YYYYMMDD_1 = os.date("%Y/%m/%d",baseTime)
	--05/09
	dateInfo.date_MMDD_1 = os.date("%m/%d",baseTime)
	--2022-05-09
	dateInfo.date_YYYYMMDD_2 = os.date("%Y-%m-%d",baseTime)
	--2022-05-09
	dateInfo.date_YYYYMMDD_3 = os.date("%Y_%m_%d",baseTime)
	--05-09
	dateInfo.date_MMDD_2 = os.date("%m-%d",baseTime)
	--2022年05月09日
	dateInfo.date_YYYY_MM_DD_1 = os.date("%Y年%m月%d日",baseTime)
	--2022年5月9日
	dateInfo.date_YYYY_M_D_1 = os.date("%Y年",baseTime)..tonumber(os.date("%m",baseTime)).."月"..tonumber(os.date("%d",baseTime)).."日"
	--Mar.09th
	dateInfo.date_M_Dth = mInfo[2]..dInfo[1]
	--5月9日
	dateInfo.date_M_D_1 = tonumber(os.date("%m",baseTime)).."月"..tonumber(os.date("%d",baseTime)).."日"
	--May. 09th, 2022
	dateInfo.date_M_Dth_YYYY_1 = mInfo[2]..' '..dInfo[1]..', '..dateInfo.YYYY
	--May 09th, 2022
	dateInfo.date_M_Dth_YYYY_2 = mInfo[1]..' '..dInfo[1]..', '..dateInfo.YYYY
	--二〇二二年五月九日
	dateInfo.date10 = yInfo[1]..mInfo[3]..dInfo[2]
	--23M04
	dateInfo.date_yyMxx = os.date("%yM%m",baseTime)
	--20230412
	dateInfo.date_YYYYMMDD = os.date("%Y%m%d",baseTime)

	dateInfo.lunarInfo = lunar.solar2LunarByTime(baseTime)

	--输出 dateInfo 信息
	return dateInfo
end

--提供 dateInfo 结构信息
local function dateInfoByDaysOffset(daysOffset)
	--baseDate准备
	daysOffset = daysOffset or 0
	local thisOffset = 0
	if type(thisOffset) == type(daysOffset) then
		thisOffset = daysOffset
	end

	local baseTime = os.date("*t")
	baseTime.day = baseTime.day + thisOffset

	local info = dateInfoByTime(os.time(baseTime))

	--输出 dateInfo 信息
	return info
end

--提供指定时间的 wInfo 信息
--[[week结构如下
wInfo.time：时间戳
wInfo.nameCN：周序名称，中文，星期一
wInfo.nameCN_1：周序名称，中文，周一
wInfo.nameEN：周序名称，英文
wInfo.nameEN_short：周序名称，简写
wInfo.xxWxx：周序，23W29
wInfo.offset2Sun：距离周日的天数
wInfo.offset2Year：年内周数，同步于xxWxx
wInfo.offset2Month：月内周数，对齐于offset2Year
]]
local function wInfoByTime(t)
	t = t or os.time()
	local timeBase = os.time()
	if type(t) == type(timeBase) then
		timeBase = t
	end
	
	local dateBase = os.date("*t")
	dateBase.day = 1

	--处理星期信息, os.date("%w"): 距离周日的天数
	local wN = tonumber(os.date("%w",timeBase))
	--计算今年以来的周数
	local weekNo = os.date("%W",timeBase) + 1
	--计算本月初日期在今年以来的周数
	local weekNo1 = os.date("%W",os.time(dateBase)) + 1

	local wInfo = {}
	wInfo.time = timeBase
	wInfo.nameCN = wNames_CN[wN+1]
	wInfo.nameCN_1 = string.gsub(wInfo.nameCN,"星期","周")
	wInfo.nameEN = wNames_EN[wN+1]
	wInfo.nameEN_short = wNames_Short[wN+1]
	wInfo.offset2Sun = wN
	wInfo.offset2Year = weekNo
	wInfo.offset2Month = weekNo - weekNo1 + 1
	wInfo.xxWxx = os.date("%y",timeBase).."W"..wInfo.offset2Year

	return wInfo
end

--提供指定时间的 week 信息
local function week(t)
	local thisInfo = wInfoByTime(t)
	return {thisInfo.nameCN,thisInfo.nameEN,thisInfo.nameEN_short,thisInfo.xxWxx}
end

--[[计算两个时间之间的差别，以 t1 为参考点，返回结构体如下：
diff.tRef：这是计算的基准时间
diff.tTgt：这是计算的目标时间
diff.timeDiff：这是时间戳差，单位是s
diff.daysDiff：这是天数差，单位是天
diff.monthsDiff：这是月数差，单位是月
diff.yearsDiff：这是年数差，单位是年
diff.weeksDiff：这是周数差，单位是周
]]
local function timeDiff(t1,t2)
	local diff = {}
	if nil == t1 then
		t1 = os.time()
	end
	if nil == t2 then
		--如果只有一个参数，则计算所给的 t1与当前时间的差值
		t2 = t1
		t1 = os.time()
	end

	diff.tRef = t1
	diff.tTgt = t2
	diff.timeDiff = 0
	diff.daysDiff = 0
	diff.monthsDiff = 0
	diff.yearsDiff = 0
	diff.weeksDiff = 0

	local t11 = os.date("*t", t1)
	local t22 = os.date("*t", t2)

	--计算时间差
	diff.timeDiff = t2 - t1

	--计算天数差
	local t11_noTime = os.time({year=t11.year, month=t11.month, day=t11.day})
	local t22_noTime = os.time({year=t22.year, month=t22.month, day=t22.day})
	diff.daysDiff = math.floor((t22_noTime - t11_noTime) / (3600 * 24))

	--计算年数差
	diff.yearsDiff = t22.year - t11.year

	--计算月数差
	diff.monthsDiff = diff.yearsDiff * 12 + t22.month - t11.month

	--计算周数差
	local t1_wn = tonumber(os.date("%w",t1))
	local t2_wn = tonumber(os.date("%w",t2))
	local daysDiffToWeekStart = diff.daysDiff + t1_wn - t2_wn
	diff.weeksDiff = math.floor(daysDiffToWeekStart/7)

	return diff
end

--计算时间偏差的语义，以 t1 为base，计算 t2 的偏离量
local function daysDiffName(t1,t2)
	local tDiff = timeDiff(t1,t2)
	local comment = ''

	if tDiff.daysDiff == -3 then
		comment = '大前天'
	elseif tDiff.daysDiff == -2 then
		comment = '前天'
	elseif tDiff.daysDiff == 0 then
		comment = '今天'
	elseif tDiff.daysDiff == -1 then
		comment = '昨天'
	elseif tDiff.daysDiff == 1 then
		comment = '明天'
	elseif tDiff.daysDiff == 2 then
		comment = '后天'
	elseif tDiff.daysDiff == 3 then
		comment = '大后天'
	elseif tDiff.weeksDiff == -2 then
		comment = '上上周'
	elseif tDiff.weeksDiff == -1 then
		comment = '上周'
	elseif tDiff.weeksDiff == 1 then
		comment = '下周'
	elseif tDiff.weeksDiff == 2 then
		comment = '下下周'
	elseif tDiff.monthsDiff == -2 then
		comment = '上上月'
	elseif tDiff.monthsDiff == -1 then
		comment = '上月'
	elseif tDiff.monthsDiff == 1 then
		comment = '下月'
	elseif tDiff.monthsDiff == 2 then
		comment = '下下月'
	elseif tDiff.yearsDiff == -3 then
		comment = '大前年'
	elseif tDiff.yearsDiff == -2 then
		comment = '前年'
	elseif tDiff.yearsDiff == -1 then
		comment = '去年'
	elseif tDiff.yearsDiff == 1 then
		comment = '明年'
	elseif tDiff.yearsDiff == 2 then
		comment = '后年'
	elseif tDiff.yearsDiff == 3 then
		comment = '大后年'
	elseif tDiff.yearsDiff ~= 0 then
		comment = math.abs(tDiff.yearsDiff)..'年'..((tDiff.yearsDiff<0) and '前' or '后')
	elseif tDiff.monthsDiff ~= 0 then
		comment = math.abs(tDiff.monthsDiff)..'个月'..((tDiff.monthsDiff<0) and '前' or '后')
	elseif tDiff.weeksDiff ~= 0 then
		comment = math.abs(tDiff.weeksDiff)..'周'..((tDiff.weeksDiff<0) and '前' or '后')
	elseif tDiff.daysDiff ~= 0 then
		comment = math.abs(tDiff.daysDiff)..'天'..((tDiff.daysDiff<0) and '前' or '后')
	end

	return comment
end

--=========================这是测试函数=======================
local function test()
	local idx

	local lunarList,jqList,dateList = lunar.jqListComming()
	print("lunarInfo")
	for idx=1,#lunarList do
		print('\t'..lunarList[idx]..'\t'..jqList[idx]..'\t'..dateList[idx])
	end

	local wInfo = week()
	print("week info")
	for idx=1,#wInfo do
		print('\t'..wInfo[idx])
	end
end

--=========================模块化封装=========================
function M.init(...)
	print("-> M.init called here")

	--抛出功能函数
	M.jqListComming = lunar.jqListComming
	M.jqIdxByName = lunar.jqIdxByName
	M.jqInfoByTime = lunar.jqInfoByTime
	M.jqListBuild = lunar.jqListBuild

	M.timeInfoByTime = timeInfoByTime
	M.dateInfoByTime = dateInfoByTime
	M.dateInfoByDaysOffset = dateInfoByDaysOffset
	M.week = week
	M.wInfoByTime = wInfoByTime
	M.timeLogo = timeLogo
	M.timeDiff = timeDiff
	M.daysDiffName = daysDiffName

	M.setDbg = setDbg
	M.test = test
end

M.init()

return M