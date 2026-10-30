#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""鸿蒙工程「脱敏导出」到 GitHub（Qoder，2026-10-30）

为什么需要这个：`F:\qoderwork\sansheng-ime-harmony` 里
  * `docs/evidence/**` 有 1,908 张真机截图（563 MB），里面**拍到过主人正在打的正文**，
    推到一个 **public** 仓库（riips7-code/sansheng-ime，public=True）等于公开他的私人文字；
  * `sign/**` 是签名私钥材料，`agconnect-services.json` 之类属密钥类文件；
  * `entry/build/**`、`oh_modules/**`、`.hvigor/**` 是构建产物与依赖，不该进库。
所以这里做的是「**按白名单语义的黑名单筛除**」：只导源码、配置、脚本、文字台账，
图片与密钥一律不出门，并在导出目录里写明「哪些没导、为什么」，免得远端看到死链以为是丢文件。

用法：
    python scripts/harmony_desensitize_export_qoder.py --dry          # 只统计，不落地
    python scripts/harmony_desensitize_export_qoder.py --dst <目录>    # 落地导出
退出码：0 正常；2 参数错。
"""
from __future__ import annotations

import os
import re
import sys

SRC = r"F:\qoderwork\sansheng-ime-harmony"

# ── 目录级排除 ────────────────────────────────────────────────────────────
SKIP_DIRS = {
    ".git", ".idea", ".hvigor", ".gradle", "__pycache__", ".pytest_cache",
    "node_modules", "oh_modules", "build", "sign", "dist", ".qoder",
    ".qoder-cn", "coverage", ".cache",
    # 本地调研草稿：含 hilog 原始抓取（可能带机主账号/手机号），不入库
    "_probe",
    # 构建产物与本地工具库：.cxx 是 CMake 中间物，.kanban/.codeartsdoer 是本机工具状态
    ".cxx", ".kanban", ".codeartsdoer", ".claude", ".cursor",
}
# docs/evidence 下按层级排除：草稿目录 tmp/ 与全部图片/截图
SKIP_EVIDENCE_DIR_PARTS = {"tmp"}

# ── 文件级排除（扩展名 / 精确名）─────────────────────────────────────────
SKIP_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".icns",
    ".p12", ".p7b", ".p7c", ".cer", ".pem", ".key", ".keystore", ".jks",
    ".log", ".dmp", ".mdmp", ".etl", ".evtx", ".pyc", ".tmp", ".bak",
    ".zip", ".7z", ".rar", ".apk", ".hap", ".app", ".exe", ".so", ".a", ".lib",
    ".tsbuildinfo",
}
# 「.bak-xxx」「.bak」这类备份文件：内容是旧版台账（可能含旧实名），一律不出门
BACKUP_PAT = ".bak"
SKIP_NAMES = {
    "agconnect-services.json", ".data-version", "local.properties",
    "signing-config.json", "keystore.properties",
}
# 软著申报材料：受理通知书/签章页含主人**实名与签字**，属私人物证材料，public 仓库一律不出门
SKIP_PATH_PREFIX = ("docs/release/copyright",)

# 原始抓取（hilog/日志/导出文本）：可能带机主账号或手机号；docs/evidence 下只留 .md 结论
EVIDENCE_RAW_EXT = {".txt", ".log", ".jsonl", ".csv", ".htm", ".html"}

# ── 文本脱敏替换表：机主实名与证件号不进 public 仓库 ──────────────────────
# 只在**导出时**替换，不改本地源文件（本地仓库存的是主人的真实记录）。
REDACTIONS = [
    ("[机主姓名已脱敏]", "[机主姓名已脱敏]"),
    ("[机主身份证号已脱敏]", "[机主身份证号已脱敏]"),
    ("[机主籍贯已脱敏]", "[机主籍贯已脱敏]"),
]
# 机主手机号：按前缀匹配 + 脱敏后的长度保持一致（11 位）
PHONE_RE = re.compile(r"(?<!\d)(1[3-9]\d)\d{4}(\d{4})(?!\d)")


def load_local_secrets():
    """从 sign/keys.local.json 取真值（只读、不打印、不落盘），
    用于把**真口令**也挡在导出之外——比在脚本里硬写更安全，
    脚本本身因此永远不含密钥明文。"""
    p = os.path.join(SRC, "sign", "keys.local.json")
    if not os.path.isfile(p):
        return []
    try:
        import json
        d = json.load(open(p, encoding="utf-8-sig"))
    except Exception:
        return []
    out = []

    def collect(o):
        if isinstance(o, dict):
            for v in o.values():
                collect(v)
        elif isinstance(o, list):
            for v in o:
                collect(v)
        elif isinstance(o, str) and len(o) >= 6:
            out.append(o)

    collect(d)
    return out

# ── 文字台账里的机主隐私痕迹（可自行判断要不要保留）──────────────────────
# 命中只统计、默认保留（台账是主人要留的记录），但会单独报数。

TEXT_EXT = {".md", ".txt", ".yaml", ".yml", ".json", ".json5", ".ets", ".ts",
            ".js", ".py", ".ps1", ".sh", ".bat", ".cmd", ".cpp", ".h", ".hpp",
            ".cc", ".lua", ".xml", ".ini", ".cfg", ".properties", ".sql",
            ".gitignore", ".gitattributes", ".editorconfig", ""}


def is_excluded_dir(rel: str, name: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    if name in SKIP_DIRS:
        # build 只在 entry/ 下才是构建产物；docs 里的 build 说明文档要留
        if name == "build":
            return parts[0] in ("entry", "oh_modules") or (len(parts) > 1 and parts[1] == "build")
        if name == "dist":
            return True
        return True
    if parts and parts[0] == "docs" and "evidence" in parts:
        if name in SKIP_EVIDENCE_DIR_PARTS:
            return True
    return False


def is_excluded_file(rel: str, name: str) -> bool:
    if any(rel.startswith(p + "/") for p in SKIP_PATH_PREFIX):
        return True
    if name in SKIP_NAMES:
        return True
    if BACKUP_PAT in name.lower() and not name.lower().endswith((".bak", ".bak-1")):
        # 形如 xxx.bak-qoder-20261030-022x（无标准扩展名）
        if ".bak" in name.lower():
            return True
    # docs/evidence 下的原始抓取（hilog/日志/网页快照）可能带机主账号 → 只留 .md 结论
    parts = rel.split("/")
    if len(parts) > 2 and parts[0] == "docs" and parts[1] == "evidence":
        if os.path.splitext(name)[1].lower() in EVIDENCE_RAW_EXT:
            return True
    ext = os.path.splitext(name)[1].lower()
    if ext in SKIP_EXT:
        return True
    if name.endswith(".gitignore") or name.endswith(".gitattributes"):
        return False
    return False


def walk(src):
    """产出 (相对路径, 绝对路径, 大小)。"""
    for root, dirs, files in os.walk(src):
        rel_root = os.path.relpath(root, src)
        rel_root = "" if rel_root == "." else rel_root.replace("\\", "/")
        keep_dirs = []
        for d in dirs:
            r = (rel_root + "/" + d) if rel_root else d
            if is_excluded_dir(r, d):
                continue
            keep_dirs.append(d)
        dirs[:] = keep_dirs
        for f in files:
            r = (rel_root + "/" + f) if rel_root else f
            if is_excluded_file(r, f):
                continue
            ap = os.path.join(root, f)
            try:
                size = os.path.getsize(ap)
            except OSError:
                size = 0
            yield r, ap, size


def main():
    dry = "--dry" in sys.argv
    dst = None
    if "--dst" in sys.argv:
        i = sys.argv.index("--dst")
        if i + 1 >= len(sys.argv):
            print("FAIL: --dst 后面要跟目录")
            return 2
        dst = sys.argv[i + 1]

    if not os.path.isdir(SRC):
        print("FAIL: 源目录不存在 %s" % SRC)
        return 2

    total = 0
    count = 0
    by_ext = {}
    big = []
    for rel, ap, size in walk(SRC):
        total += size
        count += 1
        ext = os.path.splitext(rel)[1].lower()
        by_ext[ext] = by_ext.get(ext, 0) + size
        if size > 3 * 1024 * 1024:
            big.append((size, rel))

    print("=== 脱敏后待导出清单（干跑）===")
    print("文件数 %d，合计 %.1f MB" % (count, total / 1024.0 / 1024.0))
    print("--- 体积前十的扩展名 ---")
    for ext, s in sorted(by_ext.items(), key=lambda x: -x[1])[:10]:
        print("  %-10s %8.2f MB" % (ext or "(无扩展)", s / 1024.0 / 1024.0))
    print("--- 大于 3 MB 的文件（需人工确认能不能公开）---")
    for s, rel in sorted(big, reverse=True)[:15]:
        print("  %8.2f MB  %s" % (s / 1024.0 / 1024.0, rel))

    if dry:
        print("[dry] 未落地。")
        return 0

    if not dst:
        print("FAIL: 需要 --dst <目录>")
        return 2

    import shutil
    n = 0
    redacted = {}
    converted = {}
    secrets = load_local_secrets()
    print("=== 真密钥值 %d 个将参与脱敏（只比对，不打印）===" % len(secrets))
    for rel, ap, size in walk(SRC):
        out = os.path.join(dst, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        # 脱敏作用于**文字类**文件（台账正文、法务 HTML、NOTICE、脚本注释等）；
        # 词典/配置/原始数据（rawfile/rime/**）一律按字节复制，
        # 免得正则误伤数据（词典里也有长数字串）。
        ext = os.path.splitext(rel)[1].lower()
        text_like = (ext in (".md", ".html", ".htm", ".txt", ".json", ".json5",
                             ".yaml", ".yml", ".py", ".ps1", ".sh", ".bat", ".cmd",
                             ".ts", ".ets", ".cpp", ".h", ".hpp", ".cc", ".lua")
                     or (ext == "" and rel.rsplit("/", 1)[-1].upper()
                         in ("NOTICE", "README", "LICENSE", "CHANGELOG", "AUTHORS")))
        is_data = rel.startswith("entry/src/main/resources/rawfile/rime/")
        if text_like and not is_data:
            try:
                raw = open(ap, "rb").read()
            except Exception:
                shutil.copy2(ap, out)
                n += 1
                continue
            # 旧脚本（.bat/.txt）可能是 GBK：git 收录时要把工作区文件转成 UTF-8，
            # 遇到 GBK 会直接 fatal（实测 deploy-codearts-*.bat 就是这样挂的）。
            # 这里在**导出副本**里统一转 UTF-8，内容一字不改。
            # 旧脚本（.bat/.txt）可能是 GBK。桌面仓根 .gitattributes 写着
            # `*.bat text eol=crlf working-tree-encoding=GBK` ⇒ **.bat 必须保持 GBK**
            # （导出成 UTF-8 会让 git add 直接 fatal：failed to encode from GBK to UTF-8）；
            # 其余文字统一 UTF-8 + LF。
            is_bat = ext == ".bat"
            try:
                t = raw.decode("utf-8")           # 先按 UTF-8 读（多数新文件是 UTF-8）
            except UnicodeDecodeError:
                t = raw.decode("gb18030", "replace")
                if not is_bat:
                    converted[rel] = "GBK→UTF-8"
            if is_bat:
                # 写回 cp936（严格 GBK）：桌面仓 .gitattributes 规定 .bat 工作区编码是 GBK；
                # 注意不能用 gb18030（它是 GBK 超集，git 的 GBK 解码会失败）。
                try:
                    t = t.encode("gbk", errors="replace").decode("gbk", errors="replace")
                except Exception:
                    pass
                enc, nl = "gbk", "\r\n"
            else:
                enc, nl = "utf-8", "\n"
            hits = 0
            for src, dst_txt in REDACTIONS:
                c = t.count(src)
                if c:
                    t = t.replace(src, dst_txt)
                    hits += c
            for s in secrets:
                c = t.count(s)
                if c:
                    t = t.replace(s, "[本地密钥已脱敏]")
                    hits += c
            t, c = PHONE_RE.subn(r"\1****\2", t)
            hits += c
            if hits:
                redacted[rel] = hits
            with open(out, "w", encoding=enc, newline=nl, errors="replace") as fp:
                fp.write(t)
        else:
            shutil.copy2(ap, out)
        n += 1
    print("=== 已导出 %d 个文件 -> %s ===" % (n, dst))
    # 写一份 .gitattributes：让 GBK 的 .bat 与二进制数据（OpenCC 词库等）按 binary 处理，
    # 否则 git add 会尝试把 GBK 转成 UTF-8 而失败（实测 deploy-codearts-*.bat 就是这样挂的）。
    try:
        with open(os.path.join(dst, ".gitattributes"), "w", encoding="utf-8", newline="\n") as fp:
            fp.write("# 公开副本的文本/二进制口径（Qoder 2026-10-30）\n"
                     "*.bat binary\n*.ocd2 binary\n*.db binary\n*.o binary\n"
                     "*.so binary\n*.a binary\n*.zip binary\n")
    except Exception as exc:
        print("[warn] .gitattributes 写入失败：%s" % exc)
    if converted:
        print("=== 编码转换（GBK→UTF-8）===")
        for rel, why in sorted(converted.items()):
            print("   %-60s %s" % (rel, why))
    if redacted:
        print("=== 脱敏命中（文件: 处数）===")
        for rel, c in sorted(redacted.items()):
            print("   %-60s %d" % (rel, c))
    else:
        print("=== 脱敏命中：0（注意：这不代表源里没有，需人工复核）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
