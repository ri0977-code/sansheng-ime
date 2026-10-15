-- codeLookup_Filter.lua
-- 三生输入法（原五笔词通）：编码反查 + 多音字注释（独立滤镜，不改动 inputShow_Filter.lua）
-- 版本：v3.0  (2026-10-15)
--
-- 设计原则（吸取 dsh/doubao 教训 + 本轮反馈）：
--   1. 独立文件，绝不整文件替换 inputShow_Filter，避免「修一个坏一个」。
--   2. 全程 pcall 保护，任何候选处理出错都不阻断 yield，绝不导致候选中断。
--   3. comment 一律用 cand:get_genuine().comment 赋值，且先 `or ''` 防 nil 崩溃
--      （dsh 旧版 cand.comment = cand.comment .. extra 在 nil 时崩 coroutine，导致调频/自造词全废）。
--   4. 只改 comment，不改候选顺序与身份 → 调频/自造词不受影响。
--   5. 复用 phraseComment 开关（默认开）：关闭 commentOn 时本滤镜不输出注释。
--
-- v3.0 修复（本轮反馈）：
--   A. 【拼音反查恢复】多字词若无词级拼音，按「逐字首选读音」拼接（如 海洋生物 → haiyangshengwu），
--      不再隐藏拼音。注释格式改为「拼音在前、五笔码在后」：haiyangshengwu [iitt]。
--   B. 【杜绝误导性假码】五笔码只显示两种来源：
--        (1) 词库实码（wubi86 / wnwb 自造词 / user.txt 真实词条）；
--        (2) 按【标准五笔组词规则】现算的码，但【若该码已被另一个多字词占用则隐藏】
--            —— 例：家乡的茶 现算 pxra，但 pxra 已被真实词「它找」占用，故隐藏，只显示拼音，避免误导。
--      单字占用（如 海洋生物→iitt 与单字 沙→iitt 共存）属正常，仍显示。
--   C. 【不再手动塞词】彻底移除 v2.1 的 wubi_citong 补充词典（主人要求：遵循自动组词原则，
--      不在词典里随意加词）。海洋生物→iitt 改由「标准组词规则计算 + 无多字撞车」显示，不动词典。
--      真正要可单码打出，靠 Rime 自动组词（连续上屏后即写入 user.txt，本滤镜读取显示）。
--
-- 插入位置：wubi_pinyin.custom.yaml 的 engine/filters 中，pinyinAdding_Filter 之后插入
--   - lua_filter@codeLookup_Filter
-- 并在 rime.lua 末尾增加：
--   codeLookup_Filter = require("codeLookup_Filter")

local M = {}

local logEnable, log = pcall(require, "runLog")
local sysInfoEnable, sysInfo = pcall(require, 'sysInfo')
local utf8StringEnable, utf8String = pcall(require, 'utf8String')

-- 字符数统计：优先用 Lua 5.4 内建 utf8.len（稳定可靠），fallback 到正则计数
local function utf8Len(s)
  if utf8 and utf8.len then
    local n = utf8.len(s or "")
    if n then return n end
  end
  local n = 0
  for _ in string.gmatch(s or "", "[\1-\127\194-\244][\128-\191]*") do n = n + 1 end
  return n
end

-- 计算 Rime 数据目录（dict 文件所在）。优先运行时 API 返回的目录，
-- 其次硬编码已知目录 D:/Program Files/Rime，再次 fallback 到 lua 目录的上一级。
-- 以「该目录下存在 wubi86.dict.yaml」为准。
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

-- 五笔码表：text -> 最短五笔码（多条目取最短）
local wubiMap = {}
-- 拼音表：text(单字/词) -> 读音数组（多音字收集全部读音）
local pinyinMap = {}
-- 多字词占用码集合：code -> true 表示该码已被某个「多字词」占用（用于拦截撞车假码）
local wubiMultiOwners = {}

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

-- user.txt 里的 enc* 自动编码条目不是规范五笔码，跳过（不进反查，也不参与撞车判定）
local function is_real_wubi_code(code)
  if not code or code == '' then return false end
  if code:match('^enc') then return false end   -- Rime 自动编码占位码
  if #code > 4 then return false end             -- 规范五笔码最长 4 位
  return true
end

local function add_wubi(text, code)
  if not text or text == '' or not is_real_wubi_code(code) then return end
  local cur = wubiMap[text]
  if not cur or #code < #cur then
    wubiMap[text] = code
  end
  -- 多字词占用该码 → 记入撞车集合
  if utf8Len(text) and utf8Len(text) >= 2 then
    wubiMultiOwners[code] = true
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
    if logEnable then log.writeLog('codeLookup: 跳过字典(不存在) ' .. tostring(path)) end
    return 0
  end
  -- 识别格式：含 YAML 头分隔符 '---' 的是标准词典（数据在 '...' 之后）；
  -- 否则（如 user.txt 是 tabledb，无 '---'/'...'）整文件即数据，直接读取。
  local hasHeader = false
  local probe = io.open(path, 'r')
  if probe then
    for line in probe:lines() do
      if line:sub(1, 3) == '---' then hasHeader = true; break end
    end
    probe:close()
  end
  local inData = not hasHeader
  local n = 0
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

-- 载入全部反查数据源。五笔码优先主词库；拼音全量载入（多音字收集全部读音）。
-- 注意：user.txt 仅取真实五笔码（enc* 自动编码条目已过滤），用作反查与撞车判定。
function M.load(dir)
  dir = dir or M.data_dir
  M.data_dir = dir
  wubiMap = {}
  pinyinMap = {}
  wubiMultiOwners = {}
  load_dict_file(dir .. '/wubi86.dict.yaml', 'wubi')             -- 主五笔词库（13.7万条）
  load_dict_file(dir .. '/wnwb_wubi_custom_wp.dict.yaml', 'wubi') -- 万能五笔自造词
  load_dict_file(dir .. '/wnwb_wubi_user_wp.dict.yaml', 'wubi')   -- 用户五笔自造词
  load_dict_file(dir .. '/user.txt', 'wubi')                       -- 运行时用户真实词条（自动组词结果）
  load_dict_file(dir .. '/cn_pinyin_wp.dict.yaml', 'pinyin')       -- 全量汉字拼音（含多音字多行）
  return M
end

-- 标准五笔组词规则：用每个字的「最短码」现算词组码
--   2字=每字前2码；3字=前2+第1+后2；4字=每字第1码；>4=前三字第1码+末字前2码
local function group_code(codes, L)
  local gc
  if L == 2 then
    gc = string.sub(codes[1], 1, 2) .. string.sub(codes[2], 1, 2)
  elseif L == 3 then
    gc = string.sub(codes[1], 1, 2) .. string.sub(codes[2], 1, 1) .. string.sub(codes[3], 1, 2)
  elseif L == 4 then
    gc = string.sub(codes[1], 1, 1) .. string.sub(codes[2], 1, 1)
       .. string.sub(codes[3], 1, 1) .. string.sub(codes[4], 1, 1)
  else
    gc = string.sub(codes[1], 1, 1) .. string.sub(codes[2], 1, 1)
       .. string.sub(codes[3], 1, 1) .. string.sub(codes[L], 1, 2)
  end
  if gc and #gc >= 2 and is_real_wubi_code(gc) then return gc end
  return nil
end

-- 取五笔码：优先整词实码（保证与「真能打出」一致）；未命中则按标准组词规则现算，
-- 但【若该码被另一个多字词占用则隐藏】，避免误导（如 家乡的茶 pxra→它找）。
local function get_wubi(text)
  local w = wubiMap[text]
  if w then return w end
  local L = utf8Len(text)
  if not L or L < 2 then return nil end
  local codes = {}
  for ch in string.gmatch(text, utf8.charpattern) do
    local c = wubiMap[ch]
    if not c then return nil end
    codes[#codes + 1] = c
  end
  local gc = group_code(codes, L)
  if not gc then return nil end
  -- 撞车判定：码已被另一个多字词占用 → 不显示（单字占用如 沙→iitt 视为正常共存，仍显示）
  if wubiMultiOwners[gc] then return nil end
  return gc
end

-- 取拼音：优先整词读音（多音字词级读法）；否则逐字首选读音（多字词反查提示，如 海洋生物→haiyangshengwu）。
-- 单字多音字收集全部读音（如 长→zhang/chang）。
local function get_pinyin(text)
  local list = pinyinMap[text]
  if list and #list > 0 then
    return table.concat(list, '/')
  end
  local L = utf8Len(text)
  if not L or L < 2 then return nil end
  local res = ''
  for ch in string.gmatch(text, utf8.charpattern) do
    local l = pinyinMap[ch]
    if l and #l > 0 then
      res = res .. l[1]   -- 多字词逐字取首选读音，保证输出清爽
    else
      return nil
    end
  end
  return res ~= '' and res or nil
end

-- 反查结果：拼音在前、五笔码在后（主人要求格式：haiyangshengwu [iitt]）
function M.lookup(text)
  local p = get_pinyin(text)
  local w = get_wubi(text)
  local parts = {}
  if p then parts[#parts + 1] = p end
  if w then parts[#parts + 1] = '[' .. w .. ']' end
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

-- 滤镜主体：对每个中文候选追加「拼音 [五笔码]」；全程 pcall，出错也不影响 yield。
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
  print('三生输入法 codeLookup self-test, data_dir=' .. testDir)
  print('wubi entries=' .. (function() local n=0 for _ in pairs(wubiMap) do n=n+1 end return n end)())
  print('pinyin entries=' .. (function() local n=0 for _ in pairs(pinyinMap) do n=n+1 end return n end)())
  for _, t in ipairs({ '电', '长', '你', '好', '你好', '苹果', '划', '中国', '人民', '银行',
                       '海洋生物', '春夏秋冬', '打印机', '中华人民共和国', '中国人',
                       '家乡的茶', '它找', '𧟴' }) do
    print(t .. ' -> ' .. tostring(M.lookup(t)))
  end
end

return codeLookup
