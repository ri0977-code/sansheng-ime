# 应用内许可声明 vs NOTICE 逐项核对 · 2026-10-22 19:1x · Qoder

**为什么做**：`NOTICE` 与 `third-party-declarations.md` 都收口了，但那是「文档版本」。
用户实际看到的是应用内「关于」页。两者必须分开核 —— 今天就在 About 页查出两处缺口（H-099 / H-100）。

## 一、About 页现有 10 项，逐项对 NOTICE

| About 页条目 | 标的许可 | NOTICE 里的记载 | 判定 |
|---|---|---|---|
| CC-CEDICT（zh2en 系列） | CC BY-SA 4.0 | 8 处 | ✅ |
| cn_pinyin_wp | Apache-2.0 | 3 处 | ✅ |
| ECDICT（en2zh_v2 系列） | MIT | 4 处 | ✅ |
| rime-wubi86-jidian | Apache-2.0 | 1 处 | ✅ **但只是极点权重与补充词条那一层** |
| rime-pinyin-simp | Apache-2.0 | 1 处 | ✅ |
| OpenCC | Apache-2.0 | 2 处 | ✅ |
| librime | BSD-3-Clause | 5 处 | ✅ |
| harmonyos-next-rime-har | MIT | 3 处 | ✅ |
| hMixedKeyboard | Apache-2.0 | 4 处 | ✅ |
| kanonIME | MIT | 7 处 | ✅ |

## 二、NOTICE 里有、About 页没有的（按重要性）

| 项 | NOTICE | About | 性质 |
|---|---|---|---|
| **`wubi86.dict.yaml`（86 五笔主码表，2.29 MB，**LGPL-3.0**）** | 4 处 | **0 处有效提及** | **H-100（P1）**：LGPL 告知义务缺口；用户看到的六项里没有最核心的码表 |
| `NOTICE` / `LICENSES/` 本体 | 文件存在 | 指向「安装目录」，但**包里没有** | **H-099（P1）** |
| yaml-cpp | 3 处 | 0 | 随包二进制依赖，MIT；About 页「第三方软件」区可以加一行 |
| leveldb / marisa | 2 / 3 处 | 0 | 同上，均是 librime 静态依赖 |
| Lua（`rime.lua` 及各滤镜） | 6 处 | 0 | MIT；About 页有 `kanonIME` 提到 MIT，但没单列 Lua |
| `symbols/symbols.json`（App 面板数据） | 2 处 | 0 | dyy 血脉，已在 NOTICE 如实标「授权申请中」；About 页未列 |
| 自研 Lua 滤镜（phoneComment / abbrGloss / codeLookup 等） | 各 1 处 | 0 | 本项目自写，不列不算缺，但可统一在 notice.html 里看到 |

**结论**：About 页是「精选摘要」而非完整清单，这在产品上是合理的 —— 摘要 + 一个「完整许可声明」入口即可。
**所以 H-099 修好（能打开 notice.html）之后，第 3 行起的这些项都自动可见，无需逐项加到 About 页。**
唯一必须在摘要里补的是 **LGPL 的 wubi86**：因为摘要现在把它和 Apache 的极点层混成了一项，不补会误导。

## 三、签名与发布凭据的时间核验（顺带做的，无风险）

| 项 | 结果 |
|---|---|
| 发布 Profile（`sign/release/sansheng-release.p7b`）证书链 | 华为根 → 签名服务 CA → HOS Profile Management，3 张齐全 |
| HOS Profile Management 有效期 | **2023-04-24 → 2028-04-24** ⇒ 距提审还有 1.5 年，不是风险 |
| 调试 Profile（`sanshengDebug.p7b`） | 链完整，Debug 版 Profile Management |
| `.cer` 文件内容 | 是华为根证书（公开），不是我们的签名证书本体 —— 与 README 的描述一致 |

> 注：只读了公开证书链，**没有读取任何私钥，也没执行 `openssl pkcs12 -info`**（禁做项）。

## 四、这条核对以后每次都要做

提审前按三张表核：
1. **包内实物** —— `python scripts/check_app_content.py`（11 项断言）；
2. **应用内可见文本** —— 本文件第二节（About 页 vs NOTICE）；
3. **对外文案** —— `docs/release/legal/claim-consistency-audit-2026-10-22.md`（功能断言 vs 实测）。

三张表都对上，才算「申报与实物一致」。只核其中一张，就会像今天这样：NOTICE 全对，用户界面里缺两块。
