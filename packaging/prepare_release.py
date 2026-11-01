# -*- coding: utf-8 -*-
"""生成「对外发布」打包树：packaging/release/

来源（唯一真相）：
  packaging/stage/config/        三生配置（本机已验证的同一套）
  packaging/stage/weasel-0.17.4/ 引擎本体
  packaging/stage/*.reg          输入法注册表片段

做的事：
  1) 剔除个人数据（user.txt 自调频记录、user.yaml、installation.yaml、*.userdb、sync/、日志）
  2) 剔除杂物（*.orig、weasel 自带 uninstall.exe、rime-install*.bat、预览图）
  3) 剔除带个人内容的 lua 数据文件（phraseExt personal.txt 等）
  4) 重写 .reg：把硬编码的 D:\\Program Files\\Rime 改成 $INSTDIR 占位符
  5) 校验：两张英文权重表 md5 必须等于本机；个人文件必须为 0
  6) 生成 release/BUILD-INFO.txt（内容清单 + 体积 + 校验结果）

用法： python packaging/prepare_release.py            # 生成
       python packaging/prepare_release.py --check     # 只校验不写
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys

ROOT = r"F:\workbuddywork\三生输入法"
STAGE = os.path.join(ROOT, "packaging", "stage")
REL = os.path.join(ROOT, "packaging", "release")
LIVE = r"D:\Program Files\Rime"          # 兜底口径（老机器：安装目录 == 用户目录）

# 【Qoder 2026-11-02】这台机器的「生效用户配置目录」已经不是安装目录了：
#   HKCU\Software\Rime\Weasel\RimeUserDir = G:\RimeUser（主人 2026-10 迁的）。
#   脚本原来把 LIVE 当「本机配置」比 md5，2026-11-02 跑 --check 直接
#   FileNotFoundError: D:\Program Files\Rime\zh2en_pinyin_wp.dict.yaml —— 文件在 G:\RimeUser，
#   不在 D:。这不是配置坏了，是脚本口径过期。现在按注册表解析，解析不到才退回 LIVE。
#   用 reg.exe 而不是 winreg：本机 winreg 的 KEY_READ 已含 KEY_WOW64_64KEY，
#   再 OR 上 KEY_WOW64_32KEY 会枚举出 0 个值，看起来像「值不存在」（2026-10-30 踩过）。
TIP_KEY = (r"HKLM\SOFTWARE\Microsoft\CTF\TIP\{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}"
           r"\LanguageProfile\0x00000804\{3D02CAB6-2B8E-4781-BA20-1C9267529467}")


def reg_value(key, name):
    """读一个字符串注册表值；读不到返回 None（不抛，发布脚本要能在别的机器上跑）。"""
    try:
        r = subprocess.run(["reg.exe", "query", key, "/v", name],
                           capture_output=True, text=True, encoding="gbk", errors="replace")
    except Exception:
        return None
    for line in (r.stdout or "").splitlines():
        parts = line.strip().split()
        if len(parts) >= 3 and parts[0].lower() == name.lower() and parts[1].upper() == "REG_SZ":
            val = line.strip()[len(parts[0]):].strip()
            val = val[val.find("REG_SZ") + len("REG_SZ"):].strip()
            return val or None
    return None


def _resolve_dirs():
    user = reg_value(r"HKCU\Software\Rime\Weasel", "RimeUserDir") or LIVE
    icon = reg_value(TIP_KEY, "IconFile")
    prog = os.path.dirname(icon) if icon else LIVE
    return os.path.normpath(user), os.path.normpath(prog or LIVE)


USER_CFG, PROG_DIR = _resolve_dirs()

# 个人数据 / 不该对外的文件（按文件名匹配，小写）
PERSONAL = {
    "user.txt", "user.yaml", "installation.yaml", "custom_phrase.txt",
    "runlog.txt", "phraseext personal.txt", "phrasecomment personal.txt",
    # 【Qoder 2026-11-02】phraseComment personal.txt 和 phraseExt personal.txt 同一类：
    #   stage（=真机镜像）里是主人自己的注释内容，发布树由第 2.5 步换成空模板。
    #   所以 5.6 拿真机和 stage 比 md5 时它必然不等 —— 那是设计如此，不是漂移。
    # Qoder 2026-10-26：wubi86.txt 是 **wubi86 词典的用户学习词 TextDb 导出**
    #   （文件头 `#@/db_name wubi86` + `#@/db_type tabledb` + `#@/tick 83`，
    #     正文是「工<Tab>aaaa<Tab>2」这类学习计数，本机那份 mtime 10-25 14:54，
    #     是 #125 实验把 user_dict 指向 wubi86 期间生成的残留）。
    #   和 user.txt 同一类：装到别人机器上=把主人的自造词带过去，属个人数据泄露；
    #   干净机器不需要它——引擎自己会生成。所以进白名单，而不是补进 config/。
    #   （#127 之后现役方案 db_class 全是 userdb，本文件在运行期也不会再被写。）
    "wubi86.txt",
}
# 引擎目录杂物
ENGINE_SKIP = {
    "weasel.ime.orig", "uninstall.exe", "rime-install.bat",
    "rime-install-config.bat", "start_service.bat", "stop_service.bat",
}
# 目录名：整目录跳过（data/preview 是小狼毫设置界面的配色预览，保留）
SKIP_DIRS = {"sync", "__pycache__", "weasel.user", "wiki-keep"}
# 后缀：整类跳过
SKIP_SUFFIX = (".bak", ".orig", ".sw-", ".test-bak", ".userdb", ".log", ".tmp")

# 许可证正文（本机根目录里那批 *.txt 是合规材料，不是运行时配置）。
# 它由 install.nsi 显式 File 打进安装包（LICENSE、THIRD_PARTY_NOTICES.md、LICENSES\*），
# 不需要也不应该再随 config/ 复制进用户目录；5.6 的「本机有、发布树没有」检查要跳过它们。
# 名字直接从仓库 LICENSES/ 取，避免手抄文件名（MIT-ECDICT 之类容易打错）。
_LIC_DIR = os.path.join(ROOT, "LICENSES")
LICENSE_DOCS = {n.lower() for n in os.listdir(_LIC_DIR)} if os.path.isdir(_LIC_DIR) else set()
LICENSE_DOCS |= {"license", "license.txt", "copying", "notice.txt", "third_party_notices.md"}

# 真机目录里存在、但**逐条核对过决定不进包**的运行时文件（相对生效用户目录的路径）。
# 5.6 闸门会跳过这里列出的项；每一项必须写清理由，防止下一个人当漂移"修"回去。
# 【Qoder 2026-11-02】
NOT_SHIPPED = {
    "仓键盘布局/wubi86_jidian_ios_keyboard.yaml":
        "真机 *.yaml 里 grep 不到任何引用（未接线）；主人 2026-11-02 没点名，不动",
}

INSTDIR_PLACEHOLDER = r"$INSTDIR"

CHECK_TABLES = ["zh2en_pinyin_wp.dict.yaml", "zh2en_wubi_wp.dict.yaml"]

# 【Qoder 2026-11-02 · 主人「图标保存好，打包的时候都打进去」】
# 主人这次是按「画法」数的 4 张，不是按文件名，原话：
#   「黑方底金汉字三，黑方底金环汉字三（桌面图标用）+（选择输入法时，输入法本身图标
#     （现在是和托盘的一样，需要改过来），黑方底变形汉字三，黑圆底圆形变形汉字三（托盘用）」
# 画法 → 文件是逐张渲染核对出来的（F:\sansheng_probe_log\icon_roles_20261102\artwork_map.png），
# 别凭文件名猜：bubble.ico 看着像「金环」，实际是黑圆底三；ring.ico 才是 README 的「图标二 方圆象」。
PROGRAM_ICONS = [
    ("icon-sansheng-ring.ico",   "主人点名的「黑方底金环汉字三」= README 图标二·方圆象 → 安装包 MUI_ICON / 桌面快捷方式 / 控制面板 DisplayIcon（本轮新建：此前只有 PNG，无 .ico）"),
    ("icon-sansheng-formal.ico", "主人点名的「黑方底变形汉字三」= README 图标三·鱼眼象 → 注册表 TIP IconFile×10 =「选择输入法」列表里那张（本轮新建：此前只有 PNG，无 .ico）"),
    ("icon-sansheng-tray.ico",   "主人点名的「黑圆底圆形变形汉字三」→ 托盘常驻图标（weasel.custom.yaml style/display_tray_icon=true + wubi_pinyin.custom.yaml schema/icon、schema/zhung_icon）"),
    ("icon-sansheng-cn.ico",     "主人点名的「黑方底金汉字三」= README 图标一·乾卦象 → 随包留档，暂无挂载岗位（等主人点名）"),
    ("icon-sansheng-bubble-en.ico", "wubi_pinyin.custom.yaml → schema/ascii_icon（英文模式托盘，黑圆底 A）"),
    ("icon-sansheng-bubble.ico", "黑圆底三：当前无配置引用（2026-11-02 岗位改给 tray.ico 后空出），随包留档，一句话可把 zhung_icon 回退成气泡图"),
    ("wubi86_jidian.ico",        "wubi86_jidian.schema.yaml → schema/icon（极点五笔方案）"),
]
# 品牌留档目录（assets 里既有设计源图 PNG/SVG，也必须有上面这些运行时 ICO）
ASSETS = os.path.join(ROOT, "assets")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_makensis():
    """找 NSIS 编译器：本机 D 盘已装的一份优先，其次常见位置。"""
    cands = [
        r"D:\Program Files (x86)\NSIS\makensis.exe",
        r"C:\Program Files (x86)\NSIS\makensis.exe",
        r"C:\Program Files\NSIS\makensis.exe",
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def interest_file(name):
    n = name.lower()
    if n in PERSONAL or n in ENGINE_SKIP:
        return False
    if n.endswith(SKIP_SUFFIX):
        return False
    return True


def copy_tree(src, dst, extra_skip=()):
    n, skipped = 0, []
    for dirpath, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS and not d.lower().endswith(".userdb")]
        rel = os.path.relpath(dirpath, src).replace("\\", "/")
        for fn in files:
            if not interest_file(fn) or fn.lower() in [e.lower() for e in extra_skip]:
                skipped.append(os.path.join(rel, fn) if rel != "." else fn)
                continue
            s = os.path.join(dirpath, fn)
            d = os.path.join(dst, rel, fn) if rel != "." else os.path.join(dst, fn)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            n += 1
    return n, skipped


def rewrite_reg(src, dst):
    """把 D:\\Program Files\\Rime\\xxx.ico 换成 $INSTDIR\\xxx.ico（NSIS 运行时展开）。"""
    raw = open(src, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        txt = raw.decode("utf-16")
        enc = "utf-16"
    else:
        txt = raw.decode("utf-8-sig", "replace")
        enc = "utf-8-sig"
    txt = txt.replace("D:\\\\Program Files\\\\Rime\\\\", INSTDIR_PLACEHOLDER + "\\\\")
    txt = txt.replace("D:\\Program Files\\Rime\\", INSTDIR_PLACEHOLDER + "\\")
    with open(dst, "wb") as f:
        f.write(txt.encode(enc if enc != "utf-8-sig" else "utf-8-sig"))
    n = txt.count(INSTDIR_PLACEHOLDER)
    return n


def main():
    check_only = "--check" in sys.argv
    report, problems = [], []

    if not check_only:
        for sub in ("config", "weasel-0.17.4"):
            d = os.path.join(REL, sub)
            if os.path.exists(d):
                shutil.rmtree(d)
        os.makedirs(REL, exist_ok=True)

    # 1) 配置
    n1, sk1 = copy_tree(os.path.join(STAGE, "config"), os.path.join(REL, "config"),
                        extra_skip=("readme.md",))
    report.append("config/ 收录 %d 个文件，剔除 %d 个" % (n1, len(sk1)))

    # 2) 引擎
    n2, sk2 = copy_tree(os.path.join(STAGE, "weasel-0.17.4"), os.path.join(REL, "weasel-0.17.4"))
    report.append("weasel-0.17.4/ 收录 %d 个文件，剔除 %d 个" % (n2, len(sk2)))

    # 2.5) 上游把私人内容单独放在 *personal*.txt 里；发布版留同名空模板，
    #      避免 lua 读不到文件（保持「文件在、内容为空」的最稳状态）
    stubs = {
        os.path.join("lua", "phraseExt personal.txt"):
            "# 候选词扩展 · 个人数据（发布版为空模板）\r\n"
            "# 格式： 词<Tab>要追加的候选1<Tab>候选2 ...\r\n\r\n",
        os.path.join("lua", "phraseComment personal.txt"):
            "# 候选词注释 · 个人数据（发布版为空模板）\r\n"
            "# 格式： 词<Tab>注释内容\r\n\r\n",
    }
    made = 0
    for rel, body in stubs.items():
        p = os.path.join(REL, "config", rel)
        if not check_only:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(body)
        made += 1
    report.append("个人数据文件已换成空模板 %d 个" % made)

    # 3) .reg 原样带上（里面的 D:\Program Files\Rime 只是 IconFile 初值，
    #    安装脚本导入后会立刻用 WriteRegStr 改成真实的 $INSTDIR 路径，不影响结果）
    reg_note = []
    for reg in ("weasel-clsid.reg", "weasel-clsid32.reg", "weasel-tip.reg", "weasel-tip32.reg"):
        s = os.path.join(STAGE, reg)
        d = os.path.join(REL, reg)
        if os.path.exists(s):
            if not check_only:
                shutil.copy2(s, d)
            raw = open(s, "rb").read()
            txt = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig", "replace")
            reg_note.append("%s(%d 处硬路径)" % (reg, txt.count("Program Files")))
    report.append("注册表片段原样收录：" + ", ".join(reg_note))

    # 4) 中性模板：Custom_phrase.txt / 空 user.txt 不打包（让引擎自建）
    tmpl = os.path.join(REL, "config", "Custom_phrase.txt")
    if not check_only:
        with open(tmpl, "w", encoding="utf-8", newline="\r\n") as f:
            f.write("# 三生输入法 · 自定义短语模板\r\n"
                    "# 每行一条：  短语<Tab>编码<Tab>权重\r\n"
                    "# 例：三生<Tab>ssgg<Tab>999999   →  输入 ssgg 出「三生」\r\n"
                    "\r\n")
    report.append("Custom_phrase.txt 已换成中性模板")

    # 5) 硬校验：两张英文表必须与本机一致
    for t in CHECK_TABLES:
        a = os.path.join(USER_CFG, t)
        b = os.path.join(REL, "config", t)
        ma = md5(a)
        mb = md5(b) if os.path.exists(b) else "缺失"
        if ma != mb:
            problems.append("不一致: %s live=%s release=%s" % (t, ma[:12], mb[:12]))
        else:
            report.append("校验通过 %s md5=%s" % (t, ma[:12]))

    # 5.5) 硬校验：lua 入口 rime.lua 必须在，且每个 schema 引用的 lua 名字都要有定义
    #      （v1.9/v1.9.1 笔记本「装上了但打不出汉字」的根因：本机安装目录=用户目录，
    #        rime.lua 躺在那里从来没被 stage/config 收过；干净机器上没有它，
    #        schema 里 10 个 lua_filter@/lua_translator@ 全部解析不到 -> 建不出引擎 -> 不出字。
    #        prism/table 编译是不碰 lua 的，所以部署看着完全成功。）
    entry = os.path.join(REL, "config", "rime.lua")
    if not os.path.exists(entry):
        problems.append("缺 rime.lua：发布树里没有 lua 入口，装上的机器一定打不出字")
    else:
        body = open(entry, "rb").read().decode("utf-8-sig", "replace")
        defined = set(re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*require", body, re.M))
        # 只查 schema_list 里真正启用的方案（历史遗留方案在本机也是半坏的，不该拦发布）
        active = set()
        for df in ("default.custom.yaml", "default.yaml"):
            dp = os.path.join(REL, "config", df)
            if os.path.exists(dp):
                dtxt = open(dp, "rb").read().decode("utf-8-sig", "replace")
                active |= set(re.findall(r"schema:\s*\"?([A-Za-z0-9_]+)\"?", dtxt))
        used, miss = set(), []
        for sch in sorted(active):
            for suffix in (".schema.yaml", ".custom.yaml"):
                sp = os.path.join(REL, "config", sch + suffix)
                if not os.path.exists(sp):
                    continue
                txt = open(sp, "rb").read().decode("utf-8-sig", "replace")
                for name in re.findall(r"lua_(?:filter|translator|processor|segmentor)@([A-Za-z_][A-Za-z0-9_]*)", txt):
                    used.add(name)
                    if name not in defined:
                        miss.append("%s -> %s" % (sch + suffix, name))
        if not active:
            problems.append("读不到 schema_list，无法校验 lua 接线")
        elif miss:
            problems.append("启用的 schema 引用了 rime.lua 里没有的 lua 名字: " + ", ".join(sorted(set(miss))[:8]))
        else:
            report.append("校验通过 rime.lua 定义 %d 个入口；启用方案 %s 引用 %d 个全部命中" % (
                len(defined), "/".join(sorted(active)) or "?", len(used)))

    # 5.6) 硬校验：**打包种子 stage/config** 必须覆盖本机生效用户目录的那一套运行时文件
    #      【Qoder 2026-11-02 改版】原来这条有两个盲区，把最要命的漂移放过去了：
    #        ① 比的是 release/config —— 那是上一次出包留下的完整树，而每次出包都会
    #          rmtree(release/config) 再从 **stage/config** 重铺，真正决定包里有什么的是 stage；
    #        ② 只 listdir 顶层，不看 lua/ 等子目录 —— 于是
    #          lua/enWord_Filter.lua（H-313 崩溃修复本体）不在 stage 里也照样绿灯。
    #      2026-11-02 实测：stage 缺 enWord_Filter.lua / slash_filter_qoder.lua / en_word.* 三件套，
    #      rime.lua 与 wubi_pinyin.{schema,custom}.yaml 停在旧版；当天重建一次就会把崩溃修复发丢。
    #      现在：递归走真机目录 + 比 md5（不只比存在）+ 比 stage。
    live_root, seed_cfg = USER_CFG, os.path.join(STAGE, "config")
    only_live, stale = [], []
    SKIP_DIRS_LIVE = SKIP_DIRS | {"build", "installation.dat"}
    for dirpath, dirnames, filenames in os.walk(live_root):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in SKIP_DIRS_LIVE and not d.startswith("_"))
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, live_root).replace(os.sep, "/")
            n = fn.lower()
            if not n.endswith((".lua", ".yaml", ".txt", ".ico")):
                continue          # 只看运行时配置和运行时图标（文档/构建脚本不在此列）
            if ".bak" in n or ".sw-" in n or ".orig" in n or "moved-" in n or "-bak" in n:
                continue          # 各种备份残留（后缀五花八门，按子串判）
            if n in PERSONAL or n.endswith(SKIP_SUFFIX) or n in ENGINE_SKIP \
                    or n in LICENSE_DOCS or os.path.basename(p).lower() in LICENSE_DOCS:
                continue          # 有意不带的个人数据/杂物/许可证正文
            if rel in NOT_SHIPPED:
                continue          # 逐条核对过、写明理由的不进包项（见文件头 NOT_SHIPPED）
            tp = os.path.join(seed_cfg, rel.replace("/", os.sep))
            if not os.path.isfile(tp):
                only_live.append(rel)
            elif md5(p) != md5(tp):
                stale.append("%s（真机 %s / stage %s）" % (rel, md5(p)[:12], md5(tp)[:12]))
    if only_live:
        problems.append("生效用户目录有、打包种子 stage 没有的运行时文件（重建安装包就会从包里消失）: "
                        + ", ".join(only_live[:12]))
    if stale:
        problems.append("打包种子 stage 的内容比真机旧（重建会把真机改动退回旧版）: "
                        + "; ".join(stale[:12]))
    if not only_live and not stale:
        report.append("校验通过 生效用户目录 %s 的运行时配置（含 lua/ 子目录）在打包种子 stage 中"
                      "无一遗漏且字节一致" % USER_CFG)

    # 5.7) 硬校验：运行时图标「四处齐全 + 字节一致」
    #      背景（H-312 / H-314，2026-11-01）：清 D: 根目录时把注册表指向的
    #      icon-sansheng-tray.ico 当杂物搬进了归档，托盘当场退化成「简体」两个字。
    #      当时没有任何检查会发现——上面的 5.6 只看 .lua/.yaml/.txt，图标根本不在射程里。
    #      所以这一条守的是四处：品牌留档 assets / 包内 release-config /
    #      打包输入 stage-config / 本机程序目录，任一缺失或内容不一致 ⇒ 禁止发布。
    icon_rows = []
    for name, where in PROGRAM_ICONS:
        places = {"assets": os.path.join(ASSETS, name),
                  "release": os.path.join(REL, "config", name),
                  "stage": os.path.join(STAGE, "config", name),
                  "程序目录": os.path.join(PROG_DIR, name),
                  "生效用户目录": os.path.join(USER_CFG, name)}
        # 老机器上「安装目录 == 用户目录」，两处是同一个文件，去重后只查一次
        uniq, seen = {}, set()
        for tag, p in places.items():
            k = os.path.normcase(os.path.abspath(p))
            if k in seen:
                continue
            seen.add(k)
            uniq[tag] = p
        places = uniq
        digests, absent = {}, []
        for tag, p in places.items():
            if os.path.isfile(p):
                digests[tag] = md5(p)
            else:
                absent.append(tag)
        if absent:
            problems.append("图标 %s 缺失：%s（引用处：%s）" % (name, "/".join(absent), where))
        elif len(set(digests.values())) > 1:
            problems.append("图标 %s 各处内容不一致：%s" % (
                name, ", ".join("%s=%s" % (t, d[:12]) for t, d in sorted(digests.items()))))
        else:
            icon_rows.append("%s=%s(%d B)" % (name, list(digests.values())[0][:12],
                                              os.path.getsize(places["release"])))
    if icon_rows:
        report.append("校验通过 运行时图标 %d 张在 assets/包内/stage/程序目录/生效用户目录字节一致：%s"
                      % (len(icon_rows), ", ".join(icon_rows)))

    # 6) 个人数据扫描（发布前铁律）
    leak = []
    for dirpath, dirs, files in os.walk(REL):
        for fn in files:
            n = fn.lower()
            if n in ("custom_phrase.txt", "phraseext personal.txt", "phrasecomment personal.txt"):
                continue      # 有意生成的中性模板
            if n in PERSONAL or n.endswith(SKIP_SUFFIX) or n in ENGINE_SKIP:
                leak.append(os.path.relpath(os.path.join(dirpath, fn), REL))
    if leak:
        problems.append("仍有个人/杂物文件: " + ", ".join(leak[:10]))
    else:
        report.append("个人数据扫描：0 命中")

    # 7) 安装器源码（唯一真相在 packaging/installer-src/，这里只是铺进发布树）
    ISRC = os.path.join(ROOT, "packaging", "installer-src")
    copied = []
    for fn in sorted(os.listdir(ISRC)) if os.path.isdir(ISRC) else []:
        s = os.path.join(ISRC, fn)
        if not os.path.isfile(s):
            continue
        d = os.path.join(REL, fn)
        raw = open(s, "rb").read()
        if fn.lower().endswith((".nsi", ".ps1")):
            # NSIS 与 PowerShell 5.1 都要求 UTF-8 BOM，否则中文按 ANSI 解析会炸
            body = raw.decode("utf-8-sig").lstrip("\ufeff")
            body = body.replace("\r\n", "\n")
            if not check_only:
                open(d, "wb").write(body.encode("utf-8-sig"))
        elif not check_only:
            shutil.copy2(s, d)
        copied.append(fn)
    report.append("安装器源码铺入 %d 个: %s" % (len(copied), ", ".join(copied)))

    # 7.5) 硬校验：所有 -Tip 参数必须以「0804:」开头（语言 ID 后有冒号）。
    #      v1.9.9 之前写成 0804{...}，Windows 会把它连同该语言下已有的键盘一起清掉，
    #      导致用户的万能五笔/青简等输入法从键盘列表消失。这类错误不能只靠肉眼。
    tip_bad = []
    for fn in ("install.nsi", "enable-tip.ps1", "remove-tip.ps1", "卸载三生输入法.ps1"):
        p = os.path.join(ISRC, fn)
        if not os.path.exists(p):
            continue
        body = open(p, "rb").read().decode("utf-8-sig", "replace")
        for m in re.finditer(r'-Tip\s+"([^"]*)"', body):
            tip = m.group(1)
            if not tip.startswith("0804:"):
                tip_bad.append("%s: -Tip %s" % (fn, tip))
        for m in re.finditer(r'\$TipStr\s*=\s*"([^"]*)"', body):
            if not m.group(1).startswith("0804:"):
                tip_bad.append("%s: TipStr %s" % (fn, m.group(1)))
    if tip_bad:
        problems.append("TIP 参数缺少语言 ID 后的冒号（会清空用户键盘列表）: " + "; ".join(tip_bad[:5]))
    else:
        report.append("校验通过 TIP 参数格式（0804:{CLSID}{GUID}）")

    # 7.6) 硬校验：安装包文件名里的版本号必须等于控制面板 DisplayVersion（一版一号）
    nsi_path = os.path.join(ISRC, "install.nsi")
    nsi_body = open(nsi_path, "rb").read().decode("utf-8-sig", "replace") if os.path.exists(nsi_path) else ""
    m_out = re.search(r'OutFile\s+"?([^"\r\n]+)"?', nsi_body)
    m_dv = re.search(r'WriteRegStr\s+HKLM\s+"\$\{UN_KEY\}"\s+"DisplayVersion"\s+"([^"]+)"', nsi_body)
    if not m_out or not m_dv:
        problems.append("读不到 install.nsi 的 OutFile 或 DisplayVersion，无法做版本一致性校验")
    else:
        # 版本号允许两段（v1.9 / v1.10 这种大版）或三段（v1.9.10 这种补丁版）；
        # 真正要守的是「包名版本 == 控制面板 DisplayVersion」，一版一号好回溯。
        m_ver = re.search(r'-v([0-9]+\.[0-9]+(?:\.[0-9]+)?)-setup\.exe$', m_out.group(1).strip())
        if not m_ver:
            problems.append("install.nsi 的 OutFile 不含 -vX.Y(.Z)-setup.exe 版本号: " + m_out.group(1))
        elif m_ver.group(1) != m_dv.group(1):
            problems.append("版本号不一致：包名 %s / DisplayVersion %s（一版一号）"
                            % (m_ver.group(1), m_dv.group(1)))
        else:
            report.append("校验通过 包名与控制面板版本号一致：v%s" % m_ver.group(1))

    # 8) 编译 setup.exe（找到 makensis 就编，找不到只出树）
    exe_note = "未找到 makensis，跳过编译（可手动运行 makensis install.nsi）"
    if not check_only:
        nsis = find_makensis()
        if nsis:
            nsi = os.path.join(REL, "install.nsi")
            r = subprocess.run([nsis, "-V1", nsi], cwd=REL, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            exe_list = [f for f in os.listdir(REL) if f.endswith("-setup.exe")]
            # 必须认 install.nsi 里 OutFile 的那个名字：release/ 里可能残留上一版同名后缀的 exe，
            # 按 listdir 顺序取第一个会把旧包拷进 dist/（2026-10-18 差点把 1.9.3 当 1.9.4 发出去）
            import re as _re
            want = None
            try:
                for _line in open(nsi, encoding="utf-8-sig"):
                    _mm = _re.match(r'\s*OutFile\s+"?([^"\r\n]+)"?\s*$', _line, _re.I)
                    if _mm:
                        want = _mm.group(1).strip()
                        break
            except Exception:
                want = None
            if want and want not in exe_list:
                problems.append("install.nsi 的 OutFile 是 %s，但 release/ 里没有这个产物（现有: %s），禁止发布"
                                % (want, ", ".join(sorted(exe_list))))
                out = []
            elif want:
                out = [want]
            else:
                out = exe_list[:1]
            warn = (r.stdout or "").strip() + (r.stderr or "").strip()
            if r.returncode == 0 and out:
                if want and len(exe_list) > 1:
                    report.append("注意: release/ 存在多个 setup 产物，本次只取 %s（其余属旧版残留）" % want)
                if warn:
                    report.append("makensis 警告(非致命):\n" + warn[-600:])
                dist = os.path.join(ROOT, "packaging", "dist")
                os.makedirs(dist, exist_ok=True)
                src_exe = os.path.join(REL, out[0])
                shutil.copy2(src_exe, os.path.join(dist, out[0]))
                exe_note = "已编译 %s（%.1f MB，内嵌卸载程序）-> packaging/dist/" % (
                    out[0], os.path.getsize(src_exe) / 1048576.0)
            else:
                if r.returncode == 0 and not out:
                    exe_note = "编译产物名与 install.nsi 的 OutFile 不符，已判为禁止发布（见上方问题）"
                else:
                    exe_note = "makensis 失败 rc=%s\n%s" % (r.returncode, (r.stdout or "")[-800:] + (r.stderr or "")[-400:])
                    problems.append("setup.exe 编译失败，禁止发布")
    report.append(exe_note)

    # 体积
    tot = sum(os.path.getsize(os.path.join(r, f))
              for r, _, fs in os.walk(REL) for f in fs) if os.path.isdir(REL) else 0
    report.append("release/ 总体积 %.1f MB" % (tot / 1048576.0))

    txt = "\n".join(report) + "\n" + ("\n!! 问题:\n" + "\n".join(problems) + "\n" if problems else "\n全部校验通过 ✓\n")
    if not check_only:
        open(os.path.join(REL, "BUILD-INFO.txt"), "w", encoding="utf-8").write(
            "三生输入法 · 对外发布打包树\n生成: prepare_release.py\n\n" + txt)
    print(txt)
    print("剔除清单(前 25):", sk1[:12], sk2[:12])
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
