# M3 run11 取证：rime-lua 的真实契约（结论推翻了 run9/run10 的判断）

设备：Mate 80 `7GL0226408083897`；包：`v0.3.1-engine` 之后的 DATA_VERSION `m3-sansheng-v9`；
signed HAP 24,486,742 B；`install bundle successfully`；探针 `--ps m3_probe 1`；
init 5862 ms。原始日志：`hilog-m3-run11.txt`、`m3-stderr-run11.txt`（由桥把 stderr
重定向到 `rime_user/napi_stderr.txt` 后 `hdc file recv`）。

## 1. 探针结果（本轮的对照组是 zzd_min）

| 用例 | 结果 |
|---|---|
| 诊断 `zzd_min`（纯 table_translator，无 Lua） | 4 条：你好 / 您好 / hello / 𠛈 |
| 诊断 `zzd_f4`（滤镜里 `return input`，外加 dump） | **0 条** |
| 诊断 `zzd_f5`（滤镜返回命名字段 table） | **0 条** |
| 诊断 `zzd_f6`（滤镜返回位置数组 table） | **0 条** |
| 诊断 `zzd_f7`（滤镜返回空 table） | 0 条 |
| 拼音混输 `nihao` | PASS 你好 / hello |
| H-042 样本 `nihaoma` | PASS **你好吗** |
| 五笔 `wqvb` | PASS 你好 |
| 英→中 `dog` | PASS 狗 / 跟踪 / 尾随 |
| 中→英 `haoma` | 号码 / 好吗 / number / 好嘛 |
| T9 `64426` | PASS **你好[ni hao]** / 你敢[ni gan] / 米高[mi gao] |
| T9 `746` | 亲[qin] / 品[pin] / 秦[qin] … |
| `zh_trad` 开 | PASS 中国 → **中國** |
| `getOption('zh_trad')` | 开着读到 `true`（v0.1.8 新接口生效） |
| `ascii_mode` | **FAIL**：clear 后按 `x` → commitText 空、预编辑空、候选 0（键被吞） |
| 反查 `` `ni `` | 你 / 拟 / 尼 / 呢 / 泥（native 反查，comment 需要真 Lua） |

run11 修正了 run10 的探针缺陷：`ascii_mode` 之前先 `clear()`，预编辑从 `zhongguox` 变成空——
但键仍然没有任何结果，说明问题不在「编码非空时不直出」，而在方案/开关的交互上（run12 加 `pinyin_simp` 对照）。

## 2. f4 倒出来的契约（真机原文，逐条）

```
[zzd] f4 _VERSION=Lua 5.4
[zzd] f4 input=userdata[7LuaTypeINSt4__n110shared_ptrIN4rime11TranslationEEEE: 0x5a35468758]
[zzd] f4 segment=table(array=0,kv=2)          ← 第 2 个参数是普通 Lua table，只有 2 个键
[zzd] f4 env=userdata[7LuaTypeIPNSt4__n16vectorINS0_10shared_ptrIN4rime9CandidateEEEEEE]
[zzd] input mt_keys=__gc:function __index:function __name:string __newindex:function
                 methods:table type:userdata vars_get:table vars_set:table
[zzd] input __index=function
[zzd] f4 input[1] ok=true -> nil[nil]         ← userdata 不按下标存候选
[zzd] f4 G_n=83
```

`_G` 里与本问题直接相关的名字（节选）：

```
Candidate:function  Code:function  Segment:table  Translation:function
Menu:function  Schema:function  KeyEvent:function  Opencc:function
ReverseLookup:function  UniquifiedCandidate:function  ShadowCandidate:function
TableDb:function  UserDb:function  DictEntry:function  Projection:function
log:table  rime_api:table  warn:function  yield:function  print …
以及已经加载的滤镜本体：inputShow_Filter / phraseExt_Filter / dateTime_Filter /
dynamicPhrase_Filter / phraseReplace_Filter / dic_4w_Filter / phraseComment_Filter /
pinyinAdding_Filter / codeLookup_Filter / laneChangeAndSpace_Filter / abbrGloss_Filter /
help_translator / inputShow_translator（全是 function：说明 rime.lua 已跑通，桩已就位）
```

`package.path`（真机）：

```
…/files/rime_user/lua/?.lua ; …/files/rime_user/lua/?/init.lua ;
…/files/rime/lua/?.lua ; …/files/rime/lua/?/init.lua ; /usr/local/share/lua/5.4/?.lua ; …
```

## 3. 与桌面版滤镜源码对齐

`F:/workbuddywork/三生输入法/packaging/release/config/lua/pinyinAdding_Filter.lua`：

```lua
local function pinyinAdding(input, env)                       -- 只有两个参数
        local pySwitchFlg = env.engine.context:get_option("pinyin") or false
        for cand in input:iter() do                           -- Translation userdata 的迭代器
                ...
                yield(cand)                                   -- 靠 yield 交候选
                yield(Candidate("word", cand.start, cand._end, txtWithPy, cand.comment))
        end
end
return pinyinAdding
```

对齐结论（**推翻 run9/run10 的判断**）：

1. 这版 rime-lua（librime 1.16.1 内的 SWIG/tolua 风格绑定，Lua 5.4）**与桌面版是同一套 API**：
   `input` 是 `shared_ptr<rime::Translation>` 的 userdata，滤镜用 `for cand in input:iter() do … yield(cand) end`
   产出候选，**返回值一律作废**。
2. 所以 run9/run10 的「挂了 Lua 齿轮候选就归零」**不是引擎契约差异，是我写的桩用了 `return input`**。
   桌面滤镜搬上来本来就能工作（前提：模块能 require 成功、模块里的 Windows 路径不炸）。
3. run6 观察到的 `func type error expect function` 与「候选 0 条」是两件事：前者是模块缺失导致齿轮为 nil，
   后者是桩形状错。两件事都修完，滤镜链才能真正验收。
4. `_G` 里就有 `warn:function` 和 `log:table`，没有 `rime.api`——所以 `require("rime.api")` 一直失败，
   日志走的是 `io.stderr`（桥把它重定向进了 `napi_stderr.txt`）。桩的 `warn()` 已改成优先用全局 `warn`。
5. 滤镜的第 2、第 3 个参数需要 run12 用 `zzd_f8` 再确认一次位序：桌面签名 `(input, env)` 只有两个参数，
   而这版绑定传了 3 个（`input`、一个 2 键 table、一个 `vector<shared_ptr<Candidate>>` userdata）。
   `f8` 会把 2 键 table 的键名、`env.engine.context:get_option(...)` 是否可用一并打出来。

## 4. run12 的三个待验问题

| 探针 | 要回答的问题 | 通过的判据 |
|---|---|---|
| `zzd_f8`（iter + yield 恒等放行） | 契约是否真的成立；env 在第几参数；候选字段可读 | 候选回到 4 条，日志有 `methods:` 与 `get_option` 结果 |
| `zzd_f9`（只 yield 第一条并改 comment） | 滤镜能否**裁剪**候选、能否**改 comment**（三向反查就靠这个） | 屏上 1 条，comment 带「诊断九」或「诊断九g」 |
| `zzd_f10`（中途 yield 自建 Candidate） | 滤镜能否**增候选**（中英互译/扩展靠它） | 候选里出现「诊断十[zz10]」 |

另外 `ascii_mode` 加 `pinyin_simp` 对照：若那边字母直出而 `wubi_pinyin` 不直出，
锅在 `wubi_pinyin` 的 processor 组合（`ascii_composer` 在 rawfile 里确实存在，需查设备编译后的版本）。
