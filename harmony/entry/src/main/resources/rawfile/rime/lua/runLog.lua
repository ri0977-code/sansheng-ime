-- 三生输入法 · 鸿蒙版 runLog.lua（M4 沙箱实现）
-- 归属：Qoder。桌面的 runLog.lua 见 D:/Program Files/Rime/lua/runLog.lua。
--
-- 桌面版干什么：把日志写到「模块自己所在目录」的 runLog.txt，每次 writeLog 追加一行。
-- 鸿蒙为什么不能照抄：
--   ① 性能：wubi_pinyin 挂了 13 级齿轮，其中 10 级每按一次键都会 writeLog 一次，
--      照抄就是「每按键 10 次文件打开+追加」，IME 进程里直接卡；
--   ② 位置：桌面版往**安装目录**写，鸿蒙上安装目录是只读的 HAP，写不了。
--
-- 本实现：默认空操作（写日志的调用照样是合法函数，不会把候选链打断 ——
-- run6/run13 的教训是「齿轮里的函数抛错会打断整条候选队列」），
-- 需要排查时设环境变量 SS_LUA_LOG=1 才会真的落盘，落在用户目录（沙箱可写）。
--
-- API 与桌面版保持一致：writeLog / setDbg / test / init / logDoc。

local M = {}

-- 诊断开关：默认关。鸿蒙沙箱里 os.getenv 读不到外部环境变量，
-- 所以这里同时支持用 SS_LUA_LOG 文件放在模块目录下来开（沙箱内可写、可放）。
local dbgFlg = false

local function diag_enabled()
  if dbgFlg then
    return true
  end
  local ok, v = pcall(os.getenv, "SS_LUA_LOG")
  if ok and v and v ~= '' then
    return true
  end
  -- 模块目录下的 SS_LUA_LOG 文件存在即开启（沙箱可写，便于现场打开）
  local ok2, f = pcall(function()
    local info = debug.getinfo(1, 'S')
    local src = tostring(info.source):gsub('\\', '/'):sub(2)
    local dir = src:match('^(.-)/[^/]+$')
    if not dir then
      return nil
    end
    local fh = io.open(dir .. '/SS_LUA_LOG', 'r')
    if fh then
      fh:close()
      return true
    end
    return false
  end)
  return ok2 and f == true
end

-- 日志文件：模块目录下的 runLog.txt（沙箱用户目录，可写）
local current_path = string.sub(debug.getinfo(1).source, 2, string.len("/runLog.lua") * -1)
M.logDoc = current_path .. 'runLog.txt'

M.writeLog = function(logStr)
  if not diag_enabled() then
    return
  end
  if nil == logStr then
    logStr = ''
  else
    logStr = tostring(logStr)
  end
  local ok, f = pcall(io.open, M.logDoc, 'a')
  if not ok or not f then
    return
  end
  if '' == logStr then
    f:write('\n')
  else
    local timeStamp = os.date("%Y/%m/%d %H:%M:%S")
    f:write(timeStamp .. '[' .. _VERSION .. ']' .. '\t' .. logStr .. '\n')
  end
  f:close()
end

M.setDbg = function(flg)
  dbgFlg = flg and true or false
  M.writeLog('runLog dbgFlg is ' .. tostring(dbgFlg))
end

M.test = function(printPrefix)
  if nil == printPrefix then
    printPrefix = ' '
  end
  M.writeLog('this is a test string on new line')
  M.writeLog('runLogDoc is: ' .. tostring(M.logDoc))
end

function M.init(...)
  -- 鸿蒙版没有需要初始化的动作
end

M.init()

return M
