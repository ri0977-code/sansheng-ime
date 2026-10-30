#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""桌面三生 WeaselServer 崩溃 dump 解析（Qoder，2026-10-30）

背景（10-30 10:0x）：桌面三生「打不了汉字」的根因窗口终于打开——
事件日志给出 `Application Error / id=1000`：WeaselServer.exe 0.17.4，**异常码 0xC0000374
= STATUS_HEAP_CORRUPTION（堆损坏）**，崩在 ntdll.dll；`C:\sansheng-watch\dumps\WeaselServer.exe.42848.dmp`
是那次崩溃的完整 dump（36.8 MB）。

本脚本只做「无符号」的取证，输出三件事：
  1. 异常码 / 出错地址 / 出错线程；
  2. 崩溃线程的栈扫描：把栈上落在已加载模块区间内的地址还原成 `模块名+偏移`，
     用来判断「是我们改过的那层（weaselx64.dll / rime 相关）还是系统库」；
  3. 全部模块清单（供后续配 PDB 符号化）。

用法：
    python scripts/h279_desktop_dump_analyze_qoder.py [dump路径]
退出码 0＝解析成功；2＝文件不可读。
"""
from __future__ import annotations

import io
import os
import struct
import sys

DEFAULT = r"C:\sansheng-watch\dumps\WeaselServer.exe.42848.dmp"

# 系统库：栈上出现它们没有信息量（只是帧的返回地址落点）
SKIP = ("ntdll", "kernel32", "kernelbase", "user32", "gdi32", "advapi32",
        "ole32", "shell32", "ws2_32", "bcrypt", "sechost", "combase",
        "msvcrt", "ucrtbase", "win32u", "shcore", "imm32", "comctl32")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.isfile(path):
        print("[FAIL] dump 不存在：%s" % path)
        return 2

    from minidump.minidumpfile import MinidumpFile
    from minidump.streams import CONTEXT

    md = MinidumpFile.parse(path)
    mods = [(m.baseaddress, m.baseaddress + m.size, m.name) for m in md.modules.modules]

    def which(a):
        for lo, hi, name in mods:
            if lo <= a < hi:
                return "%s+0x%X" % (name, a - lo)
        return None

    print("=== dump: %s (%d B) ===" % (os.path.basename(path), os.path.getsize(path)))
    print("=== 模块数：%d ===" % len(mods))

    exc = md.exception
    if exc is None:
        print("[FAIL] dump 里没有 exception stream")
        return 2
    tid = None
    for e in exc.exception_records:
        r = e.ExceptionRecord
        code = getattr(r, "ExceptionCode_raw", None)
        print("=== 异常 ===")
        print("  ExceptionCode_raw : 0x%08X%s" % (code, "  (0xC0000374 = STATUS_HEAP_CORRUPTION 堆损坏)"
                                                   if code == 0xC0000374 else ""))
        print("  ExceptionAddress  : 0x%X -> %s" % (r.ExceptionAddress, which(r.ExceptionAddress)))
        print("  ExceptionFlags    : 0x%X" % r.ExceptionFlags)
        print("  ExceptionInfo     : %s" % [hex(x) for x in r.ExceptionInformation])
        print("  ThreadId          : %s" % e.ThreadId)
        tid = e.ThreadId

    reader = md.get_reader()
    th = [t for t in md.threads.threads if t.ThreadId == tid]
    if not th:
        print("[FAIL] 找不到崩溃线程 %s" % tid)
        return 2
    loc = th[0].ThreadContext
    # 线程上下文是**文件偏移**（RVA），不是虚拟地址 ⇒ 直接按偏移读文件
    with open(path, "rb") as fp:
        fp.seek(loc.Rva)
        buf = fp.read(loc.DataSize)
    ctx = CONTEXT.parse(io.BytesIO(buf))
    rip = getattr(ctx, "Rip", None) or getattr(ctx, "RIP", None)
    rsp = getattr(ctx, "Rsp", None) or getattr(ctx, "RSP", None)
    print("=== 崩溃线程 %s 上下文 ===" % tid)
    print("  RIP = %s   (模块: %s)" % (hex(rip) if rip else "?", which(rip) if rip else "?"))
    print("  RSP = %s" % (hex(rsp) if rsp else "?"))

    if rsp:
        # 栈可能跨内存段 ⇒ 分段读，只取包含 rsp 的那一段
        stack = b""
        try:
            for seg in reader.memory_segments:
                if seg.start_virtual_address <= rsp < seg.end_virtual_address:
                    n = min(0x10000, seg.end_virtual_address - rsp)
                    stack = reader.read(rsp, n)
                    break
        except Exception as exc:          # 读不到就如实说明，不假装有
            print("[warn] 栈读取失败：%s" % exc)
        if stack:
            hits, seen = [], set()
            for i in range(0, len(stack) - 8, 8):
                v = struct.unpack_from("<Q", stack, i)[0]
                w = which(v)
                if not w:
                    continue
                if any(s in w.lower() for s in SKIP):
                    continue
                if w in seen:
                    continue
                seen.add(w)
                hits.append((i, v, w))
                if len(hits) >= 24:
                    break
            print("=== 栈上的模块内地址（按栈序，前 24 个唯一落点）===")
            for i, v, w in hits:
                print("  rsp+0x%04X  %016X  %s" % (i, v, w))
            print("  （以上是**无符号**的粗判；要定位到函数需要对应 PDB 符号化）")

    print("=== 模块清单（前 14 个，按大小）===")
    for lo, hi, n in sorted(mods, key=lambda x: -(x[1] - x[0]))[:14]:
        print("  %016X  %08X  %s" % (lo, hi - lo, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
