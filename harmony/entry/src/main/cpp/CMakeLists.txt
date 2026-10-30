# 声明最小版本和项目名
cmake_minimum_required(VERSION 3.4.1)
project(fanxing_rime_har)

# 1. 告诉编译器头文件（说明书）在哪里
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

# 2. 创建一个对外的 NAPI 动态库
add_library(fanxing_rime SHARED fanxing_napi.cpp)

# 3. 剥离 CMake 的温和管理，直接指定所有静态库的物理路径
set(RIME_LIB ${CMAKE_CURRENT_SOURCE_DIR}/lib/librime.a)
set(LUA_LIB ${CMAKE_CURRENT_SOURCE_DIR}/lib/liblua.a)
set(OPENCC_LIB ${CMAKE_CURRENT_SOURCE_DIR}/lib/libopencc.a)
set(MARISA_LIB ${CMAKE_CURRENT_SOURCE_DIR}/lib/libmarisa.a)
set(LEVELDB_LIB ${CMAKE_CURRENT_SOURCE_DIR}/lib/libleveldb.a)
set(YAML_LIB ${CMAKE_CURRENT_SOURCE_DIR}/lib/libyaml-cpp.a)
# 🚀 新增：日志排气管！
set(GLOG_LIB ${CMAKE_CURRENT_SOURCE_DIR}/lib/libglog.a)

# 4. 暴力缝合时刻（硬核连接参数）
target_link_libraries(fanxing_rime PUBLIC
    # =======================================================================
    # 🚀 终极暴力链接：
    # 彻底废弃 CMake 的 IMPORTED 机制，直接硬塞物理文件给底层 ld 链接器。
    # --whole-archive 强迫全量吞入；--start-group 处理所有循环依赖。
    # =======================================================================
    -Wl,--whole-archive
    -Wl,--start-group
    ${RIME_LIB}
    ${LUA_LIB}
    -Wl,--end-group
    -Wl,--no-whole-archive

    # 基础依赖库不需要 whole-archive，防止包过大或重复定义
    ${OPENCC_LIB}
    ${MARISA_LIB}
    ${LEVELDB_LIB}
    ${YAML_LIB}
    ${GLOG_LIB} # 🚀 必须在这里挂载，满足日志输出需求！

    # 鸿蒙系统库
    libace_napi.z.so
    libhilog_ndk.z.so
    libc++.a
)