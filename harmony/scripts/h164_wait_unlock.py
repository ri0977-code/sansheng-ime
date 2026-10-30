#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-164 解锁守候 + 自动取证（Qoder，2026-10-25 09:11 实测版）

为什么写：主人 2026-10-25 00:5x 的原话是「你自己可以做到真机验证的，自己做」，
而九条判据里唯一卡住的是**手机还锁着**（00:15–09:09 一直锁屏，我不猜密码、不叫醒主人）。
本脚本把「等解锁」这件事交给机器：每 <interval> 秒探一次锁屏窗口，解锁后且**桌面空闲**
（没有第三方应用在前台）才动手，按 `h164_device_accept.py` 的 12 步一条龙自动取证。

锁屏判定用系统自证，不靠截图肉眼看：
    hidumper -s WindowManagerService -a '-a'   → 找到 SCBScreenLock 的 WinId
    hidumper -s WindowManagerService -a '-w <WinId>' → IsVisible: true/false
（2026-10-25 09:10 锁屏实拍：SCBScreenLock12 WinId=15 IsVisible=true。解锁后同窗口应为 false。）

安全闸（每次注入前都重新判，不靠一次判断走全程）：
  ① 必须仍解锁；
  ② 必须仍有本应用（com.sansheng.ime）的可见窗口——pid 取自 `pidof`，与 WMS 行上的 Pid 对齐。
     任一不成立就中止，绝不在别人的应用/主人生效文档里乱点。打字只落在本应用页面自带的试打框。

用法：
    python scripts/h164_wait_unlock.py probe                 # 探一次：locked / unlocked-idle / unlocked-busy
    python scripts/h164_wait_unlock.py wait --minutes 300    # 守候（默认 45 秒一探，不注入）
    python scripts/h164_wait_unlock.py wait --minutes 300 --run   # 守候 + 解锁空闲即自动跑一条龙
    python scripts/h164_wait_unlock.py run                   # 现在就跑一条龙（要求当前已解锁且桌面空闲）
    python scripts/h164_wait_unlock.py run --dry-run         # 只打印将执行的 hdc 命令

产出（都在 docs/evidence/2026-10-25/h164-candidate-scroll/）：
    wait-unlock.log     守候/运行时间线（含每次判定依据）
    a0/a1/b1–b9/c1/c2/d1/e1/e2/f1/f2.jpeg   判据截图
    h164_lay.json / h164_cands.json         当轮布局与候选坐标（tapcand 用）
    h164-hilog.txt + h164-log-check.txt     判据③⑦ 的原始日志与检查器结论
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h164_device_accept as acc  # noqa: E402  （复用 hdc 封装/坐标表/截图/布局解析）

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

EVID = acc.EVID
LOG = os.path.join(EVID, "wait-unlock.log")


def log(msg):
    os.makedirs(EVID, exist_ok=True)
    line = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _wms_all():
    return acc.sh("shell", "hidumper -s WindowManagerService -a '-a'")


# 行样本（2026-10-25 09:10 实拍）：
# SCBScreenLock12      0         3470    15    2110 1    0    2000 0           [ 0    0    1280 2832 ] ...
_WIN_RE = __import__("re").compile(
    r"^(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(\d+)\s+"
    r"\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]")


def windows(text=None):
    """把 WMS 全量 dump 解析成窗口列表。

    可见性用 ZOrd 代理：隐藏窗口在 dump 里 ZOrd=-1（2026-10-25 09:10 实拍，31 个后台窗口全 -1）；
    锁屏窗口自身另有 IsVisible，由 locked() 单查。text 参数只为离线自测。
    """
    out = []
    for ln in (text if text is not None else _wms_all()).splitlines():
        m = _WIN_RE.match(ln)
        if not m:
            continue
        name, disp, pid, wid, typ, mode, flag, zord, ori, x, y, w, h = m.groups()
        out.append({"name": name, "pid": int(pid), "winId": int(wid), "type": int(typ),
                    "zord": int(zord), "rect": [int(x), int(y), int(w), int(h)]})
    return out


def locked():
    """True=锁屏 / False=已解锁 / None=查不到（不猜，按未知处理）。"""
    wins = windows()
    lock = [w for w in wins if w["name"].startswith("SCBScreenLock")]
    if not lock:
        return None, "WMS 里没有 SCBScreenLock 窗口"
    wid = lock[0]["winId"]
    txt = acc.sh("shell", "hidumper -s WindowManagerService -a '-w %d'" % wid)
    for ln in txt.splitlines():
        if ln.startswith("IsVisible:"):
            return ln.split(":", 1)[1].strip().lower() == "true", "SCBScreenLock WinId=%d %s" % (wid, ln.strip())
    return None, "SCBScreenLock WinId=%d 没有 IsVisible 行" % wid


def own_pid():
    pid_s = acc.sh("shell", "pidof com.sansheng.ime").strip()
    return int(pid_s) if pid_s.isdigit() else None


def app_visible():
    """本应用是否有可见窗口（判 pid）。键盘未起时进程可能不在 ⇒ 返回 False，别误判。"""
    pid = own_pid()
    if pid is None:
        return False, "pidof 无输出"
    hit = [w for w in windows() if w["pid"] == pid and w["zord"] != -1]
    return bool(hit), "pid=%d 可见窗口 %d 个%s" % (pid, len(hit), ("（%s）" % hit[0]["name"]) if hit else "")


def third_party_visible(text=None, own=None):
    """桌面空闲判定：有 Type=1（应用窗）且可见、且**不是我们自己** ⇒ 主人在用别的应用，别抢前台。

    必须排除自己：runbook 第 3 步 `aa start` 把本应用拉到前台后，若把自家 Type=1 窗算成「忙」，
    一次中途流产就再也不会重试（2026-10-25 09:2x 自查）。
    """
    if own is None and text is None:
        own = own_pid()
    ws = windows(text)
    return [w for w in ws if w["type"] == 1 and w["zord"] != -1 and w["pid"] != own]


def selftest():
    """用 2026-10-25 09:10 实拍的两行做解析自测（不碰设备）。"""
    fx = (
        "SCBScreenLock12      0         3470    15    2110 1    0    2000 0           [ 0    0    1280 2832 ] [ 0       0       ] [ 1       1       0.5     0.5     ]\n"
        "SCBGestureNavBar14   0         3470    17    2111 1    0    2200 0           [ 0    2734 1280 98   ] [ 0       0       ] [ 1       1       0.5     0.5     ]\n"
        "wechat0              0         7936    198   1    1    0    -1   0           [ 0    0    1280 2832 ] [ 0       0       ] [ 1       1       0.5     0.5     ]\n"
        "WeChatVisible        0         7936    199   1    1    0    5    0           [ 0    0    1280 2832 ] [ 0       0       ] [ 1       1       0.5     0.5     ]\n")
    ws = windows(fx)
    assert len(ws) == 4, ws
    lock = [w for w in ws if w["name"].startswith("SCBScreenLock")][0]
    assert lock["winId"] == 15 and lock["type"] == 2110, lock
    assert len(third_party_visible(fx)) == 1 and third_party_visible(fx)[0]["name"] == "WeChatVisible"
    assert third_party_visible(fx, own=7936) == [], "自家 pid 的 Type=1 窗不该算「忙」"
    assert ws[1]["rect"] == [0, 2734, 1280, 98], ws[1]

    # 前台归属闸的反例＝2026-10-25 09:39 实况：解锁落在主人记事本（notepad0 pid 26402 ZOrd=102），
    # 本应用进程 3470 只在后台（ZOrd=-1）。此时必须判「不是本应用」，否则 find_input_box
    # 会找到记事本正文并往里打字。
    fx2 = (
        "notepad0             0         26402   198   1    1    0    102  0           [ 0    0    1280 2832 ] [ 0       0       ] [ 1       1       0.5     0.5     ]\n"
        "com.sansheng.ime     0         3470    210   1    1    0    -1   0           [ 0    0    1280 2832 ] [ 0       0       ] [ 1       1       0.5     0.5     ]\n")
    ok2, why2 = own_foreground(fx2, pid=3470)
    assert ok2 is False and "notepad0" in why2, (ok2, why2)
    assert own_foreground(fx2, pid=26402)[0] is True, "记事本自己在前台时对它是 True（说明闸看的是 ZOrd 不是有没有窗）"
    assert own_foreground(fx, pid=7936)[0] is True, "WeChatVisible(pid 7936) 在最上层"
    assert own_foreground(fx, pid=3470)[0] is False, "本应用没窗/不在最上层时不该放行"

    # 试打框定位：只认 TextArea/TextInput 或带「试打」的字，且要算中心点
    import tempfile
    layout = {"attributes": {"type": "Column", "text": "", "bounds": "[0,0][1280,2832]"},
              "children": [
                  {"attributes": {"type": "Text", "text": "试一试", "bounds": "[20,1200][300,1260]"},
                   "children": []},
                  {"attributes": {"type": "TextArea", "text": "", "bounds": "[20,1300][1260,1420]"},
                   "children": []}]}
    fd, tmp = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(layout, f, ensure_ascii=False)
        box = find_input_box(tmp)
        assert box and box["type"] == "TextArea" and (box["x"], box["y"]) == (640, 1360), box
        assert layout_has_keyboard(tmp) is False, "应用页不该被当成键盘"
    finally:
        os.unlink(tmp)

    # 键盘证据：底栏字出现才算；只含页面文字（五笔 · 拼音 · 英文）不算
    kb_layout = {"attributes": {"type": "Column", "text": "", "bounds": "[0,0][1280,2832]"},
                 "children": [
                     {"attributes": {"type": "Text", "text": "五笔 · 拼音 · 英文 三向混输",
                                     "bounds": "[0,100][1280,140]"}, "children": []},
                     {"attributes": {"type": "Button", "text": "?123", "bounds": "[40,2560][140,2700]"},
                      "children": []}]}
    fd, tmp = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(kb_layout, f, ensure_ascii=False)
        assert layout_has_keyboard(tmp) is True, "底栏 ?123 没被认出来"
    finally:
        os.unlink(tmp)
    # 候选图测：合成图里画三个词块 + 右端 ▼，必须只量出 3 条且中心对得上（▼ 不算候选）
    from PIL import Image, ImageDraw
    img = Image.new("L", (1280, 2832), 255)
    dr = ImageDraw.Draw(img)
    for x1, x2 in ((55, 176), (265, 394), (482, 539), (1174, 1203)):
        dr.rectangle([x1, acc.CAND_ROWS[0] + 4, x2, acc.CAND_ROWS[1] - 4], fill=0)
    fd, tmp = tempfile.mkstemp(suffix=".jpeg")
    os.close(fd)
    try:
        img.save(tmp, quality=90)
        cs = acc.image_cands(tmp)
        assert len(cs) == 3, cs
        assert [c["x"] for c in cs] == [115, 329, 510], cs
        h1 = acc.band_hash(tmp)
        img.save(tmp, quality=90)
        assert acc.band_hash(tmp) == h1, "同一张图指纹应稳定"
    finally:
        os.unlink(tmp)

    print("SELFTEST OK：4 行解析、锁屏 winId=15、隐藏 wechat 不计、可见 WeChat 计 1、矩形正确、"
          "试打框定位 (640,1360)、键盘证据只认底栏字、前台闸拒记事本(notepad0)放行最上层、"
          "图测候选 3 条且 ▼ 被排除")
    return 0


def keyboard_panel_visible():
    """系统侧证据：WMS 里的 SCBKeyboardPanel（WinId=28，Rect 0,1849,1280,983）。

    2026-10-25 09:16 锁屏实拍：WinId=28 Type=2134 IsVisible: false；键盘升起时应为 true。
    只作**辅助**证据（第三方键盘也会把它点亮），主证据仍是布局里出现本键盘的键。
    """
    panel = [w for w in windows() if w["name"].startswith("SCBKeyboardPanel")]
    if not panel:
        return None
    txt = acc.sh("shell", "hidumper -s WindowManagerService -a '-w %d'" % panel[0]["winId"])
    for ln in txt.splitlines():
        if ln.startswith("IsVisible:"):
            return ln.split(":", 1)[1].strip().lower() == "true"
    return None


KEY_MARKERS = ("?123", "九键")   # 底栏七键里的两枚，只属于键盘、不可能出现在应用页面上


def layout_has_keyboard(layout_path):
    """直接证据：dumpLayout 里出现本键盘底栏的字（?123 / 九键）。

    为什么不再用 pidof：runbook 第 3 步已 `aa start` 拉起应用页，同 bundle 的进程必然存在，
    「pidof 非空 ⇒ 键盘起了」是恒真命题（2026-10-25 09:16 实测：只要页面在跑，进程就在）。
    """
    try:
        with open(layout_path, encoding="utf-8", errors="replace") as f:
            root = json.load(f)
    except Exception:
        return False
    hit = []

    def walk(n):
        if not isinstance(n, dict) or hit:
            return
        a = n.get("attributes") or {}
        if (a.get("text") or "").strip() in KEY_MARKERS:
            hit.append(a.get("text").strip())
        for c in n.get("children") or []:
            walk(c)

    walk(root)
    return bool(hit)


def screen_state():
    txt = acc.sh("shell", "hidumper -s DisplayPowerManagerService -a '-a'")
    for ln in txt.splitlines():
        if "State=" in ln and "Display Id" in ln:
            return ln.strip()
    return "?"


def probe():
    lk, why = locked()
    st = "locked" if lk else ("unlocked" if lk is False else "unknown")
    busy = third_party_visible() if lk is False else []
    print("LOCK %s（%s）" % (st, why))
    print("SCREEN %s" % screen_state())
    print("APP %s" % (app_visible()[1],))
    if lk is False:
        print("BUSY %s" % (("是：" + ", ".join(w["name"] for w in busy)) if busy else "否（桌面空闲）"))
    return lk, busy


def own_foreground(text=None, pid=None):
    """前台是不是本应用：ZOrd 最大（最上层）的可见 Type=1 应用窗必须属于本应用 pid。

    为什么不能只看「本应用有可见窗口」：解锁后前台上次停在主人记事本（notepad0，pid 26402），
    键盘也在，`find_input_box` 会在**记事本正文**里找到输入框并往里打字——2026-10-25 09:39 实测。
    text/pid 两个参数只为离线自测（用 09:39 那组真实 WMS 行当反例）。
    """
    if pid is None:
        pid = own_pid()
    if pid is None:
        return False, "pidof 无输出（本应用未运行）"
    apps = [w for w in windows(text) if w["type"] == 1 and w["zord"] != -1]
    if not apps:
        return False, "没有可见的应用窗"
    top = max(apps, key=lambda w: w["zord"])
    return (top["pid"] == pid,
            "前台 %s pid=%d zord=%d（本应用 pid=%d）" % (top["name"], top["pid"], top["zord"], pid))


def guard(tag):
    """注入前的双闸；返回 True 才允许点/滑/打字。"""
    lk, why = locked()
    if lk is not False:
        log("GUARD-ABORT[%s] 不再解锁：%s" % (tag, why))
        return False
    ok, why2 = own_foreground()
    if not ok:
        log("GUARD-ABORT[%s] 前台不是本应用（绝不在别人窗口里注入）：%s" % (tag, why2))
        return False
    return True


def find_input_box(layout_path):
    """从 dumpLayout 里找本应用页面的试打框（TextArea/TextInput 或占位文字「试打」）。

    为什么不能写死 (640,1600)：那一带可能压着「隐私政策/用户协议」按钮，点错会跳页
    （这条页面的真实布局到 09:15 还没在解锁后量过；宁可先 dump 再点）。
    """
    try:
        with open(layout_path, encoding="utf-8", errors="replace") as f:
            root = json.load(f)
    except Exception:
        return None
    best = None

    def walk(n):
        nonlocal best
        if not isinstance(n, dict):
            return
        a = n.get("attributes") or {}
        typ = a.get("type") or ""
        text = (a.get("text") or "").strip()
        m = re.match(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]", a.get("bounds") or "")
        if m and ("TextArea" in typ or "TextInput" in typ or "试打" in text):
            x1, y1, x2, y2 = (int(v) for v in m.groups())
            if x2 > x1 and y2 > y1:
                best = {"x": (x1 + x2) // 2, "y": (y1 + y2) // 2,
                        "bounds": [x1, y1, x2, y2], "type": typ, "text": text}
        for c in n.get("children") or []:
            walk(c)

    walk(root)
    return best


def focus_box():
    """出键盘：先 dump 找试打框再点，再用**布局里的键**证明键盘真的起了（不再信 pidof）。

    键盘没起就不往下打字——否则 12 步全部落在页面空白处，甚至可能点到「隐私政策」跳页。

    返回值：True=键盘已起 / False=键盘没起（本应用前台，可留图）/ "abort"=前台不是本应用
    （不 dump、不点、不留图：别人的画面不该进证据目录）。
    """
    ok, why = own_foreground()
    if not ok:
        log("FOCUS-ABORT 前台不是本应用，停止（不 dump、不点、不打字）：%s" % why)
        return "abort"
    acc.dump()
    box = find_input_box(os.path.join(EVID, "h164_lay.json"))
    if box:
        log("INPUT-BOX %s center=(%d,%d) bounds=%s" %
            (box["type"] or box["text"] or "?", box["x"], box["y"], box["bounds"]))
        acc.tap(box["x"], box["y"])
    else:
        log("INPUT-BOX 未在布局里找到，退回固定点 (640,1600)")
        acc.tap(640, 1600)
    # 系统侧快证：面板 IsVisible（第三方键盘也会点亮，故只用来提前放行，主证仍是下面那次 dump）
    for _ in range(6):
        time.sleep(0.8)
        if keyboard_panel_visible() is True:
            log("KEYBOARD UP（WMS SCBKeyboardPanel IsVisible=true）")
            return True
    acc.dump()
    if layout_has_keyboard(os.path.join(EVID, "h164_lay.json")):
        log("KEYBOARD UP（布局含 %s）" % "/".join(KEY_MARKERS))
        return True
    log("KEYBOARD 未出现（面板不可见且布局无键）⇒ 不继续打字，避免盲点")
    return False


def type_text(s):
    unknown = [ch for ch in s if ch not in acc.LETTERS]
    if unknown:
        raise SystemExit("未映射字符：%s（先 shot 重量坐标）" % "".join(unknown))
    for ch in s:
        acc.tap(*acc.LETTERS[ch])


def clear_evidence():
    """开跑前清掉上一轮的截图/侧车，免得上一次半途而废的旧图被当成这一轮的结果。"""
    names = ["a0", "a1"] + ["b%d" % i for i in range(1, 18)] + \
            ["c1", "c2", "d1", "e1", "e2", "f1", "f2", "f3", "f4"]
    paths = [os.path.join(EVID, n + ".jpeg") for n in names]
    paths += [os.path.join(EVID, f) for f in
              ("h164_lay.json", "h164_cands.json", "h164-hilog.txt", "h164-log-check.txt",
               "h164-audit.txt")]
    n = 0
    for p in paths:
        if os.path.exists(p):
            os.remove(p)
            n += 1
    if n:
        log("清掉上一轮证据 %d 个文件（保留 wait-unlock.log）" % n)


def runbook():
    log("RUN 开始（DRY=%s）" % acc.DRY)
    if not acc.DRY:
        clear_evidence()
    # 载体自证：先记下装机包的 updateTime，报告才能绑定到「哪一版」，不靠事后再问。
    # 只读、失败不致命（hdc 偶发抖动不该带走整条一条龙）。
    try:
        dump = acc.sh("shell", "bm dump -n %s" % acc.BUNDLE)
        ut = [ln.strip() for ln in dump.splitlines() if '"updateTime"' in ln]
        log("CARRIER %s（期望 1792859799644＝2026-10-25 00:36:39、源码 0b199eb）"
            % (ut[0] if ut else "updateTime 未取到"))
    except Exception as e:
        log("CARRIER 取 updateTime 失败：%s" % e)
    acc.sh("shell", "hilog", "-r")
    log("清 hilog 缓冲")
    acc.snip(reset=True)         # 之后每拖一次就抓一次（缓冲只留十几秒，见 snip 注释）
    acc.sh("shell", "aa", "start", "-a", acc.ABILITY, "-b", acc.BUNDLE)
    time.sleep(4)
    # 起点闸：`aa start` 之后前台必须换成我们。换不过来（被别的应用压着/起失败）就退，
    # **一张图都不拍**——2026-10-25 09:39 解锁落在主人记事本上，旧脚本会先 shot 再找输入框。
    ok, why = own_foreground()
    if not ok:
        log("FOREGROUND 首次未到位（%s），2 秒后重启一次" % why)
        time.sleep(2)
        acc.sh("shell", "aa", "start", "-a", acc.ABILITY, "-b", acc.BUNDLE)
        time.sleep(3)
        ok, why = own_foreground()
    log("FOREGROUND %s：%s" % ("本应用" if ok else "不是本应用", why))
    if not ok:
        log("FOCUS-ABORT 前台不是本应用，停止（不 dump、不点、不打字、不截图）")
        return 4
    acc.shot("a0")
    fb = focus_box()
    if fb == "abort":
        return 4
    if not fb:
        acc.shot("a1")
        return 4
    time.sleep(1.0)
    acc.shot("a1")

    # 前置：键盘可能停在上轮的符号页/九键页（aa start 不重建页面），先经长按菜单强制回 26 键。
    # 长按 ?123/ABC 一律弹菜单，点「26键」是幂等的——已在 26 键也只是关菜单。
    if not guard("ensure-qwerty"):
        return 2
    acc.press(*acc.SPECIAL["q123"])
    time.sleep(1.0)
    acc.tap(*acc.SPECIAL["lay_26"])
    time.sleep(1.0)

    # 判据①：跟手 + 尾部续页（一次滑动只续一次）
    type_text("nihao")
    time.sleep(1.0)
    if not guard("shot-b1"):
        return 2
    acc.shot("b1")
    acc.snip()                   # 抓候选出现时的 state 行（条数关系判据⑦）
    # 打字到底进没进输入框：只认截图里量到的候选条数（键盘起了也可能焦点没在试打框里）。
    # 候选坐标只能从像素量：键盘面板窗在 dumpLayout -i 里一个 text 节点都没有（10:02 实测）。
    ncands = acc.cands_from_shot("b1")
    log("候选侧车 %d 条（b1）" % ncands)
    if ncands < 2:
        acc.shot("a1")
        log("NO-CAND 打 nihao 后只量到 %d 条候选（打字没进试打框／候选行不在 y%d–%d）⇒ 停止"
            % (ncands, acc.CAND_ROWS[0], acc.CAND_ROWS[1]))
        return 5
    sig_before = acc.band_hash(os.path.join(EVID, "b1.jpeg"))
    # 判据① 的干净性：滑之前记下试打框已上屏文字，滑完再 dump 比对，必须一字不差
    lay_before = acc.dump("h164_lay_a")
    text_before = acc.input_text(lay_before)
    # 一屏约 8 条、Rime 菜单页 50 条 ⇒ 3 次拖不到尾；每次 850px @2000px/s，17 次足够撞到尾并触发续页。
    # 每滑必拍、每滑必抓日志（hilog 缓冲只留十几秒）。
    names = ["b%d" % i for i in range(2, 18)]
    for name in names:
        if not guard("smooth-%s" % name):
            return 2
        acc.smooth(1150, 1950, 300, 1950)
        time.sleep(0.9)
        acc.shot(name)
        acc.snip()               # 每次滑完立刻抓 scroll 行（晚了就被环形缓冲冲掉）
    lay_after = acc.dump("h164_lay")
    text_after = acc.input_text(lay_after)
    if text_before is not None and text_after is not None and text_before != text_after:
        log("WARN 滑动期间试打框文字变了（%d→%d 字符）——注入被当成长按/误触上了屏，"
            "b2–b17 只能当「列表动了」的证据，不能当「跟手不误触」" %
            (len(text_before), len(text_after)))
    else:
        log("NO-COMMIT %d 张滑动截图期间试打框已上屏文字未变（无误上屏）" % len(names))

    # 判据① 前提：注入的移动真让 List 滚了没有——候选行像素指纹前后一样，b2–b17 就是同一帧，
    # 不能拿去当「跟手」证据（uinput -T -m 在键盘面板上此前未证实能让 List 收到连续 Move）。
    sig_after = acc.band_hash(os.path.join(EVID, "b17.jpeg"))
    if sig_before == sig_after:
        log("WARN 16 次滑动前后候选行像素完全相同（%s）——滚动可能没生效，b2–b17 需人工复核后再用"
            % sig_before)
    else:
        log("SCROLL 候选行指纹 %s → %s（像素变过 ⇒ 列表真的动了）" % (sig_before, sig_after))

    # 判据②：退格清空编码串 → 滚动位回第一条
    # 判据④：点第 2 条应上屏第 2 条（c2 是点之前、c1 是点之后，成对看图）
    if not guard("clear-preedit"):
        return 2
    for _ in range(5):          # 编码串是 nihao，5 个退格到空
        acc.tap(*acc.SPECIAL["bk"])
    time.sleep(1.0)
    type_text("ni")
    time.sleep(1.2)
    acc.shot("c2")
    n2 = acc.cands_from_shot("c2")
    log("候选侧车 %d 条（c2：退格清空后重打 ni，第 1 条应是「妳」＝回第一条）" % n2)
    if n2 < 2:
        acc.shot("c1")
        log("NO-CAND c2 只量到 %d 条 ⇒ 不点候选，判据②④ 记未跑" % n2)
        return 5
    if not guard("tapcand"):
        return 2
    side = os.path.join(EVID, "h164_cands.json")
    with open(side, encoding="utf-8") as f:
        pick = (json.load(f) or [])[1]
    log("判据④ 点 c2 第 2 条：x=%d（bounds %d–%d），c1 应上屏同一个词" %
        (pick["x"], pick["bounds"][0], pick["bounds"][2]))
    acc.tapcand(2)
    time.sleep(1.2)
    acc.shot("c1")
    acc.dump()

    # 判据⑤：长词不截断
    if not guard("nihaoma"):
        return 2
    type_text("nihaoma")
    time.sleep(1.2)
    acc.shot("d1")

    # 判据⑧：▼ 展开/收起 + 九键/26键（长按菜单）+ 符号页
    # 本装机包底栏没有「九键」键（10:44 实拍：?123｜😊｜,｜简｜空格｜.｜↵），
    # 九键只能长按 ?123 弹 H-078 布局菜单再点；菜单坐标是 10:44 在真机上量的（y 2160–2480）。
    if not guard("cand"):
        return 2
    acc.tap(*acc.SPECIAL["cand"])
    time.sleep(1.0)
    acc.shot("e1")
    acc.tap(*acc.SPECIAL["cand"])
    time.sleep(1.0)
    acc.shot("e2")
    if not guard("lay-menu"):
        return 2
    acc.press(*acc.SPECIAL["q123"])
    time.sleep(1.0)
    acc.shot("f1")               # f1：长按 ?123 弹菜单，26键带 ✓
    acc.tap(*acc.SPECIAL["lay_9"])
    time.sleep(1.2)
    acc.shot("f2")               # f2：九键面板（1–9 三行 + ABC）
    if not guard("lay-back"):
        return 2
    acc.press(*acc.SPECIAL["q123"])   # 九键模式左下角是 ABC，同一位置长按
    time.sleep(1.0)
    acc.tap(*acc.SPECIAL["lay_26"])
    time.sleep(1.2)
    acc.shot("f3")               # f3：回到 26 键
    if not guard("q123"):
        return 2
    acc.tap(*acc.SPECIAL["q123"])
    time.sleep(1.0)
    acc.shot("f4")               # f4：符号页

    # 判据③⑦：日志 + 检查器
    acc.logs()
    logf = os.path.join(EVID, "h164-hilog.txt")
    out = subprocess.run([sys.executable, os.path.join(HERE, "h164_log_check.py"), logf],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    with open(os.path.join(EVID, "h164-log-check.txt"), "w", encoding="utf-8") as f:
        f.write(out.stdout + out.stderr)
    log("LOG-CHECK exit=%d（%s）" % (out.returncode, os.path.join(EVID, "h164-log-check.txt")))
    log("RUN 完成")
    # 收官体检：图/侧车/日志/载体/完成标记逐项数一遍，结论留档，省得事后靠肉眼挑图
    try:
        au = subprocess.run([sys.executable, os.path.join(HERE, "h164_evidence_audit.py")],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
        with open(os.path.join(EVID, "h164-audit.txt"), "w", encoding="utf-8") as f:
            f.write(au.stdout + au.stderr)
        log("AUDIT exit=%d（%s）" % (au.returncode,
                                   "证据齐全" if au.returncode == 0 else "有阻断，见 h164-audit.txt"))
    except Exception as e:
        log("AUDIT 失败：%s" % e)
    return 0


def wait(minutes, interval, do_run):
    deadline = time.time() + minutes * 60
    idle_streak = 0
    attempts = 0
    no_kb = 0        # rc=4：键盘没起来就返回，一个字符都没打进；这类不算「一次取证」
    while time.time() < deadline:
        lk, why = locked()
        if lk is not False:
            idle_streak = 0
            log("WAIT %s（%s）" % ("locked" if lk else "unknown", why))
        else:
            busy = third_party_visible()
            if busy:
                idle_streak = 0
                log("WAIT unlocked-but-busy（%s）" % ", ".join(w["name"] for w in busy))
            else:
                idle_streak += 1
                log("WAIT unlocked-idle 第 %d 次（%s）" % (idle_streak, screen_state()))
                if idle_streak >= 2:
                    if not do_run:
                        return 0
                    attempts += 1
                    log("UNLOCKED 且桌面空闲 >=2 次判定，开始取证（第 %d 次尝试）" % attempts)
                    rc = runbook()
                    if rc == 0:
                        return 0
                    if rc in (4, 5):
                        # rc=4 键盘没起来／rc=5 键盘起来了但打字没进试打框（侧车 <2 条）。
                        # 两种都在「取证」之前就退了，证据不成立，不占 3 次预算；
                        # 但也不能无限点，6 次仍不成就停手等人看。
                        no_kb += 1
                        attempts -= 1
                        log("RUN 前置不成立 rc=%d（第 %d 次），不占取证预算；继续守候" % (rc, no_kb))
                        if no_kb >= 6:
                            log("WAIT 前置 6 次不成立，停止自动取证")
                            return 4
                    else:
                        log("RUN 未完成 rc=%d（可能是中途锁屏/被打断），继续守候%s" %
                            (rc, "" if attempts < 3 else "——已达 3 次上限"))
                        if attempts >= 3:
                            return 4
                    idle_streak = 0
        time.sleep(interval)
    log("WAIT 超时（%d 分钟）未等到解锁空闲" % minutes)
    return 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["probe", "wait", "run", "selftest"])
    ap.add_argument("--minutes", type=int, default=300)
    ap.add_argument("--interval", type=int, default=45)
    ap.add_argument("--run", action="store_true", help="wait 模式下解锁空闲就自动跑一条龙")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    acc.DRY = a.dry_run
    os.makedirs(EVID, exist_ok=True)
    if a.cmd == "selftest":
        return selftest()
    if a.cmd == "probe":
        probe()
        return 0
    if a.cmd == "run":
        lk, _ = probe()
        if lk is not False:
            log("RUN-ABORT 当前不是「已解锁」状态（%s），不启动" % ("locked" if lk else "unknown"))
            return 3
        return runbook()
    return wait(a.minutes, a.interval, a.run)


if __name__ == "__main__":
    sys.exit(main())
