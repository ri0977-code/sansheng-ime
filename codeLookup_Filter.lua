-- codeLookup_Filter.lua
-- 五笔词通：编码反查 + 多音字注释（独立滤镜，不改动 inputShow_Filter.lua）
-- 版本：v2.1  (2026-10-15)
--
-- 设计原则（吸取 dsh/doubao 教训）：
--   1. 独立文件，绝不整文件替换 inputShow_Filter，避免「修一个坏一个」。
--   2. 全程 pcall 保护，任何候选处理出错都不阻断 yield，绝不导致候选中断。
--   3. comment 一律用 cand:get_genuine().comment 赋值，且先 `or ''` 防 nil 崩溃
--      （dsh 旧版 cand.comment = cand.comment .. extra 在 nil 时崩 coroutine，导致调频/自造词全废）。
--   4. 只改 comment，不改候选顺序与身份 → 调频/自造词不受影响。
--   5. 复用 phraseComment 开关（默认开）：关闭 commentOn 时本滤镜不输出注释。
--
-- v2.1 修复（解决 dsh 遗留 + 本轮反馈）：
--   A. 非词典词的反查编码，改用【标准五笔组词规则】按每字首码现算
--      （2字=每字前2码；3字=前2+第1+后2；4字=每字第1码；>4=前三字第1码+末字前2），
--      不再把每个字的「全码」裸拼（旧版 itx+iu+tg+tr=itxiutgtr 打不出原词）。
--      词库已收录的词（含 wubi_citong 补充词典）优先用词典实码，保证与「真能打出」一致。
--   B. 新增 wubi_citong.dict.yaml 补充词典（从拼音词库挑出 wubi86 未收录的多字词，
--      按组词规则登记正确编码），使常见多字词（如 海洋生物→iitt）可单码打出。
--
-- 插入位置：wubi_pinyin.custom.yaml 的 engine/filters 中，pinyinAdding_Filter 之后插入
--   - lua_filter@codeLookup_Filter
-- 并在 rime.lua 末尾增加：
--   codeLookup_Filter = require("codeLookup_Filter")

local M = {}

local logEnable, log = pcall(require, "runLog")
local sysInfoEnable, sysInfo = pcall(require, 'sysInfo')
local utf8StringEnable, utf8String = pcall(require, 'utf8String')

local utf8Len = (utf8StringEnable and utf8String.utf8Len) or function(s)
  local n = 0
  for _ in string.gmatch(s or "", "[\1-\127\194-\244][\128-\191]*") do n = n + 1 end
  return n
end

-- 计算 Rime 数据目录（dict 文件所在）。优先运行时 API 返回的目录，
-- 其次硬编码已知目录 D:/Program Files/Rime（dsh 确认的程序目录即数据目录），
-- 再次 fallback 到 lua 目录的上一级。以「该目录下存在 wubi86.dict.yaml」为准。
local function dir_has_dicts(dir)
  local f = io.open(dir .. '/wubi86.dict.yaml', 'r')
  if f then f:close(); return true end
  return false
end

local function resolve_data_dir()
  local candidates = {}
  local ok_api, api = pcall(function() return rime.get_api() end)
  if ok_api and api then
    local ok2, dd = pcall(api.get_user_data_dir, api)
    if ok2 and dd and dd ~= '' then candidates[#candidates + 1] = dd:gsub('\\', '/') end
  end
  candidates[#candidates + 1] = 'D:/Program Files/Rime'
  if sysInfoEnable and sysInfo.currentDir then
    local ok, cd = pcall(sysInfo.currentDir)
    if ok and cd and cd ~= '' then
      candidates[#candidates + 1] = cd:gsub('/lua$', ''):gsub('\\lua$', '')
    end
  end
  for _, d in ipairs(candidates) do
    if dir_has_dicts(d) then return d end
  end
  return candidates[1] or ''
end

M.data_dir = resolve_data_dir()

-- 五笔码表：text -> 最短五笔码（多条目取最短，如 电:jn < jnv、长:ta < tayi）
local wubiMap = {}
-- 拼音表：text(单字/词) -> 读音数组（多音字收集全部读音）
local pinyinMap = {}

local function split_tab(line)
  local fields = {}
  local start = 1
  while true do
    local tabPos = line:find('\t', start, true)
    if not tabPos then break end
    fields[#fields + 1] = line:sub(start, tabPos - 1)
    start = tabPos + 1
  end
  fields[#fields + 1] = line:sub(start)
  return fields
end

local function add_wubi(text, code)
  if not text or not code or text == '' or code == '' then return end
  local cur = wubiMap[text]
  -- 仅当不存在或新码更短时写入，保证规范最短码优先；自造词表/ user.txt 只在缺位时填充
  if not cur or #code < #cur then
    wubiMap[text] = code
  end
end

local function add_pinyin(text, py)
  if not text or not py or text == '' or py == '' then return end
  if not pinyinMap[text] then pinyinMap[text] = {} end
  for _, v in ipairs(pinyinMap[text]) do
    if v == py then return end
  end
  pinyinMap[text][#pinyinMap[text] + 1] = py
end

local function load_dict_file(path, kind)
  local f = io.open(path, 'r')
  if not f then
    if logEnable then log.writeLog('codeLookup: 找不到字典 ' .. tostring(path)) end
    return 0
  end
  local n = 0
  local inData = false
  for line in f:lines() do
    local c3 = line:sub(1, 3)
    if c3 == '---' then
      inData = false
    elseif c3 == '...' then
      inData = true
    elseif inData then
      if line:sub(1, 1) ~= '#' then
        local fields = split_tab(line)
        local text, val = fields[1], fields[2]
        if text and val and text ~= '' and val ~= '' and #text <= 12 then
          if kind == 'wubi' then
            add_wubi(text, val)
          elseif kind == 'pinyin' then
            add_pinyin(text, val)
          end
          n = n + 1
        end
      end
    end
  end
  f:close()
  if logEnable then log.writeLog('codeLookup: 载入 ' .. tostring(path) .. ' entries=' .. n) end
  return n
end

-- 载入全部反查数据源。五笔码优先主词库，自造词/用户词典/补充词典只在缺位时补；
-- 拼音全量载入（多音字收集全部读音）。
function M.load(dir)
  dir = dir or M.data_dir
  M.data_dir = dir
  wubiMap = {}
  pinyinMap = {}
  load_dict_file(dir .. '/wubi86.dict.yaml', 'wubi')          -- 主五笔词库（13.7万条）
  load_dict_file(dir .. '/wubi_citong.dict.yaml', 'wubi')      -- v2.1 补充词典：拼音多字词正确组词码
  load_dict_file(dir .. '/wnwb_wubi_custom_wp.dict.yaml', 'wubi') -- 万能五笔自造词
  load_dict_file(dir .. '/wnwb_wubi_user_wp.dict.yaml', 'wubi')   -- 用户五笔自造词
  load_dict_file(dir .. '/user.txt', 'wubi')                       -- 运行时自造词/用户词（兜底反查）
  load_dict_file(dir .. '/cn_pinyin_wp.dict.yaml', 'pinyin')       -- 全量汉字拼音（含多音字多行）
  return M
end

-- 取五笔码：优先整词实码（含补充词典，保证与「真能打出」一致）；
-- 未命中整词时，按【标准五笔组词规则】用每字首码现算（不再裸拼全码）。
local function get_wubi(text)
  local w = wubiMap[text]
  if w then return w end
  local L = utf8Len(text)
  if not L or L < 2 then return nil end
  -- 收集每个字的五笔码；任一字无码则无法组词，返回 nil
  local codes = {}
  for ch in string.gmatch(text, utf8.charpattern) do
    local c = wubiMap[ch]
    if not c then return nil end
    codes[#codes + 1] = c
  end
  local gc
  if L == 2 then
    -- 2字词：每字前 2 码
    gc = string.sub(codes[1], 1, 2) .. string.sub(codes[2], 1, 2)
  elseif L == 3 then
    -- 3字词：第1字前2 + 第2字第1 + 第3字前2
    gc = string.sub(codes[1], 1, 2) .. string.sub(codes[2], 1, 1) .. string.sub(codes[3], 1, 2)
  elseif L == 4 then
    -- 4字词：每字第 1 码
    gc = string.sub(codes[1], 1, 1) .. string.sub(codes[2], 1, 1)
       .. string.sub(codes[3], 1, 1) .. string.sub(codes[4], 1, 1)
  else
    -- >4字：前三字第1码 + 末字前2码
    gc = string.sub(codes[1], 1, 1) .. string.sub(codes[2], 1, 1)
       .. string.sub(codes[3], 1, 1) .. string.sub(codes[L], 1, 2)
  end
  if gc and #gc >= 2 then return gc end
  return nil
end

-- 取拼音：只取「字/词级」拼音（单字多音字在此标全读音，如 长 -> zhang/chang；
-- 多字短语若在拼音库则显示整词拼音，如 你好 -> nihao）。
-- 不再对多字无词级拼音的词逐字裸拼（避免出现 haiyangshengwu 这类拼接噪声）。
local function get_pinyin(text)
  local list = pinyinMap[text]
  if list and #list > 0 then
    return table.concat(list, '/')
  end
  return nil
end

function M.lookup(text)
  local w = get_wubi(text)
  local p = get_pinyin(text)
  local parts = {}
  if w then parts[#parts + 1] = '[' .. w .. ']' end
  if p then parts[#parts + 1] = p end
  return #parts > 0 and table.concat(parts, ' ') or nil
end

-- 是否含有中日韩表意文字（含扩展A与兼容区），用于只注释中文候选
local function has_cjk(text)
  for ch in string.gmatch(text, utf8.charpattern) do
    local b = utf8.codepoint(ch)
    if (b >= 0x3400 and b <= 0x4DBF)   -- 扩展A
       or (b >= 0x4E00 and b <= 0x9FFF) -- 基本汉字
       or (b >= 0xF900 and b <= 0xFAFF) then -- 兼容汉字
      return true
    end
  end
  return false
end

-- 滤镜主体：对每个中文候选追加 [五笔码] 拼音；全程 pcall，出错也不影响 yield。
local function codeLookup(input, env)
  local on = true
  pcall(function() on = env.engine.context:get_option("phraseComment") end)
  if not on then
    for cand in input:iter() do
      yield(cand)
    end
    return
  end
  for cand in input:iter() do
    pcall(function()
      local txt = cand.text or ''
      if has_cjk(txt) then
        local extra = M.lookup(txt)
        if extra then
          local base = cand.comment or ''
          local sep = (base ~= '' and base:sub(-1) ~= ' ' and base:sub(-1) ~= '\r') and ' ' or ''
          cand:get_genuine().comment = base .. sep .. extra
        end
      end
    end)
    yield(cand)
  end
end

M.codeLookup = codeLookup
M.has_cjk = has_cjk
M.get_wubi = get_wubi
M.get_pinyin = get_pinyin

-- 运行时加载（Rime require 本模块时执行一次，建立索引）
M.load()

-- 独立运行自测（仅在非 Rime 环境下：lua54 直接执行本文件时）
if not (sysInfoEnable and sysInfo and sysInfo.currentDir) then
  local testDir = M.data_dir ~= '' and M.data_dir or 'D:/Program Files/Rime'
  M.load(testDir)
  print('codeLookup self-test, data_dir=' .. testDir)
  print('wubi entries=' .. (function() local n=0 for _ in pairs(wubiMap) do n=n+1 end return n end)())
  print('pinyin entries=' .. (function() local n=0 for _ in pairs(pinyinMap) do n=n+1 end return n end)())
  for _, t in ipairs({ '电', '长', '你', '好', '你好', '苹果', '划', '中国', '人民', '银行',
                       '海洋生物', '春夏秋冬', '打印机', '中华人民共和国', '中国人' }) do
    print(t .. ' -> ' .. tostring(M.lookup(t)))
  end
end

return codeLookup
