-- codeLookup_Filter.lua
-- 五笔词通 · 编码反查 + 多音字注释（独立滤镜）
-- VERSION 2.0  (2026-10-15)
--
-- ===== 相对 v1 的关键修复（dsh 遗留坏问题）=====
-- v1 对「不在词库里的多字词」采用「逐字最短码裸拼」，得到的不是五笔组词码，
-- 打不出来。例：海洋生物 → itxiutgtr，实际打出来是「少修生物/不系生物」。
-- v2 改为：
--   1) 整词优先查词库（词库本来就有正确词组码，如 春夏秋冬→ddtt、你好→wqvb）；
--   2) 查不到时，按【五笔标准组词取码规则】现算，绝不再裸拼：
--        二字词：各取前两码       例 你好 = 你(wq)+好(vb) = wqvb
--        三字词：前两字各取首码 + 第三字前两码
--        四字词：各取首码         例 春夏秋冬 = d+d+t+t = ddtt；海洋生物 = i+i+t+t = iitt
--        ≥五字词：前三字首码 + 末字首码
--   这样反查出来的是「真能打出的五笔词组码」，不是假拼接。
--
-- ===== 设计原则（吸取 dsh/doubao 教训，保持不变）=====
--   1. 独立文件，绝不整文件替换 inputShow_Filter，避免「修一个坏一个」。
--   2. 全程 pcall 保护，任何候选处理出错都不阻断 yield，绝不导致候选中断。
--   3. comment 一律用 cand:get_genuine().comment 赋值，且先 `or ''` 防 nil 崩溃
--      （dsh 旧版 cand.comment = cand.comment .. extra 在 nil 时崩 coroutine，导致调频/自造词全废）。
--   4. 只改 comment，不改候选顺序与身份 → 调频/自造词不受影响。
--   5. 复用 phraseComment 开关（默认开）：关闭 commentOn 时本滤镜不输出注释。
--   6. 索引一次性构建（M.load 仅执行一次，M._built 守卫），不随每次按键重建。
--
-- ===== 挂接方式 =====
--   wubi_pinyin.custom.yaml 的 engine/filters 中，pinyinAdding_Filter 之后插入：
--     - lua_filter@codeLookup_Filter
--   rime.lua 末尾增加：
--     codeLookup_Filter = require("codeLookup_Filter")

local M = {}
M.VERSION = "2.0"

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

-- 载入全部反查数据源。五笔码优先主词库，自造词/用户词典只在缺位时补；
-- 拼音全量载入（多音字收集全部读音）。M._built 守卫确保只构建一次。
function M.load(dir)
  if M._built then return M end
  dir = dir or M.data_dir
  M.data_dir = dir
  wubiMap = {}
  pinyinMap = {}
  load_dict_file(dir .. '/wubi86.dict.yaml', 'wubi')          -- 主五笔词库（13.7万条，含正确词组码）
  load_dict_file(dir .. '/wnwb_wubi_custom_wp.dict.yaml', 'wubi') -- 万能五笔自造词
  load_dict_file(dir .. '/wnwb_wubi_user_wp.dict.yaml', 'wubi')   -- 用户五笔自造词
  load_dict_file(dir .. '/user.txt', 'wubi')                       -- 运行时自造词/用户词（兜底反查）
  load_dict_file(dir .. '/cn_pinyin_wp.dict.yaml', 'pinyin')       -- 全量汉字拼音（含多音字多行）
  M._built = true
  return M
end

-- 五笔标准组词取码规则（用于「整词不在词库」时现算正确词组码，绝不再裸拼）。
-- 依赖单字最短码（最短码是完整码的逐字前缀，取其前 1~2 码即该字对应位的标准码）。
local function phrase_code(word)
  local codes = {}
  local n = 0
  for ch in string.gmatch(word, utf8.charpattern) do
    local c = wubiMap[ch]
    if not c or c == '' then return nil end -- 含未收录字 → 无法构成词组码，交给拼音兜底
    n = n + 1
    codes[n] = c
  end
  if n == 0 then return nil end
  if n == 1 then
    return codes[1]
  elseif n == 2 then
    return codes[1]:sub(1, 2) .. codes[2]:sub(1, 2)
  elseif n == 3 then
    return codes[1]:sub(1, 1) .. codes[2]:sub(1, 1) .. codes[3]:sub(1, 2)
  else
    -- 四字及以上：前三字首码 + 末字首码
    return codes[1]:sub(1, 1) .. codes[2]:sub(1, 1) .. codes[3]:sub(1, 1) .. codes[n]:sub(1, 1)
  end
end

-- 取五笔码：优先整词码（词库里的正确词组码）；未命中则按五笔组词规则现算。
local function get_wubi(text)
  local w = wubiMap[text]
  if w then return w end
  return phrase_code(text)
end

-- 取拼音：优先整词读音；否则逐字（多音字该字标 a/b，如 长 -> zhang/chang）
local function get_pinyin(text)
  local list = pinyinMap[text]
  if list and #list > 0 then
    return table.concat(list, '/')
  end
  local res = ''
  for ch in string.gmatch(text, utf8.charpattern) do
    local l = pinyinMap[ch]
    if l and #l > 0 then
      res = res .. table.concat(l, '/')
    end
  end
  return res ~= '' and res or nil
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
M.phrase_code = phrase_code

-- 运行时加载（Rime require 本模块时执行一次，建立索引；M._built 守卫防重复）
M.load()

-- 独立运行自测（仅在非 Rime 环境下：lua54 直接执行本文件时）
if not (sysInfoEnable and sysInfo and sysInfo.currentDir) then
  local testDir = M.data_dir ~= '' and M.data_dir or 'D:/Program Files/Rime'
  M.load(testDir)
  print('codeLookup v' .. M.VERSION .. ' self-test, data_dir=' .. testDir)
  print('wubi entries=' .. (function() local n=0 for _ in pairs(wubiMap) do n=n+1 end return n end)())
  print('pinyin entries=' .. (function() local n=0 for _ in pairs(pinyinMap) do n=n+1 end return n end)())
  for _, t in ipairs({ '电', '长', '你', '好', '你好', '苹果', '划', '中国', '人民', '银行',
                       '海洋生物', '春夏秋冬', '打印机', '中华人民共和国', '我们' }) do
    print(t .. ' -> ' .. tostring(M.lookup(t)))
  end
end

return codeLookup
