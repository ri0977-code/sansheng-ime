#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""未绑定名字闸门（Qoder，2026-10-26 11:5x）。

为什么写：真机验收脚本里出现过两次「跑起来才炸」的同类错——
  ① `h180_device_accept.py` 的 `measure_toolbar_icons()` 用了只有另一个脚本才定义的 `BAR_H`
     ⇒ NameError，意味着那一步**从来没真正在设备上跑过**，闸门却一直是绿的；
  ② 同文件 `main()` 里 `args = ap.parse_args()` 一度被编辑吞掉 ⇒ 运行时 NameError。
两者都不是逻辑错，是「名字没绑上」。真机很贵（每次装机要主人输密码），
这类错必须在离线阶段就红。机器上没装 pyflakes/ruff（不联网装包），
所以这里自己做一个够用的：**只查 Name 载入是否在某处被绑过**，不猜类型、不查风格。

判据（宁可窄，不可假红）：
  · 模块级：import（含 as）、def/class、赋值、for/with/except 目标、global 声明；
  · 函数级：参数、局部赋值、for/with/except 目标、嵌套 def/class、lambda 参数、推导式变量、海象；
  · 内建名白名单 + 模块 dunder（`__file__`/`__name__`…）；
  · 出现 `from x import *` 的文件直接 SKIP（名字集合不可知，报了就是假红）。

用法：
    python scripts/check_py_undefined.py scripts/*.py    # 也可给目录
    python scripts/check_py_undefined.py --selftest      # 1 好样本必须静默 + 2 坏样本必须各自变红
退出码：0 全绑上 / 1 有未绑定名字 / 2 参数错
"""
import argparse
import ast
import builtins
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

EXTRA = {"__file__", "__name__", "__doc__", "__package__", "__spec__",
         "__loader__", "__builtins__", "__debug__", "WindowsError"}
BUILTIN = set(dir(builtins)) | EXTRA


def _targets(node, out):
    """把赋值目标里的所有名字收进 out（支持 a, (b, c), a[0], a.x, *rest）。"""
    if isinstance(node, ast.Name):
        out.add(node.id)
    elif isinstance(node, (ast.Tuple, ast.List)):
        for e in node.elts:
            _targets(e, out)
    elif isinstance(node, ast.Starred):
        _targets(node.value, out)
    # Subscript/Attribute 的目标不是绑名字，忽略


def _imports(node, out):
    for a in node.names:
        if a.name == "*":
            return True
        out.add(a.asname or a.name.split(".")[0])
    return False


def module_scope(tree):
    """模块级绑定 + 是否存在 star import。"""
    names, star = set(), False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            star = _imports(node, names) or star
        elif isinstance(node, ast.ImportFrom):
            star = _imports(node, names) or star
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            tgts = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in tgts:
                _targets(t, names)
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            _targets(node.target, names)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for it in node.items:
                if it.optional_vars is not None:
                    _targets(it.optional_vars, names)
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                names.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            names.update(node.names)
        elif isinstance(node, ast.NamedExpr):
            _targets(node.target, names)
    return names, star


def check_file(path):
    """返回 [(行号, 名字, 作用域描述)]。"""
    src = open(path, encoding="utf-8", errors="replace").read()
    try:
        tree = ast.parse(src, filename=path)
    except SyntaxError as e:
        return [(e.lineno or 0, "<语法错>", str(e.msg))]
    mod_names, star = module_scope(tree)
    if star:
        return []

    problems = []

    def scope_of(fn):
        loc = set()
        a = fn.args
        for arg in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs):
            loc.add(arg.arg)
        if a.vararg:
            loc.add(a.vararg.arg)
        if a.kwarg:
            loc.add(a.kwarg.arg)
        # 函数体内的所有绑定（含嵌套作用域里的同名也算绑过——宁可漏报不假红）
        for n in ast.walk(fn):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                _imports(n, loc)
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                loc.add(n.name)
                # 嵌套函数的**参数**也要算绑过：`def walk(n)` 里的 n 不是外层的错，
                # 只查外层作用域时它看起来「没绑」——第一版就假红了 9 个文件。
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    na = n.args
                    for arg in list(na.posonlyargs) + list(na.args) + list(na.kwonlyargs):
                        loc.add(arg.arg)
                    if na.vararg:
                        loc.add(na.vararg.arg)
                    if na.kwarg:
                        loc.add(na.kwarg.arg)
            elif isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                tgts = n.targets if isinstance(n, ast.Assign) else [n.target]
                for t in tgts:
                    _targets(t, loc)
            elif isinstance(n, (ast.For, ast.AsyncFor)):
                _targets(n.target, loc)
            elif isinstance(n, (ast.With, ast.AsyncWith)):
                for it in n.items:
                    if it.optional_vars is not None:
                        _targets(it.optional_vars, loc)
            elif isinstance(n, ast.ExceptHandler):
                if n.name:
                    loc.add(n.name)
            elif isinstance(n, (ast.Global, ast.Nonlocal)):
                loc.update(n.names)
            elif isinstance(n, ast.NamedExpr):
                _targets(n.target, loc)
            elif isinstance(n, ast.Lambda):
                la = n.args
                for arg in list(la.posonlyargs) + list(la.args) + list(la.kwonlyargs):
                    loc.add(arg.arg)
                if la.vararg:
                    loc.add(la.vararg.arg)
                if la.kwarg:
                    loc.add(la.kwarg.arg)
        loaders = [n for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)]
        for n in loaders:
            if n.id not in loc and n.id not in mod_names and n.id not in BUILTIN:
                problems.append((n.lineno, n.id, "函数 %s()" % fn.name))
        return problems

    # 模块级 Load（函数外）
    fn_nodes = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            fn_nodes.add(id(n))
    inner_loads = set()
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            problems.extend(scope_of(fn))
            for x in ast.walk(fn):
                inner_loads.add(id(x))
    for n in ast.walk(tree):
        if id(n) in inner_loads:
            continue
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            if n.id not in mod_names and n.id not in BUILTIN:
                problems.append((n.lineno, n.id, "模块级"))
    return sorted(set(problems))


def report(paths):
    bad = 0
    for p in paths:
        probs = check_file(p)
        rel = os.path.basename(p)
        try:
            rel = os.path.relpath(p).replace("\\", "/")
        except ValueError:          # 跨盘符（selftest 用 %TEMP%）时 relpath 会抛
            pass
        if not probs:
            print("  [绿] %s" % rel)
            continue
        bad += 1
        for ln, name, where in probs:
            print("  [红] %s:%d `%s` 在 %s 里没绑过" % (rel, ln, name, where))
    return bad


GOOD = '''
import os, sys as S
from ast import Name

LIMIT = 3
_pool = {}


def helper(x):
    y = x + LIMIT
    for i in range(LIMIT):
        y += i
    return [v * 2 for v in (y, 1) if v]


class K:
    def m(self, a):
        try:
            return a
        except Exception as e:
            return str(e)


def main():
    args = S.argv[1:]
    f = lambda q: q + 1
    with open(os.devnull) as fh:
        fh.read()
    print(helper(len(args)), f(1), _pool, K, Name)
'''

BAD_CONST = '''
BAR_H = 44


def a():
    return BAR_H


def b():
    return BAR_H + 1
''' .replace("BAR_H + 1", "UNDEFINED_CONST + 1")

BAD_ARGS = '''
from ast import parse


def main():
    ap = parse
    step = args.step      # args 从没绑过
    return step
'''


def selftest():
    import tempfile
    fails = 0
    tmp = tempfile.mkdtemp(prefix="pyundef_")

    def write(name, text):
        p = os.path.join(tmp, name)
        open(p, "w", encoding="utf-8").write(text)
        return p

    good = write("good.py", GOOD)
    if report([good]):
        print("SELFTEST FAIL: 好样本被误报（判据太紧，会逼人忽略它）")
        fails += 1
    else:
        print("SELFTEST OK: 好样本全绑上")

    cases = [("未定义常量", BAD_CONST, "UNDEFINED_CONST"),
             ("漏了 args = parse_args()", BAD_ARGS, "args")]
    for name, text, token in cases:
        p = write("bad_%d.py" % len(name), text)
        probs = check_file(p)
        hit = [x for x in probs if x[1] == token]
        if hit:
            print("SELFTEST OK: 负控「%s」变红（`%s`:%d）" % (name, token, hit[0][0]))
        else:
            print("SELFTEST FAIL: 负控「%s」没红（找到 %s）= 闸门无效" % (name, probs or "无"))
            fails += 1
    return fails


def expand(args):
    out = []
    for a in args:
        if os.path.isdir(a):
            for f in sorted(os.listdir(a)):
                if f.endswith(".py"):
                    out.append(os.path.join(a, f))
        else:
            out.append(a)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return 1 if selftest() else 0
    paths = expand(args.paths or [os.path.dirname(os.path.abspath(__file__))])
    paths = [p for p in paths if os.path.isfile(p)]
    if not paths:
        print("FAIL: 没给到任何 .py")
        return 1
    bad = report(paths)
    print("\n%s：%d 个文件，%d 个有未绑定名字" %
          ("FAIL" if bad else "PASS", len(paths), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
