# -*- coding: utf-8 -*-
"""外部心跳看门狗（不依赖任何 agent 内部机制，自身不会自杀）。

它做什么：
  1. 读 Qoder 心跳文件 .night-watch.json，若超过 QODER_STALL_MIN 分钟没更新 -> 判 Qoder 值守死亡。
  2. 读 docs/MAILBOX.md，找「发给 CodeArts 且超过 CODEARTS_STALL_MIN 分钟仍未闭环」的任务 -> 判 CodeArts 卡死。
  3. CodeArts 卡死 + Qoder 还活着 -> 把该任务改派 Qoder（写回 MAILBOX 新行 + 看板 reassign），让夜里不卡死。
  4. 任何异常 -> 立即弹 Windows 通知 + 写 .watchdog.json + 写日志，绝不静默。

为什么有效：原来的「巡检脚本」只弹通知、且依赖已错位的 mail_open 列索引；Qoder 值守是应用内部 qoder_cron，
会连续 3 次 session-failed 后自杀（v6/v7/v8/v10 都死过）。本看门狗跑在 Windows 任务计划程序里，
独立于 agent，不会被 agent 自杀连累；它的价值是把「死了 8 小时没人发现」变成「死了就被标记 + 自动改派」。

局限（诚实说明）：本看门狗无法「复活」Qoder 的 qoder_cron（那需要 Qoder 应用内 MCP）；它只能发现死亡并告警。
若要真·无人值守复活，需要 Qoder 暴露本地 API 或你下次醒来 1 分钟重建值守。
"""
import os
import sys
import io
import json
import time
import datetime
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_DIR = os.path.join(ROOT, ".kanban")
WATCHDOG_STATE = os.path.join(KB_DIR, "watchdog.json")
WATCHDOG_LOG = os.path.join(KB_DIR, "watchdog.log")
NIGHT_WATCH = os.path.join(ROOT, ".night-watch.json")
MAIL = os.path.join(ROOT, "docs", "MAILBOX.md")
NOTIFY = os.path.join(ROOT, "scripts", "notify.ps1")
KANBAN = os.path.join(ROOT, "scripts", "kanban.py")

PY = sys.executable


def hidden_run(cmd, **kw):
    """无窗口运行子进程——绝不弹黑窗。

    本脚本跑在任务计划里（pythonw，无控制台），若不隐藏，Windows 会给每个
    控制台子进程（tasklist/powershell）新建一个控制台窗口，表现为黑窗狂闪。
    CREATE_NO_WINDOW + STARTUPINFO(SW_HIDE) 双保险，确保任何调用方都不闪。
    """
    kw.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
    kw.setdefault("errors", "replace")
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # SW_HIDE
    kw.setdefault("startupinfo", si)
    return subprocess.run(cmd, **kw)

QODER_STALL_MIN = 12      # qoder cron 每 5 分钟一轮；12 分钟无心跳 = 死亡
CODEARTS_STALL_MIN = 30    # CodeArts 任务派出 30 分钟未闭环 = 卡死
NIGHT_START = 22           # 夜间窗口起点（22:00）
NIGHT_END = 7              # 夜间窗口终点（07:00）—— 此区间内视为「主人已睡，CodeArts 叫不醒」

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import kanban as KB


def now_iso():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    line = "%s  %s\n" % (now_iso(), msg)
    try:
        os.makedirs(KB_DIR, exist_ok=True)
        # 超过 200KB 则保留末尾 600 行，避免长期运行撑爆磁盘
        if os.path.exists(WATCHDOG_LOG) and os.path.getsize(WATCHDOG_LOG) > 200000:
            with open(WATCHDOG_LOG, encoding="utf-8") as f:
                lines = f.readlines()
            with open(WATCHDOG_LOG, "w", encoding="utf-8") as f:
                f.writelines(lines[-600:])
        with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    print(line.rstrip())


def toast(title, message):
    try:
        hidden_run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", NOTIFY, "-Title", title, "-Message", message],
            timeout=30, check=False,
        )
    except Exception as e:
        log("toast failed: %s" % e)


def load_state():
    try:
        with open(WATCHDOG_STATE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(d):
    try:
        os.makedirs(KB_DIR, exist_ok=True)
        with open(WATCHDOG_STATE, "w", encoding="utf-8", newline="") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def in_night_window():
    h = datetime.datetime.now().hour
    return h >= NIGHT_START or h < NIGHT_END


def codearts_running():
    """CodeArts Agent 进程在跑 = 在线可唤醒；不在 = 死亡，可直接接管。"""
    try:
        # 中文 Windows 的 tasklist 输出是 GBK；只搜 ASCII 进程名，故 utf-8+replace 足够且不会崩
        out = hidden_run(["tasklist"], capture_output=True, text=True,
                         encoding="utf-8", timeout=10).stdout
        return "codearts-agent" in out.lower()
    except Exception:
        return True  # 查不到则保守：当作在线，不擅自接管


def parse_night_watch():
    """返回 (last_run_dt, raw) 或 (None, None)"""
    try:
        with open(NIGHT_WATCH, encoding="utf-8", newline="") as f:
            d = json.load(f)
        # H-222 附带修正（2026-10-27 15:5x Qoder）：心跳文件的键名两边不一致过——
        # 值守 prompt 写的是 lastRunTs（"2026-10-26 22:18:48"，带秒），本脚本只认 lastRunAt，
        # 于是 parse 恒失败 -> 每轮都判「Qoder 心跳文件缺失/无法解析」并虚报死亡（watchdog.log
        # 15:26/15:32/15:37 三条 ALERT 就是这么来的）。现在两个键都认、两种格式都试。
        for key in ("lastRunAt", "lastRunTs"):
            s = d.get(key, "") or ""
            ts = s.split("(")[0].strip()
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    return datetime.datetime.strptime(ts, fmt), d
                except ValueError:
                    continue
        log("parse_night_watch: lastRunAt/lastRunTs 均无法解析 -> 视为死亡")
        return None, None
    except Exception as e:
        log("parse_night_watch failed: %s" % e)
        return None, None


def codearts_stalled_rows(minutes):
    """从 MAILBOX 找发给 CodeArts 且超时的未闭环任务。best-effort，解析失败返回 []。"""
    out = []
    try:
        txt = io.open(MAIL, encoding="utf-8", newline="").read()
    except Exception:
        return out
    now = datetime.datetime.now()
    for ln in txt.split("\n"):
        ln = ln.rstrip("\r")
        if not ln.startswith("| M-") or ln.startswith("| M-xxx"):
            continue
        cells = [c.strip() for c in ln.split("|")]
        if len(cells) < 6:
            continue
        mid, subject, ts_raw, recip, status_raw = cells[1], cells[2], cells[3], cells[4], cells[5]
        if "CodeArts" not in recip:
            continue
        if "已复核闭环" in status_raw or "done" in status_raw.lower() or "完成" in status_raw:
            continue
        # 解析时间 "2026-10-25 13:1x" 这类可能含 x；取可解析前缀
        ts_clean = ts_raw.replace("x", "0").strip()
        try:
            dt = datetime.datetime.strptime(ts_clean, "%Y-%m-%d %H:%M")
        except Exception:
            dt = None
        if dt is None:
            continue
        age = (now - dt).total_seconds() / 60.0
        if age >= minutes:
            out.append((mid, subject, int(age)))
    return out


def board_stalled(minutes):
    """看板里挂在 CodeArts 名下、超时未动的任务（kanban.py add 直接登记，不经 MAILBOX）。"""
    out = []
    try:
        c = KB.conn()
        cur = c.execute(
            "SELECT id, title, last_touched FROM tasks "
            "WHERE owner=? AND status IN ('TODO','INPROGRESS','BLOCKED')",
            ("CodeArts",),
        )
        now = datetime.datetime.now()
        for tid, title, ts in cur.fetchall():
            try:
                dt = datetime.datetime.strptime((ts or "")[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            age = (now - dt).total_seconds() / 60.0
            if age >= minutes:
                out.append((tid, title, int(age)))
        c.close()
    except Exception as e:
        log("board_stalled failed: %s" % e)
    return out


def next_mail_id():
    try:
        txt = io.open(MAIL, encoding="utf-8", newline="").read()
    except Exception:
        return "M-9000"
    maxn = 0
    for ln in txt.split("\n"):
        if ln.startswith("| M-") and not ln.startswith("| M-xxx"):
            try:
                n = int(ln.split("|")[1].strip().replace("M-", ""))
                maxn = max(maxn, n)
            except Exception:
                pass
    return "M-%d" % (maxn + 1)


def append_reassign_row(orig_mid, subject):
    new_id = next_mail_id()
    ts = now_iso()[:16]
    row = "| %s | [REASSIGN] 原 %s 超时未闭环，已由看门狗改派 Qoder 接管：%s | %s | Qoder→Qoder | **待回执** | — | 无 | — | 看门狗自动改派 |\n" % (
        new_id, orig_mid, subject, ts)
    try:
        with io.open(MAIL, encoding="utf-8", newline="") as f:
            cur = f.read()
        if not cur.endswith("\n"):
            cur += "\n"
        cur += row
        with io.open(MAIL, "w", encoding="utf-8", newline="") as f:
            f.write(cur)
        return new_id
    except Exception as e:
        log("append_reassign_row failed: %s" % e)
        return None


def main():
    log("=== watchdog run ===")
    state = load_state()
    findings = {"qoder_dead": False, "codearts_stalled": [], "reassigned": [], "alerts": []}

    # 1) Qoder 心跳
    dt, nw = parse_night_watch()
    qoder_dead = False
    if dt is None:
        qoder_dead = True
        msg = "Qoder 心跳文件缺失/无法解析 .night-watch.json"
        findings["alerts"].append(msg)
        log("QODER: 心跳文件异常 -> 视为死亡")
    else:
        age = (datetime.datetime.now() - dt).total_seconds() / 60.0
        qoder_dead = age >= QODER_STALL_MIN
        log("QODER: 心跳 %s，距今 %.1f 分钟 -> %s" % (dt, age, "死亡" if qoder_dead else "存活"))
        # 把心跳写进看板事件（每轮记一次，便于早晨回看）
        try:
            c = KB.conn()
            KB.log(c, "qoder_heartbeat", "-", "age_min=%.1f dead=%s" % (age, qoder_dead))
            c.commit(); c.close()
        except Exception:
            pass

    if qoder_dead:
        findings["qoder_dead"] = True
        a = "Qoder 值守心跳停止（>%d分钟无更新）！夜里可能静默。请唤醒 Qoder 重建值守。" % QODER_STALL_MIN
        findings["alerts"].append(a)
        # 夜间不弹通知：主人睡了收不到，弹窗只扰民。写日志 + 进 watchdog.json 晨报即可
        log("ALERT: " + a)

    # 2) CodeArts 卡死 + 改派（仅夜间窗口或 CodeArts 进程已死才接管，白天不抢活）
    night = in_night_window()
    ca_dead = not codearts_running()
    takeover = night or ca_dead
    stalled = codearts_stalled_rows(CODEARTS_STALL_MIN)
    already = set(state.get("reassigned_ids", []))
    if stalled:
        log("CODEARTS: 发现 %d 条超时未闭环任务 | 夜间=%s CodeArts在线=%s 接管=%s" % (
            len(stalled), night, (not ca_dead), takeover))
        for mid, subject, age in stalled:
            findings["codearts_stalled"].append({"id": mid, "subject": subject, "age_min": age})
            if qoder_dead:
                log("  %s 卡死 %d 分钟，但 Qoder 也死了，无法改派（等早上）" % (mid, age))
                if takeover:
                    a = "CodeArts 任务 %s 卡死 %d 分钟，但 Qoder 也死了，夜里无人接管！" % (mid, age)
                    findings["alerts"].append(a)
                    log("ALERT: " + a)
                continue
            if not takeover:
                # 白天且 CodeArts 在线：仅记录，不抢活（CodeArts 可能在干）
                log("  %s 卡死 %d 分钟，但白天且 CodeArts 在线，仅记录不接管" % (mid, age))
                continue
            if mid in already:
                # 已改派过：看板 owner=Qoder，绝不再写 MAILBOX（否则每轮刷 11 行，既膨胀又催眠 Qoder）
                log("  %s 此前已改派 Qoder（看板 owner=Qoder），不重复写 MAILBOX" % mid)
                continue
            # 接管：改派 Qoder（看板改 owner + MAILBOX 只写一次）
            try:
                c = KB.conn()
                KB.reassign(c, mid, "Qoder")
                c.commit(); c.close()
            except Exception as e:
                log("  reassign board failed: %s" % e)
            new_id = append_reassign_row(mid, subject)
            if new_id:
                findings["reassigned"].append({"from": mid, "to": new_id})
                already.add(mid)
                state["reassigned_ids"] = sorted(already)
                a = "夜间：CodeArts 任务 %s 超时 %d 分钟未动，已改派 Qoder（%s）。" % (mid, age, new_id)
                findings["alerts"].append(a)
                log("  %s 已改派 -> %s" % (mid, new_id))
    else:
        log("CODEARTS: 无超时未闭环任务")

    # 2b) 看板滞留任务（H-xxx 直接登记在 board.db，不经 MAILBOX；改派只动看板，绝不写 docs/）
    board_items = board_stalled(CODEARTS_STALL_MIN)
    if board_items:
        log("BOARD: 发现 %d 条 CodeArts 滞留任务" % len(board_items))
        for tid, title, age in board_items:
            findings["codearts_stalled"].append({"id": tid, "subject": title, "age_min": age})
            if qoder_dead:
                log("  看板 %s 滞留 %d 分钟，但 Qoder 也死了，无法改派（等早上）" % (tid, age))
                if takeover:
                    a = "看板任务 %s 滞留 %d 分钟，但 Qoder 也死了，夜里无人接管！" % (tid, age)
                    findings["alerts"].append(a)
                    log("ALERT: " + a)
                continue
            if not takeover:
                log("  看板 %s 滞留 %d 分钟，但白天且 CodeArts 在线，仅记录不接管" % (tid, age))
                continue
            if tid in already:
                log("  看板 %s 此前已改派 Qoder，跳过" % tid)
                continue
            try:
                c = KB.conn()
                KB.reassign(c, tid, "Qoder")
                c.commit(); c.close()
            except Exception as e:
                log("  board reassign failed: %s" % e)
                continue
            findings["reassigned"].append({"from": tid, "to": "board:owner=Qoder"})
            already.add(tid)
            state["reassigned_ids"] = sorted(already)
            a = "看板任务 %s 滞留 %d 分钟未动，已改派 Qoder 接管（看板 owner=Qoder）。" % (tid, age)
            findings["alerts"].append(a)
            log("  看板 %s 已改派 -> Qoder" % tid)
    else:
        log("BOARD: 无 CodeArts 滞留任务")

    # 3) 渲染看板（看板由 agent 用 kanban.py 主动登记；此处只渲染，不做 MAILBOX 全量镜像）
    try:
        c = KB.conn()
        KB.render(c)
        c.commit(); c.close()
    except Exception as e:
        log("render failed: %s" % e)

    # 4) 汇总状态
    state["last_run"] = now_iso()
    state["qoder_dead"] = qoder_dead
    state["codearts_stalled"] = findings["codearts_stalled"]
    state["reassigned"] = findings["reassigned"]
    state["alerts"] = findings["alerts"]
    save_state(state)

    log("=== done. dead=%s stalled=%d reassigned=%d alerts=%d ===" % (
        qoder_dead, len(stalled), len(findings["reassigned"]), len(findings["alerts"])))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log("WATCHDOG CRASH: %s" % e)
        try:
            toast("SanshengIME 看门狗异常", "看门狗自身报错：%s" % e)
        except Exception:
            pass
        sys.exit(1)
