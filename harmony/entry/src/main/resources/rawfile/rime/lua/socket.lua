-- 三生输入法 · 鸿蒙版 socket.lua（M4 安全桩）
-- 归属：Qoder。桌面的 socket.lua 见 D:/Program Files/Rime/lua/socket.lua。
--
-- 桌面版干什么：require 'socket.core'，去 socket/ 目录加载 luaSocket 的 Windows DLL
--   （core.dll），给 dynamicPhrase_Filter 做「按公网 IP 出动态短语」用。
-- 鸿蒙为什么不能照抄：
--   ① 没有 luaSocket 的 musl 版本，require 必然失败；
--   ② 这台输入法是「本机处理、不联网」的（根 NOTICE 的隐私声明），
--      按公网 IP 查短语本身就是联网行为，产品上就不该做。
--
-- 本实现：保留桌面版的调用契约（socketEnable 开关 + socket.dns.*），
-- 但 socketEnable 恒为 false ⇒ dynamicPhrase_Filter 里那段
--   `if socketEnable then ... socket.dns.getaddrinfo(socket.dns.gethostname()) ...`
-- 永远不进，动态短语只走本地数据（eventsList 那套）。
-- 即使有人误调 socket.dns.getaddrinfo，也只返回 nil，不会抛错打断候选链
-- （run6/run13 的教训：齿轮里抛错 = 整条候选队列断掉）。

local M = {}

-- 恒关：见文件头「本机处理、不联网」。
M.socketEnable = false

M.socket = {
  dns = {
    -- 安全桩：拿不到主机名，也拿不到地址。返回 nil 而不是抛错。
    gethostname = function()
      return nil
    end,
    getaddrinfo = function(_host)
      return nil
    end
  },
  tcp = function()
    return nil
  end,
  connect = function()
    return nil
  end
}

-- 桌面版有 init()，这里保持同名空实现，防止调用方写 socket.init() 时 nil 调用。
function M.init(...)
end

M.init()

return M
