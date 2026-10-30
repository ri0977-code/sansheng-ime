"""横屏真机量具：按像素坐标点三生键盘的键（H-116：dumpLayout 看不见 IME 窗口，
所以坐标只能从 screenCap 的像素里量出来）。

坐标来源：ls01.png（2832x1280，rotation 270，备忘录输入框聚焦、三生 26 键弹起），
用「白键被深色字形切成两段」的方式逐行合并得到键心：
  row1 y=765  q w e r t y u i o p
  row2 y=883  a s d f g h j k l
  row3 y=1001 z x c v b n m
底栏 y=1119 由本目录 measure_bottom.py 复核后填。
"""
import subprocess
import sys
import time

HDC = r"D:\DevTools\DevEco\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"
T = "7GL0226408083897"

KEYS = {
    "q": (456, 765), "w": (670, 765), "e": (883, 765), "r": (1096, 765),
    "t": (1309, 765), "y": (1522, 765), "u": (1735, 765), "i": (1949, 765),
    "o": (2162, 765), "p": (2375, 765),
    "a": (512, 883), "s": (738, 883), "d": (964, 883), "f": (1190, 883),
    "g": (1416, 883), "h": (1642, 883), "j": (1868, 883), "k": (2094, 883),
    "l": (2320, 883),
    "z": (764, 1001), "x": (981, 1001), "c": (1199, 1001), "v": (1416, 1001),
    "b": (1634, 1001), "n": (1851, 1001), "m": (2069, 1001),
}


def run(*args):
    r = subprocess.run(["env", "MSYS2_ARG_CONV_EXCL=*", HDC, "-t", T] + list(args),
                       capture_output=True)
    return ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace")


def tap(x, y, pause=0.30):
    run("shell", "uitest", "uiInput", "click", str(x), str(y))
    time.sleep(pause)


def type_word(word, pause=0.30):
    for ch in word:
        p = KEYS.get(ch)
        if p is None:
            print("unknown key %r" % ch, file=sys.stderr)
            continue
        tap(p[0], p[1], pause)


def swipe(x1, y1, x2, y2, speed=2000, pause=0.6):
    run("shell", "uitest", "uiInput", "swipe", str(x1), str(y1), str(x2), str(y2),
        str(speed))
    time.sleep(pause)


def shot(name):
    run("shell", "uitest", "screenCap", "-p", "/data/local/tmp/%s.png" % name)
    out = "%s.png" % name
    run("file", "recv", "//data/local/tmp/%s.png" % name, out)
    return out
