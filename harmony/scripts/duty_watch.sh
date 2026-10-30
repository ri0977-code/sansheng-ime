# 三生输入法 CodeArts 夜间值守处理剧本（v14）
#C# 由 cron 每 5 分钟调用。严格守 NIGHT-WATCH-V10.md + D-030 边界。
# v13 改进：检测到 OPEN 后输出消息内容，让 cron AI 会话能自动处理（写 ACK + commit）。
# v14 改进：ACK 后自动清理已回执的 OPEN 状态列，防止反复检出同一消息。
# 守则：不写业务代码 / 不构建 / 不装机 / 不注入真机。只处理信箱沟通与合规类事务。

REPO="F:/qoderwork/sansheng-ime-harmony"
MAILBOX="$REPO/docs/MAILBOX.md"
NOTIFY="PYTHONIOENCODING=utf-8 python $REPO/scripts/notify_hidden.py"

cd "$REPO" || exit 2

# 1. 并发保护：主会话 20 分钟内活跃则本轮只读
LAST=$(date -r docs/PROGRESS.md +%s 2>/dev/null || echo 0)
NOW=$(date +%s)
if [ $((NOW - LAST)) -lt 1200 ]; then
  echo "主会话活跃（PROGRESS 20 分钟内），本轮只读，不处理"
  exit 0
fi

# 2. 先清理已 ACK 但状态仍为 OPEN 的行（防止反复检出同一消息）
PYTHONIOENCODING=utf-8 python "$REPO/scripts/mail_ack_cleanup.py" 2>/dev/null

# 3. 检测 OPEN 消息
PYTHONIOENCODING=utf-8 python "$REPO/scripts/mail_open.py" --who CodeArts -v
EXIT=$?

if [ $EXIT -eq 1 ]; then
  echo "信箱无 OPEN 消息"
  exit 0
fi

if [ $EXIT -ne 0 ]; then
  NOTIFY "Sansheng IME" "信箱巡检异常，请人工查看"
  echo "mail_open.py 异常，退出码 $EXIT"
  exit $EXIT
fi

# 4. 有 OPEN：弹通知 + 输出 OPEN 行内容供 cron AI 会话处理
NOTIFY "Sansheng IME - 新任务" "信箱有 Qoder 委托，正在自动处理"

echo "=== OPEN 消息内容 ==="
# 输出 MAILBOX 中最后 5 条消息（包含 OPEN 行），供 cron AI 会话读取处理
tail -5 "$MAILBOX"
echo "=== 请处理以上 OPEN 消息：读 MAILBOX.md 理解内容，写 ACK 回复追加到 MAILBOX.md 末尾，git add + commit ==="
echo "=== 边界：不碰 entry/src/** 的业务代码，不构建，不签名，不装机 ==="
exit 0