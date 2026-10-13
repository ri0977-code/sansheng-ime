# 五笔词通 · 安装说明

**五笔拼音中英混输自造词**

一套基于 Rime（小狼毫）的中文输入法方案：五笔字型 + 汉语拼音混输 + 中英双向翻译 + 自动造词。

---

## 一、这是什么

| 能力 | 说明 |
|---|---|
| 五笔 · 拼音混输 | 打五笔码或拼音都能出词，同一方案内自由切换 |
| 中 → 英 | 打 `vb`（好）候选出 good / good-looking；打 `agjs`（苹果）出Apple |
| 英 → 中 | 打 `good` 出「好 / 好处 / 好的」；10.6 万条英中词条 |
| 自动造词 | 打「刚」再打「需」上屏后，下次直接打 `mqfd` 出「刚需」 |
| 词频自适应 | 常用词会随使用自动上移 |
| 自造词继承 | 可选导入万能五笔的自造词（附在包里，默认不启用） |

**不支持**：整句翻译。词库是**词级**的（ECDICT 词典），打整句只会逐词匹配，没有句子级翻译。

---

## 二、安装（Windows）

### 前提
已安装**小狼毫（Weasel）0.17.4 或更新版本**。若未装：https://github.com/rime/weasel/releases

### 步骤

1. **解压**本包（得到 `wubi-citong-v1.0.0` 文件夹）

2. **双击 `install.bat`**

   脚本会自动：
   - 扫描 C/D/E/F/G 盘，找到小狼毫安装目录
   - 备份你原来的配置到 `_wbcitong_backup`
   - 复制全部词库、方案、lua 滤镜
   - 完成提示

3. **退出并重新打开小狼毫**（托盘右键 → 退出）

4. 重新打开后，托盘右键 → **重新部署**

5. 按 `F4` 切换方案，会看到三个：
   - **五笔·拼音**（主推，功能最全）
   - 拼音混输
   - 拼音混输·繁体

### 如果 install.bat 报错

| 提示 | 处理 |
|---|---|
| 「没找到小狼毫安装目录」 | 确认已装官方小狼毫；或手动把 `rime` 文件夹里的文件复制到 Rime 目录 |
| 「无法创建备份目录」 | 用**管理员身份**运行 `install.bat` |
| 复制后没生效 | 确认执行了「重新部署」，且完全退出过小狼毫 |

### 手动安装（备选）

不用脚本的话：把 `rime` 文件夹里**所有文件和 lua 子目录**复制到 Rime 安装目录（覆盖），然后重新部署。

### 可选：导入万能五笔自造词

包里 `rime/我的自造词_可选/` 目录放了从万能五笔迁移的自造词（1387 条，50 KB）。

**默认不启用**（这些是个人用词习惯，你可以选择是否继承）。要启用：

1. 把该目录下 4 个 `wnwb_*_wp.dict.yaml` 复制到 Rime 安装目录
2. 编辑 `wubi86.dict.yaml`，在 `import_tables:` 下加：
   ```yaml
     - wnwb_wubi_user_wp
     - wnwb_wubi_custom_wp
     - wnwb_pinyin_user_wp
     - wnwb_pinyin_custom_wp
   ```
3. 把 `wubi86.dict.yaml` 的 `version:` 改一下（如 `0.14` → `0.15`），强制重编译
4. 重新部署

---

## 三、验证是否装好

切换到「五笔·拼音」方案，测试：

| 输入 | 期望 |
|---|---|
| `vb` | 第1「好」，附近有 good |
| `hao` | 第1「好」，附近有 good |
| `pingguo` | 苹果 |
| `agjs` | 苹果 + Apple |
| `good` | 好 / 好处 / 好的 |
| 打「刚」「需」上屏 → `mqfd` | 「刚需」（自动造词） |

---

## 四、词库来源与许可

| 词库 | 来源 | 许可 |
|---|---|---|
| 中文拼音码 `cn_pinyin_wp` | 极点/小狼毫拼音词库 | 随 Rime 生态 |
| 中→英 `zh2en_pinyin_wp` / `zh2en_wubi_wp` | ECDICT | MIT / 免费商用，**需标注** |
| 英→中 `en2zh_v2_wp` | ECDICT | 同上 |
| 自造词（可选） | 用户个人数据 | 用户自有 |

**发布/分发时请标注词库来源为 ECDICT。**

---

## 五、文件清单

```
wubi-citong-v1.0.0/
├─ install.bat                 ← 双击这个安装
├─ rime/                      ← 安装源（脚本会复制这些）
│  ├─ wubi_pinyin.schema.yaml       五笔·拼音（主推）
│  ├─ wubi_pinyin.custom.yaml
│  ├─ wubi86_jidian_pinyin.schema.yaml      拼音混输
│  ├─ wubi86_jidian_trad_pinyin.schema.yaml 拼音混输·繁体
│  ├─ default.custom.yaml            方案清单（只留 3 个）
│  ├─ cn_pinyin_wp.dict.yaml         中文拼音码 65114 条
│  ├─ zh2en_pinyin_wp.dict.yaml      中→英（拼音）89737 条
│  ├─ zh2en_wubi_wp.dict.yaml        中→英（五笔）89841 条
│  ├─ en2zh_v2_wp.dict.yaml          英→中 106004 条
│  ├─ wubi86.dict.yaml 等基础字典
│  ├─ *_py.dict.yaml（别名）
│  ├─ lua/                          滤镜（含关键修复）
│  └─ 我的自造词_可选/                ← 可选，默认不启用
└─ 使用说明/                本文档
```

---

*五笔词通 · 五笔拼音中英混输自造词*