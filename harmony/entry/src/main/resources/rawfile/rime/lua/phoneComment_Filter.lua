-- phoneComment_Filter.lua
-- 安卓版专用，由 build-android-qoder.py 生成（桌面版没有这个文件，也不该有）。
-- 取代桌面链尾的 laneChangeAndSpace_Filter：那个的上限是 150 字符且把 <br> 转成真实换行，
-- 是给电脑宽气泡设计的；手机上会把一个候选撑成 3 行，一屏只剩 4 个候选。
--
-- 为什么截断不会伤到反查：codeLookup_Filter 把反查码【前置】写入 comment，
--   本滤镜从右边截，所以 [vbrq] / 拼音 永远先保住，被砍掉的只是末尾的词典释义。
-- 为什么截断不会伤到互译：打 good 出「善行 / 好的」这些候选本身来自 wubi86 主词库表
--   （import_tables 里的 en2zh_v2_wp），注释只是附带说明。
-- 想回到桌面那种长注释：把下面 MAX_WIDTH 改大（或直接换回 laneChangeAndSpace_Filter）再重新打包。

local MAX_WIDTH = 20   -- 一条注释的显示宽度预算：汉字/全角算 2，ASCII 算 1

-- <br> 与 &nbsp 在手机上不换行也没意义，一律折成空格（桌面版是转成 \r 真换行）
local function tidy(s)
  s = s:gsub("<br>", " "):gsub("&nbsp;?", " ")
  s = s:gsub("[ \t]+", " ")
  s = s:gsub("^ ", ""):gsub(" $", "")
  return s
end

-- 按显示宽度截断：UTF-8 首字节定长，汉字 3 字节算 2 格，ASCII 算 1 格
local function clip(s, budget)
  local w, i, out, n = 0, 1, {}, #s
  while i <= n do
    local b = s:byte(i)
    local len = 1
    if b >= 0xF0 then len = 4
    elseif b >= 0xE0 then len = 3
    elseif b >= 0xC0 then len = 2 end
    local cols = (len >= 3) and 2 or 1
    if w + cols > budget then
      return table.concat(out) .. "…"
    end
    w = w + cols
    out[#out + 1] = s:sub(i, i + len - 1)
    i = i + len
  end
  return table.concat(out)
end

local function phoneComment_Filter(input, env)
  for cand in input:iter() do
    local ok, changed, cmt = pcall(function()
      local c = cand.comment
      if not c or c == "" then return false, nil end
      local t = clip(tidy(c), MAX_WIDTH)
      if t == c then return false, nil end
      return true, t
    end)
    if ok and changed then
      -- 用 get_genuine 只改注释，保留候选自身的类型与身份（不重建 Candidate，不动调频/自造词）
      pcall(function() cand:get_genuine().comment = cmt end)
    end
    yield(cand)
  end
end

return phoneComment_Filter
