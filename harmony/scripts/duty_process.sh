#!/bin/bash
# 三生输入法 CodeArts 值守处理循环（v12）
# 被 cron 或 Windows 任务计划每 5 分钟调用
# 逻辑：检测 OPEN 消息 → 有则读信箱、按角色边界处理、写回 MAILBOX、commit

REPO="F:/qoderwork/sansheng-ime-harmony"
MAILBOX="$REPO/docs/MAILBOX.md"
NOTIFY="PYTHONIOENCODING=utf-8 python $REPO/scripts/notify_hidden.py"

cd "$REPO" || exit 2

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

# 有 OPEN 消息：弹通知 + 读信箱末尾让本会话（模型）能看到待处理项
NOTIFY "Sansheng IME - 新任务" "信箱有 Qoder 委托，请处理"
echo "有 OPEN 消息，已通知。待处理项见 MAILBOX.md 末尾 OPEN 行。"
exit 0