#!/usr/bin/env python3
# h279_bubble_shot.py (Qoder) —— H-278 单手模式下「长按气泡仍在键正上方」的取证脚本
# 思路：uitest 没有 touchDown/touchUp，只有整段的 longClick（按住→松开），
# 而我们的气泡是按下 450ms 后出、松手即消失 ⇒ 必须在 longClick 还在按住的那几百毫秒里抢一帧屏。
# 做法：后台线程发 longClick，主线程连拍 snapshot_display，事后按深色气泡底色 (#3A3F47) 找有泡的帧。
# 用法：python scripts/h279_bubble_shot.py <x> <y> <tag>
import subprocess, sys, os, threading, time, glob

HDC = "D:/DevTools/DevEco/DevEco Studio/sdk/default/openharmony/toolchains/hdc.exe"
OUT = r"F:/qoderwork/sansheng-ime-harmony/docs/evidence/2026-10-30/h279-device"
BG_POP = (0x3A, 0x3F, 0x47)


def sh(args):
    return subprocess.run([HDC, "shell"] + args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def snap(path):
    sh(["snapshot_display", "-f", path])


def main():
    x, y, tag = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    tmp = os.path.join(OUT, "_burst")
    os.makedirs(tmp, exist_ok=True)
    for f in glob.glob(os.path.join(tmp, "*")):
        os.remove(f)
    t = threading.Thread(target=lambda: sh(["uitest", "uiInput", "longClick", str(x), str(y)]), daemon=True)
    t.start()
    frames = []
    for i in range(14):
        p = "/data/local/tmp/%s_%02d.jpeg" % (tag, i)
        snap(p)
        frames.append((i, p))
    time.sleep(0.2)
    for i, p in frames:
        loc = os.path.join(tmp, "%s_%02d.jpeg" % (tag, i))
        subprocess.run([HDC, "file", "recv", p, loc], capture_output=True)
    print("captured", len(glob.glob(os.path.join(tmp, "*.jpeg"))))


if __name__ == "__main__":
    main()
