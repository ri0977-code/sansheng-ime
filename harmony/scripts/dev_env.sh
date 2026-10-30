#!/bin/sh
# 三生输入法 · Mate 80 真机驱动小工具（H-048 候选栏 v2 验收用）
# 用法：. scripts/dev_env.sh && dshot docs/evidence/2026-10-21/xxx.png
export MSYS_NO_PATHCONV=1
HDC="/d/DevTools/DevEco/DevEco Studio/sdk/default/openharmony/toolchains/hdc.exe"
BUNDLE=com.sansheng.ime

d_shell() { "$HDC" shell "$@"; }
d_tap()   { "$HDC" shell uitest uiInput click "$1" "$2"; }
d_swipe() { "$HDC" shell uitest uiInput swipe "$1" "$2" "$3" "$4" 800; }  # x1 y1 x2 y2
d_ktext() { "$HDC" shell uitest uiInput inputText "$1" "$2" "$3"; }       # id text
d_stop()  { "$HDC" shell aa force-stop "$BUNDLE"; "$HDC" shell aa force-stop "$BUNDLE:inputMethod"; }
d_start() { "$HDC" shell aa start -b "$BUNDLE" -a EntryAbility "$@"; }

# dshot <本地相对路径.png>  截屏并回收到 cwd（hdc file recv 目标必须是相对路径）
dshot() {
  local out="$1"
  mkdir -p "$(dirname "$out")"
  "$HDC" shell rm -f /data/local/tmp/cap.png >/dev/null 2>&1
  "$HDC" shell uitest screenCap -p /data/local/tmp/cap.png >/dev/null
  rm -f cap_recv.png
  "$HDC" file recv /data/local/tmp/cap.png ./cap_recv.png >/dev/null
  cp -f ./cap_recv.png "$out"
  echo "saved: $out"
}
