#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三生输入法 · 鸿蒙移植 · 中间落盘流水 + 收件箱（Qoder/CodeArts 共用）

主人 2026-10-21 14:49 的要求（原话）：
  「你们干活过程中，尤其长任务，中间落盘的东西一定要及时记录并通知对方。
    自己也要及时关注对方的通知，把这个机制建起来。」

为什么光有 MAILBOX 不够：MAILBOX 是「一阶段一条」的正式信，长任务里我（或 CodeArts）
中途会落一堆东西 —— 改过的 yaml、新脚本、真机日志、探针页、备份文件。
这些**在阶段结束前对方看不见**，于是出现两种事故：
  ① 同一时间改同一个文件，后写的把先写的覆盖掉（M2 差点撞上 `fanxing_napi.cpp`）；
  ② 一方已经修好了等验证的东西，另一方还在按旧结论排查（今天 14:36 我按
     「H-042 未修」的旧认知准备重跑，其实 CodeArts 的 M-030-re 已经躺在 MAILBOX 里）。

三条命令就用起来了：
  python scripts/wip.py inbox                 # 开工/每轮真机前：看对方有什么新的
  python scripts/wip.py log --who Qoder ...   # 中间一落盘就记一条，不等阶段结束
  python scripts/wip.py read --who Qoder W-007  # 看过对方的条目就签字（对方能看到我读了）

状态语义：WIP=还在改，别依赖；READY=可取用；BLOCKED=被什么卡住，需要对方动。
退出码：inbox 有未读=0 且打印提示；纯查询失败=2。

产物：docs/WIP.md（人读的流水表）+ docs/.wip-state-<who>.json（各自读到哪儿了，不入库）。
"""

import argparse
import datetime
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIP_MD = os.path.join(ROOT, "docs", "WIP.md")
MAILBOX_MD = os.path.join(ROOT, "docs", "MAILBOX.md")
COLS = ["编号", "时间", "谁", "里程碑", "状态", "落盘文件", "这一步在做什么", "对对方的影响", "对方已读"]
WATCH_DIRS = [
    os.path.join(ROOT, "entry", "src"),
    os.path.join(ROOT, "docs"),
    os.path.join(ROOT, "scripts"),
]
# 归属表：谁改的路径。撞车时先看这张表（规则：不要动对方在飞的文件）。
OWNER_RULES = [
    ("entry/src/main/cpp", "Qoder"),
    ("entry/src/main/ets/engine", "Qoder"),
    ("entry/src/main/resources/rawfile/rime", "Qoder"),
    ("scripts", "Qoder"),
    ("entry/src/main/ets/pages", "CodeArts"),
    ("entry/src/main/ets/components", "CodeArts"),
    ("entry/src/main/ets/inputmethod", "CodeArts"),
]
DONE_WORDS = ("DONE", "READ", "VERIFIED", "已读", "已验收")


# 第三方/生成物，不记变更（一次报 300 个头文件等于没报）
IGNORE_PREFIX = (
    "entry/src/main/cpp/include",
    "entry/src/main/cpp/lib",
    "entry/build",
    "build",
    "oh_modules",
    ".hvigor",
    "docs/.wip-state",
)


def rel(path):
    return os.path.relpath(path, ROOT).replace("\\", "/")


def ignored(path_rel):
    return any(path_rel.startswith(p) for p in IGNORE_PREFIX)


def who_owns(path_rel):
    for prefix, owner in OWNER_RULES:
        if path_rel.startswith(prefix):
            return owner
    return "共享"


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def state_path(who):
    return os.path.join(ROOT, "docs", ".wip-state-%s.json" % who.lower())


def load_state(who):
    p = state_path(who)
    if os.path.isfile(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # noqa: BLE001
            pass
    return {"seen_wip": [], "seen_mailbox": [], "snapshots": {}}


def save_state(who, state):
    with open(state_path(who), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def ensure_table():
    if os.path.isfile(WIP_MD):
        with open(WIP_MD, "r", encoding="utf-8") as f:
            text = f.read()
        if text.strip():
            return text
    header = """# 中间落盘流水（WIP log）

长任务里**每落一批文件就记一行**，不等阶段收口；对方每轮开工先跑
`python scripts/wip.py inbox`。规则见本表下方的「协议」。

| """ + " | ".join(COLS) + """ |
|""" + "---|" * len(COLS) + """
"""
    footer = """

## 协议（2026-10-21 主人定案，Qoder/CodeArts 都要守）

1. **落盘即记**：新建或改动 `entry/src/**`、`scripts/**`、`docs/evidence/**` 里的文件后，
   立刻 `python scripts/wip.py log --who <你> --milestone <M?> --status WIP|READY|BLOCKED
   --files "路径,路径" --doing "在做什么" --impact "对方要不要动/别动什么"`。
2. **每轮开工先看收件箱**：跑任何构建/装机/真机轮次之前先
   `python scripts/wip.py inbox --who <你>`；`build.ps1` 已内置一次 brief 检查。
3. **读过要签字**：`python scripts/wip.py read --who <你> W-012`（或在 MAILBOX 回一条
   `M-xxx-re`）。「对方已读」空着 = 这条还没生效，作者不能假设对方知道。
4. **别动对方在飞的文件**：`状态=WIP` 的行，其「落盘文件」归作者独占；
   要改先在 MAILBOX 说一声，等对方转成 READY。
5. **结论只有真机算数**：WIP/READY 都不等于 VERIFIED；VERIFIED 只由装机取证的一方写，
   证据文件路径要出现在「落盘文件」里。
6. **跨阶段大动作**（升 DATA_VERSION、换接口版本、打标签、装机）→ 同时写 MAILBOX 正式条目，
   WIP 行只是「先说一声」。
"""
    with open(WIP_MD, "w", encoding="utf-8", newline="\n") as f:
        f.write(header + footer)
    return open(WIP_MD, "r", encoding="utf-8").read()


def parse_rows(text):
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < len(COLS) or cells[0] in ("编号",) or set(cells[0]) <= set("-: "):
            continue
        rows.append(cells)
    return rows


def next_id(rows):
    n = 0
    for r in rows:
        if r[0].startswith("W-"):
            try:
                n = max(n, int(r[0][2:]))
            except ValueError:
                pass
    return "W-%03d" % (n + 1)


def insert_row(row_cells):
    text = ensure_table()
    lines = text.splitlines()
    # 插到表格最后一行之后、协议标题之前
    last = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("| W-") or s.startswith("|W-"):
            last = i
    if last is None:
        # 表头分隔线之后
        for i, line in enumerate(lines):
            if line.strip().startswith("|---") or set(line.strip()) <= set("|-: "):
                last = i
    body = "| " + " | ".join(row_cells) + " |".replace("  ", " ")
    lines.insert(last + 1, body)
    with open(WIP_MD, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return body


def changed_files(snapshots):
    """返回 (自上次 checkpoint 起变更的文件, 当前 mtime 快照)。"""
    cur = {}
    for d in WATCH_DIRS:
        for p in glob.glob(os.path.join(d, "**", "*"), recursive=True):
            if os.path.isfile(p):
                r = rel(p)
                if ignored(r) or r == "docs/WIP.md":
                    continue
                cur[r] = os.path.getmtime(p)
    if not snapshots:
        # 第一次跑：只建基线，不把全仓库报成「对方新落的盘」
        return [], cur
    changed = []
    for path, m in cur.items():
        old = snapshots.get(path)
        if old is None or m > old + 1:
            changed.append(path)
    return changed, cur


def parse_rows_table(text, min_cols):
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < min_cols or cells[0] in ("编号",):
            continue
        if set("".join(cells[:2])) <= set("-: "):
            continue
        rows.append(cells)
    return rows


def cmd_log(args):
    text = ensure_table()
    rows = parse_rows(text)
    rid = next_id(rows)
    files = ", ".join("`%s`" % f.strip() for f in args.files.split(",") if f.strip())
    row = [rid, now(), args.who, args.milestone, args.status.upper(),
           files or "-", args.doing or "-", args.impact or "-", ""]
    body = insert_row(row)
    # 落盘即 checkpoint 自己，免得 inbox 把自己的改动报成对方的
    st = load_state(args.who)
    changed, cur = changed_files(st.get("snapshots", {}))
    st["snapshots"] = cur
    save_state(args.who, st)
    print("RECORDED %s" % rid)
    print(body)
    other = "CodeArts" if args.who == "Qoder" else "Qoder"
    print("提醒：%s 下一轮 `wip.py inbox --who %s` 就能看到这条。" % (other, other))
    return 0


def cmd_read(args):
    st = load_state(args.who)
    seen_wip = set(st.get("seen_wip", []))
    seen_mb = set(st.get("seen_mailbox", []))
    ids = set(args.ids)
    for rid in ids:
        if rid.startswith("M-"):
            seen_mb.add(rid)
        else:
            seen_wip.add(rid)
    st["seen_wip"] = sorted(seen_wip)
    st["seen_mailbox"] = sorted(seen_mb)
    save_state(args.who, st)
    text = ensure_table()
    lines = text.splitlines()
    out = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else []
        if len(cells) >= len(COLS) and cells[0] in args.ids and cells[2] != args.who:
            cells[-1] = "%s 已读 %s" % (args.who, now())
            line = "| " + " | ".join(cells[:len(COLS) - 1] + [cells[-1]]) + " |"
        out.append(line)
    with open(WIP_MD, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print("MARKED READ by %s: %s" % (args.who, " ".join(args.ids)))
    return 0


def cmd_inbox(args):
    me = args.who
    other = "CodeArts" if me == "Qoder" else "Qoder"
    st = load_state(me)
    seen_wip = set(st.get("seen_wip", []))
    seen_mb = set(st.get("seen_mailbox", []))
    lines = []
    unread_wip = []
    text = ensure_table()
    for cells in parse_rows(text):
        if cells[2] != other:
            continue
        done = any(w in cells[-1] for w in ("已读", "READ")) or cells[0] in seen_wip
        if cells[4] == "DONE" and done:
            continue
        if done:
            continue
        unread_wip.append(cells)
    unread_mb = []
    auto_seen = set()
    if os.path.isfile(MAILBOX_MD):
        first_run = not os.path.isfile(state_path(me))
        theirs = []
        for cells in parse_rows_table(open(MAILBOX_MD, "r", encoding="utf-8").read(), 7):
            rid, when, direction, topic, status = cells[0], cells[1], cells[2], cells[3], cells[-1]
            if not direction.strip().startswith(other):
                # 「方向」列写作 `CodeArts → Qoder`；只看发件人是我对面的那一方
                continue
            theirs.append((rid, when, topic, status))
        # 第一次跑（没有 state）：历史 DONE/ACK 条目按已读建基线，
        # 但**最近 5 条一律列出来**，免得「刚写完还没读的回复」被当成历史吞掉。
        if first_run:
            for rid, _w, _t, status in theirs[:-5]:
                if any(x in status for x in DONE_WORDS):
                    auto_seen.add(rid)
        for rid, when, topic, status in theirs:
            if rid in seen_mb or rid in auto_seen:
                continue
            unread_mb.append((rid, when, topic, status))
        if first_run:
            print("（首次运行：MAILBOX 历史 DONE/ACK 已按已读建基线，只列最近未读的 %d 条；"
                  "之后以 state 文件为准）" % len(unread_mb))
    changed, cur = changed_files(st.get("snapshots", {}))
    st["snapshots"] = cur
    if auto_seen:
        st["seen_mailbox"] = sorted(set(st.get("seen_mailbox", [])) | auto_seen)
    save_state(me, st)
    mine = sorted(c for c in changed if who_owns(c) == me)
    theirs = sorted(c for c in changed if who_owns(c) != me and who_owns(c) != "共享")
    shared = sorted(c for c in changed if who_owns(c) == "共享")

    if args.brief:
        n = len(unread_wip) + len(unread_mb)
        print("[wip] %s 未读：WIP %d 条 / MAILBOX %d 条；对方新落盘 %d 个文件"
              % (me, len(unread_wip), len(unread_mb), len(theirs)))
        if n or theirs:
            print("[wip] 本轮开工前先跑：python scripts/wip.py inbox --who %s" % me)
        return 0

    print("=== inbox for %s（%s）===" % (me, now()))
    print("--- %s 写给我、我还没签字的 WIP 落盘 ---" % other)
    if not unread_wip:
        print("  （无）")
    for cells in unread_wip:
        print("  %s %s [%s/%s] %s\n      文件: %s\n      影响: %s" %
              (cells[0], cells[1], cells[3], cells[4], cells[6], cells[5], cells[7]))
    print("--- MAILBOX 里 %s 写给我、我还没读的条目 ---" % other)
    if not unread_mb:
        print("  （无）")
    for rid, when, topic, status in unread_mb:
        print("  %s %s | %s | 状态=%s" % (rid, when, topic, status or "-"))
    print("--- 磁盘上自上次 checkpoint 的变更（按归属）---")
    print("  我(%s)这边: %d 个" % (me, len(mine)))
    for c in mine[:40]:
        print("    %s" % c)
    print("  %s 那边: %d 个" % (other, len(theirs)))
    for c in theirs[:40]:
        print("    %s" % c)
    if shared:
        print("  归属未登记（先问对方再动）: %d 个" % len(shared))
        for c in shared[:20]:
            print("    %s" % c)
    if unread_wip or unread_mb:
        print("=> 有未读：处理完请 `python scripts/wip.py read --who %s <编号>` 签字" % me)
    else:
        print("=> 收件箱干净")
    return 0


def cmd_snapshot(args):
    st = load_state(args.who)
    changed, cur = changed_files(st.get("snapshots", {}))
    st["snapshots"] = cur
    save_state(args.who, st)
    print("snapshot saved for %s: %d files" % (args.who, len(cur)))
    return 0


def main():
    ap = argparse.ArgumentParser(description="三生鸿蒙 WIP 落盘流水 + 收件箱")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_log = sub.add_parser("log", help="记一条中间落盘")
    p_log.add_argument("--who", required=True, choices=["Qoder", "CodeArts"])
    p_log.add_argument("--milestone", required=True, help="如 M3 / M2 / H-042")
    p_log.add_argument("--status", default="WIP", choices=["WIP", "READY", "BLOCKED"])
    p_log.add_argument("--files", required=True, help="逗号分隔的相对路径")
    p_log.add_argument("--doing", required=True)
    p_log.add_argument("--impact", default="")
    p_log.set_defaults(func=cmd_log)

    p_inbox = sub.add_parser("inbox", help="看对方的新落盘/新信 + 磁盘变更")
    p_inbox.add_argument("--who", required=True, choices=["Qoder", "CodeArts"])
    p_inbox.add_argument("--brief", action="store_true")
    p_inbox.set_defaults(func=cmd_inbox)

    p_read = sub.add_parser("read", help="给对方条目签「已读」")
    p_read.add_argument("--who", required=True, choices=["Qoder", "CodeArts"])
    p_read.add_argument("ids", nargs="+")
    p_read.set_defaults(func=cmd_read)

    p_snap = sub.add_parser("snapshot", help="只刷新磁盘快照（不打印）")
    p_snap.add_argument("--who", required=True, choices=["Qoder", "CodeArts"])
    p_snap.set_defaults(func=cmd_snapshot)

    args = ap.parse_args()
    # Windows 控制台 gbk：统一 utf-8，打不出来的换 ?，别把诊断吞了
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
