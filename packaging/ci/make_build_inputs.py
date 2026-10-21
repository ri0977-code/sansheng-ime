# -*- coding: utf-8 -*-
"""组装 CI 构建输入包 build-inputs（GitHub Actions 复现安装包用的那个 7z）。

为什么要这个脚本：CI 的 `config/` **不来自仓库**（`packaging/release` 整棵是 gitignore 的），
它从公开 Release 里下载 `sansheng-build-inputs-v<版本>.7z`。抬了版本号却没重发这个包，
CI 就会出一个「版本号新、配置还是老版本」的假包 —— `build_installer.py` 第 1b 号硬门会拦下，
但拦下不等于发好。所以顺序永远是：出包 → 上传 → 改工作流三行 → 跑 CI → 发 Release。

包结构照 v1.9.10 那只（已解在 _probe/build-inputs/v1910/ 当参照）逐条对齐：

    sansheng-build-inputs-v<版本>/
        INPUTS-INFO.txt        说明（人读的）
        MANIFEST.sha256        每行 `<sha256>␣␣<相对路径>`（两个空格），覆盖包内每个文件
        config/                = packaging/release/config 原样（129 → 本版 119 个文件；
                                 个人数据由 build_installer.py 的 STUBS 步覆盖成空模板）
        engine-overlay/        官方 weasel-0.17.4 x64 里被三生换掉的 4 个文件
        reg/                   4 个 .reg

用法：
    python packaging/ci/make_build_inputs.py --version 1.10.1
    python packaging/ci/make_build_inputs.py --version 1.10.1 --dry   # 只列要装什么
产物默认落在 `packaging/dist/`，同名目录留在 `_probe/build-inputs/` 供核对。
"""
import argparse
import hashlib
import io
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGING = os.path.dirname(HERE)
REPO = os.path.dirname(PACKAGING)
RELEASE = os.path.join(PACKAGING, "release")
DIST = os.path.join(PACKAGING, "dist")

# 官方引擎里被我们替换的那 4 个（托盘图标、IME 图标、翻页设置）
OVERLAY = ["WeaselServer.exe", "weasel.ime", "weaselx64.ime",
           os.path.join("data", "default.yaml")]
ENGINE_DIR = "weasel-0.17.4"
# release 根目录下的注册表片段，build_installer.py 要求正好 4 个
REG = ["weasel-clsid.reg", "weasel-clsid32.reg", "weasel-tip.reg", "weasel-tip32.reg"]

INFO_TMPL = u"""三生输入法 v%(ver)s · CI 构建输入包
=====================================

用途
----
本包只供 GitHub Actions 复现 v%(ver)s 安装包使用，不是给普通用户下载的。
普通用户请到 https://github.com/ri0977-code/sansheng-ime/releases/tag/v%(ver)s
下载 sansheng-ime-v%(ver)s-setup.exe。

内容
----
config/            v%(ver)s 安装到 Rime 用户目录的完整配置（%(nconfig)d 个文件）
engine-overlay/    官方 Weasel 0.17.4 x64 引擎中被三生替换的 4 个文件：
                     WeaselServer.exe   托盘图标
                     weasel.ime         32 位输入法图标
                     weaselx64.ime      64 位输入法图标
                     data/default.yaml  去掉逗号/句号翻页
reg/               4 个注册表片段（IconFile 由安装器运行时改写）

来源
----
config/ 取自打包当时实际编译进 v%(ver)s 的 packaging/release/config。
engine-overlay/ 取自同一棵 release/%(eng)s；其余引擎文件与官方
weasel-0.17.4.0-installer.exe 的 x64 版本逐字节一致。
官方安装包 SHA256: cf509534a8f5f8af9c98ed7cbb8f135439f145a8cbe7e50ede42bb5b5ab45c29

本版相对 v1.10 的配置差异（config/ 里）
------------------------------------
新增 2 个：lua/rawEcho_translator.lua（含数字缩写出词）、lua/abbr_num.txt（95 条数据）。
扩容 1 个：lua/abbr_en.txt 422 → 603 条。
改动 4 个：wubi_pinyin.custom.yaml（recognizer 补 punct / rawNum 两条模式并挂 rawEcho）、
  rime.lua（接线）、abbrGloss_Filter.lua（修「0 候选时把普通候选也吞掉」）、
  symbols.custom.yaml（清掉 162 个 None 占位串 + 1 条手误空项）。
少了 14 个：wnwb_* 万能五笔导入层（v1.10 起下架）—— v1.9.10 那只包是 129 个文件就是这个原因。

校验
----
MANIFEST.sha256 列出包内每个文件的 SHA256，构建前由 build_installer.py 逐个核对。
"""


def sha256(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path, root):
    return os.path.relpath(path, root).replace(os.sep, "/")


def copytree(src, dst):
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="如 1.10.1（不带 v）")
    ap.add_argument("--release", default=RELEASE, help="出包树，默认 packaging/release")
    ap.add_argument("--out", default=DIST, help="7z 落点，默认 packaging/dist")
    ap.add_argument("--work", default=os.path.join(REPO, "_probe", "build-inputs"),
                    help="组装目录的父目录，留作核对")
    ap.add_argument("--sevenzip", default=None, help="7z/7za 可执行文件，默认自动找")
    ap.add_argument("--dry", action="store_true", help="只打印将要装进去的文件，不写任何东西")
    a = ap.parse_args()

    name = "sansheng-build-inputs-v%s" % a.version
    stage = os.path.join(a.work, "stage-v%s" % a.version)
    bundle = os.path.join(stage, name)

    cfg_src = os.path.join(a.release, "config")
    eng_src = os.path.join(a.release, ENGINE_DIR)
    missing = []
    if not os.path.isdir(cfg_src):
        missing.append(cfg_src)
    for f in OVERLAY:
        if not os.path.isfile(os.path.join(eng_src, f)):
            missing.append(os.path.join(eng_src, f))
    for f in REG:
        if not os.path.isfile(os.path.join(a.release, f)):
            missing.append(os.path.join(a.release, f))
    if missing:
        raise SystemExit("出包树缺文件，先跑 packaging/prepare_release.py：\n  " +
                         "\n  ".join(missing))

    ncfg = sum(1 for _r, _d, fs in os.walk(cfg_src) for f in fs)
    plan = ["%s/%s" % (name, rel(os.path.join(r, f), cfg_src))
            for r, _d, fs in os.walk(cfg_src) for f in sorted(fs)]
    plan += ["%s/engine-overlay/%s" % (name, f.replace(os.sep, "/")) for f in OVERLAY]
    plan += ["%s/reg/%s" % (name, f) for f in REG]
    plan += ["%s/INPUTS-INFO.txt" % name, "%s/MANIFEST.sha256" % name]
    print("将打包 %d 个文件（config %d + overlay 4 + reg 4 + 说明 1 + MANIFEST 1）"
          % (len(plan), ncfg))
    if a.dry:
        for p in plan[:12]:
            print("  " + p)
        print("  …（完整清单去掉 --dry 后落盘）")
        return

    if os.path.isdir(stage):
        shutil.rmtree(stage)
    copytree(cfg_src, os.path.join(bundle, "config"))
    for f in OVERLAY:
        dst = os.path.join(bundle, "engine-overlay", f)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(eng_src, f), dst)
    os.makedirs(os.path.join(bundle, "reg"), exist_ok=True)
    for f in REG:
        shutil.copy2(os.path.join(a.release, f), os.path.join(bundle, "reg", f))
    with io.open(os.path.join(bundle, "INPUTS-INFO.txt"), "w", encoding="utf-8",
                 newline="\r\n") as f:
        f.write(INFO_TMPL % {"ver": a.version, "nconfig": ncfg, "eng": ENGINE_DIR})

    files = []
    for r, _d, fs in os.walk(bundle):
        for f in fs:
            p = os.path.join(r, f)
            if rel(p, bundle) != "MANIFEST.sha256":
                files.append(p)
    files.sort(key=lambda p: rel(p, bundle))
    with io.open(os.path.join(bundle, "MANIFEST.sha256"), "w", encoding="utf-8",
                 newline="\n") as mf:
        for p in files:
            mf.write("%s  %s\n" % (sha256(p), rel(p, bundle)))
    print("MANIFEST 写好：%d 行" % len(files))

    seven = a.sevenzip
    if not seven:
        for cand in (r"C:\Program Files\7-Zip\7z.exe",
                     r"C:\Program Files (x86)\7-Zip\7z.exe",
                     shutil.which("7z") or "", shutil.which("7za") or "",
                     os.path.join(PACKAGING, "extra", "7za.exe")):
            if cand and os.path.isfile(cand):
                seven = cand
                break
    if not seven:
        raise SystemExit("找不到 7z/7za，用 --sevenzip 指定")
    os.makedirs(a.out, exist_ok=True)
    arc = os.path.join(a.out, name + ".7z")
    if os.path.isfile(arc):
        os.remove(arc)
    p = subprocess.run([seven, "a", "-t7z", "-mx=5", "-bso0", "-bsp0", arc, name],
                       cwd=stage, capture_output=True)
    if p.returncode != 0:
        raise SystemExit("7z 打包失败：\n" + p.stdout.decode("utf-8", "replace") +
                         p.stderr.decode("utf-8", "replace"))
    h = sha256(arc)
    print("")
    print("产物：%s" % arc)
    print("大小：%d B（%.2f MB）" % (os.path.getsize(arc), os.path.getsize(arc) / 1048576.0))
    print("SHA256：%s" % h)
    print("")
    print("把这三行填进 .github/workflows/build-installer.yml 的 env：")
    print('  INPUTS_URL: https://github.com/ri0977-code/sansheng-ime/releases/'
          'download/build-inputs-v%(v)s/sansheng-build-inputs-v%(v)s.7z' % {"v": a.version})
    print("  INPUTS_SHA256: %s" % h)
    print('  EXPECTED_VERSION: "%s"' % a.version)
    print("")
    print("注意：tag 用 build-inputs-v%s（不是 v%s），并且这个 Release 别设成 latest。"
          % (a.version, a.version))


if __name__ == "__main__":
    main()
