-- enWord_Filter.lua
-- 版本：2026-10-29 10:5x v3.2（自调频改「最近用过优先」+ 英文必占前三 + 反查补位 + 排障开关）；三端以此份为准
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
--
-- 合同：librime 1.13 协程生成器：for cand in input:iter() do ... yield(cand) end

local M = {}

local MAX_EN_CANDS = 5  -- 英文联想候选最多保留数（不含用户调频选过的）
local LOOKAHEAD = 45    -- 场景2/3 找「用户用过的英文词」时的英文前瞻条数上限

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
local codeSet = {}
local revMap = {}   -- 中文 → 英文本词，供码/拼音输入时把英文补进前三（优先读 en_word_rev.tsv）

local function load_gloss(path)
  local f = io.open(path, 'r'); if not f then return 0 end
  local n = 0
  for line in f:lines() do
    local t = line:find('\t', 1, true)
    if t then
      local k, v = line:sub(1, t - 1), line:sub(t + 1)
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
    local zh, w = line:match('^([^\t]+)\t(%S+)$')
    if zh and w then revMap[zh] = w; n = n + 1 end
  end
  f:close(); return n
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
    local t = line:find('\t', 1, true)
    if t then
      local k, v = line:sub(1, t - 1), line:sub(t + 1)
      local set = {}
      for zh in v:gmatch('[^|]+') do set[zh] = true end
      transMap[k] = set; n = n + 1
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
local function is_en_word(t)
  return t ~= nil and #t >= 2 and t:match('^[a-zA-Z]+$') ~= nil
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
  callTick = callTick + 1
  local raw = ''
  pcall(function() raw = tostring(env.engine.context.input or '') end)
  if raw == '' then raw = lastRaw end
  raw = raw:lower()
  if raw ~= '' then lastRaw = raw end
  ensure_hook(env)

  merge_from_disk()   -- 别的输入窗口刚写过的记录，这边下一次出候选就该生效
  local f = freq[raw]

  -- 场景1：输入是精确英文本词且有中文译词（glossMap ∩ transMap 命中）
  --   无使用记录 → 英文本词#1、中文译词#2；有使用记录 → 用过的候选按次数在前
  if #raw >= 1 and raw:match('^[a-z]+$') ~= nil and glossMap[raw] ~= nil and transMap[raw] ~= nil then
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
    local trans = transMap[raw]
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
    local g = glossMap[raw]
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
    return
  end

  -- 场景2/3：输入是码（codeSet 命中）或纯英文前缀（含单字母，如 z）
  --   中文优先、英文限量；凑够即停（止血卡顿）。
  --   自调频只需要多看一眼 LOOKAHEAD 条英文，找用户用过的词，不改变早停量级。
  if codeSet[raw] or (#raw >= 1 and raw:match('^[a-z]+$') ~= nil) then
    trace('S23 ' .. raw .. ' code=' .. tostring(codeSet[raw] == true))
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
          local w = revMap[t]
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
              cand = Candidate('word', 0, #raw, w, glossMap[w] or '')
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
end

function M.load()
  for _, d in ipairs(candidate_dirs()) do
    local ng = load_gloss(d .. '/en_word_gloss.tsv')
    if ng > 0 then
      M.data_dir = d; M.count = ng
      M.trans = load_trans(d .. '/en_word_trans.tsv')
      M.codes = load_codes(d .. '/en_word_codes.txt')
      M.rev = load_rev(d .. '/en_word_rev.tsv')
      if M.rev == 0 then M.rev = build_rev_fallback() end
      freqPath = d .. '/en_word_userfreq.tsv'
      M.freq = load_freq(freqPath)
      local df = io.open(d .. '/en_word_debug.on', 'r')
      if df then df:close(); dbgOn = true; dbgDir = d end
      if dbgOn then
        local lf = io.open(d .. '/en_word_debug.log', 'a')
        if lf then
          lf:write(os.date('%H:%M:%S ') .. 'LOAD dir=' .. d .. ' gloss=' .. tostring(ng) ..
                   ' rev=' .. tostring(M.rev) .. ' freq=' .. tostring(M.freq) .. '\n')
          lf:close()
        end
      end
      return M
    end
  end
  M.data_dir = ''; M.count = 0; M.trans = 0; M.codes = 0; M.freq = 0
  return M
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
