# 收到 CodeArts 交付后 · 我这边的六步（2026-10-23 14:5x · Qoder）

> **用途**：他交齐收口五件＋交付行（带「本机构建」字节数）后，我照这个走。一步都不许跳。
> **铁律复述**：不碰 `sign/**` 密钥内容、不问不写任何密码；同一个 HAP 不重复安装；真机用完只 `power-shell suspend`；夜里不跑 `release_build.ps1`。

---

## 0. 接住交付行（5 分钟，只读）

```bash
# ① 他报的数进得来吗：WIP 最新行有「CodeArts 署名 + unsigned 字节数 + 未被回抄」
PYTHONIOENCODING=utf-8 python scripts/h106_precheck.py
```
期望：`台账有待验收的 CodeArts 交付行` OK、`交付行含 unsigned 字节数` OK。
若 `交付字节数标注了构建来源` 是 warn ⇒ 他没写「本机构建」，先在 MAILBOX 里让他补一句（**别拿这个数去比**——本机有 271,577 B CRLF 漂移）。

## 1. 等他静置 ≥120 秒

`h106_precheck.py` 的 `代码已静置 >=120s` 那一条就是干这个的。不过就等，**不许提前构建**。

## 2. 强制全量独立构建（不用他的产物）

```bash
powershell -ExecutionPolicy Bypass -File scripts/build.ps1
```
期望输出形如 `BUILD OK: ...entry-default-unsigned.hap (28,xxx,xxx bytes)`。
**认「32 executed」**，不要「N executed / M up-to-date」（up-to-date = 复用，不是独立构建——10:1x 我在这上面栽过一次）。

## 3. 只比字节数（不比 hash）

| 我方量到 | 他交付行写的 | 判定 |
|---|---|---|
| unsigned 28,164,312 B | unsigned 28,164,312 B（本机构建） | ✅ 一致，进第 4 步 |
| 不一致 | — | ❌ 停手，写 MAILBOX 说明差多少，**不 sign、不 install** |

## 4. 内容闸门（16 项）

```bash
# 裸 HAP 先跑一遍（⑩ 允许 WARN）
PYTHONIOENCODING=utf-8 python scripts/check_app_content.py entry/build/default/outputs/default/entry-default-unsigned.hap
```
期望：**16/16**（探针页摘掉后 ⑩ 也该 PASS）。有阻断项 ⇒ 打回，不装机。

## 5. 签名 + 装机（要主人在场输密码）

```bash
# 签名（会向主人要一次密钥密码 —— 我不碰）
powershell -ExecutionPolicy Bypass -File scripts/release_build.ps1
```
这条链会自己做：构建 → 签名 → **内容闸门（不过就把 `.app`＋`.sha256` 改名隔离再抛错）** → 打 `.app` → 归档到 `F:/qoderwork/sansheng-release-artifacts`。
装机用 `scripts/install.ps1`（**同一个 HAP 只装一次**）。

## 6. 装机后

| 顺序 | 动作 | 判据 |
|---|---|---|
| 6.1 | `hdc shell bm dump -n com.sansheng.ime \| grep updateTime` | 是本次时间（证明装的是新版） |
| 6.2 | `hdc shell ime -g` | `com.sansheng.ime` |
| 6.3 | 真机回归：照 `docs/evidence/2026-10-23/final-package-device-regression.md` 走 | 八条功能＋本轮专项 |
| 6.4 | 归档 | `python scripts/archive_release_artifacts.py --write` |
| 6.5 | 重拍 5 张商店截图 | 照 `docs/release/store/screenshot-reshoot-script.md` |
| 6.6 | 打 release `.app`（若第 5 步没打） | 16/16 才许交 |
| 6.7 | 手机休眠 | `hdc shell power-shell suspend` |
| 6.8 | 写台账 | ISSUES 对应行改 VERIFIED／PROGRESS 一行／WIP 复核行（**回抄他的字节数**） |

---

## 我自己的验收行怎么写（WIP 9 格）

```
| W-2xx | 2026-10-23 15:3x | Qoder | H-096 | VERIFIED | docs/... | 独立全量重编 28,xxx,xxx B（N executed），与他报 unsigned 一致；16 项闸门 16/16；装机后 updateTime=15:2x、ime=com.sansheng.ime；真机八条＋专项全过 | 截图 5 张已重拍 | 已读 |
```

**复核行必须回抄他报的字节数** —— 不回抄，`h106_precheck.py` 会把同一行交付当成「还没验收」，我就可能重复构建同一个 HAP（02:5x 修过的互等死锁）。
