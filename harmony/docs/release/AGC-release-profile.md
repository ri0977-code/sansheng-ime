# AGC 发布 Profile（.p7b）点单页 · 主人 5 分钟

> 2026-10-22 12:5x · Qoder · 对应 `docs/release/SIGNING.md` §4/§7
> 现状：发布私钥库 `.p12`、CSR、**发布证书 `.cer` 都已核验落盘**，链条上**只缺 `.p7b` 这一个文件**。

## ✅ 本页使命已完成（2026-10-22 13:40）

主人 13:1x 说「p7b 放好了」，按第二节的落点收讫。第三节列的四步已全部做完并落盘：

| 步 | 结果 |
|---|---|
| Profile 字段核验 | **通过**：`type=release`、`bundle-name=com.sansheng.ime`、`app-distribution-type=app_gallery`、有效期 2026-10-22 11:45 → 2029-10-22 11:45、`apl=normal`（无 ACL）、`app-identifier` 与应用对得上；4,016 B，sha256 `922fe91c…820679`。只读证书与 Profile，未打印任何密钥内容。 |
| `.app` 构建 | **出件**：`entry-default-release-signed.hap` **27,822,532 B**（sha256 `64dfcc2e…3ebd5c`）→ `sansheng-ime-1.0.0-release.app` **11,791,326 B**（sha256 `8dad9f3f…b5b6ef1`）。产物清单与复现命令在 `docs/release/SIGNING.md` §8。**2026-10-23 08:4x：这两个件已不在盘上（00:08 我执行的 `hvigorw clean` 清空了 `entry/build`，机器上无第三处副本（H-144）），留档哈希仅作历史证明** |
| 大小 + SHA-256 入库 | 已写 `docs/release/SIGNING.md` §7/§8 与 `docs/PROGRESS.md` 13:40 行。 |
| 发布私钥机外备份 | **已补齐**：`E:\sansheng-sign-backup\20261022-132646\sign\`（13 文件 + `MANIFEST.sha256.txt`）。**发现并已修正**：09:28 那份旧备份的 `sign/release/` 是空的 —— 发布私钥此前实际无备份。E:/F: 是同一台机器，**仍需主人把 13:26 这份搬到机外第三地**（U 盘/移动盘），这是全项目唯一不可补救的一项。 |

**还差的（都不依赖签名，见第五节）**：软著/电子版权证书、隐私政策外链与 AGC 隐私表单、商店截图重拍。**工信部 APP 备案不在这一列** —— 本行原文把「APP 备案号」算作待办，是 12:5x 的旧口径，同日 13:57 已按 D-018 判免办。
**构建口径提醒**：当前 `.app` 出自**脏工作树**，只算链路验证件，**不可提审**；等 H-106／H-107／H-108 三条收口 + 工作树干净后由 Qoder 重建并重新记 sha256（**10-23 更正**：本行原文写的「H-081 残留三条」已在 10-22 随 H-081/082/084 一起 VERIFIED，不再是重建前提）。release 签名 HAP **任何时候都不要 `hdc install`**。

---

## 一、要点的页面（照这个顺序点）

| 步 | 位置 | 点什么 / 填什么 |
|---|---|---|
| 1 | 登录 [AppGallery Connect](https://developer.huawei.com/consumer/cn/service/josp/agc/index.html)，用你自己那个已实名的开发者账号 | 顶部/左侧进 **「证书、APP ID和Profile」** |
| 2 | 左侧导航栏选 **「Profile」**（不是「证书」） | 右上角点 **「添加」** |
| 3 | 弹窗里 **应用名称** | 选 **「三生输入法」**（就是 `com.sansheng.ime` 那条）。选完 **包名自动填**，看一眼是不是 `com.sansheng.ime` |
| 4 | **Profile 名称** | 填 `sansheng-release-profile`（≤100 字符，随便认得出就行） |
| 5 | **类型** | 选 **「发布」** ← 最容易点错的一格，选「调试」构建脚本会直接报 `profile type is 'debug'` |
| 6 | **选择证书** | 选那条**发布证书**（就是你今天下载 `sansheng-release.cer` 时对应的那条，名字里带 release 的） |
| 7 | **受限 ACL 权限** | **不勾**。输入法这套能力不需要 ACL，勾了反而要把权限申请走一遍 |
| 8 | 点 **「提交」**，回到列表 | 找到刚建的那条，点 **「下载」**，得到 `.p7b` |

如果第 6 步下拉里**找不到发布证书**，说明第 1 步进的账号或项目不对，先别乱建，回来告诉我看到的提示原文。
如果提示账号没有「访问发布类Profile」权限，把提示原文发我，那是角色权限页里勾一下的事。

---

## 二、下载之后：文件必须放哪、叫什么

只有一个地方、只有一个名字，构建脚本认死这个名字：

```
F:\qoderwork\sansheng-ime-harmony\sign\release\sansheng-release.p7b
```

- 从浏览器下载的多半叫 `hello.p7b` 或一串数字，**直接重命名**成 `sansheng-release.p7b`。
- 放到 `sign/release/` 里（那边已经有 `sansheng-release.p12` / `.cer` / `.csr` 三个文件，放一起就对）。
- **别放到 `F:\codeartswork\...\sign\`**——那个目录里只有调试四件套，没有发布私钥，放了也签不出来。
- `.p7b` / `.cer` 里没有私钥，可以放在本机；但**不要发到聊天里、不要贴进任何共享文档、不要 git add**（`sign/` 整个目录本来就不入库）。

弄完在群里说一句「**p7b 放好了**」就行，剩下的跑构建、验签、记指纹是我这边的事。

---

## 三、我拿到文件之后会做什么（你不用管，列出来是为了对齐）

1. `powershell -File scripts/release_build.ps1` → 产出 `entry/build/default/outputs/default/sansheng-ime-<版本>-release.app`。
2. 用 `hdcuitool`/`verify-app` 验签，并解 Profile 里的 **类型必须是 release、包名必须是 `com.sansheng.ime`**（只看这两个字段，不打印密钥）。
3. 把 `.app` 的**大小 + SHA-256** 写进 `docs/release/SIGNING.md` §7 和 `docs/PROGRESS.md`。
4. 提醒你把整个 `sign/` 重拷一份机外（现在手机那份缺 `release/`，E: 那份缺 `.cer`）。**发布私钥丢了就永远发不了新版本**，这是唯一不可补救的一项。

**注意：这个 `.app` 是提审包，不要 `hdc install` 到 Mate 80。** 发布 Profile 不绑设备，装了也起不来；真机回归继续用调试签名的 HAP。

---

## 四、点错了怎么办（官方口径）

| 情况 | 后果 | 处理 |
|---|---|---|
| 类型选成「调试」 | 构建报 `profile type is 'debug'` | 删掉该 Profile，重新按第 5 步建 |
| 应用选成别的项目/应用 | 报 `profile bundle-name is '...'` | 重建，第 3 步看清包名 |
| 证书那条想删/换 | **删证书会连带它签出的所有 Profile 一起失效** | 先建 Profile，别动证书；账号发布证书上限 3 张，我们现在用了 1 张 |
| Profile 数量 | 每个应用最多 100 个 | 够用，不必省 |
| 公钥指纹 | 发布 Profile 建好后，**指纹会自动加到应用**（无需手动配） | 若提示指纹数量到上限（50）再来找我 |

来源：华为官方 [申请发布证书](https://developer.huawei.com/consumer/cn/doc/app/agc-help-add-releasecert-0000001946273961)、[发布应用（含 Profile 概念）](https://device.harmonyos.com/cn/docs/apiref/harmonyos-guides/ide-publish-app)、[申请发布 Profile 步骤梳理](https://harmonyosdev.csdn.net/6a9755712b83d06f0ecaa6f7.html)。

---

## 五、和上架其它材料的先后关系

`.p7b` 到手 → `.app` 出得来，但**提审还差三样**（都不依赖签名；其中原第 2 样「办备案」10-22 已判免办，只剩提审页勾一下）：

1. **软著 / 电子版权证书**（AGC「版权信息」是必填项，普通应用不能勾免责函）；
2. ~~**APP 备案号**（单机应用也要备案）~~ → **更正（D-018，10-22 13:57）**：**免办工信部备案**。华为《应用审核 Checklist》原文「无需备案类型：单机应用、境外应用」；提审页「备案信息」处勾 **「单机应用」**（口径表 `docs/release/store/listing.md` §8 第 15 行，判定与依据 `docs/release/standalone-no-filing.md`）。**本页 13:40 收稿时漏改了这一节**，代价是一条永久硬约束：**任何版本不得新增网络权限**；
3. **隐私政策外链 + AGC 隐私表单**（对齐「本机处理、不联网」）。

商店截图等 **H-106／H-107／H-108** 收口后重拍，别用返工前的图提审（**10-23 更正**：原文把 H-081/H-082 当前提，那两条含 H-084 已 10-22 VERIFIED）；这一拍是 owner-bound —— 夜里不点主人屏幕，也不拿返工前的图交。
