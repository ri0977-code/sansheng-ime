# `_probe/` 里被台账引用的证据副本

整理：Qoder　登记：2026-10-30 07:5x　工单：H-282　口径：D-034

`_probe/` 是 26.8 MB 的调研草稿目录，按 D-034 不入 git；但 docs/ 里有 133 处引用指向它，仓库推到 GitHub 后那些就是死链。本目录把这些**被点名引用**的原件逐字节复制过来（不是移动，`_probe/` 原样留在本地），并把每条被哪几行台账引用一并列出，所以旧写法 `_probe/xxx` 在这里能按文件名找到对应副本。

生成命令：`python scripts/import_probe_cited_evidence_qoder.py`（`--check` 只核对不写盘）。副本与源文件 sha256 逐条相等，下表哈希取前 16 位。

| 副本路径 | 字节 | sha256(前16) | 引用它的台账文件 |
|---|---|---|---|
| `docs/evidence/_probe-cited/bench_enword_translator_qoder.py` | 7231 B | `b3f9542ad3efe78c` | `docs/HANDOFF.md`, `docs/ISSUES.md`, `docs/MAILBOX.md`, `docs/PROGRESS.md` |
| `docs/evidence/_probe-cited/enWord_Filter.userfreq.lua` | 21830 B | `3ea8189d19c0d486` | `docs/ISSUES.md`, `docs/MAILBOX.md` |
| `docs/evidence/_probe-cited/gen_en_word_rev.py` | 3279 B | `ca3093c6d4b8e162` | `docs/MAILBOX.md` |
| `docs/evidence/_probe-cited/h272-harmony-verify.txt` | 4129 B | `29fb54b273d2d957` | `docs/HANDOFF.md`, `docs/MAILBOX.md` |
| `docs/evidence/_probe-cited/h274-perkey-cost.txt` | 663 B | `cfd8a813cb121e76` | `docs/ISSUES.md` |
| `docs/evidence/_probe-cited/krun_cost_qoder.py` | 4847 B | `be4b0e2130e0ee50` | `docs/HANDOFF.md`, `docs/MAILBOX.md` |
| `docs/evidence/_probe-cited/mate80-cap4.txt` | 1643007 B | `0092e7d6f818ec34` | `docs/evidence/2026-10-30/release-app/H-280-app-1.0.0-release-build.md` |
| `docs/evidence/_probe-cited/module_load_cost_qoder.py` | 4231 B | `244a3d441bfeafff` | `docs/MAILBOX.md` |
| `docs/evidence/_probe-cited/patches-20261029/enWord_translator.lua.qoder-v32-indexed` | 8547 B | `2583bc5e35e39a75` | `docs/HANDOFF.md`, `docs/ISSUES.md`, `docs/MAILBOX.md`, `docs/PROGRESS.md` |
| `docs/evidence/_probe-cited/rawfile-backups-20261029/enWord_translator.lua.bak-qoder-20261029-143x-before-bisect` | 6478 B | `c26ecb379cabee0a` | `docs/MAILBOX.md` |
| `docs/evidence/_probe-cited/rawfile-backups-20261029/enWord_translator.lua.peer-v31-20261029-144338` | 5887 B | `9f85b93835378905` | `docs/HANDOFF.md`, `docs/MAILBOX.md`, `docs/PROGRESS.md` |
| `docs/evidence/_probe-cited/rawfile-backups-20261029/enWord_translator.lua.peer-v34-20261029-150548` | 3570 B | `1ad09f089d40fc60` | `docs/HANDOFF.md` |
| `docs/evidence/_probe-cited/rawfile-backups-20261029/enWord_translator.lua.peer-v35-20261029-152449` | 3294 B | `24fccf6ce54d2590` | `docs/ISSUES.md` |
| `docs/evidence/_probe-cited/rime_probe.py` | 7766 B | `39d82b75a0824d7e` | `docs/HANDOFF.md`, `docs/ISSUES.md`, `docs/MAILBOX.md` |
| `docs/evidence/_probe-cited/run_1b_regression.py` | 2494 B | `cab04e81cad8e96d` | `docs/HANDOFF.md`, `docs/ISSUES.md`, `docs/MAILBOX.md` |
| `docs/evidence/_probe-cited/run_harmony_translator_offline_qoder.py` | 5094 B | `a844a15f976c8772` | `docs/HANDOFF.md`, `docs/ISSUES.md`, `docs/MAILBOX.md`, `docs/PROGRESS.md` |
| `docs/evidence/_probe-cited/v1963_popup2.png` | 85248 B | `295a9bec7dc89e30` | `docs/MAILBOX.md` |
| `docs/evidence/_probe-cited/v1964_popup2.png` | 84643 B | `5aa17cc756cd18c5` | `docs/MAILBOX.md` |
| `docs/evidence/_probe-cited/v1965_for_rime.png` | 64517 B | `87c3a68b3276f689` | `docs/MAILBOX.md` |
| `docs/evidence/_probe-cited/v1965_wh2.png` | 54223 B | `79dbc806a8f95f4e` | `docs/MAILBOX.md` |
| `docs/evidence/_probe-cited/verify_bucket_patch_qoder.py` | 2576 B | `091b1b0ea7a31915` | `docs/ISSUES.md`, `docs/MAILBOX.md` |
| `docs/evidence/_probe-cited/win_filter_bench.py` | 5494 B | `45e8f19d6ce246e6` | `docs/HANDOFF.md`, `docs/MAILBOX.md` |
| `docs/evidence/_probe-cited/win_filter_userfreq_test.py` | 10425 B | `9b6e3e4368a3935c` | `docs/HANDOFF.md`, `docs/ISSUES.md`, `docs/MAILBOX.md` |

## 台账里提到但磁盘上没有的路径（写法本身是省略/坏行，不是丢文件）

- `_probe/1965_*.png`（出现于 `docs/MAILBOX.md`）
- `_probe/abbr_candidates_20261021.md`（出现于 `docs/release/legal/third-party-audit-2026-10-22.md`）
- `_probe/build-inputs/stage-v1.10.x`（出现于 `docs/ISSUES.md`）
- `_probe/gen_en_word_ltr_idx.py`（出现于 `docs/MAILBOX.md`）
- `_probe/h272-bucket-eq-cost-20261029.txt`（出现于 `docs/HANDOFF.md`, `docs/ISSUES.md`, `docs/MAILBOX.md`）
- `_probe/h272-win-suite-20261029.txt`（出现于 `docs/HANDOFF.md`, `docs/ISSUES.md`, `docs/MAILBOX.md`）
- `_probe/nova6-1968-upgrade.txt`（出现于 `docs/MAILBOX.md`）
- `_probe/nova6-backup-20261029-170x/`（出现于 `docs/HANDOFF.md`, `docs/MAILBOX.md`, `docs/PROGRESS.md`）
- `_probe/nova6-speed-20261029.txt`（出现于 `docs/HANDOFF.md`, `docs/ISSUES.md`, `docs/MAILBOX.md`, `docs/PROGRESS.md`）
- `_probe/nova6_upgrade_1916_b.py`（出现于 `docs/MAILBOX.md`）
- `_probe/rawfile-backups-20261029/`（出现于 `docs/HANDOFF.md`, `docs/ISSUES.md`, `docs/MAILBOX.md`, `docs/PROGRESS.md`）
