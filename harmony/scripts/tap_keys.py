"""从 uitest dumpLayout 的 JSON 里找出键盘按键的真实坐标与标签。

用法：
    python scripts/tap_keys.py dump.json n i h a o     # 依次点这 5 个键
    python scripts/tap_keys.py dump.json --list        # 只列出所有可点元素

为什么需要它：键盘高度会随候选栏内容变化（L1 是否显示、候选几行），
硬编码坐标必然点偏——我按固定 y 点，结果打出的是 `jiha ui o` 而不是 `nihao`。
`uitest dumpLayout` 给的是**当前**每个节点的 bounds 与 text/description，
用它反查坐标才是稳的。
"""
import json
import re
import subprocess
import sys

HDC = r"D:\DevTools\DevEco\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"
LAY = "/data/local/tmp/lay.json"
LOCAL = "tmp-live-layout.json"


def sh(*args):
    env_prefix = ["env", "MSYS2_ARG_CONV_EXCL=*"]
    r = subprocess.run(env_prefix + [HDC] + list(args), capture_output=True)
    return (r.stdout or b"") + (r.stderr or b"")


def refresh():
    sh("shell", "uitest dumpLayout -p", LAY)
    r = subprocess.run(
        ["env", "MSYS2_ARG_CONV_EXCL=*", HDC, "file", "recv", LAY, LOCAL],
        capture_output=True)
    with open(LOCAL, "rb") as f:
        return json.loads(f.read().decode("utf-8", "replace"))


def walk(node, out):
    a = node.get("attributes", {})
    b = a.get("bounds", "")
    m = re.match(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]", b or "")
    if m:
        x1, y1, x2, y2 = map(int, m.groups())
        out.append({
            "text": a.get("text", ""),
            "desc": a.get("description", ""),
            "clickable": a.get("clickable", ""),
            "cx": (x1 + x2) // 2,
            "cy": (y1 + y2) // 2,
            "box": b,
        })
    for c in node.get("children", []) or []:
        walk(c, out)
    return out


def key_pool(dump):
    """只取键盘区（屏幕下半 40%）的可点元素。"""
    nodes = walk(dump, [])
    out = []
    for n in nodes:
        if n["cy"] < 1700:
            continue
        label = (n["text"] or n["desc"] or "").strip()
        if not label:
            continue
        out.append(n)
    return out



OURS = "com.sansheng.ime"
FOREIGN = ("百度", "du", "小艺", "讯飞", "搜狗", "微信", "搜狗", "sogou", "baidu", "iflytek")


def is_ours(proc):
    """进程名判定：输入法扩展进程叫 com.sansheng.ime:inputMethod，主进程叫包名本身。"""
    return proc == OURS or proc.startswith(OURS + ":")


def panel_owner():
    """屏上键盘面板窗口（softKeyboard*）的属主包名。纯读，不点屏。

    为什么必须有这一步（H-116）：`uitest dumpLayout` 取不到我们输入法窗口的子节点
    ——00:53 实测宿主是记事本时，默认 dump 只回到记事本窗口（可点元素 3 个），
    `-m false` 里我们的面板窗口只剩一个没有子节点的 WindowScene 根。于是 probe()
    的「单字母键 <20」把「面板就是三生的」误判成「键盘没弹出」。窗口属主 + 进程名
    是独立于节点树的证据：hidumper 给窗口 pid，`ps -p` 给进程名。
    返回 [(窗口名, 包名, 矩形)]，取不到时为空表。
    """
    txt = sh("shell", 'hidumper -s WindowManagerService -a "-a"').decode("utf-8", "replace")
    wins = []
    for line in txt.splitlines():
        cols = line.split()
        if not cols or not cols[0].startswith("softKeyboard"):
            continue
        pid = cols[2] if len(cols) > 2 else ""
        rect = ""
        i = line.find("[")
        if i >= 0:
            rect = " ".join(line[i:].split("]")[0].split())
        wins.append((cols[0], pid, rect))
    out = []
    for name, pid, rect in wins:
        ps = sh("shell", "ps -p %s -f" % pid).decode("utf-8", "replace").splitlines()
        bundle = ps[-1].split()[-1] if ps else "?"
        out.append((name, bundle, rect))
    return out


def probe(dump):
    """判定当前屏上能不能按「我们的键位」自动点击。返回 (ok, 说明)。

    注意它只看节点树，判不了「面板是谁的」——那由 panel_owner() 负责。
    """
    pool = key_pool(dump)
    letters = sum(1 for n in pool if re.fullmatch(r"[a-z]", (n["text"] or "").strip()))
    labels = " ".join((n["text"] or "") + (n["desc"] or "") for n in pool)
    foreign = sorted({f for f in set(FOREIGN) if f and f.lower() in labels.lower()})
    has_paging = "?123" in labels or "123" in labels
    info = "可点元素 %d 个 / 单字母键 %d 个 / 数字切换键 %s / 他牌标记 %s" % (
        len(pool), letters, "有" if has_paging else "无", foreign or "无")
    if letters < 20:
        return False, ("节点树里没有 26 键面板 —— 当前停在符号/数字页，"
                       "或 dumpLayout 取不到输入法窗口的子节点（H-116）。"
                       "此时不要盲点坐标。") + info
    if foreign:
        return False, "屏上面板带他牌输入法标记 %s ⇒ 默认输入法不是三生（H-086）。" % "/".join(foreign) + " " + info
    return True, info


def main():
    args = sys.argv[1:]
    dump = refresh()
    pool = key_pool(dump)
    wins = panel_owner()
    ours = [w for w in wins if is_ours(w[1])]
    if not wins:
        h086 = False
        print("[闸门] 面板属主: 屏上没有 softKeyboard 窗口 ⇒ 键盘未弹出【不可测】")
    elif ours:
        h086 = True
        print("[闸门] 面板属主: 三生（%s）⇒ 默认输入法是我们【可测】"
              % "; ".join("%s %s" % (w[0], w[2]) for w in ours))
    else:
        h086 = False
        print("[闸门] 面板属主: %s ⇒ 不是三生（H-086）【不可测】"
              % "; ".join("%s=%s" % (w[0], w[1]) for w in wins))
    ok, why = probe(dump)
    print("[闸门] 节点取键（自动点击用）: %s —— %s" % ("可用" if ok else "不可用", why))
    if "--check" in args:
        return 0 if h086 else 2
    if not (h086 and ok):
        print("拒绝点击：需同时满足 ① 面板属主是三生（H-086）② 节点树取到 26 键。"
              "②取不到时（见 H-116）改由主人手点 + 截图验收，不要盲点坐标。")
        return 2
    if "--list" in args:
        for n in pool:
            print("%-28s (%4d,%4d) %s" % (n["text"][:28], n["cx"], n["cy"], n["box"]))
        return 0

    wanted = [a.lower() for a in args if not a.startswith("-")]
    for w in wanted:
        hit = None
        for n in pool:
            t = (n["text"] or "").strip().lower()
            d = (n["desc"] or "").strip().lower()
            if t == w or d == w or (len(w) > 1 and w in d):
                hit = n
                break
        if not hit:
            print("NOT FOUND:", w)
            return 1
        sh("shell", "uitest uiInput click %d %d" % (hit["cx"], hit["cy"]))
        print("tapped %-6s at (%d,%d)" % (w, hit["cx"], hit["cy"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())