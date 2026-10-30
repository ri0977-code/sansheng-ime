-- 三生输入法 · 鸿蒙版 sysInfo.lua（M4 沙箱实现）
-- 归属：Qoder。桌面的 sysInfo.lua 见 D:/Program Files/Rime/lua/sysInfo.lua。
--
-- 桌面版干什么：一堆 os.getenv 的 Windows 环境变量读取器 + 一个 currentDir()。
-- 鸿蒙上的处理：
--   ① currentDir() **原样保留**（debug.getinfo(2) 取调用者所在目录）——
--      这是真被用到的：dic_4w / phraseComment / phraseExt / phraseReplace /
--      pinyinAdding / eventsList 六个模块都用它拼「数据表在哪儿」，
--      桌面数据表与脚本同层，鸿蒙上我们也把两者放在同一个 lua/ 目录里 → 天然对齐。
--   ② Windows 环境变量全部给「未知」：dynamicPhrase_Filter 里有
--      `if '未知' ~= sysInfo.WINDIR() then` 这类判断，给「未知」就会跳过 Windows 专属候选，
--      不会在鸿蒙上冒出一堆「C:\Windows\...」的假候选。
--   ③ computerName / userName / osName 给鸿蒙能给的真实值，
--      dynamicPhrase 的「💡系统」候选就能显示真东西而不是「未知」。
--
-- API 与桌面版保持一致：任何桌面模块用到的字段都保留，不删字段（删了会 nil 调用）。

local logEnable, log = pcall(require, "runLog")

local M = {}
local dbgFlg = false

M.setDbg = function(flg)
  dbgFlg = flg
  print('sysInfo dbgFlg is ' .. tostring(dbgFlg))
end

-- 鸿蒙沙箱里 os.getenv 读不到 Windows 变量，一律回落「未知」。
local function envOrUnknown(name)
  local ok, v = pcall(os.getenv, name)
  if ok and v and v ~= '' then
    return v
  end
  return '未知'
end

M.homePath = function()
  return envOrUnknown("HOME")
end

M.computerName = function()
  return envOrUnknown("HOSTNAME")
end

M.userName = function()
  return envOrUnknown("USER")
end

M.osName = function()
  return 'HarmonyOS'
end

M.NUMBER_OF_PROCESSORS = function()
  return envOrUnknown("NUMBER_OF_PROCESSORS")
end

M.pwd = function()
  return envOrUnknown("PWD")
end

M.oldPwd = function()
  return envOrUnknown("OLDPWD")
end

M.PROCESSOR_IDENTIFIER = function()
  return envOrUnknown("PROCESSOR_IDENTIFIER")
end

M.PROGRAMDATA = function()
  return '未知'
end

M.PROGRAMFILES = function()
  return '未知'
end

M.PROGRAMFILESx86 = function()
  return '未知'
end

M.APPDATA = function()
  return '未知'
end

M.WINDIR = function()
  return '未知'
end

M.COMMONPROGRAMFILES = function()
  return '未知'
end

M.COMMONPROGRAMFILESx86 = function()
  return '未知'
end

M.TEMP = function()
  return envOrUnknown("TMPDIR")
end

M.SYSTEMDRIVE = function()
  return '未知'
end

-- 与桌面版同义：返回**调用者**所在目录（debug.getinfo(2) = 调用 currentDir 的那一层）。
-- 桌面上它落在 <安装目录>/lua，鸿蒙上落在 <沙箱用户目录>/lua —— 两个模块都把数据表放在
-- 脚本同层，所以「同层」的语义在两边一致。
M.currentDir = function()
  local info = debug.getinfo(2) -- 2: 返回调用 currentDir 的函数的信息
  if not info or not info.source then
    return ''
  end
  -- 解析 info.source 所在的路径
  local path = info.source
  path = string.sub(path, 2, -1) -- 去掉开头的 "@"
  path = string.gsub(path, '\\', '/')
  path = string.match(path, "^(.*)/") -- 捕获最后一个 "/" 之前的部分
  return path or ''
end

M.writeLog = function(printPrefix)
  printPrefix = printPrefix or ''

  if logEnable then
    log.writeLog(printPrefix .. 'homePath: ' .. M.homePath())
    log.writeLog(printPrefix .. 'computerName: ' .. M.computerName())
    log.writeLog(printPrefix .. 'userName: ' .. M.userName())
    log.writeLog(printPrefix .. 'osName: ' .. M.osName())
    log.writeLog(printPrefix .. 'pwd: ' .. M.pwd())
    log.writeLog(printPrefix .. 'oldPwd: ' .. M.oldPwd())
    log.writeLog(printPrefix .. 'numberOfProcessors: ' .. M.NUMBER_OF_PROCESSORS())
    log.writeLog(printPrefix .. 'progressorIdentifier: ' .. M.PROCESSOR_IDENTIFIER())
    log.writeLog(printPrefix .. 'programData: ' .. M.PROGRAMDATA())
    log.writeLog(printPrefix .. 'programFiles: ' .. M.PROGRAMFILES())
    log.writeLog(printPrefix .. 'programFilesx86: ' .. M.PROGRAMFILESx86())
    log.writeLog(printPrefix .. 'appData: ' .. M.APPDATA())
    log.writeLog(printPrefix .. 'winDir: ' .. M.WINDIR())
    log.writeLog(printPrefix .. 'commonProgramFiles: ' .. M.COMMONPROGRAMFILES())
    log.writeLog(printPrefix .. 'commonProgramFilesx86: ' .. M.COMMONPROGRAMFILESx86())
    log.writeLog(printPrefix .. 'temp: ' .. M.TEMP())
    log.writeLog(printPrefix .. 'systemDrive: ' .. M.SYSTEMDRIVE())
    log.writeLog(printPrefix .. 'currentDir: ' .. M.currentDir())
  end
end

return M
