# -*- coding: utf-8 -*-
"""一次性清理：修复看门狗 REASSIGN 自我循环造成的污染。

- 删 MAILBOX 里全部 [REASSIGN] 噪音行（看门狗 23:52 后每 5 分钟写 11 条，264 行）
- 删 docs/KANBAN.md（已迁到 .kanban/KANBAN.md，docs/ 下不再刷新，避免催眠 Qoder 值守）
- 留一条只读通知行说明看板新路径
- watchdog.json 记入已改派 ID，防止看门狗再改派同一批任务
"""
import io
import json
import os
import re

ROOT = r"F:\qoderwork\sansheng-ime-harmony"
MAIL = os.path.join(ROOT, "docs", "MAILBOX.md")
KANBAN_DOC = os.path.join(ROOT, "docs", "KANBAN.md")
STATE = os.path.join(ROOT, ".kanban", "watchdog.json")

# 1) 清理 REASSIGN 噪音行
s = io.open(MAIL, encoding="utf-8", newline="").read()
lines = s.split("\n")
keep = [ln for ln in lines if "[REASSIGN]" not in ln]
removed = len(lines) - len(keep)

# 2) 留一条只读通知（就一条，之后 MAILBOX 只由 agent 通信写入）
ids = [int(m[2:]) for m in re.findall(r"\| (M-\d+) \|", "\n".join(keep))]
next_id = (max(ids) + 1) if ids else 1
note = (
    "| M-%d | [看门狗] 看板已迁至 .kanban/KANBAN.md（docs/ 下不再渲染，避免刷新 mtime 让 Qoder 值守误判主人在线而只读）；"
    "CodeArts 卡死任务已在看板改派 Qoder，此后看门狗不再重复写 MAILBOX | 2026-10-26 00:10 | 看门狗→全员 | "
    "**只读通知** | — | 无 | — | 路径变更+去重说明 |" % next_id
)
out = "\n".join(keep)
if not out.endswith("\n"):
    out += "\n"
out += note + "\n"
io.open(MAIL, "w", encoding="utf-8", newline="").write(out)
print("removed REASSIGN rows: %d | notice row: M-%d" % (removed, next_id))

# 3) 删 docs/KANBAN.md
if os.path.exists(KANBAN_DOC):
    os.remove(KANBAN_DOC)
    print("removed docs/KANBAN.md")

# 4) watchdog.json 记已改派 ID
stalled_ids = ["M-177", "M-178", "M-180", "M-181", "M-182", "M-184",
               "M-186", "M-187", "M-190", "M-191", "M-205", "M-206", "M-207", "M-208"]
try:
    d = json.load(io.open(STATE, encoding="utf-8"))
except Exception:
    d = {}
d["reassigned_ids"] = sorted(set(d.get("reassigned_ids", [])) | set(stalled_ids))
d["reassigned"] = []
json.dump(d, io.open(STATE, "w", encoding="utf-8", newline=""), ensure_ascii=False, indent=2)
print("reassigned_ids (%d): %s" % (len(d["reassigned_ids"]), d["reassigned_ids"]))

# 5) 自检：MAILBOX 里不应再有 REASSIGN
txt = io.open(MAIL, encoding="utf-8", newline="").read()
print("self-check REASSIGN remaining:", txt.count("[REASSIGN]"))
