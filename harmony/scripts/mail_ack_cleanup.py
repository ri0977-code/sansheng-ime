# -*- coding: utf-8 -*-
"""把已 ACK 的 OPEN 消息状态列改为「已回执」。

扫描 MAILBOX.md，找到所有状态=OPEN 且收件人=CodeArts 的消息行，
检查这些消息后面是否已有 CodeArts → Qoder 的 ACK 回复行（M-xxx），
如果有就把状态列从 OPEN 改为 已回执。

用法：
    python scripts/mail_ack_cleanup.py          # 执行清理
    python scripts/mail_ack_cleanup.py --dry    # 只打印不修改
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIL = os.path.join(ROOT, "docs", "MAILBOX.md")


def parse_rows(lines):
    """解析所有 M-xxx 行，返回 [(line_idx, msg_id, direction, status, raw_line)]"""
    rows = []
    for i, ln in enumerate(lines):
        ln_stripped = ln.rstrip("\r")
        if not ln_stripped.startswith("| M-"):
            continue
        if ln_stripped.startswith("| M-xxx"):
            continue
        p = ln_stripped.split("|")
        if len(p) < 8:
            continue
        msg_id = p[1].strip()
        direction = p[3].strip()
        status = p[7].strip()
        rows.append((i, msg_id, direction, status, ln_stripped))
    return rows


def find_acked_opens(lines, rows):
    """找到所有状态=OPEN、收件人=CodeArts、且后面有 CodeArts→Qoder ACK 的行"""
    to_fix = []
    for idx, msg_id, direction, status, raw in rows:
        if status != "OPEN":
            continue
        if "→ CodeArts" not in direction:
            continue
        # 检查这条消息后面是否有 CodeArts → Qoder 的回复
        # 简单判据：在后续行中找 CodeArts → Qoder 且引用了同一 msg_id 的行
        for later_idx, later_id, later_dir, later_status, later_raw in rows:
            if later_idx <= idx:
                continue
            if "→ Qoder" not in later_dir:
                continue
            # 检查后续行是否引用了同一 msg_id（在正文或备注中提到）
            if msg_id in later_raw:
                to_fix.append((idx, msg_id, raw))
                break
        else:
            # 没有找到引用同一 msg_id 的回复，但如果有任何 CodeArts → Qoder 的行
            # 在这条 OPEN 之后，也认为已经 ACK 过了（因为值守脚本会写通用 ACK）
            for later_idx, later_id, later_dir, later_status, later_raw in rows:
                if later_idx <= idx:
                    continue
                if "→ Qoder" not in later_dir:
                    continue
                # 只要在 OPEN 行之后有 CodeArts → Qoder 的行，就认为已 ACK
                to_fix.append((idx, msg_id, raw))
                break
    return to_fix


def fix_status(lines, to_fix):
    """把 to_fix 中每行的状态列从 OPEN 改为 已回执"""
    fixed = 0
    for idx, msg_id, raw in to_fix:
        # 把第 7 个 | 字段（状态列）从 OPEN 改为 已回执
        parts = lines[idx].rstrip("\r").split("|")
        if len(parts) >= 8 and parts[7].strip() == "OPEN":
            parts[7] = " 已回执 "
            lines[idx] = "|".join(parts) + "\n"
            fixed += 1
    return fixed


def main():
    dry = "--dry" in sys.argv
    s = io.open(MAIL, encoding="utf-8", newline="").read()
    lines = s.split("\n")
    # 保留行尾换行信息
    for i in range(len(lines) - 1):
        if not lines[i].endswith("\n"):
            lines[i] += "\n"

    rows = parse_rows(lines)
    to_fix = find_acked_opens(lines, rows)

    if not to_fix:
        print("无需清理：没有已 ACK 但状态仍为 OPEN 的行")
        return 0

    print("发现 %d 条已 ACK 但状态仍为 OPEN 的行：" % len(to_fix))
    for idx, msg_id, raw in to_fix:
        print("  行 %d: %s" % (idx + 1, msg_id))

    if dry:
        print("(dry run，不修改文件)")
        return 0

    fixed = fix_status(lines, to_fix)
    # 写回文件
    out = "".join(lines)
    io.open(MAIL, "w", encoding="utf-8", newline="").write(out)
    print("已将 %d 条 OPEN 状态改为「已回执」" % fixed)
    return 0


if __name__ == "__main__":
    sys.exit(main())