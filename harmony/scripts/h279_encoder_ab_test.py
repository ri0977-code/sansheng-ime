#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
h279_encoder_ab_test.py (Qoder) —— H-279 自造词根因的**离线 A/B 判定实验**

为什么要在电脑上做这个实验：
  鸿蒙端「自造词」不工作的根因已定位到打包词库 `wubi86.dict.yaml` 丢了第 4 列（末级全码 stem），
  引擎侧 `UnityTableEncoder::TranslateWord` 因此几乎每个字都取不到全码 ⇒ `EncodePhrase` 存不下词。
  但「读代码得出」不等于「验过」。装一次真机要主人输一次密码（AGENTS.md 4.x／主人 2026-10-25 明令：
  不许反复装机），所以先用**同一颗引擎、同一份配置、只换词库**做一次对照：
    A 组 = 修复前的 wubi86.dict.yaml（25 行有 stem，docs/evidence/.../wubi86.dict.yaml.before-stems）
    B 组 = 修复后的 wubi86.dict.yaml（20935 行有 stem，和桌面/安卓一致）
  判定：两组都先分别上屏 行 / 不 / 行（喂给 commit_history），再重开一个 session 打 tgtf。
        只有 B 组能出「行不行」⇒ 证明丢的确实是 stem 列，且补回来就通。
        若 A、B 都出 ⇒ 本实验证伪了根因（说明是 enable_sentence 现拼，得回查引擎侧）。
        若 A、B 都不出 ⇒ Windows 侧 librime 与鸿蒙侧行为有差，本实验只能当参考，结论仍以真机为准。

引擎：weasel-0.17.4 的 rime.dll（x64，librime 的 C API，头文件用本仓 entry/src/main/cpp/include/rime_api.h 解析字段序）。
用法：PYTHONIOENCODING=utf-8 python scripts/h279_encoder_ab_test.py [A|B|AB]
"""
import ctypes
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

REPO = r"F:/qoderwork/sansheng-ime-harmony"
HEADER = REPO + "/entry/src/main/cpp/include/rime_api.h"
RAWMEDIR = REPO + "/entry/src/main/resources/rawfile/rime"
OLD_DICT = REPO + "/docs/evidence/2026-10-30/h279-dict/wubi86.dict.yaml.before-stems"
NEW_DICT = RAWMEDIR + "/wubi86.dict.yaml"
DLLS = [
    r"F:/dshdesktopwork/rime-backup-20261015-2045-workbuddy/weasel-0.17.4",
]
SCHEMA = "wubi_pinyin"


# ---------------------------------------------------------------- API 结构解析
def api_field_order():
    """从 rime_api.h 里按声明顺序取 RimeApi 结构体的函数指针字段名。"""
    src = open(HEADER, encoding="utf-8").read()
    m = re.search(r"typedef struct RIME_FLAVORED\(rime_api_t\) \{(.*?)\n\} RIME_FLAVORED\(RimeApi\);",
                  src, re.S)
    if not m:
        raise RuntimeError("RimeApi 结构体没找到，头文件版本变了？")
    body = m.group(1)
    names = re.findall(r"\(\s*\*\s*([A-Za-z_][A-Za-z_0-9]*)\s*\)\s*\(", body)
    if len(names) < 60:
        raise RuntimeError("只解析到 %d 个字段，不像完整的 RimeApi" % len(names))
    return names


FIELDS = api_field_order()


class RimeTraits(ctypes.Structure):
    _fields_ = [
        ("data_size", ctypes.c_int),
        ("shared_data_dir", ctypes.c_char_p),
        ("user_data_dir", ctypes.c_char_p),
        ("distribution_name", ctypes.c_char_p),
        ("distribution_code_name", ctypes.c_char_p),
        ("distribution_version", ctypes.c_char_p),
        ("app_name", ctypes.c_char_p),
        ("modules", ctypes.POINTER(ctypes.c_char_p)),
        ("min_log_level", ctypes.c_int),
        ("log_dir", ctypes.c_char_p),
        ("prebuilt_data_dir", ctypes.c_char_p),
        ("staging_dir", ctypes.c_char_p),
    ]


class RimeComposition(ctypes.Structure):
    _fields_ = [("length", ctypes.c_int), ("cursor_pos", ctypes.c_int),
                ("sel_start", ctypes.c_int), ("sel_end", ctypes.c_int),
                ("preedit", ctypes.c_char_p)]


class RimeCandidate(ctypes.Structure):
    _fields_ = [("text", ctypes.c_char_p), ("comment", ctypes.c_char_p),
                ("reserved", ctypes.c_void_p)]


class RimeMenu(ctypes.Structure):
    _fields_ = [("page_size", ctypes.c_int), ("page_no", ctypes.c_int),
                ("is_last_page", ctypes.c_int),
                ("highlighted_candidate_index", ctypes.c_int),
                ("num_candidates", ctypes.c_int),
                ("candidates", ctypes.POINTER(RimeCandidate)),
                ("select_keys", ctypes.c_char_p)]


class RimeContext(ctypes.Structure):
    _fields_ = [("data_size", ctypes.c_int),
                ("composition", RimeComposition),
                ("menu", RimeMenu),
                ("commit_text_preview", ctypes.c_char_p),
                ("select_labels", ctypes.POINTER(ctypes.c_char_p))]


class RimeCommit(ctypes.Structure):
    _fields_ = [("data_size", ctypes.c_int), ("text", ctypes.c_char_p)]


# H-279(Qoder) ABI 坑：rime_api.h:57 `typedef uintptr_t RimeSessionId` ⇒ x64 上是 8 字节。
# 早先用 c_uint32 声明，Microsoft x64 调用约定下 RCX 的高 32 位是脏的，引擎读到的是不存在的
# session id：deploy 一切正常（不传 session），到 select_schema 就返回 0，且日志里连错误都没有
# （schema 已经真的加载完、engine 已经 start 了），一度让人以为配置有问题。全部改成 c_size_t。
SIGS = {
    "setup": (None, [ctypes.c_void_p]),
    "initialize": (None, []),
    "finalize": (None, []),
    "start_maintenance": (None, [ctypes.c_int]),
    "join_maintenance_thread": (None, []),
    "create_session": (ctypes.c_size_t, []),
    "destroy_session": (ctypes.c_int, [ctypes.c_size_t]),
    "find_session": (ctypes.c_int, [ctypes.c_size_t]),
    "select_schema": (ctypes.c_int, [ctypes.c_size_t, ctypes.c_char_p]),
    "get_current_schema": (ctypes.c_int, [ctypes.c_size_t, ctypes.c_char_p, ctypes.c_int]),
    "process_key": (ctypes.c_int, [ctypes.c_size_t, ctypes.c_int, ctypes.c_int]),
    "get_context": (ctypes.c_int, [ctypes.c_size_t, ctypes.c_void_p]),
    "free_context": (None, [ctypes.c_void_p]),
    "get_commit": (ctypes.c_int, [ctypes.c_size_t, ctypes.c_void_p]),
    "free_commit": (None, [ctypes.c_void_p]),
    "clear_composition": (ctypes.c_int, [ctypes.c_size_t]),
    "select_candidate_on_current_page": (ctypes.c_int, [ctypes.c_size_t, ctypes.c_size_t]),
    "set_option": (None, [ctypes.c_size_t, ctypes.c_char_p, ctypes.c_int]),
    "get_option": (ctypes.c_int, [ctypes.c_size_t, ctypes.c_char_p]),
    "sync_user_data": (ctypes.c_int, []),
    "get_version": (ctypes.c_char_p, []),
}


class Rime:
    def __init__(self, dll_dir):
        os.environ["PATH"] = dll_dir + os.pathsep + os.environ.get("PATH", "")
        self.dll = ctypes.WinDLL(os.path.join(dll_dir, "rime.dll"))
        get_api = self.dll.rime_get_api
        get_api.restype = ctypes.c_void_p
        addr = get_api()
        if not addr:
            raise RuntimeError("rime_get_api() 返回空")
        names = FIELDS
        layout = [("data_size", ctypes.c_int), ("_pad", ctypes.c_char * 4)]
        layout += [(n, ctypes.c_void_p) for n in names]
        Api = type("RimeApi", (ctypes.Structure,), {"_fields_": layout})
        self.api = ctypes.cast(addr, ctypes.POINTER(Api)).contents
        self.f = {}
        for n in names:
            p = getattr(self.api, n)
            if not p:
                continue
            restype, argtypes = SIGS.get(n, (None, None))
            proto = ctypes.CFUNCTYPE(restype if restype else None, *(argtypes or []))
            self.f[n] = proto(p)

    def has(self, n):
        return n in self.f

    def version(self):
        try:
            gv = self.dll.rime_get_version
            gv.restype = ctypes.c_char_p
            return gv().decode()
        except Exception as e:
            return "?%s" % e

    def call(self, n, *a):
        return self.f[n](*a)


# ---------------------------------------------------------------- 测试步骤
# 造词实验只关心 translator(dictionary: wubi86) 这一条链。
# 但 librime 的 ConfigDependency 会遍历**整份 schema**，凡是键名叫 dictionary 的都当成依赖去
# Dictionary::Require()（schema.cc / config_dependency.cc），于是这四个「互译/英文」命名空间
# 也会在加载时被拉进来。实测：weasel 侧的部署只产出 wubi86/pinyin_simp 的 .table.bin，
# en_word 的没有 ⇒ 加载 wubi_pinyin 时 dictionary.cc:368 报 "Error loading table for
# dictionary 'en_word'"，select_schema 直接返回 0，实验根本进不到造词那一步。
# 鸿蒙真机不受影响（那边 en_word 由 Lua 的 enWord_Filter 提供，H-260(CodeArts) v44），
# 这是**离线 harness 侧的障碍，不是对根因的反证**，所以在副本里剥掉这四段。
EXTRA_DICT_NAMESPACES = ("en_word", "zh2en_wubi", "en2zh_v2", "zh2en_pinyin")


def strip_unused_dict_namespaces(path, also_drop_translator_refs=False):
    """按顶层键剥掉与造词无关的 dictionary 命名空间；只动副本，不动仓库原文件。

    返回 (dropped_blocks, dropped_translator_lines)。
    custom.yaml 里 `engine/translators/+` 挂着 `table_translator@en_word`，
    光剥 schema 的 en_word: 配置块会让它变成 "en_word/dictionary not specified in schema"，
    所以两份副本都要处理。
    """
    lines = open(path, encoding="utf-8").read().split("\n")
    out, dropped, dropped_lines, i = [], [], [], 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", ln)
        if m and m.group(1) in EXTRA_DICT_NAMESPACES:
            dropped.append(m.group(1))
            i += 1
            while i < len(lines) and (lines[i][:1] in (" ", "\t") or not lines[i].strip()):
                i += 1
            continue
        if also_drop_translator_refs and not ln.lstrip().startswith("#"):
            if any(re.search(r"(?:translator|filter)@" + ns + r"\s*(?:#.*)?$", ln)
                   for ns in EXTRA_DICT_NAMESPACES):
                dropped_lines.append(ln.strip()[:60])
                i += 1
                continue
        out.append(ln)
        i += 1
    open(path, "w", encoding="utf-8").write("\n".join(out))
    return dropped, dropped_lines


def make_shared(variant_dir, dict_src):
    shutil.copytree(RAWMEDIR, variant_dir, symlinks=False, ignore=shutil.ignore_patterns("build"))
    shutil.copyfile(dict_src, os.path.join(variant_dir, "wubi86.dict.yaml"))
    note = []
    for fn, with_refs in (("wubi_pinyin.schema.yaml", False),
                          ("wubi_pinyin.custom.yaml", True)):
        p = os.path.join(variant_dir, fn)
        if not os.path.exists(p):
            continue
        blocks, refs = strip_unused_dict_namespaces(p, with_refs)
        if blocks:
            note.append("%s 剥块[%s]" % (fn, ",".join(blocks)))
        if refs:
            note.append("%s 剥行[%s]" % (fn, ";".join(refs)))
    print("  [harness] 副本里剥掉的非造词词典引用: %s" % (" | ".join(note) or "无"))
    # H-279(Qoder) 判定用改动：userdb(LevelDB) 里的键是二进制 syllable graph，人读不出编码；
    # 换成 tabledb 后，RimeFinalize 会把用户词落成纯文本 `user.txt`（word<TAB>code<TAB>freq），
    # 于是「引擎到底给 行不行 编出了什么码」直接可见。真机仍是 userdb，不影响结论。
    sp = os.path.join(variant_dir, "wubi_pinyin.schema.yaml")
    body = open(sp, encoding="utf-8").read()
    if "db_class: userdb" in body:
        open(sp, "w", encoding="utf-8").write(body.replace("db_class: userdb", "db_class: tabledb"))
        print("  [harness] 副本 translator/db_class: userdb -> tabledb（只为了能读 user.txt 里的编码）")
    return variant_dir


def type_keys(r, sid, s):
    for ch in s:
        r.call("process_key", sid, ord(ch), 0)


def candidates(r, sid):
    ctx = RimeContext()
    ctx.data_size = ctypes.sizeof(RimeContext)
    out = []
    if r.call("get_context", sid, ctypes.byref(ctx)):
        n = ctx.menu.num_candidates
        for i in range(n):
            c = ctx.menu.candidates[i]
            out.append((c.text.decode("utf-8", "replace"),
                        (c.comment or b"").decode("utf-8", "replace")))
    r.call("free_context", ctypes.byref(ctx))
    return out


def preedit(r, sid):
    """当前输入串 —— 用来证明按键确实进了引擎，而不是 candidates() 空列表被误读成「没造出词」。"""
    ctx = RimeContext()
    ctx.data_size = ctypes.sizeof(RimeContext)
    s = ""
    if r.call("get_context", sid, ctypes.byref(ctx)):
        s = (ctx.composition.preedit or b"").decode("utf-8", "replace")
    r.call("free_context", ctypes.byref(ctx))
    return s


def drain_commit(r, sid):
    cm = RimeCommit()
    cm.data_size = ctypes.sizeof(RimeCommit)
    got = ""
    if r.call("get_commit", sid, ctypes.byref(cm)):
        got = (cm.text or b"").decode("utf-8", "replace")
    r.call("free_commit", ctypes.byref(cm))
    return got


def commit_char(r, sid, code, want):
    """打 code，选出文本正好等于 want 的候选并上屏；返回是否成功。"""
    type_keys(r, sid, code)
    cands = candidates(r, sid)
    idx = next((i for i, (t, _) in enumerate(cands) if t == want), None)
    if idx is None:
        return False, cands
    ok = r.call("select_candidate_on_current_page", sid, idx)
    committed = drain_commit(r, sid)
    return bool(ok) and committed == want, cands


def boot(tag, shared, user, logd, full_check):
    """起一次引擎；返回 Rime。finalize 之后可以再 boot 一次（和桌面端退出/重启同路径）。"""
    r = Rime(DLL_DIR)
    tr = RimeTraits()
    tr.data_size = ctypes.sizeof(RimeTraits)
    tr.shared_data_dir = shared.encode()
    tr.user_data_dir = user.encode()
    tr.distribution_name = b"HS279AB"
    tr.distribution_code_name = b"h279ab"
    tr.distribution_version = b"0.0.1"
    tr.app_name = ("rime.h279ab_" + tag).encode()
    tr.modules = None
    tr.min_log_level = 0
    tr.log_dir = logd.encode()
    tr.prebuilt_data_dir = None
    tr.staging_dir = None
    r.call("setup", ctypes.byref(tr))
    r.call("initialize")
    r.call("start_maintenance", full_check)
    r.call("join_maintenance_thread")
    return r


ENC_PREFIX = "\x7fenc\x1f"   # unity_table_encoder.cc:16 kEncodedPrefix，造词写进用户库时的键前缀


def read_user_txt(user_dir):
    """tabledb 在 RimeFinalize 时把用户词写成纯文本 word<TAB>key<TAB>freq。

    key 以 "\\x7fenc\\x1f" 开头的是**引擎自己造出来的词**（CreateEntry 里加了 kEncodedPrefix），
    去掉前缀剩下的就是这次实验要的「编码到底生成了什么码」。
    返回 (文件列表, [(文件, 词, 解码后的码, 原始列, freq), ...])。
    """
    files, entries = [], []
    for dp, _, fns in os.walk(user_dir):
        for fn in fns:
            if not fn.endswith(".txt"):
                continue
            p = os.path.join(dp, fn)
            try:
                txt = open(p, encoding="utf-8", errors="replace").read().splitlines()
            except OSError:
                continue
            if not (txt and txt[0].startswith("#") and any("\t" in l for l in txt[1:6])):
                continue
            files.append(p)
            for l in txt:
                f = l.split("\t")
                if len(f) < 3:
                    continue
                entries.append((os.path.relpath(p, user_dir), f[0],
                                f[1][len(ENC_PREFIX):] if f[1].startswith(ENC_PREFIX) else f[1],
                                "ENC" if f[1].startswith(ENC_PREFIX) else "raw", f[2]))
    return files, entries


def run_variant(tag, dict_src, root):
    shared = make_shared(os.path.join(root, "shared-" + tag), dict_src)
    user = os.path.join(root, "user-" + tag)
    os.makedirs(user, exist_ok=True)
    logd = os.path.join(root, "log-" + tag)
    os.makedirs(logd, exist_ok=True)

    rep = {"tag": tag, "steps": []}
    r = boot(tag, shared, user, logd, 1)
    rep["librime"] = r.version()

    sid = r.call("create_session")
    sel = r.call("select_schema", sid, SCHEMA.encode())
    rep["steps"].append("create_session=%s find_session=%s select_schema(%s)=%d"
                        % (sid, r.call("find_session", sid) if r.has("find_session") else "?",
                           SCHEMA, sel))
    if sel and r.has("get_current_schema"):
        buf = ctypes.create_string_buffer(128)
        if r.call("get_current_schema", sid, buf, 128):
            rep["steps"].append("current_schema=%s" % buf.value.decode())
    if not sel:
        import glob as _g
        for lp in sorted(_g.glob(os.path.join(logd, "*INFO*")))[-1:]:
            txt = open(lp, encoding="utf-8", errors="replace").read().splitlines()
            print("---- FULL log tail (%s) ----" % os.path.basename(lp))
            for l in txt[-45:]:
                print("  ", l[:220])
        print("---- build dir ----")
        bd = os.path.join(user, "build")
        print("  ", sorted(os.listdir(bd)) if os.path.isdir(bd) else "no build dir")
        # 部署产物里的 schema 才是真正的加载对象（AGENTS.md 规则 11：取证看引擎实际加载的东西）
        bs = os.path.join(bd, SCHEMA + ".schema.yaml")
        if os.path.exists(bs):
            body = open(bs, encoding="utf-8", errors="replace").read()
            print("---- built schema: translators/dictionary keys ----")
            for l in body.splitlines():
                if re.match(r"^\s*(- )?(table_translator|script_translator|[a-z_]+/dictionary|dictionary:)", l) \
                        or "translator" in l:
                    print("  ", l[:160])
    # 关掉句子合成，让「tgtf 出行不行」只能是造词的结果（enable_sentence 是现拼，会污染判定）
    r.call("set_option", sid, "enable_sentence".encode(), 0)
    rep["steps"].append("set_option enable_sentence=0 (判定用，发布配置仍是 1)")

    learn = []
    for code, want in (("tf", "行"), ("gi", "不"), ("tf", "行")):
        ok, cands = commit_char(r, sid, code, want)
        learn.append("%s->%s:%s" % (code, want, "OK" if ok else "FAIL(%s)" %
                                    ",".join(t for t, _ in cands[:5])))
    rep["steps"].append("分别上屏 " + " / ".join(learn))
    r.call("sync_user_data")
    r.call("destroy_session", sid)

    # 阶段 1 收尾：finalize ⇒ tabledb 的 Close()/SaveToFile() ⇒ 用户词写成纯文本
    r.call("sync_user_data")
    r.call("destroy_session", sid)
    r.call("finalize")

    files, entries = read_user_txt(user)
    learned = sorted({c for _, w, c, kind, _f in entries if w == "行不行" and kind == "ENC"})
    rep["user_txt_files"] = [os.path.relpath(p, user) for p in files]
    rep["user_行不行_encoded_codes"] = learned
    rep["user_行不行_tgtf"] = "tgtf" in learned
    # 主判据用主人实际打的那个码：tgtf（三字词=第一、二字首码+第三字前两码 ⇒ t+g+t+f）
    code = "tgtf" if rep["user_行不行_tgtf"] else (learned[0] if learned else None)
    rep["encoded_code"] = code or "(引擎没给 行不行 造出任何码)"

    # 阶段 2：重新启动引擎。finalize 把内存态（commit_history、现拼结果）全部销毁，
    # 所以这一步能出「行不行」，只可能是从落盘的用户词库读出来的 —— 也就是「记住了」。
    r2 = boot(tag + "-p2", shared, user, logd, 0)
    sid = r2.call("create_session")
    sel = r2.call("select_schema", sid, SCHEMA.encode())
    r2.call("set_option", sid, "enable_sentence".encode(), 0)
    rep["steps"].append("phase2 create_session=%s select_schema=%d" % (sid, sel))
    probes = ["tgtf"]
    for c in learned:
        if c not in probes and len(probes) < 3:
            probes.append(c)
    hits = {}
    for probe in probes:
        if r2.has("clear_composition"):
            r2.call("clear_composition", sid)
        type_keys(r2, sid, probe)
        cands = candidates(r2, sid)
        hit = next((i for i, (t, _) in enumerate(cands) if t == "行不行"), None)
        if hit is not None:
            hits[probe] = hit
        rep["probe_%s" % probe] = {
            "preedit": preedit(r2, sid),
            "n_candidates": len(cands),
            "行不行": ("命中，第 %d 位，comment=%r" % (hit, cands[hit][1])) if hit is not None else "未命中",
            "top": " | ".join("%s%s" % (t, ("(%s)" % c if c else "")) for t, c in cands[:6]),
        }
    r2.call("sync_user_data")
    r2.call("destroy_session", sid)
    r2.call("finalize")

    if "tgtf" in hits:
        rep["verdict_能造出并记住"] = "PASS：打 tgtf ⇒ 重开引擎后第 %d 位出「行不行」" % hits["tgtf"]
    elif hits:
        rep["verdict_能造出并记住"] = "PART：造出词了但码不是 tgtf（命中的是 %s）" % list(hits)
    else:
        rep["verdict_能造出并记住"] = "FAIL：重开引擎后打「%s」都出不了「行不行」" % "/".join(probes)

    # 用户词库落盘证据（真机用 userdb=LevelDB，这里按字节找词形；离线副本已换 tabledb 故常为 0 字节）
    blob = b""
    for dp, _, fns in os.walk(user):
        for fn in fns:
            if ".user." in fn or fn.endswith((".ldb", ".log")):
                try:
                    blob += open(os.path.join(dp, fn), "rb").read()
                except OSError:
                    pass
    rep["userdb_has_行不行"] = "行不行".encode() in blob
    rep["userdb_bytes"] = len(blob)
    return rep


DLL_DIR = None
EVIDENCE = REPO + "/docs/evidence/2026-10-30/h279-dict"
VARIANTS = {"A": ("A-old-dict", OLD_DICT), "B": ("B-fixed-dict", NEW_DICT)}


def print_rep(rep):
    for k, v in rep.items():
        if k == "steps":
            for s in v:
                print("   -", s)
        elif isinstance(v, dict):
            print("  %s:" % k)
            for kk, vv in v.items():
                print("      %s: %s" % (kk, vv))
        elif isinstance(v, list):
            print("  %s: %s" % (k, " | ".join(str(x) for x in v) if len(v) <= 12
                                else "%d 项: %s ..." % (len(v), v[:6])))
        else:
            print("  %s: %s" % (k, v))


def find_dll():
    global DLL_DIR
    for d in DLLS:
        if os.path.exists(os.path.join(d, "rime.dll")):
            DLL_DIR = d
            return True
    return False


def json_path(tag):
    return os.path.join(EVIDENCE, "encoder-ab-%s.json" % tag)


def worker(which):
    """一个进程只跑一个变体：同一进程里第二次 initialize 会在 rime.dll 里踩空指针
    （实测 access violation reading 0x...40，AGENTS.md 规则 11 要求把这种判据写清楚）。"""
    if not find_dll():
        print("找不到 rime.dll"); return 2
    tag, src = VARIANTS[which]
    print("engine dir:", DLL_DIR)
    root = tempfile.mkdtemp(prefix="h279ab-")
    print("workdir:", root)
    print("\n=== %s (%s) ===" % (tag, src))
    try:
        rep = run_variant(tag, src, root)
    except Exception as e:
        import traceback
        traceback.print_exc()
        rep = {"tag": tag, "error": repr(e)}
    rep["dict_md5"] = _md5(src)
    rep["dict_bytes"] = os.path.getsize(src)
    print_rep(rep)
    import json
    with open(json_path(tag), "w", encoding="utf-8") as fp:
        json.dump(rep, fp, ensure_ascii=False, indent=2)
    print("wrote", json_path(tag))
    return 0


def _md5(p):
    import hashlib
    h = hashlib.md5()
    with open(p, "rb") as fp:
        for blk in iter(lambda: fp.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def orchestrator():
    """AB：把两个变体各自起一个子进程跑，再把两份 JSON 合成对照表。"""
    import json
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    reps = []
    for which in ("A", "B"):
        tag = VARIANTS[which][0]
        out = os.path.join(EVIDENCE, "encoder-ab-%s.stdout.log" % tag)
        err = os.path.join(EVIDENCE, "encoder-ab-%s.stderr.log" % tag)
        with open(out, "wb") as fo, open(err, "wb") as fe:
            rc = subprocess.call([sys.executable, os.path.abspath(__file__), which],
                                 env=env, stdout=fo, stderr=fe)
        print("[%s] rc=%d  (%s / %s)" % (tag, rc, os.path.basename(out), os.path.basename(err)))
        try:
            reps.append(json.load(open(json_path(tag), encoding="utf-8")))
        except (OSError, ValueError) as e:
            reps.append({"tag": tag, "error": "子进程没写出 JSON: %r" % e})
    for rep in reps:
        print("\n=== %s (dict %s B, md5 %s) ===" % (rep.get("tag"), rep.get("dict_bytes"),
                                                    rep.get("dict_md5")))
        print_rep(rep)
    a, b = reps

    def tgtf_hit(rep):
        """判据＝主人那一下：打 tgtf 能不能出「行不行」。A 组也会造词，但造出来的是一堆
        从错误 stem 推出来的码（hgha/hgtf/…），tgtf 上根本没有 —— 所以不能只看「库里有没有词」。"""
        return str((rep.get("probe_tgtf") or {}).get("行不行", "")).startswith("命中")

    print("=" * 68)
    print("对照判定（丢掉的第 4 列 stem 是不是 自造词 的根因）")
    print("  A 坏词库（25 行有 stem） : %s" % a.get("verdict_能造出并记住", a.get("error")))
    print("  B 修好的词库（20935 行） : %s" % b.get("verdict_能造出并记住", b.get("error")))
    print("  A 给 行不行 造出的码: %s" % a.get("user_行不行_encoded_codes"))
    print("  B 给 行不行 造出的码: %s" % b.get("user_行不行_encoded_codes"))
    if not tgtf_hit(a) and tgtf_hit(b):
        print("  ⇒ 只有 B 打 tgtf 出词：根因成立 —— 丢的确实是第 4 列 stem，补回来造词链就通")
    elif tgtf_hit(a):
        print("  ⇒ A 也打 tgtf 出词：本实验证伪了根因，得回查 enable_sentence 现拼 / UI 触发")
    else:
        print("  ⇒ 两边都不出：Windows 侧 librime 与鸿蒙行为有差，本实验只能当参考，结论以真机为准")
    merged = os.path.join(EVIDENCE, "encoder-ab-offline.json")
    with open(merged, "w", encoding="utf-8") as fp:
        json.dump(reps, fp, ensure_ascii=False, indent=2)
    print("wrote", merged)
    return 0


def main():
    which = (sys.argv[1] if len(sys.argv) > 1 else "AB").upper()
    if which in VARIANTS:
        return worker(which)
    return orchestrator()


if __name__ == "__main__":
    sys.exit(main())
