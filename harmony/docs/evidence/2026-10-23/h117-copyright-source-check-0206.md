# H-117 软著送审材料核对（2026-10-23 02:0x，Qoder）

> 触发：闸门排在 H-106 之后、CodeArts 尚未交付，夜里空闲；M6 第④项（软著/电子版权材料）是我自己归属的活，
> 且不碰 `entry/src/**`、不构建、不签名、不装机、不碰手机。这一轮只做「送审那三份文件到底还配不配得上今天的代码」。

## 一、量到的事实（全部可复现，命令附后）

1. **源程序清单是 8 小时前的**。`docs/release/copyright/source-code-manifest.md` 写「生成日期 2026-10-22 / 14 个文件 / 5708 行 / 后 30 页起始全局行号 4209」。
   当前实测同样的 14 个文件共 **5995 行**，4 个文件漂移：

   | 文件 | 登记 | 现在 | 差 |
   |---|---:|---:|---:|
   | `entry/src/main/ets/pages/KeyboardIndex.ets` | 2122 | 2364 | +242 |
   | `entry/src/main/ets/pages/AboutPage.ets` | 382 | 410 | +28 |
   | `entry/src/main/ets/inputmethod/KeyboardController.ets` | 478 | 488 | +10 |
   | `entry/src/main/ets/pages/LegalPage.ets` | 134 | 141 | +7 |

   ⇒ 若现在就把 17:45 那套 PDF 交上去，**页数口径与代码不符**（后 30 页起点应从 4209 走到 4496）。
   README §七第 5 条我自己写的铁律就是这个：「不要用旧 PDF 配新代码」——铁律没有自动检查，靠人记。

2. **有两个源码文件既没进清单、也没写「为什么不含」**：`pages/SettingsPage.ets`（109 行）、`pages/SettingsCategoryPage.ets`（447 行）。
   准确说法是：**昨天 17:45 那轮我确实处理过它们，但结论只写在 `README.md` 的讨论段（"暂不收——等主人对 H-090 拍板"），
   没落到送审那份 `source-code-manifest.md` 的「二、未包含的内容与原因」里**。登记机构看的是 manifest，不是我们的讨论记录。
   而现在 H-090 **已定案**（1.0.0 摘掉应用内设置入口），这个"等拍板"的口子早该关。
3. `main_pages.json` 仍注册 `pages/SettingsPage` 与 `pages/SettingsCategoryPage` ⇒ 这两页**随包编译**；
   但 `Index.ets:79` 的 `openSettings()` 在 `entry/src/main` 全目录 **0 处调用**（grep 实测，仅定义那一行）⇒ 用户打不开。
   说明书通篇没有这两页（只讲系统「设置」）。⇒ 结论：继续排除是对的，但必须**在 manifest 里写明理由**，不能再靠 README 散文。
4. `cpp/include/**`（上游 rime/opencc/marisa/leveldb/yaml-cpp 头文件）与 `cpp/lib/**`（.a/.so 预编译库）**同样从未出现在排除清单里**。
   头文件不是 `.ets/.cpp` 所以没进源程序文档，但「未包含的内容与原因」是登记口径的一部分，缺声明就是缺声明。
5. 说明书 `operation-manual.md:35` 残留一句 **「用户词典与设置只保存在应用沙箱」**。
   这是 18:03 那轮重打时改掉的四处之外**漏掉的第 5 处**，同一类问题：H-104 已判定「全部设置保存在沙箱」这句话本身不成立
   （32/71 个 prefKey 全库 0 消费），H-090 又已把应用内设置入口摘掉 ⇒ 1.0.0 里根本没有用户能改的"设置"。
   实测 1.0.0 真正常写的沙箱数据只有：Rime 用户词典/自造词 + `Index.ets:57-59` 的「已同意隐私提示」标记。
6. 已验证 18:03 那三条修订没被我这次重打覆盖：`关于 → 完整许可声明`（H-099）1 处、`LGPL-3.0`（H-100）1 处、
   `用户词典与自造词不可恢复`（H-090 口径）1 处，均在正文里。
7. `git status` 实测：`entry/src/**` 有 **14 个文件未提交**（CodeArts 工作区，最新一次改动 01:17:02）。
   ⇒ 冻结点不只看"H-106 验完"，还得看"代码已提交"，否则清单里那 14 行「行数」对不上任何一个可复现的版本。

## 二、我做了什么（只动自己归属的文件）

| 文件 | 动作 |
|---|---|
| `docs/release/copyright/operation-manual.md` | 1.4 隐私要点第 4 条拆开重写（见上第 5 条），补一句「本版本（1.0.0）未挂载应用内设置入口」 |
| `docs/release/copyright/operation-manual.html` | `python scripts/build_copyright_manual.py` 重新生成，17,165 B，sha256 `57502258…4e21` |
| `docs/release/copyright/pdf/operation-manual.pdf` | Chrome 无头重打，**12 页 / 1,367,995 B**，sha256 `4a09c032…6e26`（旧 `850007ce…e3bf` 作废） |
| `scripts/build_copyright_source.py` | ① `EXCLUDED` 补 4 条声明（cpp/include、cpp/lib、两个设置页，理由逐条写）；② 新增 `--check`（`--strict` 可选）：扫全仓库 `.ets/.cpp`，任何文件既不在 `SOURCES` 也不在 `EXCLUDED` ⇒ exit 1；并比对 manifest 登记的行数 vs 当前行数报漂移；末尾打 HEAD 短码 + `entry/src` 未提交文件数；③ 扫描跳过 `.cxx`/`build` 等生成目录（`entry/.cxx/**/CMakeCXXCompilerId.cpp` 这类 CMake 生成物不是源码，第一版没剪掉，被我自己的自测抓出来了） |
| `docs/release/copyright/README.md` | §一 更新说明书 PDF 行；§五 换成新哈希（含 md/html 两颗）；§六 把"等 H-090 拍板"改成已定案的排除理由 + 记录这次自我更正 + 冻结命令新增第 0 步 `--check --strict` |

**没有**重新生成 `source-code.txt/html/pdf`：代码还要为 H-106/107/103 改，现在打一套只会立刻又过期，
且会让 txt/html（今天新行号）与 PDF（昨天旧行号）互相不一致。冻结时用第 0 步的 `--check --strict` 卡住，再一条命令重打三件套。

## 三、判据双向验过（这条是给我自己那条铁律用的：坏样本必须先能报错）

```
# 好样本（当前声明表）
$ python scripts/build_copyright_source.py --check
扫描 .ets/.cpp：27 个 ⇒ 清单内 14 / 已声明不含 13 / 未声明 0 / 清单里但文件已不在 0
已打印文档登记的 14 个文件 / 5708 行；当前实际 5995 行 ⇒ 行数漂移 4 个文件
  后 30 页起始全局行号：文档口径 4209，当前应为 4496
代码树指纹：HEAD bd3a4dd，entry/src 未提交改动 14 个文件
结论：通过                    ⇒ exit 0

# 已知坏样本（把两条设置页声明删掉后重跑同一函数）
  [未声明] entry/src/main/ets/pages/SettingsCategoryPage.ets（447 行）—— 既不在 SOURCES，也没在 EXCLUDED 写理由
  [未声明] entry/src/main/ets/pages/SettingsPage.ets（109 行）—— 同上
结论：不通过（有未声明/已消失的文件）  ⇒ exit 1
```

⇒ 好样本 0 / 坏样本 1，判据成立才把这条写进 README 的冻结命令里。

## 四、留给冻结点（不提前做）

1. 闸门四项（H-106 → H-108 → H-107 → H-103）全部验完、且 CodeArts 把工作区**提交**后：
   `python scripts/build_copyright_source.py --check --strict` ⇒ 必须 exit 0（未声明 0、且行数漂移为 0）。
2. 然后 `python scripts/build_copyright_source.py` + Chrome 重打 `pdf/source-code.pdf`，页数、字节、sha256 同步进 README §五 与 manifest §五。
3. H-101 的 A/B 仍等主人拍板：选 A（现在就用 7 张旧图提交）⇒ 说明书画像会过期但代码材料是新的；
   选 B（布局定稿后重拍）⇒ 第 1、2 步与重拍一起做。无论 A/B，**AGC 那 5 张商店截图都要用最终包重拍**。
