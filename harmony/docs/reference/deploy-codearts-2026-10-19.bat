@echo off
REM ============================================================
REM 三生输入法 · 一键部署脚本
REM 用法: deploy.bat
REM 前提: 鸿蒙 7 真机已连接 (USB 或无线调试)
REM ============================================================

setlocal

REM === 路径配置 ===
set "DEVECO_SDK_HOME=D:\DevTools\DevEco\DevEco Studio\sdk"
set "JAVA_HOME=D:\DevTools\DevEco\DevEco Studio\jbr"
set "HDC=D:\DevTools\DevEco\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"
set "PROJECT=F:\codeartswork\_ref_harmonyos-rime\harmonyos-next-rime-har-main"
set "HAP=%PROJECT%\entry\build\default\outputs\default\entry-default-unsigned.hap"

REM === 设置环境 ===
set "PATH=%JAVA_HOME%\bin;%DEVECO_SDK_HOME%\toolchains;%PATH%"

REM === 检查设备 ===
echo [1/4] 检查设备...
"%HDC%" list targets > hdc_list.txt 2>&1
for /f "tokens=1" %%i in ('type hdc_list.txt ^| find /v "" ^| find /v "[Empty]"') do (
    set DEVICE=%%i
)
if "%DEVICE%"=="" (
    echo ? 未检测到设备
    echo.
    echo 请按以下步骤连接设备:
    echo 1. 手机/平板 开启 开发者模式 (设置 > 关于手机 > 连点版本号 7 次)
    echo 2. 开启 USB 调试 (设置 > 系统和更新 > 开发人员选项 > USB 调试)
    echo 3. 用 USB 线连接电脑，或开启无线调试
    echo 4. 重新运行此脚本
    pause
    del hdc_list.txt 2>nul
    exit /b 1
)
echo ? 已连接设备: %DEVICE%

REM === 构建 HAP ===
echo.
echo [2/4] 构建 HAP...
cd /d "%PROJECT%"
set "PATH=%JAVA_HOME%\bin;D:\DevTools\DevEco\DevEco Studio\tools\node;%PATH%"
D:\DevTools\DevEco\DevEco Studio\tools\node\node.exe D:\DevTools\DevEco\DevEco Studio\tools\hvigor\bin\hvigorw.js assembleApp
if errorlevel 1 (
    echo ? 构建失败
    pause
    del hdc_list.txt 2>nul
    exit /b 1
)
echo ? 构建完成

REM === 检查 HAP 产物 ===
echo.
echo [3/4] 检查产物...
if not exist "%HAP%" (
    echo ? 未找到 HAP: %HAP%
    del hdc_list.txt 2>nul
    exit /b 1
)
for %%f in (%HAP%) do set HAP_SIZE=%%~zf
echo ? HAP 大小: %HAP_SIZE% 字节

REM === 安装 HAP ===
echo.
echo [4/4] 安装到设备...
"%HDC%" -t %DEVICE% install "%HAP%"
if errorlevel 1 (
    echo ? 安装失败
    echo.
    echo 可能原因:
    echo 1. HAP 未签名 (需要用 DevEco Studio 签名)
    echo 2. 设备未授权 (请在设备上确认 USB 调试授权)
    echo 3. 系统版本不兼容 (需要 HarmonyOS 7.0+)
    echo.
    echo 建议: 用 DevEco Studio 打开工程，Run > Run 'entry' 自动签名安装
    pause
    del hdc_list.txt 2>nul
    exit /b 1
)
echo ? 安装成功!

REM === 启动应用 ===
echo.
echo 启动应用...
"%HDC%" -t %DEVICE% shell am start -n com.fanxing.rimedemo/.EntryAbility

echo.
echo ========================================
echo ? 部署完成!
echo ========================================
echo.
echo 请在设备上:
echo 1. 打开 设置 > 系统 > 语言与输入法 > 输入法
echo 2. 添加 "三生输入法" 到可用输入法列表
echo 3. 切换输入法，测试是否出现
echo.
echo 如果输入法不在列表中:
echo → 这是闸门①，整条 HAR 路线的可行性在此验证
echo → 如果在: 闸门①通过，可以继续开发键盘 UI 和引擎
echo → 如果不在: 鸿蒙 7 对调试签名输入法有限制，需上架或换策略

del hdc_list.txt 2>nul
pause