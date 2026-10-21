#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the 三生输入法 installer from public inputs (CI edition).

Inputs
------
1. The public build-inputs archive (config / engine overlay / .reg), published
   next to the release and verified by SHA256 in the workflow.
2. The official Weasel 0.17.4 installer from rime/weasel, also SHA256-pinned.
3. packaging/installer-src/ from this repository.

The script deliberately has no dependency on a developer machine: it does not
read the live Rime directory, and every path comes from --inputs/--work/--out.
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PACKAGING = Path(__file__).resolve().parents[1]
INSTALLER_SRC = PACKAGING / "installer-src"

PERSONAL = {
    "user.txt", "user.yaml", "installation.yaml", "custom_phrase.txt",
    "runlog.txt", "phraseext personal.txt",
}
ENGINE_SKIP = {
    "weasel.ime.orig", "uninstall.exe", "rime-install.bat",
    "rime-install-config.bat", "start_service.bat", "stop_service.bat",
}
SKIP_DIRS = {"sync", "__pycache__", "weasel.user", "wiki-keep", "$pluginsdir"}
SKIP_SUFFIX = (".bak", ".orig", ".sw-", ".test-bak", ".userdb", ".log", ".tmp")

REQUIRED_ENGINE = [
    "WeaselServer.exe", "WeaselDeployer.exe", "WeaselSetup.exe",
    "weasel.dll", "weaselx64.dll", "rime.dll", "weasel.ime", "weaselx64.ime",
    "WinSparkle.dll", "curl.exe", "7z.exe", "7z.dll",
    "data/default.yaml", "data/opencc/STCharacters.ocd2",
]
# official x64 payload sizes (used to prove 7z kept the x64 copy, not x86)
EXPECT_RAW = {"WeaselServer.exe": 2243072, "rime.dll": 3524096}

STUBS = {
    Path("lua") / "phraseExt personal.txt":
        "# 候选词扩展 · 个人数据（发布版为空模板）\r\n"
        "# 格式： 词<Tab>要追加的候选1<Tab>候选2 ...\r\n\r\n",
    Path("lua") / "phraseComment personal.txt":
        "# 候选词注释 · 个人数据（发布版为空模板）\r\n"
        "# 格式： 词<Tab>注释内容\r\n\r\n",
}

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_tool(env_name, candidates, names):
    v = os.environ.get(env_name)
    if v and Path(v).exists():
        return v
    for c in candidates:
        if c and Path(c).exists():
            return c
    for c in names:
        w = shutil.which(c)
        if w:
            return w
    return None


def find_7z():
    return find_tool("SEVENZIP", [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        "/usr/bin/7z",
        "/usr/local/bin/7z",
    ], ("7z", "7za"))


def find_makensis():
    return find_tool("MAKENSIS", [
        r"C:\Program Files (x86)\NSIS\makensis.exe",
        r"C:\Program Files\NSIS\makensis.exe",
        "/usr/bin/makensis",
        "/usr/local/bin/makensis",
    ], ("makensis",))


def verify_manifest(inputs):
    """Check every file of the build-inputs bundle against MANIFEST.sha256."""
    mf = inputs / "MANIFEST.sha256"
    if not mf.exists():
        raise SystemExit("缺失 %s（构建输入包不完整）" % mf)
    bad, n = [], 0
    for line in mf.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, rel = line.split("  ", 1)
        p = inputs / rel
        if not p.exists():
            bad.append("缺失 " + rel)
        elif sha256(p) != digest:
            bad.append("校验失败 " + rel)
        else:
            n += 1
    if bad:
        raise SystemExit("构建输入包校验失败:\n  " + "\n  ".join(bad[:10]))
    print("输入包校验通过：%d 个文件" % n)


def extract_official(sevenzip, installer, raw):
    if raw.exists():
        shutil.rmtree(raw)
    raw.mkdir(parents=True)
    # -aos keeps the first copy of a duplicated archive name; in the official
    # Weasel installer that is the x64 build (verified below).
    r = subprocess.run([sevenzip, "x", "-y", "-aos", "-o" + str(raw), str(installer)],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        raise SystemExit("解压官方 Weasel 安装包失败:\n" + r.stdout[-1000:] + r.stderr[-1000:])
    for fn, size in EXPECT_RAW.items():
        p = raw / fn
        if not p.exists():
            raise SystemExit("官方安装包里找不到 %s" % fn)
        if p.stat().st_size != size:
            raise SystemExit(
                "官方安装包解出来的 %s 是 %d 字节，预期 x64 为 %d 字节。"
                "7z 的 -aos 行为变了，拒绝继续打包。" % (fn, p.stat().st_size, size))


def copy_engine(raw, dst, overlay):
    if dst.exists():
        shutil.rmtree(dst)
    n = 0
    for src in raw.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(raw)
        parts = [p.lower() for p in rel.parts[:-1]]
        name = src.name.lower()
        if any(p in SKIP_DIRS for p in parts):
            continue
        if name in ENGINE_SKIP or name.startswith("weaselarm"):
            continue
        if name.endswith(SKIP_SUFFIX):
            continue
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
        n += 1
    for src in overlay.rglob("*"):
        if src.is_file():
            rel = src.relative_to(overlay)
            out = dst / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out)
    for rel in REQUIRED_ENGINE:
        if not (dst / rel).exists():
            raise SystemExit("引擎缺少必需文件: " + rel)
    print("引擎就绪：%d 个官方文件 + 覆盖层 %d 个" %
          (n, sum(1 for p in overlay.rglob("*") if p.is_file())))
    return dst


def copy_config(inputs, dst):
    src = inputs / "config"
    if not src.is_dir():
        raise SystemExit("构建输入包缺少 config/")
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    # Release-version stubs must be empty even if a future bundle contains
    # a developer's local file by accident.
    for rel, body in STUBS.items():
        p = dst / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8", newline="")
    # Custom_phrase.txt stays byte-identical to the release tree. It is already
    # the neutral template there, and the installer only writes it on a fresh
    # install (upgrades keep the user's own file).
    cp = dst / "Custom_phrase.txt"
    if not cp.exists() or cp.stat().st_size > 4096:
        raise SystemExit("config/Custom_phrase.txt 缺失或不像模板（>4KB）")
    print("配置就绪：%d 个文件" % sum(1 for p in dst.rglob("*") if p.is_file()))


def copy_installer_src(dst):
    n = 0
    for src in sorted(INSTALLER_SRC.iterdir()):
        if not src.is_file():
            continue
        out = dst / src.name
        if src.suffix.lower() in (".nsi", ".ps1"):
            body = src.read_bytes().decode("utf-8-sig").lstrip("\ufeff")
            body = body.replace("\r\n", "\n")
            out.write_bytes(body.encode("utf-8-sig"))
        else:
            shutil.copy2(src, out)
        n += 1
    print("安装器源码铺入：%d 个" % n)


def copy_reg(inputs, dst):
    reg_dir = inputs / "reg"
    files = sorted(reg_dir.glob("*.reg")) if reg_dir.is_dir() else []
    if len(files) != 4:
        raise SystemExit("构建输入包里的 .reg 不是 4 个（实际 %d）" % len(files))
    for p in files:
        shutil.copy2(p, dst / p.name)
    print("注册表片段：4 个")


def check_release(release):
    problems = []

    # 1) rime.lua wiring
    entry = release / "config" / "rime.lua"
    if not entry.exists():
        problems.append("缺 config/rime.lua：装上的机器会打不出字")
    else:
        body = entry.read_bytes().decode("utf-8-sig", "replace")
        defined = set(re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*require", body, re.M))
        active = set()
        for df in ("default.custom.yaml", "default.yaml"):
            dp = release / "config" / df
            if dp.exists():
                dtxt = dp.read_bytes().decode("utf-8-sig", "replace")
                active |= set(re.findall(r"schema:\s*\"?([A-Za-z0-9_]+)\"?", dtxt))
        used, miss = set(), []
        for sch in sorted(active):
            for suffix in (".schema.yaml", ".custom.yaml"):
                sp = release / "config" / (sch + suffix)
                if not sp.exists():
                    continue
                txt = sp.read_bytes().decode("utf-8-sig", "replace")
                for name in re.findall(
                        r"lua_(?:filter|translator|processor|segmentor)@([A-Za-z_][A-Za-z0-9_]*)", txt):
                    used.add(name)
                    if name not in defined:
                        miss.append("%s -> %s" % (sch + suffix, name))
        if not active:
            problems.append("读不到 schema_list，无法校验 lua 接线")
        elif miss:
            problems.append("schema 引用了 rime.lua 里没有的 lua 名字: " + ", ".join(sorted(set(miss))[:8]))
        else:
            print("校验通过 rime.lua：定义 %d 个入口，启用方案 %s 引用 %d 个全部命中"
                  % (len(defined), "/".join(sorted(active)) or "?", len(used)))

    # 1b) v1.10 功能门：构建输入包必须是含缩写滤镜的那一套配置。
    # CI 的配置来自公开 build-inputs 压缩包，不是仓库；如果输入包还停在 v1.9.10，
    # 装出来的「v1.10」里根本没有 abbrGloss_Filter.lua —— 版本号对、内容不对，比不发布更坏。
    for need in ("config/lua/abbrGloss_Filter.lua", "config/lua/abbr_en.txt"):
        if not (release / need).exists():
            problems.append("构建输入包缺 %s：输入包还是旧版配置，"
                            "必须先发布 build-inputs-v1.10 并更新工作流 INPUTS_URL/SHA256" % need)

    # 2) TIP format
    tip_bad = []
    for fn in ("install.nsi", "enable-tip.ps1", "remove-tip.ps1", "卸载三生输入法.ps1"):
        p = release / fn
        if not p.exists():
            continue
        body = p.read_bytes().decode("utf-8-sig", "replace")
        for m in re.finditer(r'-Tip\s+"([^"]*)"', body):
            if not m.group(1).startswith("0804:"):
                tip_bad.append("%s: -Tip %s" % (fn, m.group(1)))
        for m in re.finditer(r'\$TipStr\s*=\s*"([^"]*)"', body):
            if not m.group(1).startswith("0804:"):
                tip_bad.append("%s: TipStr %s" % (fn, m.group(1)))
    if tip_bad:
        problems.append("TIP 参数缺少语言 ID 后的冒号（会清空用户键盘列表）: " + "; ".join(tip_bad[:5]))
    else:
        print("校验通过 TIP 参数格式")

    # 3) version consistency
    nsi = release / "install.nsi"
    nsi_body = nsi.read_bytes().decode("utf-8-sig", "replace") if nsi.exists() else ""
    m_out = re.search(r'OutFile\s+"?([^"\r\n]+)"?', nsi_body)
    m_dv = re.search(r'WriteRegStr\s+HKLM\s+"\$\{UN_KEY\}"\s+"DisplayVersion"\s+"([^"]+)"', nsi_body)
    version = None
    if not m_out or not m_dv:
        problems.append("读不到 install.nsi 的 OutFile 或 DisplayVersion")
    else:
        m_ver = re.search(r'-v([0-9]+\.[0-9]+\.[0-9]+)-setup\.exe$', m_out.group(1).strip())
        if not m_ver:
            problems.append("OutFile 不含 -vX.Y.Z-setup.exe: " + m_out.group(1))
        elif m_ver.group(1) != m_dv.group(1):
            problems.append("版本号不一致：包名 %s / DisplayVersion %s"
                            % (m_ver.group(1), m_dv.group(1)))
        else:
            version = m_ver.group(1)
            print("校验通过 版本号 v%s（包名与 DisplayVersion 一致）" % version)

    # 4) personal / junk scan
    leak = []
    for p in release.rglob("*"):
        if not p.is_file():
            continue
        n = p.name.lower()
        if n in ("custom_phrase.txt", "phraseext personal.txt", "phrasecomment personal.txt"):
            continue
        if n in PERSONAL or n.endswith(SKIP_SUFFIX) or n in ENGINE_SKIP:
            leak.append(str(p.relative_to(release)))
    if leak:
        problems.append("仍有个人/杂物文件: " + ", ".join(leak[:10]))
    else:
        print("个人数据扫描：0 命中")

    if problems:
        raise SystemExit("构建前校验失败:\n  " + "\n  ".join(problems))
    return version


def compile_installer(makensis, release):
    nsi = release / "install.nsi"
    r = subprocess.run([makensis, "-V1", str(nsi)], cwd=str(release),
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        raise SystemExit("makensis 失败 rc=%s\n%s\n%s"
                         % (r.returncode, (r.stdout or "")[-1500:], (r.stderr or "")[-800:]))
    body = nsi.read_bytes().decode("utf-8-sig", "replace")
    m = re.search(r'OutFile\s+"?([^"\r\n]+)"?', body)
    want = m.group(1).strip() if m else None
    if not want or not (release / want).exists():
        raise SystemExit("install.nsi 的 OutFile 产物不存在: %s" % want)
    print("makensis 产物: %s（%.1f MB）" % (want, (release / want).stat().st_size / 1048576.0))
    return release / want


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True, help="解压后的 build-inputs 根目录（含 config/、MANIFEST.sha256）")
    ap.add_argument("--weasel-installer", required=True, help="官方 weasel-0.17.4.0-installer.exe")
    ap.add_argument("--work", required=True, help="临时构建目录")
    ap.add_argument("--out", required=True, help="最终 setup.exe 输出目录")
    ap.add_argument("--expect-version", default=None,
                    help="期望版本号；与 install.nsi 不一致时拒绝构建（防止输入包与源码串版）")
    args = ap.parse_args()

    inputs = Path(args.inputs).resolve()
    raw = Path(args.work).resolve() / "weasel-raw"
    release = Path(args.work).resolve() / "release"
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if release.exists():
        shutil.rmtree(release)
    release.mkdir(parents=True)

    sevenzip = find_7z()
    makensis = find_makensis()
    if not sevenzip:
        raise SystemExit("找不到 7z")
    if not makensis:
        raise SystemExit("找不到 makensis（CI 里用 choco install nsis）")
    print("7z:", sevenzip)
    print("makensis:", makensis)

    verify_manifest(inputs)
    extract_official(sevenzip, Path(args.weasel_installer).resolve(), raw)
    copy_engine(raw, release / "weasel-0.17.4", inputs / "engine-overlay")
    copy_config(inputs, release / "config")
    copy_reg(inputs, release)
    copy_installer_src(release)
    version = check_release(release)
    if args.expect_version and version != args.expect_version:
        raise SystemExit("版本串了：install.nsi 是 v%s，构建输入包是 v%s"
                         % (version, args.expect_version))

    exe = compile_installer(makensis, release)
    ascii_name = "sansheng-ime-v%s-setup.exe" % version
    target = out / ascii_name
    shutil.copy2(exe, target)
    digest = sha256(target)
    (out / "SHA256SUMS.txt").write_text("%s  %s\n" % (digest, ascii_name),
                                        encoding="utf-8", newline="\n")
    total = sum(p.stat().st_size for p in release.rglob("*") if p.is_file())
    print("\n构建完成")
    print("  %s" % target)
    print("  SHA256 %s" % digest)
    print("  release/ %.1f MB" % (total / 1048576.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
