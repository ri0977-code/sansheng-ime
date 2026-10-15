-- codeLookup_Filter.lua
-- 三生输入法（原五笔词通）：编码反查 + 多音字注释（独立滤镜，不改动 inputShow_Filter.lua）
-- 版本：v1.1  (2026-10-15)
--
-- 设计原则（吸取 dsh/doubao 教训 + 本轮反馈）：
--   1. 独立文件，绝不整文件替换 inputShow_Filter，避免「修一个坏一个」。
--   2. 全程 pcall 保护，任何候选处理出错都不阻断 yield，绝不导致候选中断。
--   3. comment 一律用 cand:get_genuine().comment 赋值，且先 `or ''` 防 nil 崩溃
--      （dsh 旧版 cand.comment = cand.comment .. extra 在 nil 时崩 coroutine，导致调频/自造词全废）。
--   4. 只改 comment，不改候选顺序与身份 → 调频/自造词不受影响。
--   5. 复用 phraseComment 开关（默认开）：关闭 commentOn 时本滤镜不输出注释。
--
-- 版本沿革：五笔词通 v1→v3（在 dsh 残局上重建）＝ 更名前；三生输入法自 v1.0 起重新计版。
--   · v1.0 ＝ 原「五笔词通 v3.0」更名基线：拼音反查恢复(逐字首选读音) + 碰撞检测 + 移除手动词典 + user.txt(tabledb) 正确加载。
--   · v1.1（本轮真机反馈修复）：
--      1) 拼音注释改由上游 pinyinAdding_Filter 负责（其以 ✔ 标注拼音），本滤镜不再追加拼音，
--         仅对「单字多音字」补充全部读音，消除「打拼音时注释里多出一份拼音」的重复。
--      2) 五笔反查码前置：[五笔码] 在前，其余在后，保证始终可见不被末尾截断（如 good→好 的 vbrq）。
--      3) 碰撞隐藏逻辑保留：现算码被另一多字词占用则隐藏（家乡的茶 pxra 与 它找 撞车 → 不显示）。
--      4) 不手动塞词原则不变：遵循自动组词，海洋生物→iitt 由标准规则计算显示，不动词典。
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

-- 反查结果（自测用）：五笔码在前、拼音在后 [wubi] pinyin；正式链路由 codeLookup 处理（含前置与去重）
function M.lookup(text)
  local p = get_pinyin(text)
  local w = get_wubi(text)
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

-- 判断上游（pinyinAdding_Filter）是否已把拼音写进 comment：
-- pinyinAdding 用 '✔' 作为拼音分隔符；或 comment 已含目标拼音串，则视为已显示，避免重复。
local function pinyin_already_shown(base, py)
  if not base or base == '' then return false end
  if base:find('✔', 1, true) then return true end
  if py and py ~= '' and base:find(py, 1, true) then return true end
  return false
end

-- 滤镜主体：仅追加「五笔反查码」（前置，保证可见）+ 单字多音字补全读音；拼音交由上游 pinyinAdding。
-- 全程 pcall，出错也不影响 yield。
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
        local w = get_wubi(txt)
        local p = get_pinyin(txt)
        local L = utf8Len(txt)
        local base = cand.comment or ''
        local parts = {}
        if w then parts[#parts + 1] = '[' .. w .. ']' end
        -- 拼音：单字仅当「多音字(含/)」才补全部读音，避免与上游单读重复；多字词上游已注✔则不重复
        local addPy = false
        if p then
          if L == 1 then
            addPy = (not pinyin_already_shown(base, p)) or (p:find('/', 1, true) ~= nil)
          else
            addPy = not pinyin_already_shown(base, p)
          end
        end
        if addPy then parts[#parts + 1] = p end
        local extra = #parts > 0 and table.concat(parts, ' ') or nil
        if extra then
          -- 五笔码前置：extra 放最前，原 comment 接在后面，确保反查码始终可见不被截断
          local sep = (base ~= '' and base:sub(1, 1) ~= ' ') and ' ' or ''
          cand:get_genuine().comment = extra .. sep .. base
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
