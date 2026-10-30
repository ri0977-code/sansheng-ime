-- enWord_translator.lua
-- v36：完全空函数——排查 lua_translator 注册本身是否有开销
-- 如果 v36 卡 → 问题在 librime 为 lua_translator 创建 Translation 对象的开销
-- 如果 v36 不卡 → 问题在 enWord_translator 的逻辑（loadBuckets/内存等）

local function enWordTranslate(input, seg)
  return
end

return enWordTranslate
