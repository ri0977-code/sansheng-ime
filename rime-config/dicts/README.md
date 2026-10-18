# rime-config/dicts · 英文词库表版本备份

放的是**本机 `D:\Program Files\Rime` 生效版**的两张中英表，以及本次英文抬权的完整明细。
`rime-config/` 原来只有 4 个 override 文件，词库表不在版本管理内，所以改动无法追溯——现在补上。

| 文件 | 说明 |
| --- | --- |
| `zh2en_pinyin_wp.dict.yaml` | 拼音码→英文。md5 `4f9ad7bf6ed8b9943a01e9807699e69a`（与本机一致） |
| `zh2en_wubi_wp.dict.yaml` | 五笔码→英文。md5 `3caca934ea14b89407d760c98e621929`（与本机一致） |
| `en-weight-plan-6991.json` | 2026-10-17 23:32 实际抬的 6991 行：`code / text / zh / match / table / cur_w / new_w` |
| `en-weight-plan-7007-待审.csv` | 全量方案 7007 条（含未上的 16 条），带把握度分档，可逐条勾 |

改动性质：**只改第 3 字段（权重）**，text/code/stem 与行数一字未动，没有新增或删除任何词条。

改这几张表之前必读（`演进与遗留问题记录.md` 第四节）：

- 新权重 = `0.99 × 该码中文第一名权重`，几何平均抢不过 Lua 注入候选。
- 选词源是 `lua/dic_4w_cn.txt` 的本字释义，匹配允许 `love ↔ to love`，只认主释义；DSH 精选表（`zh2en_pinyin_py` 的 3e7 档）不能兜底。
- 一律「只升不降」，写完要删 `build/wubi86*` 再 `qoder_deploy.bat` 重编。

回滚原件在 `_sansheng_backup/20261017-233232-qoder-en-pos2-live-full7007/`（上一批在 `-184040-`、`-162000-`）。
