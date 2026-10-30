#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三生输入法 · rawfile Rime 数据本地校验（M3 教训）

为什么要它：真机部署失败时，librime 的报错只写在进程的 glog/stderr 里，
HAP 进程的 stderr 进不了 hilog——上一次 default.yaml 第 63 行
`"\\": "\\\\"`（双引号里 `\"` 是转义引号，YAML 直接解析失败）
导致三个方案全部 build 失败、候选全空，我在 Mate 80 上跑了两轮才把日志捞出来。
这类错误在本地 0.1 秒就能查出来，不该占真机时间。

用法：
  python scripts/check_rime_yaml.py [目录，默认 entry/src/main/resources/rawfile/rime]

分两种口径，和 librime 自己一致：
  - 配置类（schema / custom / default / *.example.yaml）：整个文件必须是合法 YAML；
  - 词库类（*.dict.yaml）：只有 `...` 之前的头部是 YAML，头之后是 TSV，
    用 YAML 口径去解析 TSV 会误报「tab 不能起始 token」。

退出码：0 = 全部通过；1 = 有文件解析失败（打印文件、行列与原因）。
"""
import io
import os
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("需要 PyYAML：pip install pyyaml\n")
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Windows 控制台默认 gbk，报错行里的 CJK 文件名/提示语会直接抛 UnicodeEncodeError，
# 把诊断信息吞掉。统一切到 utf-8（打不出的字符替换成 ?），保证取证时看得见。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DEFAULT_DIR = os.path.join(ROOT, "entry", "src", "main", "resources", "rawfile", "rime")

# 这些后缀走「全文 YAML」口径
CONFIG_SUFFIX = (".schema.yaml", ".custom.yaml", ".yaml")


def split_dict_header(text):
    """词库文件：返回 `...` 分隔线之前的头部；没有分隔线则整个文件当头部。"""
    lines = []
    for line in text.split("\n"):
        if line.strip() == "...":
            break
        lines.append(line)
    return "\n".join(lines) + "\n"


def check_file(path):
    with io.open(path, encoding="utf-8-sig") as fh:
        text = fh.read()
    name = os.path.basename(path)
    if name.endswith(".dict.yaml"):
        text = split_dict_header(text)
    try:
        list(yaml.safe_load_all(text))
    except Exception as exc:  # noqa: BLE001 - 要把原始解析错误报给开发者
        return "FAIL %s: %s" % (name, str(exc).replace("\n", " / "))
    return None


def load_text(path):
    with io.open(path, encoding="utf-8-sig") as fh:
        text = fh.read()
    if os.path.basename(path).endswith(".dict.yaml"):
        text = split_dict_header(text)
    return text


def find_imports(node, trail=()):
    """递归找 {import_preset: <name>} 这种小节，返回 (小节名, 预设名) 列表。
    librime 的 legacy_preset_config_plugin 会按「本节的键名」去预设文件里取同名小节，
    取不到就报 "failed to include section default:recognizer"。"""
    out = []
    if isinstance(node, dict):
        if "import_preset" in node and isinstance(node["import_preset"], str):
            section = trail[-1] if trail else "(root)"
            out.append((section, node["import_preset"]))
        for key, value in node.items():
            out.extend(find_imports(value, trail + (key,)))
    elif isinstance(node, list):
        for item in node:
            out.extend(find_imports(item, trail))
    return out


def check_preset_sections(target):
    """第二道校验：所有 `import_preset: X` 引用的 section 在 X.yaml 里必须真的存在。
    M3 真机教训：鸿蒙版 default.yaml 是我手写的，只写了 key_binder/punctuator，
    三个 schema 都 `recognizer: import_preset: default`，于是
    default:recognizer 取不到 → 方案配置编译失败 → build/ 里只有 default.yaml、
    没有任何 prism/table .bin → 引擎选中方案成功但每次按键 0 候选。
    这条规则在本地 0.1 秒就能查出来，不该占真机时间。"""
    problems = []
    presets = {}
    files = []
    for dirpath, _dirnames, filenames in os.walk(target):
        for fn in sorted(filenames):
            if fn.endswith(CONFIG_SUFFIX):
                files.append(os.path.join(dirpath, fn))
    for path in files:
        name = os.path.basename(path)
        if name.endswith(".schema.yaml") or name.endswith(".custom.yaml"):
            continue
        try:
            doc = yaml.safe_load(load_text(path))
        except Exception:  # noqa: BLE001 - 解析失败由 check_file 报，这里跳过
            continue
        if isinstance(doc, dict):
            presets[name[:-5]] = set(doc.keys())  # default.yaml -> key "default"
    for path in files:
        name = os.path.basename(path)
        if not (name.endswith(".schema.yaml") or name.endswith(".custom.yaml")):
            continue
        try:
            doc = yaml.safe_load(load_text(path))
        except Exception:  # noqa: BLE001
            continue
        for section, preset in find_imports(doc):
            keys = presets.get(preset)
            if keys is None:
                problems.append("FAIL %s: %s 引用 import_preset: %s，但 %s.yaml 没打进 rawfile"
                                % (name, section, preset, preset))
            elif section not in keys:
                problems.append("FAIL %s: %s 引用 import_preset: %s，但 %s.yaml 里没有 %s 小节"
                                % (name, section, preset, preset, section))
    return problems


def check_backslash_mapping(target):
    """D-023／M-140：半角反斜杠必须出半角反斜杠，不能是顿号。

    背景：14:1x 实测 `default.yaml` 的 `punctuator.half_shape` 里 `'\': '、'`
    ⇒ 半角反斜杠打成顿号，路径/命令没法输入。主人四天没回这道选择题，我按
    「能过审怎么来」定死（D-023）并派 M-140 给 CodeArts。
    这条断言让「他改对没有」变成一条命令，不用人翻 YAML。

    14:2x 修过一个真 bug：第一版调用不存在的 `load_config()`，被
    `except Exception: continue` 吞掉 ⇒ 对当前坏状态**静默放过**（判据等于没有）。
    现在只用本文件里真实存在的 `load_text` + `yaml`，并且**不再吞异常**。
    """
    out = []
    for dirpath, _d, filenames in os.walk(target):
        for fn in sorted(filenames):
            if not fn.endswith(CONFIG_SUFFIX):
                continue
            fp = os.path.join(dirpath, fn)
            text = load_text(fp)
            try:
                docs = list(yaml.safe_load_all(text))
            except Exception:
                continue          # 解析失败由 check_file 报，不在这里重复
            for data in docs:
                if not isinstance(data, dict):
                    continue
                punct = data.get("punctuator") or {}
                if not isinstance(punct, dict):
                    continue
                hs = punct.get("half_shape") or {}
                if not isinstance(hs, dict):
                    continue
                if "\\" not in hs:
                    continue      # 这个文件没定义反斜杠映射，不关它事
                v = hs["\\"]
                first = v[0] if isinstance(v, list) and v else v
                if first != "\\":
                    out.append(u"[半角反斜杠] %s：punctuator.half_shape 里反斜杠映射 = %r "
                               u"⇒ 半角反斜杠会打成 %r，应为反斜杠本身（D-023／M-140）"
                               % (os.path.relpath(fp, target), v, first))
    return out


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    bad = []
    total = 0
    for dirpath, _dirnames, filenames in os.walk(target):
        for fn in sorted(filenames):
            if not fn.endswith(CONFIG_SUFFIX):
                continue
            total += 1
            result = check_file(os.path.join(dirpath, fn))
            if result:
                bad.append(result)
    bad.extend(check_preset_sections(target))
    bad.extend(check_backslash_mapping(target))
    print("checked %d yaml file(s) under %s" % (total, target))
    for line in bad:
        print(line)
    if bad:
        print("=> %d 个问题，别装机，先修数据" % len(bad))
        return 1
    print("=> all parse OK (含 import_preset 小节交叉校验)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
