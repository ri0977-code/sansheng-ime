# 三生输入法权限清单

**适用版本**：HarmonyOS 1.0.0 及后续版本（以实际安装包为准）
**核对日期**：2026-10-22
**核对依据**：`entry/src/main/module.json5` 的 `requestPermissions` 字段

## 一、已声明的权限

| 权限 | 用途 | 触发场景 | 是否必需 | 拒绝后的影响 |
|---|---|---|---|---|
| `ohos.permission.VIBRATE` | 按键轻振反馈 | 按下键盘按键时 | 否 | 键盘仍可正常输入，仅无振动反馈；设备无振动器时同样静默降级 |

本应用没有申请其他任何权限。

## 二、未声明的敏感权限

本应用**未声明**以下权限，因此无法访问对应能力：

- 网络：`ohos.permission.INTERNET`、`ohos.permission.GET_NETWORK_INFO`
- 位置：`ohos.permission.LOCATION`、`ohos.permission.APPROXIMATELY_LOCATION`
- 相机：`ohos.permission.CAMERA`
- 麦克风：`ohos.permission.MICROPHONE`
- 通讯录：`ohos.permission.READ_CONTACTS`、`ohos.permission.WRITE_CONTACTS`
- 日历、通话记录、短信
- 相册/媒体：`ohos.permission.READ_IMAGEVIDEO`、`ohos.permission.WRITE_IMAGEVIDEO`
- 剪贴板：本应用未调用剪贴板读取接口
- 设备标识：本应用未读取 OAID、IMEI、设备序列号等标识

## 三、不属于权限的系统能力

| 能力 | 用途 | 是否上传 |
|---|---|---|
| 输入法服务（InputMethodExtensionAbility） | 接收系统输入法框架的按键与编辑事件 | 否，全部本机处理 |
| 屏幕尺寸与方向 | 横竖屏键盘布局计算 | 否，不保存 |
| 应用沙箱存储 | 保存用户词典、自造词与设置 | 否，仅本机 |

## 四、复核方式

发布新版本前，应重新核对 `module.json5`，确认没有新增权限；如新增权限，必须同步更新本清单、隐私政策与应用市场隐私表单。
