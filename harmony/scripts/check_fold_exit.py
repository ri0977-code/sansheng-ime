# -*- coding: utf-8 -*-
"""验证 h106_precheck 的「折叠出口在候选栏右上角三角」判据有已知坏样本保护。

为什么单独写：14:4x 我把 H-106 的旧判据（底栏每栏都要有收起键）换成新判据
（三角智能双功能），但 selfcheck() 只覆盖「交付行」那一组，不覆盖结构判据。
没有已知坏样本保护的判据＝没人知道它坏没坏。

本脚本造两份临时源码：
  好样本 = 真源码（含 candidates.length 条件分支 + hideKeyboard）
  坏样本 = 好源码删掉条件分支（模拟「又把收起键挪回底栏」的旧病复发）
然后跑 h106_precheck --kb <文件>，断言：
  好样本 ⇒ 新判据 OK
  坏样本 ⇒ 新判据 FAIL（点名）
任一不符 exit 1。
"""
import io
import os
import re
import subprocess
import sys

ROOT = "F:/qoderwork/sansheng-ime-harmony"
SRC = "entry/src/main/ets/pages/KeyboardIndex.ets"
PY = sys.executable


def run(kb):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.Popen([PY, "scripts/h106_precheck.py", "--kb", kb],
                         cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    out = p.communicate()[0].decode("utf-8", "replace")
    return out


def verdict(out):
    """返回新判据那一行的结论（True=OK / False=FAIL / None=没这条）。"""
    for ln in out.splitlines():
        if "折叠出口在候选栏右上角三角" in ln:
            return ln.strip().startswith("[OK")
    return None


def main():
    src = io.open(os.path.join(ROOT, SRC), encoding="utf-8").read()
    tmp = os.path.join(ROOT, "entry/src/main/ets/pages/_foldcheck_tmp.ets")
    io.open(tmp, "w", encoding="utf-8", newline="\n").write(src)

    out_good = run("entry/src/main/ets/pages/_foldcheck_tmp.ets")
    v_good = verdict(out_good)

    # 坏样本：把条件分支整段换掉 ⇒ 只剩一个普通 onClick（模拟旧病复发）
    bad = src.replace(
        "if (this.candidates.length > 0 || this.preedit.length > 0) {",
        "if (false) {", 1)
    assert bad != src, "坏样本构造失败：没找到条件分支"
    io.open(tmp, "w", encoding="utf-8", newline="\n").write(bad)
    out_bad = run("entry/src/main/ets/pages/_foldcheck_tmp.ets")
    v_bad = verdict(out_bad)

    os.remove(tmp)
    print("好样本（真源码）        ⇒ %s" % ("OK" if v_good else ("FAIL" if v_good is False else "没这条判据")))
    print("坏样本（删条件分支）    ⇒ %s" % ("OK" if v_bad else ("FAIL" if v_bad is False else "没这条判据")))
    ok = (v_good is True) and (v_bad is False)
    print("结论：%s" % ("判据有已知坏样本保护" if ok else "判据坏了 —— 好样本必须 OK、坏样本必须 FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
