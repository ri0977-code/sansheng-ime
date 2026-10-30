#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H-205 / H-206 / H-207 真机一轮：先取「旧包判红」基线，再装机，再验全绿（Qoder，2026-10-26 17:2x）

为什么要有这个驱动（不是偷懒，是顺序问题）：
  主人 2026-10-26 骂的三条（L1 与候选挤成一行 / 退格下滑多恢复一遍 / v 点多少次也粘不上）
  我只在**源码侧**修好了，闸门绿不等于装机绿。而装机之前必须先在**当前这个有缺陷的装机版**上
  把 `bs` / `paste` 两条判据跑出红——判据在缺陷版上是绿的，就等于量具是哑的，
  回头新包「全绿」也证明不了任何事（H-198 那轮就是栽在哑量具上）。
  手机现在是锁屏（主人不在/睡觉），所以我不能把「基线 → 装机 → 复验」拆成两次手动操作，
  也不能凭记忆跳掉基线。本脚本把三步串成一条，且每一步注入前都过 `h164_wait_unlock.guard()`
  （解锁 + 前台必须是我们自己的应用）。

口径（与夜间验收链一致，别改）：
  · 只在「已解锁且桌面空闲」连续两次探测（间隔 --interval 秒）后才动手；
  · 装机目标写死 Mate 80 = 7GL0226408083897，绝不让 install.ps1 猜设备；
  · 跨构建只比 unsigned 字节数，不比 hash（H-133）；
  · 收尾只做 `power-shell suspend` 把屏幕交还给主人，不做任何解锁/点击他应用的动作；
  · 全程只点本应用 `com.sansheng.ime` 的试打框与键盘面板，绝不往第三方应用注入。

用法：
    python scripts/h205_h207_device_round.py                # 守候（默认 480 分钟，90 秒一探）
    python scripts/h205_h207_device_round.py --minutes 60 --interval 60
    python scripts/h205_h207_device_round.py --no-install    # 只取旧包基线，不装机（基线跑完就收）
    python scripts/h205_h207_device_round.py --force         # 跳过守候，现在就跑（自己先看一眼锁屏状态）
"""
import argparse
import datetime
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import h164_wait_unlock as wu            # noqa: E402  复用锁屏判定 / 桌面空闲判定 / 双闸
import h202_h204_device_accept as acc    # noqa: E402  复用本轮真机判据与证据目录

EVID = acc.EVID
SIGNED = os.path.join(ROOT, "entry", "build", "default", "outputs", "default",
                      "entry-default-signed.hap")
TARGET = "7GL0226408083897"               # Mate 80；install.ps1 绝不猜设备
REPORT = os.path.join(EVID, "device_round_report.txt")


def say(msg):
    line = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    os.makedirs(EVID, exist_ok=True)
    with open(REPORT, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def installed_build():
    """装机版身份（旧包基线的凭证）：只取版本号与 updateTime，不碰签名材料。"""
    txt = wu.acc.sh("shell", "bm dump -n com.sansheng.ime")
    keep = [l.strip() for l in txt.splitlines()
            if any(k in l for k in ("versionCode", "versionName", "updateTime", "installTime"))]
    return keep[:6]


def run_step(name, argv):
    """子进程跑同一个脚本的子命令（判据与日志都归它自己），把输出并进报告。"""
    say("STEP %s: python %s" % (name, " ".join(argv)))
    p = subprocess.run([sys.executable] + argv, cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    with open(os.path.join(EVID, "step_%s.log" % name), "w", encoding="utf-8") as f:
        f.write("$ %s\n%s\nexit=%d\n" % (" ".join(argv), out, p.returncode))
    keys = ("PASS", "FAIL", "WARN", "栏高", "文字分段", "胶囊", "result=",
            "not registered", "SystemExit", "Traceback", "判定")
    for ln in out.splitlines():
        if any(k in ln for k in keys):
            say("    | " + ln.strip()[:170])
    say("STEP %s exit=%d（日志 step_%s.log）" % (name, p.returncode, name))
    return p.returncode


def wait_idle(minutes, interval):
    """等「已解锁且桌面空闲」连续两次；期间只在内存里判定，不做任何注入。"""
    deadline = time.time() + minutes * 60
    streak = 0
    n = 0
    while time.time() < deadline:
        n += 1
        lk, why = wu.locked()
        if lk is False:
            busy = wu.third_party_visible()
            if busy:
                streak = 0
                say("PROBE#%d 已解锁但桌面在忙（%s）——不接管主人正在用的页面" % (
                    n, ", ".join(b["name"] for b in busy[:3])))
            else:
                streak += 1
                say("PROBE#%d 已解锁且桌面空闲（连续 %d 次）" % (n, streak))
                if streak >= 2:
                    return True
        else:
            if n == 1 or streak != 0:
                say("PROBE#%d 仍锁屏（%s）——按铁律不点主人屏幕，继续等" % (n, why))
            streak = 0
        time.sleep(interval)
    say("TIMEOUT 等了 %d 分钟没等到「解锁且空闲」，本轮不装机不注入" % minutes)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=480.0)
    ap.add_argument("--interval", type=float, default=90.0)
    ap.add_argument("--no-install", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    os.makedirs(EVID, exist_ok=True)
    script = os.path.join("scripts", "h202_h204_device_accept.py")

    say("===== 一轮开始 =====")
    say("待装 unsigned/signed：unsigned 28349351 B → signed %d B（HEAD 由 9b02ad6 重建，"
        "hvigor 报 UP-TO-DATE ⇒ 与 16:46 那次同源）" % (os.path.getsize(SIGNED)
                                                    if os.path.exists(SIGNED) else -1))
    say("装机前身份：%s" % (" / ".join(installed_build()) or "读不到"))
    if not a.force:
        if not wait_idle(a.minutes, a.interval):
            return 3
    else:
        say("FORCE 跳过守候（调用方已自行确认手机空闲）")

    # ---- ① 旧包基线：这两条必须**红**，否则量具是哑的，新包绿也不算证据 ----
    base = {}
    for key, cmd in (("bs", "bs"), ("paste", "paste")):
        if not wu.guard("baseline-%s" % key):
            say("ABORT 基线 %s 前双闸没过（锁屏或前台不是本应用）" % key)
            return 4
        base[key] = run_step("old_" + key, [os.path.join(".", script), cmd])
    say("旧包基线 exit：bs=%d paste=%d（预期都非 0＝判据在缺陷版上变红）" % (
        base["bs"], base["paste"]))
    if base["bs"] == 0 and base["paste"] == 0:
        say("WARN 两条基线在旧包上全绿 ⇒ 量具可能是哑的；新包结果只能算「没变坏」，"
            "不能算「已修好」。继续，但报告里按这条口径写。")

    if a.no_install:
        say("--no-install：基线跑完就收，不装机")
        wu.acc.sh("shell", "power-shell suspend")
        return 0

    # ---- ② 装机（一次；显式目标，绝不让脚本猜设备）----
    say("装机：%s → %s" % (os.path.basename(SIGNED), TARGET))
    r = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File",
                        os.path.join(ROOT, "scripts", "install.ps1"),
                        "-Hap", SIGNED, "-Target", TARGET],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    with open(os.path.join(EVID, "step_install.log"), "w", encoding="utf-8") as f:
        f.write(out + "\n")
    for ln in out.splitlines()[-8:]:
        say("    install| " + ln.strip()[:170])
    say("装机 exit=%d" % r.returncode)
    if r.returncode != 0:
        say("ABORT 装机没成功就别跑判据（会拿旧包的结果当新包）")
        return 5
    say("装机后身份：%s" % (" / ".join(installed_build()) or "读不到"))

    # ---- ③ 新包全量验收（①~⑧ 八组）----
    time.sleep(3.0)                      # 让系统把输入法面板切到新包
    if not wu.guard("run-new-build"):
        say("ABORT 验收前双闸没过")
        return 4
    rc = run_step("new_run", [os.path.join(".", script), "run"])
    say("新包全量验收 exit=%d（0＝八组全过）" % rc)

    wu.acc.sh("shell", "power-shell suspend")
    say("===== 一轮结束：屏幕交还（只做 suspend）；报告 %s =====" % REPORT)
    return rc


if __name__ == "__main__":
    sys.exit(main())
