#!/bin/bash
# 三生输入法值守巡检脚本（纯脚本版，不依赖 AI 模型）
# 用法：由 Windows 任务计划程序定时调用
# 逻辑：用 mail_open.py 检测信箱 OPEN 消息 → 有就弹通知

PYTHONIOENCODING=utf-8 python F:/qoderwork/sansheng-ime-harmony/scripts/mail_open.py --who CodeArts
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  PYTHONIOENCODING=utf-8 python F:/qoderwork/sansheng-ime-harmony/scripts/notify_hidden.py "Sansheng IME - 新任务" "信箱有 Qoder→CodeArts 的 OPEN 消息待处理"
  echo "信箱有 OPEN 消息，已弹通知"
elif [ $EXIT_CODE -eq 1 ]; then
  echo "信箱无 OPEN 消息"
else
  echo "mail_open.py 退出码 $EXIT_CODE（用法错误）"
fi