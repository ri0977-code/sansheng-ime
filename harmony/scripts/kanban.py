# -*- coding: utf-8 -*-
"""第三方看板：Qoder / CodeArts 共享任务场地（SQLite 单文件 + Markdown 渲染）。

设计目标（主人的诉求）：
  - 给两个 agent 一个「中立的第三方沟通场地」，不依赖某一家的内部机制。
  - 任务带状态机 + 最后活动时间戳，做到「一直顺延往下走、卡死看得见」。
  - 看门狗据此判定卡死、自动改派。

状态机：
  TODO -> INPROGRESS -> DONE
  （任意态可 -> BLOCKED，带 blocked_reason；BLOCKED 可回到 INPROGRESS/TODO）

每条任务带 last_touched（最后活动时间戳）。看门狗用它与「现在」的差值判定卡死。

用法（agent 或人都能调）：
  python kanban.py init
  python kanban.py add  --id M-200 --title "修 H-154 空格键面" --owner CodeArts --prio 1
  python kanban.py claim --id M-200 --by Qoder        # 认领（顺延：把 owner 改成的认领方）
  python kanban.py touch --id M-200                   # 报活（刷新 last_touched）
  python kanban.py done  --id M-200
  python kanban.py block --id M-200 --reason "..."
  python kanban.py reassign --id M-200 --to Qoder     # 超时改派
  python kanban.py stalled --minutes 30               # 列出卡死任务
  python kanban.py render                             # 写 docs/KANBAN.md
  python kanban.py sync                               # 从 docs/MAILBOX.md 同步开放任务（best-effort）
"""
import os
import sys
import json
import sqlite3
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_DIR = os.path.join(ROOT, ".kanban")
DB = os.path.join(KB_DIR, "board.db")
BOARD_MD = os.path.join(ROOT, ".kanban", "KANBAN.md")
MAIL = os.path.join(ROOT, "docs", "MAILBOX.md")

STATUSES = ("TODO", "INPROGRESS", "BLOCKED", "DONE")
OWNERS = ("Qoder", "CodeArts", "Shared")

STATUS_CN = {
    "TODO": "待办",
    "INPROGRESS": "进行中",
    "BLOCKED": "阻塞",
    "DONE": "完成",
}


def now_iso():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def conn():
    os.makedirs(KB_DIR, exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute(
        """CREATE TABLE IF NOT EXISTS tasks(
            id TEXT PRIMARY KEY,
            title TEXT,
            owner TEXT,
            status TEXT,
            prio INTEGER DEFAULT 3,
            assigned_to TEXT,
            last_touched TEXT,
            created_at TEXT,
            blocked_reason TEXT,
            meta TEXT
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            kind TEXT,
            task_id TEXT,
            detail TEXT
        )"""
    )
    c.commit()
    return c


def log(cur, kind, tid, detail):
    cur.execute(
        "INSERT INTO events(kind,task_id,detail,ts) VALUES(?,?,?,?)",
        (kind, tid, detail, now_iso()),
    )


# ---- 任务操作 ----
def add_task(cur, tid, title, owner, prio=3, status="TODO", meta=""):
    cur.execute(
        "INSERT OR REPLACE INTO tasks(id,title,owner,status,prio,assigned_to,last_touched,created_at,meta) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (tid, title, owner, status, prio, owner, now_iso(), now_iso(), meta),
    )
    log(cur, "add", tid, "owner=%s status=%s prio=%s" % (owner, status, prio))


def touch(cur, tid):
    cur.execute("UPDATE tasks SET last_touched=? WHERE id=?", (now_iso(), tid))
    log(cur, "touch", tid, "")


def set_status(cur, tid, status, reason=""):
    if status not in STATUSES:
        raise ValueError("bad status: %s" % status)
    cur.execute(
        "UPDATE tasks SET status=?, blocked_reason=?, last_touched=? WHERE id=?",
        (status, reason, now_iso(), tid),
    )
    log(cur, "status:%s" % status, tid, reason)


def reassign(cur, tid, to):
    if to not in OWNERS:
        raise ValueError("bad owner: %s" % to)
    cur.execute(
        "UPDATE tasks SET owner=?, assigned_to=?, last_touched=? WHERE id=?",
        (to, to, now_iso(), tid),
    )
    log(cur, "reassign", tid, "-> %s" % to)


def get_stalled(cur, minutes):
    cutoff = (datetime.datetime.now() - datetime.timedelta(minutes=minutes)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    rows = cur.execute(
        "SELECT id,title,owner,status,last_touched,blocked_reason FROM tasks "
        "WHERE status!='DONE' AND last_touched<? ORDER BY prio, id",
        (cutoff,),
    ).fetchall()
    return rows


def list_all(cur):
    return cur.execute(
        "SELECT id,title,owner,status,prio,last_touched,blocked_reason FROM tasks "
        "ORDER BY status, prio, id"
    ).fetchall()


# ---- Markdown 渲染 ----
def render(cur):
    rows = list_all(cur)
    by_status = {s: [] for s in STATUSES}
    for r in rows:
        by_status[r[3]].append(r)
    lines = []
    lines.append("# 第三方协作看板（Qoder / CodeArts）")
    lines.append("")
    lines.append("> 自动生成，请勿手改。任务带最后活动时间戳，卡死一眼可见。")
    lines.append("> 生成时间：%s" % now_iso())
    lines.append("")
    lines.append("| 编号 | 标题 | 归属 | 优先级 | 最后活动 | 阻塞原因 |")
    lines.append("|---|---|---|---|---|---|")
    for s in STATUSES:
        items = by_status[s]
        if not items:
            continue
        lines.append("")
        lines.append("### %s（%d）" % (STATUS_CN[s], len(items)))
        for r in items:
            tid, title, owner, status, prio, lt, br = r
            br_s = ("`%s`" % br) if br else "—"
            lines.append(
                "| %s | %s | %s | P%d | %s | %s |" % (tid, title, owner, prio, lt, br_s)
            )
    txt = "\n".join(lines) + "\n"
    with open(BOARD_MD, "w", encoding="utf-8", newline="") as f:
        f.write(txt)
    return len(rows)


# ---- best-effort 从 MAILBOX 同步 ----
def _parse_mail_rows():
    if not os.path.exists(MAIL):
        return []
    out = []
    try:
        with open(MAIL, encoding="utf-8", newline="") as f:
            for ln in f:
                ln = ln.rstrip("\r")
                if not ln.startswith("| M-") or ln.startswith("| M-xxx"):
                    continue
                cells = [c.strip() for c in ln.split("|")]
                # cells[0]='' , [1]=编号, [2]=主题, [3]=时间, [4]=收发, [5]=状态, ...
                if len(cells) < 6:
                    continue
                mid = cells[1]
                subject = cells[2]
                recip = cells[4]  # 含 "→ CodeArts" / "→ Qoder"
                status_raw = cells[5]
                out.append((mid, subject, recip, status_raw))
    except Exception:
        return []
    return out


def sync(cur):
    rows = _parse_mail_rows()
    n_add = 0
    n_upd = 0
    for mid, subject, recip, status_raw in rows:
        if "CodeArts" in recip:
            owner = "CodeArts"
        elif "Qoder" in recip:
            owner = "Qoder"
        else:
            owner = "Shared"
        raw = status_raw.lower()
        if "已复核闭环" in status_raw or "done" in raw or "完成" in status_raw:
            status = "DONE"
        elif "挂起" in status_raw or "blocked" in raw or "失联" in status_raw:
            status = "BLOCKED"
        elif "进行中" in status_raw or "处理中" in status_raw:
            status = "INPROGRESS"
        else:
            status = "TODO"
        # 只把「未闭环」的行同步进看板，避免 258 条历史档案污染活看板
        if status == "DONE":
            # 已闭环：若看板里还有，标记完成；否则跳过
            if cur.execute("SELECT id FROM tasks WHERE id=?", (mid,)).fetchone() is not None:
                cur.execute("UPDATE tasks SET status='DONE',last_touched=? WHERE id=?", (now_iso(), mid))
                n_upd += 1
            continue
        if cur.execute("SELECT id FROM tasks WHERE id=?", (mid,)).fetchone() is None:
            add_task(cur, mid, subject, owner, prio=3, status=status, meta="from MAILBOX")
            n_add += 1
        else:
            cur.execute(
                "UPDATE tasks SET owner=?, title=?, status=? WHERE id=?",
                (owner, subject, status, mid),
            )
            n_upd += 1
    return n_add


def main():
    c = conn()
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    cmd = args[0]

    def arg(name, default=None):
        if name in args:
            return args[args.index(name) + 1]
        return default

    if cmd == "init":
        print("kanban initialized: %s" % DB)
    elif cmd == "add":
        tid = arg("--id"); title = arg("--title"); owner = arg("--owner", "Shared")
        prio = int(arg("--prio", "3") or 3)
        if not tid or not title:
            print("add 需要 --id 和 --title"); return 2
        add_task(c, tid, title, owner, prio)
        c.commit(); print("added %s" % tid)
    elif cmd == "touch":
        touch(c, arg("--id")); c.commit(); print("touched")
    elif cmd == "done":
        set_status(c, arg("--id"), "DONE"); c.commit(); print("done")
    elif cmd == "block":
        set_status(c, arg("--id"), "BLOCKED", arg("--reason", "")); c.commit(); print("blocked")
    elif cmd == "reassign":
        reassign(c, arg("--id"), arg("--to")); c.commit(); print("reassigned")
    elif cmd == "stalled":
        mins = int(arg("--minutes", "30") or 30)
        rows = get_stalled(c, mins)
        for r in rows:
            print("%s | %s | %s | %s | 最后活动 %s" % r)
        print("共 %d 条卡死(>%d分钟)" % (len(rows), mins))
    elif cmd == "render":
        n = render(c); c.commit(); print("rendered %d 条 -> %s" % (n, BOARD_MD))
    elif cmd == "sync":
        n = sync(c); c.commit(); print("synced +%d 新任务" % n)
    elif cmd == "list":
        for r in list_all(c):
            print("%s | %s | %s | %s | P%d | %s | %s" % r)
    else:
        print("unknown cmd: %s" % cmd); return 2
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
