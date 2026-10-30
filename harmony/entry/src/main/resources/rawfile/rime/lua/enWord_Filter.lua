-- enWord_Filter.lua
-- 版本：2026-10-29 17:4x v3.3（英文三张表改「按首字母惰性读桶」+ 行尾 \r 归一；H-272）；三端以此份为准
-- 上一版：2026-10-29 10:5x v3.2（自调频改「最近用过优先」+ 英文必占前三 + 反查补位 + 排障开关）
-- 三生输入法 · 英文单词候选：注释 + 自动判型 + 自调频 + 联想限量
--
-- 排序口径（2026-10-29 主人改定：自调频必须生效，不许固定排序）：
--   ① 用户调频优先——最近一次点过/按数字键/空格上屏过的候选排到最前，其次按累计次数。
--      「最近优先」是 10:5x 主人反馈（qtal 下点了 cat 却上不到第一位）后改的：
--      原来只按次数排，猫 已有 2 次记录，cat 点一次只有 1 次，永远到不了第一位；
--      现在按「谁最后用的谁在前」，点一次就上位，和主人对「调频」的直觉一致。
--      五笔/拼音/英文三种来源一视同仁。
--   ② 没有使用记录时走默认口径：
--      英文本词且有中文译词 → 英文本词#1、中文译词#2；
--      五笔/拼音码或英文前缀 → 中文优先、英文联想最多 MAX_EN_CANDS 个，
--      并且保证前三位里留一个英文位（主人 2026-10-29 口径：五笔/拼音/英文各占前三位一位）；
--      其它 → 零成本放行。
--   ③ 注释：仅给精确本词加「中文 五笔/拼音」，如 apple→苹果 agjs/pingguo
--   ④ 记录落盘：<user_data_dir>/en_word_userfreq.tsv（raw \t 候选 \t 次数 \t 最近序号），跨重启有效。
--      用 commit_notifier 记「这次上屏的是哪个候选」：librime Context::Commit 先触发
--      通知再 Clear，回调里 ctx.input 仍是原码、ctx:get_commit_text() 是可上屏文本。
--      通知要「每个会话各挂一次」，见下面 ensure_hook 的注释（这是之前 Windows 上
--      「换了窗口就不记录」的根因）。
--
-- 性能（2026-10-29 PC 卡顿止血，沿用）：
--   码/前缀场景中文照常流出，英文只收 MAX_EN_CANDS 个即 break，
--   不再把 en_word 的上万条前缀命中逐条迭代。
--   自调频记录的存在不改变早停：只为「找用户用过的英文词」多看 LOOKAHEAD 条。
-- 性能（2026-10-29 17:4x H-272 再止血，nova6 连说两句「还是有点卡」之后）：
--   进窗口不再整表解析英文三张表，改成按键首字母读桶（见下面「按首字母惰性读桶」一段）。
--   台架 _probe/h272_bucket_eq_cost_qoder.py 量的本机口径：旧版一个窗口 load 中位 241.2 ms，
--   新版 17.6 ms + 首键读桶 5.1 ms；按当天真机实测的 3.6 倍 CPU 差折算到 nova6
--   约 868 ms → 约 80 ms。18 个场景输出与旧版逐字节一致，索引坏/缺反查表也一致（兜底）。
--
-- 合同：librime 1.13 协程生成器：for cand in input:iter() do ... yield(cand) end

local M = {}

local MAX_EN_CANDS = 5  -- 英文联想候选最多保留数（不含用户调频选过的）
local SCAN_CAP = 40       -- 场景1b 每次最多扫这么多条（有界；量级与场景2/3 原早停一致）
local LOOKAHEAD = 45    -- 场景2/3 找「用户用过的英文词」时的英文前瞻条数上限
local MAX_ZH_CANDS = 60 -- 场景2/3 中文候选上限（2026-10-29 19:4x 加，H-274：不设上限时每键 45-73 ms）

-- ---------------------------------------------------------------- 数据目录

local function candidate_dirs()
  local c = {}
  local ok, api = pcall(function() return rime.get_api() end)
  if ok and api then
    local ok2, dd = pcall(api.get_user_data_dir, api)
    if ok2 and dd and dd ~= '' then c[#c + 1] = dd:gsub(string.char(92), '/') end
  end
  local okd, info = pcall(function() return debug.getinfo(1, 'S') end)
  if okd and info and info.source and tostring(info.source):sub(1, 1) == '@' then
    local p = tostring(info.source):sub(2):gsub(string.char(92), '/'):match('^(.-)/lua/[^/]+$')
    if p and p ~= '' then c[#c + 1] = p end
  end
  c[#c + 1] = 'D:/Program Files/Rime'
  local e = os.getenv('APPDATA')
  if e and e ~= '' then c[#c + 1] = (e .. '/Rime'):gsub(string.char(92), '/') end
  return c
end

-- ---------------------------------------------------------------- 词表

local glossMap = {}
local transMap = {}
local transList = {}  -- 英文 → 中文译词（按表里原顺序，1b 造候选要用第一条）
local codeSet = {}
local revMap = {}   -- 中文 → 英文本词，供码/拼音输入时把英文补进前三（优先读 en_word_rev.tsv）

-- 2026-10-29 17:3x H-272 台架逐字节比对逼出来的一条：三张表（gloss/trans/codes）是 CRLF，
-- rev/idx 是 LF。Windows 上 io.open('r') 会把 CRLF 翻成 LF，Linux/安卓不会——
-- 于是同一份数据在安卓上每个值末尾都挂着一个 '\r'（注释里跟着走，看不见但存在）。
-- 桶读走的是 'rb'（必须按字节偏移取段），更不会有这个翻译。
-- 统一在这里 chomp 掉行尾 '\r'：两个平台、两条读法（整表 / 读桶）出来的值完全一致。
-- 用 byte(-1)==13 判断而不是 sub(-1)：整表一次要过 21 万行，sub 每行多造两个字符串，
-- 台架量出来那一下能把整表成本从 264 ms 顶到 563 ms（兜底路径就是整表，不能让它变慢）。
local function chomp(s)
  if s:byte(-1) == 13 then return s:sub(1, -2) end
  return s
end

-- 2026-10-29 19:2x Qoder：鸿蒙侧「调频生效但卡」，PC 台架量不出来，只能在设备上量。
-- 输出走 io.stderr（rime.lua 注释里实测：这条能落进 hilog，全局 warn 落不进去）。
-- 只在 load（每窗口一次）和单次读桶超过 5 ms 时打，正常打字不刷屏。
local function dbgline(s)
  pcall(function() io.stderr:write('[ENW] ' .. s .. '\n') end)
end

-- 每次按键都会调一次滤镜，量这一层才看得出「越打越卡」花在哪
local function __cost(raw, t0, tag)
  local dt = (os.clock() - t0) * 1000
  if dt > 2 then dbgline(string.format('%s %.1f ms raw=%s', tag, dt, raw)) end
end

local function load_gloss(path)
  local f = io.open(path, 'r'); if not f then return 0 end
  local n = 0
  for line in f:lines() do
    local ln = chomp(line)
    local t = ln:find('\t', 1, true)
    if t then
      local k, v = ln:sub(1, t - 1), ln:sub(t + 1)
      if k ~= '' then glossMap[k] = v; n = n + 1 end
    end
  end
  f:close(); return n
end

-- 反查表：离线按「译词第一位优先 + 词典权重≥3 + 取短」生成（_probe/gen_en_word_rev.py），
-- 运行时只做一次查表；缺文件时退回用 gloss 首义项凑一个（质量差些但不空）。
local function load_rev(path)
  local f = io.open(path, 'r'); if not f then return 0 end
  local n = 0
  for line in f:lines() do
    local zh, w = chomp(line):match('^([^\t]+)\t(%S+)$')
    if zh and w then revMap[zh] = w; n = n + 1 end
  end
  f:close(); return n
end

-- 2026-10-29 19:5x Qoder（H-274 收尾）：反查表 22,262 行 / 373,202 B，原来每个新输入窗口整表读，
-- 设备实测 load 里它占 17-24 ms（占整个 load 的 95%）。可补位时只查「前三条中文」的反查，
-- 一次最多用两三个首字节段。现在改成按 UTF-8 首字节 seek+read 只读那一段（最大 110 KB）。
-- 兜底一条不许猜：索引缺失、键首字节不在表里、读段失败 ⇒ 整表读＝旧行为。
local revIdx = nil          -- { [byte0] = {s=起始字节, l=长度} }
local revDone = {}          -- 已并进内存的段
local revFile = nil         -- 'rb' 句柄
local revAll = false        -- 整表读过了

local function load_rev_idx(path)
  local f = io.open(path, 'r'); if not f then return nil end
  local idx, n = {}, 0
  for line in f:lines() do
    local ln = chomp(line)
    if ln:sub(1, 1) ~= '#' then
      local name, b0, st, len = ln:match('^(%S+)	(%d+)	(%d+)	(%d+)$')
      if name and b0 then
        idx[tonumber(b0)] = { s = tonumber(st), l = tonumber(len) }
        n = n + 1
      end
    end
  end
  f:close()
  return n > 0 and idx or nil
end

local function rev_each(blob)
  for ln in (blob .. '\n'):gmatch('([^\n]*)\n') do
    local zh, w = chomp(ln):match('^([^\t]+)\t(%S+)$')
    if zh and w then revMap[zh] = w end
  end
end

local function rev_whole()
  revAll = true
  if not revFile then return end
  revFile:seek('set', 0)
  rev_each(revFile:read('*a') or '')
end

-- 读 zh 所在的那一段；索引指望不上就整表读
local function ensure_rev(zh)
  if revAll then return end
  if not revIdx or not revFile then rev_whole(); return end
  local b0 = zh and zh:byte(1)
  if not b0 or not revIdx[b0] then rev_whole(); return end
  if revDone[b0] then return end
  revDone[b0] = true
  local rng = revIdx[b0]
  local t0 = os.clock()
  revFile:seek('set', rng.s)
  local blob = revFile:read(rng.l)
  if not blob then
    revDone[b0] = nil
    rev_whole()
    return
  end
  rev_each(blob)
  local dt = (os.clock() - t0) * 1000
  if dt > 3 then dbgline(string.format('revseg 0x%02X %.1f ms %d B', b0, dt, rng.l)) end
end

local function rev_of(zh)
  ensure_rev(zh)
  return revMap[zh]
end

local function build_rev_fallback()
  local n = 0
  for w, g in pairs(glossMap) do
    if #w >= 2 and w:match('^[a-zA-Z]+$') then
      local zh = g:match('^([^%s]+)')
      if zh then
        local cur = revMap[zh]
        if not cur or #w < #cur or (#w == #cur and w < cur) then revMap[zh] = w; n = n + 1 end
      end
    end
  end
  return n
end

local function load_trans(path)
  local f = io.open(path, 'r'); if not f then return 0 end
  local n = 0
  for line in f:lines() do
    local ln = chomp(line)
    local t = ln:find('\t', 1, true)
    if t then
      local k, v = ln:sub(1, t - 1), ln:sub(t + 1)
      local set = {}
      for zh in v:gmatch('[^|]+') do set[zh] = true end
      transMap[k] = set; n = n + 1
      local lst = {}
      for zh in v:gmatch('[^|]+') do
        if zh ~= '' then lst[#lst + 1] = zh end
      end
      if #lst > 0 then transList[k] = lst end
    end
  end
  f:close(); return n
end

local function load_codes(path)
  local f = io.open(path, 'r'); if not f then return 0 end
  local n = 0
  for line in f:lines() do
    line = line:gsub('%s+$', '')
    if line ~= '' then codeSet[line] = true; n = n + 1 end
  end
  f:close(); return n
end

-- ---------------------------------------------------------------- 按首字母惰性读桶（H-272）
-- 2026-10-29 17:2x Qoder，主人 nova6 连说两句「还是有点卡」之后量的就是这一段：
--   librime 每个输入窗口一个新 Lua VM，旧写法一进窗口就把 gloss/trans/codes 三张表整表读进内存
--   （本机分段：gloss 37-60 ms、trans 124-139 ms、codes 42-71 ms、rev 14-34 ms，合计 217 ms；
--    nova6 的 CPU 当天实测比本机慢 3.6 倍 ⇒ 折算一个窗口约 0.9 s，正对上「等1秒吧大概」）。
--   现在改读 en_word_ltr_idx.tsv（_probe/gen_en_word_ltr_idx.py 生成，只记字节偏移、不复制词库）：
--   按键的首字母 seek+read 只读那一桶（最大 158 KB / 平均 50 KB，整表是 3.5 MB）。
-- 兜底口径一条不许猜：索引缺失、键不升序、首字符不是字母、读段失败 ⇒ 一律退回整表读＝旧行为，
--   功能少一条都不算优化。

local bucketIdx = nil       -- { gloss = { a = {s=起始字节, l=长度}, ... }, trans = {}, codes = {} }
local bucketDone = {}       -- { gloss = { a = true }, ... }：这个桶已经并进内存
local bucketAll = {}        -- { gloss = true }：这张表整表读过了，不必再看桶
local bucketFiles = {}      -- { gloss = 文件句柄 }（'rb' 常驻，本 VM 复用）
local filePaths = {}        -- { gloss/trans/codes = 全路径 }
local bucketHits = 0        -- 排障用：本 VM 走了几次桶读

local function bucket_letter(k)
  if not k or k == '' then return nil end
  local c = k:sub(1, 1):lower()
  if c:match('^[a-z]$') then return c end
  return nil
end

local function bucket_each(name, blob)
  if name == 'gloss' then
    for ln in (blob .. '\n'):gmatch('([^\n]*)\n') do
      local line = chomp(ln)
      local tab = line:find('\t', 1, true)
      if tab then
        local k, v = line:sub(1, tab - 1), line:sub(tab + 1)
        if k ~= '' then glossMap[k] = v end
      end
    end
  elseif name == 'codes' then
    for ln in (blob .. '\n'):gmatch('([^\n]*)\n') do
      local one = ln:gsub('%s+$', '')
      if one ~= '' then codeSet[one] = true end
    end
  else
    for ln in (blob .. '\n'):gmatch('([^\n]*)\n') do
      local line = chomp(ln)
      local tab = line:find('\t', 1, true)
      if tab then
        local k, v = line:sub(1, tab - 1), line:sub(tab + 1)
        local set = {}
        for zh in v:gmatch('[^|]+') do set[zh] = true end
        transMap[k] = set
        local lst = {}
        for zh in v:gmatch('[^|]+') do if zh ~= '' then lst[#lst + 1] = zh end end
        if #lst > 0 then transList[k] = lst end
      end
    end
  end
end

local function load_whole(name)
  bucketAll[name] = true
  local p = filePaths[name]
  if not p then return 0 end
  if name == 'gloss' then return load_gloss(p) end
  if name == 'codes' then return load_codes(p) end
  return load_trans(p)
end


-- 读一张表里 key 所在的那一桶；返回 true 表示「查这张表前该做的加载做完了」
local function ensure_bucket(name, key)
  if bucketAll[name] then return true end
  if not key or key == '' then return true end     -- 空键：什么都不用查，别为此整表读
  local l = bucket_letter(key)
  if not l or not bucketIdx or not bucketIdx[name] or not bucketIdx[name][l] then
    load_whole(name)                               -- 索引指望不上 → 整表兜底
    return true
  end
  bucketDone[name] = bucketDone[name] or {}
  if bucketDone[name][l] then return true end
  bucketDone[name][l] = true
  if bucketFiles[name] == nil then
    bucketFiles[name] = filePaths[name] and io.open(filePaths[name], 'rb') or false
  end
  local f = bucketFiles[name]
  if not f then
    bucketDone[name][l] = nil
    return load_whole(name) > 0
  end
  local rng = bucketIdx[name][l]
  local __t = os.clock()
  f:seek('set', rng.s)
  local blob = f:read(rng.l)
  if not blob then
    bucketDone[name][l] = nil
    return load_whole(name) > 0
  end
  bucketHits = bucketHits + 1
  bucket_each(name, blob)
  local __dt = (os.clock() - __t) * 1000
  if __dt > 5 then
    dbgline(string.format('bucket %s/%s %.1f ms %d B', name, l, __dt, rng.l))
  end
  return true
end

local function gloss_of(w)      ensure_bucket('gloss', w); return glossMap[w] end
local function trans_set_of(w)  ensure_bucket('trans', w); return transMap[w] end
local function trans_list_of(w) ensure_bucket('trans', w); return transList[w] end
local function code_of(w)       ensure_bucket('codes', w); return codeSet[w] end

local function load_index(path)
  local f = io.open(path, 'r'); if not f then return nil end
  local idx, n = {}, 0
  for line in f:lines() do
    local ln = chomp(line)
    if ln:sub(1, 1) ~= '#' then
      local name, l, s, len = ln:match('^(%S+)\t([a-z])\t(%d+)\t(%d+)$')
      if name and l then
        idx[name] = idx[name] or {}
        idx[name][l] = { s = tonumber(s), l = tonumber(len) }
        n = n + 1
      end
    end
  end
  f:close()
  return n > 0 and idx or nil
end

-- ---------------------------------------------------------------- 自调频记忆

local freq = {}        -- raw -> { [候选文本] = 使用次数 }
local freqSeq = {}     -- raw -> { [候选文本] = 最近使用的全局序号 }（越大越新）
local seqCounter = 0   -- 全局递增序号，跨重启由文件里的 seq 续上
local freqPath = nil
local lastRaw = ''     -- 最近一次滤镜看到的原码（上屏回调里 ctx.input 万一已空时兜底）
local lastFreqSize = nil -- 调频文件字节数；变了才重读（每个输入窗口一个 Lua 虚拟机，靠文件同步）
local dbgOn = false    -- 数据目录有 en_word_debug.on 时开排障日志
local dbgDir = ''

local function trace(msg)
  if not dbgOn then return end
  local fh = io.open(dbgDir .. '/en_word_debug.log', 'a')
  if fh then fh:write(os.date('%H:%M:%S ') .. msg .. '\n'); fh:close() end
end

-- 解析调频文件并「取大」合并进内存（同一 raw/txt 已记 5 次，读到 3 次不会倒退）。
-- 2026-10-29 11:5x 真机双会话台架查出两个必须一起修的问题：
--   ① 每个输入窗口是独立 session、独立 Lua 虚拟机，commit_notifier 只挂在自己那份
--      Context 上。旧版「只挂一次」= 换窗口打字完全不记录（主人机上 09:42 之后
--      一笔都没写进文件，而单会话台架看着一切正常）。
--   ② 保存是整文件重写：A 窗口内存里没有 B 窗口刚写的记录，A 一写就把 B 的抹掉。
--   所以写入前先按大小变化重读合并，且合并用「取大」而不是累加
--   （自己刚写的那行再读回来不能翻倍）。
local function parse_freq_file()
  if not freqPath then return 0 end
  local f = io.open(freqPath, 'r'); if not f then return 0 end
  local sz = f:seek('end')
  f:seek('set', 0)
  local n = 0
  for line in f:lines() do
    -- 兼容旧格式（三列）：没有 seq 的按「读取顺序」补一个递增序号，老记录仍能参与排序
    local raw, txt, cnt, seq = line:match('^(%S+)\t(.-)\t(%d+)\t?(%d*)$')
    if raw and txt and txt ~= '' then
      local m = freq[raw]; if not m then m = {}; freq[raw] = m end
      local c = tonumber(cnt) or 1
      if (m[txt] or 0) < c then m[txt] = c end
      local s = tonumber(seq)
      if not s or s <= 0 then
        seqCounter = seqCounter + 1
        s = seqCounter
      elseif s > seqCounter then
        seqCounter = s
      end
      local sm = freqSeq[raw]; if not sm then sm = {}; freqSeq[raw] = sm end
      if s > (sm[txt] or 0) then sm[txt] = s end
      n = n + 1
    end
  end
  f:close()
  return n
end

local function load_freq(path)
  freqPath = path
  lastFreqSize = nil
  return parse_freq_file()
end

-- 文件字节数没变就什么都不做；变了才整份重读合并
local function merge_from_disk()
  if not freqPath then return end
  local sz
  local f = io.open(freqPath, 'r')
  if f then
    sz = f:seek('end')
    f:close()
  else
    sz = 0
  end
  if sz == nil then return end
  if lastFreqSize == sz then return end
  lastFreqSize = sz
  parse_freq_file()
end

local function save_freq()
  if not freqPath then return end
  local lines = {}
  for raw, m in pairs(freq) do
    if raw:match('^[a-z]+$') then
      local sm = freqSeq[raw] or {}
      for txt, cnt in pairs(m) do
        if txt ~= '' and txt:find('[\t\r\n]') == nil then
          lines[#lines + 1] = raw .. '\t' .. txt .. '\t' .. tostring(cnt) ..
                              '\t' .. tostring(sm[txt] or 0)
        end
      end
    end
  end
  table.sort(lines)
  local body = table.concat(lines, '\n')
  if #lines > 0 then body = body .. '\n' end
  local f = io.open(freqPath, 'w')
  if not f then return end
  f:write(body)
  f:close()
  lastFreqSize = #body
end

local function record(raw, txt)
  raw = tostring(raw or ''):lower()
  txt = tostring(txt or '')
  if raw == '' or txt == '' or #txt > 64 then return end
  if raw:match('^[a-z]+$') == nil then return end
  if txt:find('[\t\r\n]') then return end
  merge_from_disk()          -- 先把别的窗口写的记录并进来，避免整文件重写把它们抹掉
  seqCounter = seqCounter + 1
  local m = freq[raw]
  if not m then m = {}; freq[raw] = m end
  m[txt] = (m[txt] or 0) + 1
  local sm = freqSeq[raw]
  if not sm then sm = {}; freqSeq[raw] = sm end
  sm[txt] = seqCounter
  save_freq()
  trace('COMMIT raw=' .. raw .. ' txt=' .. txt .. ' n=' .. tostring(m[txt]) .. ' seq=' .. tostring(seqCounter))
end

-- 上屏时记一笔（Context::Commit 在 Clear 之前发通知，input 还是原码）
--   2026-10-29 11:5x 根因修正：原来用单一 hooked 布尔量「只挂一次」，挂的是第一次跑滤镜
--   那个会话的 context。小狼毫每个输入窗口/每个 app 都是一个独立 session，各自有
--   Context::commit_notifier——只挂首个会话的结果就是：他换窗口打字，回调根本不触发，
--   调频文件从 09:42 起一笔都没写过（真机台架单会话，所以台架看起来「一切正常」）。
--   会话身份怎么拿（台架实测）：tostring(env.engine) 在同一会话里稳定、跨会话不同；
--   而 tostring(env.engine.context) 每次取值都是新代理，不能用。
--   所以按 engine 身份「每个会话挂一次」，表设上限滚动清理；万一地址被新会话复用导致
--   重复挂接，下面的 tick 去重保证一次上屏只记一笔。
local hookedEngine = {}
local hookedOrder = {}
local callTick = 0      -- 每次滤镜调用 +1；同一次上屏触发的多个回调都落在同一个 tick 里
local lastRecTick = -1
local lastRecRaw = ''
local lastRecTxt = ''

local function ensure_hook(env)
  pcall(function()
    local engine = env.engine
    if not engine then return end
    local key = tostring(engine)
    if hookedEngine[key] then return end
    local ctx = engine.context
    if not ctx then return end
    hookedEngine[key] = true
    hookedOrder[#hookedOrder + 1] = key
    if #hookedOrder > 64 then
      local old = table.remove(hookedOrder, 1)
      hookedEngine[old] = nil
    end
    trace('HOOKSET ' .. key .. ' total=' .. tostring(#hookedOrder))
    ctx.commit_notifier:connect(function(cx)
      -- 上屏回调里任何异常都不能冒到引擎（会打断上屏），整段再包一层 pcall
      pcall(function()
        local raw, txt = '', ''
        pcall(function() raw = tostring(cx.input or '') end)
        pcall(function() txt = tostring(cx:get_commit_text() or '') end)
        if txt == '' then
          pcall(function()
            local c = cx:get_selected_candidate()
            if c then txt = tostring(c.text or '') end
          end)
        end
        if raw == '' then raw = lastRaw end
        -- 同一次上屏只记一笔：重复挂接（同一 tick）或重复文本都丢掉
        if callTick == lastRecTick and raw == lastRecRaw and txt == lastRecTxt then
          trace('DUP  raw=' .. tostring(raw) .. ' txt=' .. tostring(txt))
          return
        end
        lastRecTick, lastRecRaw, lastRecTxt = callTick, raw, txt
        -- 排障：记录不起作用时，靠这几行判断是「回调没触发」还是「抓到的文本是空」
        trace('HOOK raw=' .. tostring(raw) .. ' txt=' .. tostring(txt) .. ' last=' .. tostring(lastRaw))
        record(raw, txt)
      end)
    end)
  end)
end

-- 判断候选 text 是否是英文单词（纯英文字母，长度>=2）
-- 2026-10-29 19:4x Qoder（H-274 真凶）：场景2/3 每收一条候选就调一次这里，
-- 而中文候选动辄几百条，`^[a-zA-Z]+$` 每条都跑一遍正则＝每键 45-73 ms（设备实测）。
-- 中文 UTF-8 首字节都 >= 0xE4，先看首字节直接返回 false，绝大多数候选不再进正则。
local function is_en_word(t)
  if t == nil or #t < 2 then return false end
  local b = t:byte(1)
  if not b or b >= 0x80 then return false end
  return t:match('^[a-zA-Z]+$') ~= nil
end

-- 按「最近用过优先、其次次数」把用过的候选提到前面（稳定：同序号保持原有先后）
local function reorder_with_freq(buf, raw)
  local f = freq[raw]
  if not f or next(f) == nil then return buf end
  local s = freqSeq[raw] or {}
  local picks = {}
  for i = 1, #buf do
    local t = buf[i].text or ''
    local n = f[t]
    if n then picks[#picks + 1] = { i = i, n = n, s = s[t] or 0 } end
  end
  if #picks == 0 then return buf end
  table.sort(picks, function(a, b)
    if a.s ~= b.s then return a.s > b.s end
    if a.n ~= b.n then return a.n > b.n end
    return a.i < b.i
  end)
  local used = {}
  local out = {}
  for _, p in ipairs(picks) do used[p.i] = true; out[#out + 1] = buf[p.i] end
  for i = 1, #buf do if not used[i] then out[#out + 1] = buf[i] end end
  return out
end

-- 前三位各占一位（2026-10-29 主人口径：五笔/拼音/英文要在候选前三各占一位）：
--   前三条里一个英文都没有时，把候选流里第一个英文搬到第 3 位。
--   只搬一个、只动一条，不改变其它候选的相对次序。
local function pull_en_into_head(buf)
  if #buf < 3 then return buf end
  for i = 1, 3 do
    if is_en_word(buf[i] and buf[i].text) then return buf end
  end
  local ei = nil
  for i = 4, #buf do
    if is_en_word(buf[i].text) then ei = i; break end
  end
  if not ei then return buf end
  local c = table.remove(buf, ei)
  table.insert(buf, 3, c)
  return buf
end

local function enWord(input, env)
  local __t0 = os.clock()
  callTick = callTick + 1
  local raw = ''
  pcall(function() raw = tostring(env.engine.context.input or '') end)
  if raw == '' then raw = lastRaw end
  raw = raw:lower()
  if raw ~= '' then lastRaw = raw end
  ensure_hook(env)

  merge_from_disk()   -- 别的输入窗口刚写过的记录，这边下一次出候选就该生效
  local f = freq[raw]

  -- 场景1b（2026-10-29 新增）：输入是纯字母、有中文译词，但词库里没有这个英文本词
  --   —— 全是 ECDICT 只有大写形式的缩写词（APP/CPU/OK/AI/URL…，3437 个一条没收）。
  --   引擎此时给不出本词，译词又排在第 147 条，所以直接造两条：本词#1 + 中文译词#2，
  --   后面接有界扫描到的真候选（五笔/拼音中文 + 限 5 条英文联想）。
  if #raw >= 2 and raw:match('^[a-z]+$') ~= nil and gloss_of(raw) == nil and trans_list_of(raw) ~= nil then
    trace('S1b ' .. raw)
    local zhBuf, enBuf = {}, {}
    local enSeen = 0
    for cand in input:iter() do
      local t = cand.text or ''
      if is_en_word(t) then
        enSeen = enSeen + 1
        if enSeen > MAX_EN_CANDS then
          -- 已经够数，剩下的英文补全不再看（这里不 break，是为了继续收中文）
        else
          enBuf[#enBuf + 1] = cand
        end
      else
        zhBuf[#zhBuf + 1] = cand
      end
      if #zhBuf >= 8 or enSeen >= MAX_EN_CANDS + 15 or #zhBuf + enSeen >= SCAN_CAP then break end
    end
    local merged = {}
    -- 本词 #1：注释给「中文译词 + 反查码」，和场景1 的观感保持一致
    local firstZh = trans_list_of(raw)[1]
    merged[1] = Candidate('word', 0, #raw, raw,
                          (gloss_of(raw) or firstZh) .. ' ' .. (rev_of(firstZh) or ''))
    -- 中文译词 #2（若真候选里已经有它，就用引擎那条，别造重复的）
    local dup = nil
    for i = 1, #zhBuf do
      if (zhBuf[i].text or '') == firstZh then dup = i; break end
    end
    if dup then
      merged[2] = table.remove(zhBuf, dup)
    else
      merged[2] = Candidate('word', 0, #raw, firstZh,
                            (rev_of(firstZh) and (raw .. ' ' .. rev_of(firstZh))) or raw)
    end
    for i = 1, #zhBuf do merged[#merged + 1] = zhBuf[i] end
    for i = 1, #enBuf do merged[#merged + 1] = enBuf[i] end
    merged = reorder_with_freq(merged, raw)
    for i = 1, #merged do yield(merged[i]) end
    __cost(raw, __t0, 'enw1b')
    return
  end

  -- 场景1：输入是精确英文本词且有中文译词（glossMap ∩ transMap 命中）
  --   无使用记录 → 英文本词#1、中文译词#2；有使用记录 → 用过的候选按次数在前
  if #raw >= 1 and raw:match('^[a-z]+$') ~= nil and gloss_of(raw) ~= nil and trans_set_of(raw) ~= nil then
    trace('S1 ' .. raw)
    local buf = {}
    for cand in input:iter() do buf[#buf + 1] = cand end

    -- 默认口径：英文本词移到#1
    local wi = nil
    for i = 1, #buf do
      if (buf[i].text or ''):lower() == raw then wi = i; break end
    end
    if wi then
      local w = table.remove(buf, wi)
      table.insert(buf, 1, w)
    end

    -- 默认口径：中文译词移到#2
    local trans = trans_set_of(raw)
    if trans then
      for j = 2, #buf do
        if trans[buf[j].text or ''] then
          local c = table.remove(buf, j)
          table.insert(buf, 2, c)
          break
        end
      end
    end

    -- 给本词加注释（中文释义 + 反查码）
    local g = gloss_of(raw)
    if g then
      for i = 1, #buf do
        if (buf[i].text or ''):lower() == raw then
          pcall(function()
            local base = buf[i].comment or ''
            if base:find(g, 1, true) == nil then
              local sep = (base ~= '' and base:sub(1, 1) ~= ' ') and ' ' or ''
              buf[i]:get_genuine().comment = g .. sep .. base
            end
          end)
          break
        end
      end
    end

    -- 英文联想限量：本词(#1)不计数，其余英文最多 MAX_EN_CANDS 个；
    -- 用户调频选过的英文词不受限（否则被限量吃掉，调频又失效）
    local result = {}
    local enCount = 0
    for i = 1, #buf do
      local t = buf[i].text or ''
      if i > 1 and is_en_word(t) and not (f and f[t]) then
        if enCount < MAX_EN_CANDS then
          result[#result + 1] = buf[i]
          enCount = enCount + 1
        end
      else
        result[#result + 1] = buf[i]
      end
    end

    result = reorder_with_freq(result, raw)
    for i = 1, #result do yield(result[i]) end
    __cost(raw, __t0, 'enw1')
    return
  end

  -- 场景2/3：输入是码（codeSet 命中）或纯英文前缀（含单字母，如 z）
  --   中文优先、英文限量；凑够即停（止血卡顿）。
  --   自调频只需要多看一眼 LOOKAHEAD 条英文，找用户用过的词，不改变早停量级。
  local is_code = code_of(raw)
  if is_code or (#raw >= 1 and raw:match('^[a-z]+$') ~= nil) then
    trace('S23 ' .. raw .. ' code=' .. tostring(is_code == true))
    local zhBuf, enBuf = {}, {}
    local enSeen = 0
    local want = nil
    if f then
      for t in pairs(f) do
        if is_en_word(t) then want = want or {}; want[t] = true end
      end
    end
    for cand in input:iter() do
      local t = cand.text or ''
      if is_en_word(t) then
        enSeen = enSeen + 1
        enBuf[#enBuf + 1] = cand
        if want and want[t] then
          want[t] = nil
          if next(want) == nil then want = nil end
        end
        if enSeen >= MAX_EN_CANDS + 15 and want == nil then break end
        if enSeen >= MAX_EN_CANDS + LOOKAHEAD then break end
      else
        zhBuf[#zhBuf + 1] = cand
        -- 2026-10-29 19:4x Qoder：中文原来不设上限，`input:iter()` 会把几百上千条全收进来，
        -- 后面还要 reorder/pull 各走一遍——这就是「越打越卡、最后一块出来」的来源。
        -- 留 MAX_ZH_CANDS 条足够前几页与前三占位；用户调频过的词由 want 兜住，不会因为截断丢掉。
        if #zhBuf >= MAX_ZH_CANDS then break end
      end
    end
    local merged = {}
    for i = 1, #zhBuf do merged[#merged + 1] = zhBuf[i] end
    local enKeep = 0

    -- 反向补位（2026-10-29 主人口径：五笔/拼音/英文要在候选前三各占一位）：
    --   码或拼音输入时，给首位中文补上它的英文本词，如 qtal→猫 第2位出 cat、mao→毛 第2位出 hair。
    --   只补一个、只在前三条中文里找。
    --   2026-10-29 真机复现修正：英文缓冲里往往已经有这个词（qtal 的 cat、mao 的 hair 都由
    --   译词翻译器产出），旧写法「已存在就不补」会把它留在几百条中文之后，等于没补。
    --   现在改成「从英文缓冲里摘出来放到第 2 位」：摘得到就用引擎原候选（保留注释/权重），
    --   摘不到才现造一个；同时保证它不会再在队尾重复出现。
    if #zhBuf > 0 then
      local headTexts = {}
      for i = 1, math.min(#zhBuf, 6) do headTexts[zhBuf[i].text or ''] = true end
      local seen = 0
      for i = 1, #zhBuf do
        local t = zhBuf[i].text or ''
        if not is_en_word(t) then
          seen = seen + 1
          local w = rev_of(t)
          if dbgOn then
            trace('S2 ' .. raw .. ' zh#' .. tostring(i) .. '=' .. t .. ' rev=' .. tostring(w) .. ' zh=' .. #zhBuf .. ' en=' .. #enBuf)
          end
          if w and w ~= '' and not headTexts[w] then
            local dup = nil
            for j = 1, #enBuf do
              if (enBuf[j].text or '') == w then dup = j; break end
            end
            local cand
            if dup then
              cand = table.remove(enBuf, dup)
            else
              cand = Candidate('word', 0, #raw, w, gloss_of(w) or '')
            end
            table.insert(merged, i + 1, cand)
            break
          end
          if seen >= 3 then break end
        end
      end
    end

    for i = 1, #enBuf do
      local t = enBuf[i].text or ''
      if enKeep < MAX_EN_CANDS or (f and f[t]) then
        merged[#merged + 1] = enBuf[i]
        enKeep = enKeep + 1
      end
    end
    merged = reorder_with_freq(merged, raw)
    merged = pull_en_into_head(merged)
    __cost(raw, __t0, 'enw23')
    if dbgOn then   -- 拼字符串本身有代价，只在开了排障时才拼（打字延迟敏感）
      local r = {}
      for i = 1, math.min(#merged, 6) do r[i] = merged[i].text or '' end
      trace('OUT ' .. raw .. ' ' .. table.concat(r, '|'))
    end
    for i = 1, #merged do yield(merged[i]) end
    return
  end

  -- 场景4：其它 → 零成本放行
  for cand in input:iter() do yield(cand) end
  __cost(raw, __t0, 'enw4')
end

function M.load()
  local __t0 = os.clock()
  local __tA
  bucketDone, bucketAll, bucketFiles, bucketHits = {}, {}, {}, 0
  for _, d in ipairs(candidate_dirs()) do
    local gp = d .. '/en_word_gloss.tsv'
    local pf = io.open(gp, 'r')
    local head = nil
    if pf then head = pf:read('l'); pf:close() end
    if head and head:find('\t', 1, true) then
      M.data_dir = d
      filePaths = { gloss = gp, trans = d .. '/en_word_trans.tsv', codes = d .. '/en_word_codes.txt' }
      __tA = os.clock()
      bucketIdx = load_index(d .. '/en_word_ltr_idx.tsv')
      local __idx = (os.clock() - __tA) * 1000
      M.lazy = (bucketIdx ~= nil)
      -- 桶模式下这三个字段是「当前已读进内存的条数」，开局 0，别当全量看（全量看 M.probe()）
      M.count = 0; M.trans = 0; M.codes = 0
      __tA = os.clock()
      -- 反查表改成按需读：这里只开句柄 + 读分段索引（352 B），不再整表 373 KB。
      revFile = io.open(d .. '/en_word_rev.tsv', 'rb')
      revIdx = revFile and load_rev_idx(d .. '/en_word_rev_idx.tsv') or nil
      revDone = {}
      revAll = false
      local __rev = (os.clock() - __tA) * 1000
      M.rev = revFile and (revIdx and -1 or 0) or 0   -- -1＝有表、按需分段；0＝缺表/无索引
      if not revFile then
        if M.lazy then load_whole('gloss') end   -- 兜底反查要扫整张 gloss 表：先读满，别拿半截表建反查
        M.rev = build_rev_fallback()
      end
      freqPath = d .. '/en_word_userfreq.tsv'
      __tA = os.clock()
      M.freq = load_freq(freqPath)
      local __freq = (os.clock() - __tA) * 1000
      local df = io.open(d .. '/en_word_debug.on', 'r')
      if df then df:close(); dbgOn = true; dbgDir = d end
      dbgline(string.format('load %.1f ms (idx %.1f rev %.1f freq %.1f) lazy=%s rev=%s',
               (os.clock() - __t0) * 1000, __idx, __rev, __freq, tostring(M.lazy),
               revFile and (revIdx and 'seg' or 'whole') or 'none'))
      if dbgOn then
        local lf = io.open(d .. '/en_word_debug.log', 'a')
        if lf then
          lf:write(os.date('%H:%M:%S ') .. 'LOAD dir=' .. d .. ' lazy=' .. tostring(M.lazy) ..
                   ' rev=' .. tostring(M.rev) .. ' freq=' .. tostring(M.freq) .. '\n')
          lf:close()
        end
      end
      return M
    end
  end
  M.data_dir = ''; M.count = 0; M.trans = 0; M.codes = 0; M.freq = 0; M.rev = 0; M.lazy = false
  dbgline('load failed: no data dir')
  return M
end

-- 台架用：本 VM 读了几个桶、内存里各表有多少条（验「只读一段」是否真生效）
function M.probe()
  local ng, nt, nc = 0, 0, 0
  for _ in pairs(glossMap) do ng = ng + 1 end
  for _ in pairs(transList) do nt = nt + 1 end
  for _ in pairs(codeSet) do nc = nc + 1 end
  return { hits = bucketHits, gloss = ng, trans = nt, codes = nc,
           lazy = M.lazy and 1 or 0, rev = M.rev or 0 }
end

M.enWord = enWord
M.record = record
-- 台架/排查用：把调频记录指到别处（不传参则清空内存记录）
function M.set_freq_file(p)
  freq = {}
  freqPath = p or nil
  M.freq = freqPath and load_freq(freqPath) or 0
  return M.freq
end
M.load()

return enWord
