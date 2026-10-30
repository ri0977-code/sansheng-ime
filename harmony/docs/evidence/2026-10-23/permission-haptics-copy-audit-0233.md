# 权限与触感文案交叉核（02:3x · Qoder · M6③／M6⑤）

> 起因有两条：① H-064 留了一条铁律「任何文档不得写『触感已验』」，需要确认对外文案没有踩线；
> ② `listing.md` §8 第 14 项写着「只有 `VIBRATE`，非敏感非受限 ⇒ 不需要使用场景视频」，
> 这是提审时要照抄的对外判断，得看它在包内与文案里是否自洽。
> 本轮只读代码、只改 `docs/**`；没动 `entry/src/**`、没构建、没签名、没装机、没碰手机。

## 一、六个表面逐条实测（全部当场量的，不是引用旧结论）

| 表面 | 实际内容 | 判定 |
|---|---|---|
| 清单声明 | `entry/src/main/module.json5:13-23` 只有一条 `ohos.permission.VIBRATE`，`reason: $string:ime_vibrate_reason`，`usedScene.abilities: [InputMethodService]`，`when: inuse` | 与 §8 第 14 项、`permission-list.md` 一致 |
| 理由文案 | `AppScope/resources/base/element/string.json:24-25` = 「按键时提供轻触振动反馈」 | 与实际调用用途一致（不是空占位） |
| 代码调用点 | `KeyboardIndex.ets:123` import `vibrator`、`:853-855` `startVibration({type:'time',duration:20}, {usage:'touch'})` + `.catch` 静默降级 | 权限确实被使用 ⇒ 不属于「声明未用权限」 |
| 隐私政策 | `docs/release/legal/privacy-policy.md:35`（为提供按键触感调用系统振动能力，不读取振动历史或设备标识）、`:53` 权限表 | 与清单一致，且明确写了失败可正常输入 |
| 权限清单 | `docs/release/legal/permission-list.md:11` 用途／时机／是否可拒／拒绝后果 | 与上面三处同口径 |
| 商店文案 | `listing.md` §2／§3 **没有任何振动或触感承诺** | H-064 铁律未踩线 |
| 说明书 | `operation-manual.md:171`（权限说明）、`:201` FAQ「按键没有振动？」 | 措辞是解释而非承诺，PASS |

## 二、抓到的一处不一致（在源码注释里，不在功能里）

- `KeyboardIndex.ets:52-53` 的 M-037/M-038 文件头注释仍写着：
  「…（**module.json5 不加权限，Qoder 决定**）」。
- 实际：`git log` 显示 `2fea788`（2026-10-22 02:43，H-062「按键触摸体系收口——…／振动权限」）已经把权限加进 `module.json5`，
  并且 H-064 的证据行本身就写着「包内 `ohos.permission.VIBRATE` 已声明并在已安装模块中可见」。
- ⇒ **注释过期**，与随包的清单相互矛盾。功能没坏（降级路径是对的），坏的是「源码自述」与「清单」各说一套。
- 为什么值得记一笔而不是忽略：软著送审的**源程序文档就是从这些 `.ets` 直接生成的**
  （`docs/release/copyright/source-code.html` 里就包含这段文件头注释），送审材料里出现一句与实际清单相反的自我说明，
  后续任何一次交叉核都会被它带偏——我自己这次就先被它带偏了一次（按注释以为包内无权限声明）。
- **处置**：不改代码。一句注释不值当重新出包，重新出包就要主人再输一次密码；
  挂 H-120（P3），随 CodeArts 下一次本来就存在的交付顺手删掉「（module.json5 不加权限，Qoder 决定）」这半句。

## 三、仍然成立的两条限制（别把这张表读成「触感已验」）

1. **振动能否在这台 Mate 80 上真实生效 = 未复核**，仍是 H-064：当时的 hilog 是 `Can not find deviceId property` /
   `InitServiceClient Get service failed` / `StartVibratorOnceEnhanced … ret:75759617`，`hidumper -ls` 无 vibrator SA。
   本轮没有装机、没有碰手机，所以**没有推翻也没有证实**，只确认了「对外文案没有承诺它」。
2. §8 第 14 项「不需要使用场景视频」是**按官方规则做的判断**（VIBRATE 非受限权限），不是实测结论；
   提交时以 AGC 现场表单实际要求为准，若现场要求补充说明，属主人那边的一次填写，不是代码问题。

## 四、复现命令

```
grep -n -A6 requestPermissions entry/src/main/module.json5
grep -n -A2 ime_vibrate_reason AppScope/resources/base/element/string.json
grep -rn "vibrator\|startVibration" entry/src/main/ets --include=*.ets
grep -rn "振动\|触感" docs/release/legal/privacy-policy.md docs/release/legal/permission-list.md docs/release/store/listing.md docs/release/copyright/operation-manual.md
git log --oneline -1 2fea788
```

**踩到的坑（记下来防止再犯）**：第一次 `grep -rn ime_vibrate_reason entry/src/main/resources` 返回空 ⇒ 差点判成「声明了权限但没有理由串」。
理由串在 **`AppScope/resources/base/element/string.json`**（应用级，不在模块级目录）。资源解析路径分 AppScope 与 entry 两层，
grep-0 不等于不存在——这条规则又验证了一次。
