# 标点数据合并方案（D-020 选 A 的落地口径）

> ## ⚠ 本方案作废（2026-10-22 15:5x 复核后由作者本人撤回）
>
> 两个前提都被测量否掉了，数字见 `docs/evidence/2026-10-22/d-020-landing-audit.md`：
>
> 1. **「多义标点和 `/` 符号会随删文件而失效」不成立。** 已签名发布包解出来看，`punctuator` 走的始终是
>    `wubi_pinyin.custom.yaml:77 import_preset: default`，而自有 `default.yaml` 的 `half_shape` 是 32 个**单值**键、
>    没有 `symbols` 块 ⇒ 那 8 个多值标点键和 105 组 `/xx` 在任何构建里**都没生效过**，不存在需要「保一项都不丢」的东西。
>    桌面端（dyy 原配 `:49` 与主人现行 `:66`）用的是 `import_preset: symbols`，这条线在移植时被改成了 `default`，
>    所以「并表」是把我自己搞错的因果当成需求。
> 2. **下文「`symbols.custom.yaml` 与安卓同名文件逐字节相同 ⇒ 自有整理数据，无第三方许可问题」是错的。**
>    逐字节相同只证明两个端发的是同一份文件，不证明来源。安卓版自己的 `THIRD_PARTY_NOTICES.md` 第 41/96 行
>    白纸黑字写着它是「dyy 斜杠符号表的改版（清 `None` 占位 + 补释义），主体版权归 dyy」；
>    我这边和 `dyyRime-master/symbols.custom.yaml` 逐行比，105 组里只有 15 行差异，全是删掉的 `None` 占位项。
>    ⇒ 它属于 `NOTICE` 里「授权申请中」那一档，不能当自有数据。`NOTICE` 与
>    `docs/release/legal/third-party-declarations.md` §四 已按实测改成如实表述。
>
> 结论：**不做并表**。1.0.0 的符号输入由 App 自己的符号面板承担（H-061 已验收；注意面板数据 `symbols.json`
> 同样派生自这张 dyy 表，已在声明里更正）。给 CodeArts 的三条改法见 `docs/MAILBOX.md` M-079。

**作者**：Qoder · 2026-10-22 15:2x
**用途**：主人已拍板 1.0.0 不带上游 `symbols.yaml`（见 `docs/DECISIONS.md` D-020）。本方案给出**不依赖任何第三方数据**的替代做法，
让本轮真正需要的「多义标点」和 `/` 模式符号输入**一项都不丢**，同时把包内标点数据变成 100% 自有。
**改法由 CodeArts 决定与实施，我不碰 `entry/src/**`。**
**（保留原文仅供追溯，判据以本文件顶部作废声明为准。）**

## 一、先说结论：要保留的东西本来就在我们自己的文件里

关键事实（实测）：`entry/src/main/resources/rawfile/rime/symbols.custom.yaml`（11,696 B，md5 `b1e28d38ede993a7403b8087c55bc194`）
与主人安卓版数据根的同名文件
`F:/dshdesktopwork/sansheng-ime-android/rime/symbols.custom.yaml` **逐字节相同**（`diff` 0 行差异）⇒ **自有整理数据，无第三方许可问题**。

它里面已经有两个块：

| 块 | 位置（行号） | 内容 | 与本轮的关系 |
|---|---|---|---|
| `punctuator/half_shape/+` | 第 10–31 行 | 20 个键的多义标点（含 `[` → ［【〔、`'` → ‘’「」、`"` → “”『』） | **就是待补测 H-06x 那条「多义标点」的全部内容** |
| `punctuator/symbols/+` | 第 32–41 行 | `/zt` `/tj` `/jd` `/dc` `/lm` `/lmd` `/szd` `/szk` `/szm` 九组 `/` 模式符号 | **待补测的「九键 `/szd`」在这一块** |

也就是说：**这两块跟上游 `symbols.yaml` 没有关系**，它们是我们自己文件里的 patch 条目。
上游那份文件独有的只有 `/py`（拼音字母）、`/pp`（偏旁）、`/kx`（康熙部首）、`/bz`（笔画）、`/zb`（注音）等分节
——主人已确认这些不进 1.0.0。

## 二、为什么现在必须搬：`symbols.custom.yaml` 会变成死文件

`*.custom.yaml` 是**对同名 preset 的补丁**。`symbols.custom.yaml` 只有在某个 schema
`punctuator/import_preset: symbols` 时才会被读到。D-020 之后 `import_preset` 回 `default` ⇒
这个文件**不再被任何地方引用**，里面那 20 个键和 9 组符号会**一起失效**（表现为：`[` 只出「【」不再多义、`/szd` 无候选）。
所以「删掉上游 symbols.yaml」必须和「把这两块并进 `default.yaml`」同一次做，否则功能回退。

## 三、建议改法（一次提交内完成）

1. 把 `symbols.custom.yaml` 第 10–31 行的 20 个键，逐条并进自有 `default.yaml` 的 `punctuator.half_shape`
   （**覆盖同名单值项**，例如现在是 `"[": "【"`，改成 `"[": ["［", "【", "〔"]`；`"'": "’"` 改成 `"'": ["‘", "’", "「", "」"]`）。
2. 把第 32–41 行的 9 组并进 `default.yaml` 的 `punctuator.symbols`（`default.yaml` 目前**没有** `symbols` 小节，是纯新增）。
3. 删除 `rawfile/rime/symbols.yaml` 与 `rawfile/rime/symbols.custom.yaml`，并从
   `RimeDataInstaller.ets` 的 `SHARED_FILES` 里同时摘掉这两项；`DATA_VERSION` `m8-parity-v19` → **v20**（词库下发清单变了必须升）。
4. `wubi_pinyin.custom.yaml` 的 `punctuator/import_preset` 回 `default`。
   **同一份 diff 里被删掉的 `script_translator@pinyin` 那 14 行请单独处置（H-089），两件事不要混。**

### 必须一起检查的两个坑

- **`recognizer/patterns/punct`（实测已查，这是个真缺口）**：`/` 模式要有 `punct` 识别式才出候选。
  逐文件检索 `punct:` 命中数：`wubi_pinyin.custom.yaml` **1**（`"^/([0-9]0?|[A-Za-z]+)$"`，`/szd` 能被 `[A-Za-z]+` 匹配）、
  `pinyin_simp.schema.yaml` **1**，但 **`sansheng_t9.schema.yaml` 0 命中、`wubi_pinyin.schema.yaml` 0 命中、自有 `default.yaml` 的 patterns 里也只有 email/uppercase/url**。
  ⇒ **九键（T9）现在根本没有 `punct` 识别式**，「九键 `/szd`」这条待补测在 T9 下不可能通，与 `symbols.yaml` 在不在无关。
  并入 `default.yaml` 时请**顺带在 `default.yaml` 的 `recognizer/patterns` 里补一条 `punct`**（三个方案都 `import_preset: default`，一处补齐三处生效），
  否则这条待验项会继续挂着。
- **`full_shape` 空块**：`symbols.custom.yaml` 第 8–9 行的 `punctuator/full_shape/+` 是**空的**（注释写「全角标点暂不做处理」），
  搬的时候不要把它当成有内容搬过去。

## 四、我这边的验收判据（改完我逐条量，不看构建是否绿）

1. `grep -c "symbols" entry/src/main/resources/rawfile/rime/*.yaml` 里**不再有** `symbols.yaml` / `symbols.custom.yaml` 两个文件；
   `SHARED_FILES` 里两项已摘除；`DATA_VERSION` 为 v20。
2. `default.yaml` 的 `punctuator.half_shape` 中，`[` `]` `'` `"` `_` `#` `^` `` ` `` `$` 这 9 个键的值是**列表**（多义），
   且逐条与 `symbols.custom.yaml` 原第 10–31 行**字面相同**（我按行比对，保证没混进上游数据）。
3. `default.yaml` 新增的 `punctuator.symbols` 恰好 9 组：`/zt` `/tj` `/jd` `/dc` `/lm` `/lmd` `/szd` `/szk` `/szm`；
   上游独有的 `/py` `/pp` `/kx` `/bz` `/zb` **不出现**（出现即说明是从上游文件抄的，D-020 就被破坏了）。
4. 真机（等 CodeArts 出签名 debug HAP、设备空闲）：`[` 连按出 ［【〔；`'` 连按出 ‘’「」；九键 `/szd` 出 ⒈⒊；横屏翻页正常；
   26 键 `nihao` 候选条数不低于 M5 已验证的口径（H-089 一并复测）。
5. `NOTICE` 与声明页：本轮**不需要**为标点数据加任何第三方条目（全部自有）；我复核文字后关闭 H-088。

## 五、代价清单（给主人看的，一句话版）

砍掉上游 `symbols.yaml` 之后，1.0.0 失去的是：`/py`（带声母韵母符号）、`/pp`（偏旁）、`/kx`（康熙部首）、`/bz`（笔画）、`/zb`（注音）
这几组「打斜杠码出生僻符号」的输入。多义标点（`[` `'` `"` 连按换形）和 `/szd` `/zt` 这类常用符号串**都保留**，
因为它们本来就在我们自己的文件里。
