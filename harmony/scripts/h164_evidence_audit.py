#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-164 取证包体检（Qoder，2026-10-25 09:29）

为什么写：九条判据的「结果」列是我自己填的。填之前先让机器数一遍——
哪张图没有、哪张是空帧、哪次跑被守卫中止、日志检查器到底是红是绿、
设备上装的是不是我们以为的那一版。人眼挑图会漏，脚本不会。

只看本地文件，不碰设备、不改应用。

用法：
    python scripts/h164_evidence_audit.py                     # 默认体检 docs/evidence/2026-10-25/h164-candidate-scroll
    python scripts/h164_evidence_audit.py <目录>
    python scripts/h164_evidence_audit.py --selftest          # 合成样本（好/缺图/空帧/红检查/换载体/被中止）

退出码：0 必需项齐全且无阻断；1 有阻断（证据不成立，别填「通过」）。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(os.path.dirname(HERE), "docs", "evidence", "2026-10-25", "h164-candidate-scroll")

SHOTS = ["a0", "a1"] + ["b%d" % i for i in range(1, 18)] + ["c1", "c2", "d1", "e1", "e2", "f1", "f2", "f3", "f4"]
MIN_JPEG = 10240          # 正常键盘截图 200 KB 上下；<10 KB 基本是空帧/坏图
EXPECT_CARRIER = "1792859799644"   # 2026-10-25 00:36:39，源码 0b199eb


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def audit(d, expect_carrier=EXPECT_CARRIER):
    fatal, warn, notes = [], [], []

    # 1) 16 张截图在不在、是不是空帧
    missing, tiny = [], []
    for name in SHOTS:
        p = os.path.join(d, "%s.jpeg" % name)
        if not os.path.exists(p):
            missing.append(name)
        elif os.path.getsize(p) < MIN_JPEG:
            tiny.append("%s(%d B)" % (name, os.path.getsize(p)))
    if missing:
        fatal.append("截图缺失 %d 张：%s" % (len(missing), ", ".join(missing)))
    if tiny:
        fatal.append("截图疑似空帧（<%d B）：%s" % (MIN_JPEG, ", ".join(tiny)))
    if missing:
        notes.append("缺图时对应判据一律「未跑」，不许拿别的图顶")

    # 2) b1–b17 若逐字节相同 ⇒ 注入没让 List 动，不能当「跟手」证据
    bp = [os.path.join(d, "b%d.jpeg" % i) for i in range(1, 18)]
    have_b = [p for p in bp if os.path.exists(p)]
    if len(have_b) >= 3:
        uniq = {_md5(p) for p in have_b}
        if len(uniq) == 1:
            warn.append("b1–b17 逐字节相同（%d 张）——滚动没生效，判据① 不能填通过" % len(have_b))
        elif len(uniq) < len(have_b) // 2:
            warn.append("b1–b17 只有 %d 种画面（%d 张）——多数帧没变，逐张复核" % (len(uniq), len(have_b)))
        else:
            notes.append("b1–b17 共 %d 种画面（%d 张）" % (len(uniq), len(have_b)))

    # 3) 侧车
    for fn in ("h164_lay.json", "h164_cands.json"):
        p = os.path.join(d, fn)
        if not os.path.exists(p):
            fatal.append("缺侧车 %s（判据④ 的坐标来源）" % fn)
            continue
        try:
            with open(p, encoding="utf-8") as f:
                obj = json.load(f)
            if fn == "h164_cands.json":
                n = len(obj or [])
                if n < 2:
                    fatal.append("%s 只有 %d 条候选（打字没进试打框？）" % (fn, n))
                else:
                    o0 = obj[0] or {}
                    notes.append("候选侧车 %d 条（源 %s），第 1 条 %s" %
                                 (n, o0.get("src", "?"), o0.get("text") or "图测位置"))
        except Exception as e:
            fatal.append("%s 解析失败：%s" % (fn, e))

    # 4) hilog 与检查器结论
    hl = os.path.join(d, "h164-hilog.txt")
    lc = os.path.join(d, "h164-log-check.txt")
    if not os.path.exists(hl) or os.path.getsize(hl) == 0:
        fatal.append("缺 h164-hilog.txt（判据③⑥⑦ 的原始日志）")
    else:
        with open(hl, encoding="utf-8", errors="replace") as f:
            text = f.read()
        if "H-164 scroll" not in text:
            fatal.append("hilog 里没有 H-164 scroll 行——判据①③⑦ 未覆盖")
        if "ResetPaging" in text:
            warn.append("hilog 出现 ResetPaging——判据⑥ 要逐行看是不是在滚动途中触发")
    if not os.path.exists(lc):
        fatal.append("缺 h164-log-check.txt（判据③⑦ 的检查器结论）")
    else:
        with open(lc, encoding="utf-8", errors="replace") as f:
            out = f.read()
        if "违规" in out and "无违规" not in out:
            m = re.search(r"违规 (\d+) 条", out)
            fatal.append("日志检查器报违规 %s 条（判据③⑦ 不通过）" % (m.group(1) if m else "?"))
        elif "无违规" in out:
            notes.append("日志检查器：无违规")
        else:
            fatal.append("检查器输出里既没有「无违规」也没有「违规」——这份结论不可用")

    # 5) 时间线：载体、守卫中止、前置失败
    wl = os.path.join(d, "wait-unlock.log")
    if not os.path.exists(wl):
        fatal.append("缺 wait-unlock.log（时间线与 CARRIER 依据）")
    else:
        with open(wl, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        carrier = [ln for ln in lines if "CARRIER" in ln]
        if not carrier:
            fatal.append("日志里没有 CARRIER 行——无法证明跑的是哪一版装机包")
        elif expect_carrier and expect_carrier not in carrier[-1]:
            fatal.append("载体不是 0b199eb（期望 updateTime=%s）：%s" % (expect_carrier, carrier[-1].strip()))
        else:
            notes.append("载体对得上 0b199eb")
        last_start = max([i for i, ln in enumerate(lines) if "RUN 开始" in ln] or [-1])
        tail = lines[last_start + 1:] if last_start >= 0 else lines
        if any("GUARD-ABORT" in ln for ln in tail):
            fatal.append("最后一次运行被守卫中止（中途锁屏/离开本应用）——证据不完整")
        if any("FOCUS-ABORT" in ln for ln in tail):
            fatal.append("最后一次运行被前台闸中止（前台不是本应用）——不把别人的界面当证据")
        for kw, msg in (("NO-CAND", "前置失败 rc=5（打字没进框）"),
                        ("滚动可能没生效", "滚动可能没生效"),
                        ("WARN 滑动期间试打框文字变了", "注入被当成长按/误触，已上屏"),
                        ("RUN 未完成", "最后一次运行没跑完")):
            if any(kw in ln for ln in tail):
                warn.append(msg)
        if not any("RUN 完成" in ln for ln in tail):
            fatal.append("日志里没有「RUN 完成」——这轮没走完 12 步")

    return fatal, warn, notes


def report(d, expect_carrier=EXPECT_CARRIER):
    fatal, warn, notes = audit(d, expect_carrier)
    print("=== H-164 取证包体检：%s ===" % d)
    print("截图 %d 张应有：%s" % (len(SHOTS), ", ".join(SHOTS)))
    if notes:
        print("\n事实：")
        for n in notes:
            print("  " + n)
    if warn:
        print("\n提示（不阻断，但填「通过」前要人工看）：")
        for w in warn:
            print("  " + w)
    if fatal:
        print("\n阻断 %d 条（证据不成立，相关判据只能填「未跑/不通过」）：" % len(fatal))
        for f_ in fatal:
            print("  " + f_)
        return 1
    print("\n体检通过：%d 张图、侧车、日志、检查器结论、载体与完成标记都齐。" % len(SHOTS))
    return 0


def _write(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if isinstance(data, bytes):
        with open(p, "wb") as f:
            f.write(data)
    else:
        # 显式 UTF-8：Windows 默认 GBK 会把中文样本写成读不回来的字节（自测第一版就栽在这）
        with open(p, "w", encoding="utf-8") as f:
            f.write(data)


def _mk_good(d):
    """造一套「全绿」样本：25 张 20 KB、侧车 5 条、日志含 CARRIER/scroll/RUN 完成、检查器无违规。"""
    for i, name in enumerate(SHOTS):
        _write(os.path.join(d, "%s.jpeg" % name), os.urandom(20000) + bytes([i]))
    _write(os.path.join(d, "h164_lay.json"), json.dumps({"attributes": {"type": "root"}, "children": []}))
    _write(os.path.join(d, "h164_cands.json"),
           json.dumps([{"text": "你%d" % i, "x": 100 + i * 80, "y": 1900} for i in range(5)],
                      ensure_ascii=False))
    _write(os.path.join(d, "h164-hilog.txt"),
           "SSKeyboard H-164 scroll first=0 last=7 n=8 absFirst=0 absLast=7\n")
    _write(os.path.join(d, "h164-log-check.txt"), "=== H-164 日志判据 ===\n无违规：⑦ 条数关系、③ 续页触发与次数、② 回片都成立。\n")
    _write(os.path.join(d, "wait-unlock.log"),
           '2026-10-25 09:30:00 CARRIER "updateTime": %s,\n'
           "2026-10-25 09:30:01 RUN 开始（DRY=False）\n"
           "2026-10-25 09:31:10 RUN 完成\n" % EXPECT_CARRIER)


def selftest():
    cases = []

    def add(name, mutate, want_rc, want_txt):
        cases.append((name, mutate, want_rc, want_txt))

    add("GOOD 全绿", lambda d: None, 0, ["体检通过"])
    add("缺 d1", lambda d: os.remove(os.path.join(d, "d1.jpeg")), 1, ["截图缺失 1 张：d1"])
    add("空帧 d1", lambda d: _write(os.path.join(d, "d1.jpeg"), b"x" * 100), 1, ["疑似空帧"])
    add("b1–b17 同一帧", lambda d: [ _write(os.path.join(d, "b%d.jpeg" % i), b"z" * 20000) for i in range(1, 18) ],
        0, ["b1–b17 逐字节相同", "判据① 不能填通过"])
    add("检查器报违规", lambda d: _write(os.path.join(d, "h164-log-check.txt"), "违规 2 条：\n  L3 ...\n"),
        1, ["日志检查器报违规 2 条"])
    add("载体不符", lambda d: _write(os.path.join(d, "wait-unlock.log"),
                                    'CARRIER "updateTime": 111,\nRUN 开始（DRY=False）\nRUN 完成\n'),
        1, ["载体不是 0b199eb"])
    add("被守卫中止", lambda d: _write(os.path.join(d, "wait-unlock.log"),
                                     'CARRIER "updateTime": %s,\nRUN 开始（DRY=False）\nGUARD-ABORT 锁屏\n' % EXPECT_CARRIER),
        1, ["最后一次运行被守卫中止", "没有「RUN 完成」"])
    add("被前台闸中止", lambda d: _write(os.path.join(d, "wait-unlock.log"),
                                     'CARRIER "updateTime": %s,\nRUN 开始（DRY=False）\n'
                                     'FOCUS-ABORT 前台不是本应用，停止（不 dump、不点、不打字、不截图）\n' % EXPECT_CARRIER),
        1, ["最后一次运行被前台闸中止", "没有「RUN 完成」"])
    add("候选侧车不足", lambda d: _write(os.path.join(d, "h164_cands.json"), json.dumps([{"text": "x"}])),
        1, ["只有 1 条候选"])

    bad = 0
    for name, mutate, want_rc, want_txt in cases:
        d = tempfile.mkdtemp(prefix="h164audit_")
        try:
            _mk_good(d)
            mutate(d)
            import io
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = report(d)
            out = buf.getvalue()
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)
        miss = [t for t in want_txt if t not in out]
        if rc != want_rc or miss:
            bad += 1
            print("FAIL %s：rc=%d（期望 %d）%s" % (name, rc, want_rc,
                                                 ("；缺：%s" % "／".join(miss)) if miss else ""))
        else:
            print("ok   %s → rc=%d" % (name, rc))
    print("\nSELFTEST %s：%d 例，%d 失败" % ("OK" if bad == 0 else "FAIL", len(cases), bad))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", nargs="?", default=DEFAULT_DIR)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--expect-carrier", default=EXPECT_CARRIER)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    return report(a.dir, a.expect_carrier)


if __name__ == "__main__":
    sys.exit(main())
