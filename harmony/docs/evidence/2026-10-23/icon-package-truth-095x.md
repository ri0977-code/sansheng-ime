# 图标两层真相：包内两条引用各是哪张图（H-105/H-108 · 2026-10-23 09:5x）

> 只读量测，对象是 CodeArts 09:09 装的 debug unsigned HAP
>
> **11:3x 部分作废（只这一句是新的，正文一字未改）**：本文「包内两条图标引用是同一图形」只对 **09:09 那份包**成立 —— `73d7d07`（10:02）起能力层 `app_icon.png` 已换成 32,629 B／512 黑底金，应用层仍是蓝底三条键帽 ⇒ 两层已不同图（H-146）。本文「H-108 根因是 `isLauncherApp=false`」那句**已作废**（记事本对照组否证），见同目录 `h108-islauncher-root-cause-retracted-1017.md`。
> `F:\qoderwork\_audit_tmp\2026-10-23\delivery-0909\entry-default-unsigned.hap`
> （**28,202,740 B**，sha256 `2ba817722bb37d3be50061af3fdf2ada620885388b90238cc3d122f1d5f6bbc0`）。
> 目的：把「应用级分层图标」与「能力/启动窗图标」两条引用各自指向哪张图、包里是哪一版，
> 一次钉死，避免再把 H-108 当成「少一张 PNG」。

## 1. 包内实测

| 包内路径 | 字节 | sha256 前 16 |
|---|---|---|
| `resources/base/media/app_icon.png` | 15,931 | `945080b77675e349` |
| `resources/base/media/background.png` | 6,034 | `50f5aebb6cba9908` |
| `resources/base/media/foreground.png` | 8,884 | `e2eb41dcfc9c5ae0` |
| `resources/base/media/layered_image.json` | 81 | `999cc80144382dc4` |

`layered_image.json` 内容：

```json
{"layered-image":{"background":"$media:16777222","foreground":"$media:16777223"}}
```

## 2. 两条引用各指向哪张

| 层 | 引用 | 源文件 | 结论 |
|---|---|---|---|
| 应用级（AGC / 桌面分层图标） | `AppScope/app.json5:7` → `$media:layered_image` | `AppScope/.../background.png` 5,533 B、`foreground.png` 6,258 B；与 `docs/release/store/icon/layered/*-1024.png` 同 sha256 | 包内被 hvigor 重采样成 512（6,034／8,884 B），**像素同图**（05:4x 已量：最大差 1／17，均值 0.417／0.009） |
| 能力 / 启动窗 | `entry/src/main/module.json5:30,32` → `$media:app_icon` | `entry/src/main/resources/base/media/app_icon.png` = 15,931 B，sha256 `945080b77675e349…`，**与 `docs/release/store/icon/gen-appicon-512.png` 逐字节相同** | 512×512 蓝底三条白键帽；**09:09 包里已经是这张，不再是 182 B 的 DevEco 模板** |

⇒ 库里两条路径现在画的是**同一个图形**（蓝底三条键帽），只是应用级走分层、能力层走单张。
AGC 上传件继续用 `icon/layered/preview-216.png`（应用级这条路），**不要**改成 `appicon-216.png`（旧四宫格）。

## 3. 由此改判的两条

1. **H-105 包级已闭**：⑨b 判据（`module.json5` 的 `icon`/`startWindowIcon` 不得是 48×48 模板）
   在 09:09 的 release 包上是 PASS（整包 15/16、阻断 0，唯一未过是 ⑩ 探针页）。
   **仍未验**：启动窗（splash）在真机上的那一眼，留作真机外观项，不再当素材缺陷。
2. **H-108 根因不是图**：09:12 的 `bm dump` 已量到应用级 `isLauncherApp=false`、
   EntryAbility 级 `isLauncherAbility=false`（W-193）⇒ 桌面根本不渲染这个图标。
   09:5x 的包级量测进一步证明**素材层已经是对的**（上表）。所以：
   - 不要再换 `app_icon.png`（W-193 已换过，9b 已转绿）；
   - 剩余工作在 `module.json5`／`app.json5` 的 launcher 声明研究，按归属归 CodeArts；
     W-193 里「按归属归 Qoder」这句与分工表不符，以 `docs/DECISIONS.md`／分工表为准。

## 4. 边界

- 本条只证明**包内素材与引用正确**，不证明桌面上看得见图标（第 ⑯ 项仍需解锁后实拍）。
- 启动窗实际画面未拍；`startWindowIcon` 已指到 512 三键帽，但系统怎么裁、是否显示，仍属真机目视项。
