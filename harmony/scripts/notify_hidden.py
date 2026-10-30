# -*- coding: utf-8 -*-
"""无窗口 Windows 通知包装器（绝不弹黑窗）。

用法：python notify_hidden.py "标题" "消息"

为什么存在：bash / 任务计划（pythonw）链路里直接调 powershell，
Windows 会给控制台子进程新建一个控制台窗口，表现为黑窗狂闪。
本包装对 powershell 调 CREATE_NO_WINDOW + STARTUPINFO(SW_HIDE) 双保险。

署名：WorkBuddy · 2026-10-25
"""
import os
import subprocess
import sys

PS1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notify.ps1")


def main():
    if len(sys.argv) < 3:
        sys.stderr.write("usage: notify_hidden.py <title> <message>\n")
        return 2
    title, message = sys.argv[1], sys.argv[2]
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # SW_HIDE
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", PS1, "-Title", title, "-Message", message],
            creationflags=subprocess.CREATE_NO_WINDOW,
            startupinfo=si, timeout=30, check=False,
        )
    except Exception as e:
        sys.stderr.write("notify failed: %s\n" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
