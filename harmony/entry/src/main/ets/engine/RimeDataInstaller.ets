import { fileIo as fs } from '@kit.CoreFileKit';
import { common } from '@kit.AbilityKit';

const TAG: string = 'SSRimeData';
/**
 * 数据版本：M3 = 三生完整数据（五笔·拼音·英文混输 + 中英互译 + OpenCC 简繁 + 智能九键方案）。
 * 数据内容一变必须改这个值，否则老沙箱里的旧数据不会被替换（真机踩过 H-039/DataVersion）。
 * v3：default.yaml 第 63 行的坏 YAML（`"\": "\\"`，双引号里 `\` 是转义）修好后必须重放，
 * 否则设备上还是那份让 yaml-cpp 报错、三个 schema 全部编译失败、build/ 空、零候选的旧文件
 * ——14:36 真机实测就是这么踩的：本地改了，marker 还是 v2，文件根本没更新。
 */
/*
 * v5：加 rime.lua（librime-lua 的齿轮入口，只能放 user 目录）。
 * run6 真机实证：wubi_pinyin 的 engine/filters 里 12 级 lua_filter 没有 rime.lua 时，
 * librime-lua 仍会建出 LuaFilter/LuaTranslation 对象，但每次调用抛
 * "func type error expect function"，抛错的 LuaTranslation::Next 打断候选队列 ——
 * 现象是预编辑正常、候选 0 条（stderr 里 611 次 Next error）。
 * M3 先放「桩版」rime.lua（滤镜恒等放行、翻译器不出候选）打通主链路，
 * 真滤镜随 scripts/port_rime_data.py --lua-modules 逐步补上，require 成功即自动生效。
 */
/*
 * v6：H-044 诊断轮 —— 基础方案里摘掉 zh2en_wubi / en2zh_v2 / zh2en_pinyin 三个
 * table_translator（它们的词库在桌面端和真机都没编译出 table.bin）。
 * 目的：确认「translator 初始化失败会不会让整条候选链归零」。
 * 由 scripts/port_rime_data.py 的 DROP_LINE_PREFIXES 生成，不是手改数据。
 */
/*
 * v7：H-044 诊断第二轮 —— 把 wubi_pinyin 里所有 lua_* 齿轮（含 custom.yaml 整表替换的
 * filters）一并摘掉，同时放入 5 个 zzd_* 诊断方案（最小五笔 / +反查 / +Lua桩 /
 * +用户词典 / 完整复刻）。run8 实证：wubi86 三个 .bin 与桌面端尺寸逐字节一致
 * （2826556 / 9101972 / 3695604）、stderr 零错误、schema 切换成功，候选仍恒 0；
 * 而同一台机器同一座桥上的 sansheng_t9（script_translator）候选正常。
 * 所以这一轮要问的是：table_translator 在这套运行时里到底能不能出词。
 * zzd_* 只用于定位，定位完连同 DROP_LINE_PREFIXES 一起删掉。
 */
/*
 * v8：run9 真机结论 —— 摘掉 lua_* 后 wubi_pinyin 全绿（wqvb→你好、nihaoma→你好吗、
 * dog→狗、zhongguo→中國），zzd_min/rvl/ud 也出词，只有挂了桩齿轮的 zzd_lua/zzd_full 恒 0。
 * 所以 H-044 的锅在 Lua 齿轮本身。本轮把 zzd_* 换成 4 个「单齿轮」方案，
 * 分开问：掐候选的是 filter 还是 translator？rime-lua(1.16.1) 传进 filter 的
 * input 是什么 Lua 类型？决定 M4 移植真滤镜时要不要写适配器。
 */
/*
 * v9：run10 真机结论 —— 掐候选的是 **filter**：`zzd_min` 4 条、`zzd_f2`(return input) 0 条、
 * `zzd_f3`(return 重建 table) 0 条、`zzd_t1/t2`(lua_translator 桩) 与 min 完全一致（无害）。
 * stderr 实测 `f2 input type=userdata len=?`、`f3 rebuilt 0 from userdata`
 * ⇒ 这版 rime-lua 传给滤镜的是 Translation **userdata**，不是桌面那套候选 table；
 * 桌面的 12 级滤镜（table 进 table 出）搬过来必然全军覆没，M4 必须先写适配层。
 * 【本行结论已被 run11 推翻，正确契约见下面的 v10 —— 保留原文是为了留下「猜错过一次」的证据链】
 * 本轮 zzd_* 换成 1 个「只倒契约」的 f4（metatable / 方法名 / 全局类型名 / Lua 版本）
 * + 3 个「返回形状」探针（f5 命名字段 table、f6 位置数组 table、f7 空 table）。
 */
/*
 * v10：run11 dump 出来的真契约 —— 滤镜是**协程生成器**，靠 `yield(cand)` 出候选，返回值作废：
 * `_VERSION=Lua 5.4`，input = 包 shared_ptr<rime::Translation> 的 userdata（metatable 有
 * methods/vars_get/vars_set，`input[1]` 为 nil），`_G` 里有 `yield` / `Candidate` / `log` / `warn`；
 * 桌面 lua/pinyinAdding_Filter.lua:25 正是 `for cand in input:iter() do ... yield(cand) end`。
 * ⇒ run9/run10 的「Lua 齿轮掐候选」是**桩用了 return** 造成的假象，passthrough 已改成 iter+yield；
 * M4 不需要 table↔userdata 适配器，需要的是把真模块放上来。
 * 本轮 f8 验 iter/yield/env 位序，f9 验「裁候选 + 改 comment」，f10 验「yield 自建 Candidate」。
 */
/*
 * v11：run12 真机把 v10 的三条推断全部证实（原文 docs/evidence/2026-10-21/hilog-m3-run12.txt）：
 * zzd_min 4 条 ≡ zzd_f8 4 条（iter+yield 恒等无损）、zzd_f9 「候选1条 你好[诊断九g]」
 * （滤镜能裁候选、能改 comment —— 三向反查注释就靠这条）、zzd_f10 「诊断十[zz10]」插到最前
 * （滤镜能自建 Candidate）。所以本轮把 DROP_LINE_PREFIXES 里的 `- lua_translator@` /
 * `- lua_filter@` 撤掉，wubi_pinyin 重新挂回桌面那 13 级齿轮（2 translator + 11 filter，
 * 现在指向桩），要问的问题变成：**桩链跑满 13 级后候选还是不是 4 条**。
 * 只保留 3 个没编译出 table.bin 的互译 table_translator 的摘除。
 */
/*
 * v12（M3 收口版）：H-044 结案，诊断产物全部下线 —— rawfile 里不再有 zzd_*.schema.yaml，
 * rime.lua 里的 zzd_* 诊断齿轮、NAPI 里的诊断部署循环、探针里的诊断段一起删掉。
 * run13 实测：挂满 13 级齿轮的 wubi_pinyin 与摘链时逐条一致（wqvb→你好/您好/hello/𠛈、
 * nihaoma→你好吗、dog→狗、haoma→号码[kgdc]、T9 64426→你好[ni hao]、zh_trad→中國）。
 * 同轮修掉 H-041 ②：英文模式（ascii_mode）下字母直出改由桥负责 ——
 * 真机量到 `process_key` 对 printable 字母返回 handled=0（librime 侧没吃掉这个键，
 * wubi_pinyin 与 pinyin_simp 表现一致，与开关本身无关），桥在「不在组词中」时补一发直出，
 * 与 H-024 数字直出同一套语义；实测 x/X/连打 hi 全部上屏。
 */
/*
 * v13（M4 三生能力落地）：把桌面端那 13 级 Lua 齿轮**真模块**放上包。
 * 前 12 版只在 user 目录放一份 rime.lua（齿轮桩版：恒等放行 / 不出候选），
 * 桌面有而鸿蒙没有的能力有 9 项：拼音注释、短语释义、自定义短语、动态短语、
 * 时间日期、中英对照、编码反查、英文缩写释义、候选换行。
 * 本版起额外释放 lua/ 目录（真模块 + 数据表 + 鸿蒙沙箱实现 runLog/sysInfo/socket），
 * 释放清单由 scripts/port_rime_data.py 生成（rime/lua-files.json），避免两边漏文件。
 */
/*
 * v14（M4 返工一）：补齐两个**发布件早就引用、但模块与 rime.lua 全局从未移植**的齿轮：
 *   rawEcho_translator（wubi_pinyin.custom.yaml 用 engine/translators/+ 追加，**生效**）
 *   Upper_Filter（wubi_pinyin.schema.yaml 的 filters 列表）
 * 缺全局 ⇒ rime-lua 每次调用抛 "func type error expect function"，
 * 抛错的 LuaTranslation::Next 会把整条候选队列打断 ⇒ 真机现象：预编辑正常、候选只剩 2 条，
 * 而且不报错。run13/run6 是同一个坑，所以这次同时给 scripts/port_rime_data.py 加了
 * 「yaml 引用 ↔ 模块 ↔ rime.lua 全局」三层完备性检查，少一个就让移植脚本非 0 退出。
 * 顺带把 Upper_Filter 的 cand.comment 兜成空串（鸿蒙这版 rime-lua 无注释时 comment 是 nil）。
 */
// v18（M5/D-012）：wubi_pinyin.custom.yaml 追加 script_translator@pinyin（pinyin_simp），
// 26 键拼音从「整词精确」升级为逐字/词组/整句；五笔 table、用户词典与互译候选不动。
const DATA_VERSION: string = 'h279-stems-redeploy';  // 2026-10-30 Qoder(H-279)：wubi86.dict.yaml 补回第 4 列 stem（25 行 → 20935 行，md5 e7dfa7a7… → 8e020b02…）+ custom 里 max_phrase_length 4 → 6。不升这个号，ensure() 在已装机上会因 MARKER 相同直接 return，新词库既不会重铺、rime_user/build 里的旧 wubi86.table.bin 也不会重编 ⇒ 装了包等于没装。
// 2026-10-30 Qoder(H-276)：上一版 'h275b-punct-deploy' 修的是「清 build 缓存删错目录」（真机制 staging=rime_user/build）。
// 2026-10-30 CodeArts 原值 'h275-punct-rebuild'（同 H-274 意图：清 build 缓存确保 punctuator 重新 deploy）
const MARKER: string = '.data-version';

/**
 * 释放到 shared 目录（filesDir/rime）的文件。
 * 每一项都是 rawfile 里的相对路径；子目录（opencc/…）会跟着一起建。
 * 清单由 scripts/port_rime_data.py 从桌面端三生数据里算出闭包，
 * 逐文件的来源与 md5 见 docs/evidence/2026-10-21/m3-data-manifest.json。
 */
const SHARED_FILES: string[] = [
  'default.yaml',
  'wubi_pinyin.schema.yaml',
  'wubi_pinyin.custom.yaml',
  'pinyin_simp.schema.yaml',
  'sansheng_t9.schema.yaml',


  // 主词库：wubi86 的 import_tables 引 4 个 _wp，少一个就整类候选消失且不报错
  'wubi86.dict.yaml',
  // 2026-10-29 19:2x Qoder（H-273）：主表 import_tables 补回这两张极点表，
  // 缺文件时 librime 会整本编译失败（安卓 H-270 就是这么炸的），所以必须一起铺。
  'wubi86_jidian.dict.yaml',
  'cn_pinyin_jidian_wp.dict.yaml',
  'cn_pinyin_wp.dict.yaml',
  'zh2en_pinyin_wp.dict.yaml',
  'zh2en_wubi_wp.dict.yaml',
  'en2zh_v2_wp.dict.yaml',
  // 三个中英互译 translator 用的是不带 _wp 的同名词典
  'zh2en_wubi.dict.yaml',
  'zh2en_pinyin.dict.yaml',
  'en2zh_v2.dict.yaml',

  // H-260(CodeArts): v38 table_translator@en_word 方案——Qoder 已准备 dict + schema
  'en_word.dict.yaml',
  'en_word.schema.yaml',

  // 拼音底座：反查 + T9 的数据来源
  'pinyin_simp.dict.yaml',
  // H-044 的诊断方案 zzd_*（run6–run13）结案后已全部删除：
  // rime.lua 里量到的真契约（env 在第 2 参数、候选靠 yield 出、comment 可改）
  // 记在 docs/evidence/2026-10-21/m3-run11-contract.md 与 scripts/port_rime_data.py 的文件头，M4 照那个写。
  // OpenCC 简→繁（.ocd2 是预编译的，设备上不需要 opencc CLI）
  'opencc/s2t.json',
  'opencc/STCharacters.ocd2',
  'opencc/STPhrases.ocd2'
];

/**
 * 释放到 user 目录（filesDir/rime_user）的文件。
 * librime 的 lua 插件只在 **user_data_dir** 找 rime.lua，并把
 * `<user>/?.lua` 与 `<user>/lua/?.lua` 加进 package.path；
 * 所以 M3b 移植滤镜时必须把 rime.lua + lua/ 放到这一边，放 shared 是不生效的。
 * 现在的 rime.lua 是 scripts/port_rime_data.py 生成的桩版（见上面 v5 注释）：
 * 齿轮存在且是函数，主链路能出词；真模块（socket.lua 要加载 luaSocket DLL、
 * runLog.lua 要往只读目录写日志、若干模块用 os.getenv('APPDATA') 找数据）
 * 还在逐个去 Windows 化，补齐后 require 成功即自动替换桩。
 */
const USER_FILES: string[] = [
  'Custom_phrase.txt',
  'rime.lua',
  // H-260(CodeArts): enWord_Filter 数据文件已移除（filter 已注释，translator 用 bucket 文件不走 USER_FILES）
  // H-272(Qoder 2026-10-29)：滤镜 v3.3 恢复挂载，它的四张数据表必须落在 user 目录
  // （滤镜按 get_user_data_dir 找文件，放 shared 读不到）。索引只 1,942 B，记字节偏移不复制词库。
  'en_word_gloss.tsv',
  'en_word_trans.tsv',
  'en_word_codes.txt',
  'en_word_rev.tsv',
  'en_word_ltr_idx.tsv',
  // H-274(2026-10-29 20:xx Qoder)：反查表按 UTF-8 首字节分段索引（352 B，只记偏移不复制词库）。
  // 上次 DATA_VERSION 没把它铺进去，滤镜会因拿不到索引退回整表读（旧行为，功能不缺但 load 多 ~20 ms）。
  'en_word_rev_idx.tsv',
];

/**
 * v13（M4）：lua/ 目录的释放清单文件名（相对 rawfile/rime/）。
 * 内容是纯文本，一行一个相对路径（"lua/xxx.lua" / "lua/xxx.txt"），
 * 由 scripts/port_rime_data.py 扫目录生成 —— ArkTS 侧没法枚举 rawfile 目录，
 * 只能靠这份名单才知道该往沙箱里放哪些文件；名单自动生成 ⇒ 桌面加模块不会漏。
 * 用纯文本而不是 JSON：ArkTS 侧 split('\n') 最省事，解析失败也不会带崩整个安装流程。
 */
const LUA_MANIFEST: string = 'lua-files.txt';

/** 已确保存在的目录，避免对同一个路径重复 mkdirSync（H-039：目录已存在时 mkdirSync 仍抛 File exists）。 */
const madeDirs: Set<string> = new Set<string>();

/**
 * 把 HAP rawfile 里的 Rime 数据释放到应用沙箱。
 * 归属：Qoder。
 *
 * 为什么需要它：hdc 的 shell 用户无权写 /data/app/el2/.../files，
 * 数据只能由应用自己从 rawfile 释放。
 */
export class RimeDataInstaller {
  static async ensure(sharedPath: string, context?: common.Context): Promise<void> {
    // H-274 排障：必须放在 MARKER 检查之前——版本号没变时 ensure 会直接 return，
    // 放在后面就永远捞不到上一次会话的 [ENW] 计时（19:38 那次就是这么丢的）。
    RimeDataInstaller.dumpEnwProbe(sharedPath + '_user/napi_stderr.txt');
    try {
      if (fs.accessSync(sharedPath + '/' + MARKER) &&
        fs.readTextSync(sharedPath + '/' + MARKER) === DATA_VERSION) {
        console.info(`${TAG} data ${DATA_VERSION} already present`);
        // H-276(Qoder 2026-10-30)：沙箱文件 hdc 读不到，标点配置到底是什么版本只能由应用自己报。
        RimeDataInstaller.punctProbe(sharedPath + '/default.yaml', 'present shared');
        RimeDataInstaller.punctProbe(sharedPath + '_user/build/default.yaml', 'present staging');
        return;
      }
    } catch (e) {
      // 不存在或不可读，继续释放
    }

    // IME 扩展进程里全局 getContext() 会返回空（真机 11:22 实证），
    // 所以优先用控制器显式传入的 InputMethodExtensionContext。
    let ctx: common.Context | undefined = context;
    if (ctx === undefined) {
      try {
        ctx = getContext() as common.Context;
      } catch (e) {
        ctx = undefined;
      }
    }
    if (ctx === undefined || ctx.resourceManager === undefined) {
      throw new Error('resourceManager unavailable: pass InputMethodExtensionContext to engine.init()');
    }

    // NAPI 那边把 user 目录定成 sharedPath + '_user'（见 fanxing_napi.cpp），
    // 但它是 init 时才 mkdir；数据比 init 早，所以这里自己建。
    const userPath: string = sharedPath + '_user';
    RimeDataInstaller.ensureDir(sharedPath);
    RimeDataInstaller.ensureDir(userPath);

    // H-274(CodeArts)：DATA_VERSION 变化时清除 build 缓存，确保引擎重新 deploy。
    // H-276(Qoder 2026-10-30)：上面那版删错了目录。真机 init 日志实证了两个目录不是一回事：
    //   dirs: prebuilt=<shared>/build  staging=<shared>_user/build
    // librime 的 schema 编译产物（*.schema.yaml / *.table.bin / default.yaml 的部署副本）
    // 全在 **staging** = user_data_dir/build = sharedPath + '_user/build'；
    // 删 prebuilt 目录等于没删，引擎发现缓存齐全 ⇒ deploy 78 ms 直接跳过 ⇒
    // default.yaml 里的 punctuator 怎么改都不生效（符号面板点符号不出候选/出旧候选）。
    RimeDataInstaller.punctProbe(sharedPath + '/default.yaml', 'before shared');
    RimeDataInstaller.punctProbe(userPath + '/build/default.yaml', 'before staging');
    RimeDataInstaller.removeDirRecursive(userPath + '/build');
    RimeDataInstaller.removeDirRecursive(sharedPath + '/build');   // 老的 prebuilt 目录，删掉无害

    const t0: number = Date.now();
    let bytes: number = 0;
    for (const name of SHARED_FILES) {
      bytes += RimeDataInstaller.release(ctx, sharedPath, name);
    }
    for (const name of USER_FILES) {
      bytes += RimeDataInstaller.release(ctx, userPath, name);
    }
    // v13（M4）：lua/ 真模块 + 数据表 → 释放到 <user>/lua/
    // librime-lua 的 package.path 含 "<user>/?.lua" 与 "<user>/lua/?.lua"，
    // 所以齿轮与数据表都必须落在 user 目录这一侧（放 shared 目录不生效，见 M3 注释）。
    let luaCount: number = 0;
    try {
      luaCount = RimeDataInstaller.releaseLuaTree(ctx, userPath);
    } catch (e) {
      // 释放失败不能拖垮整个数据安装：齿轮缺失只会少几项能力，不会让主链路断。
      console.warn(`${TAG} lua tree release failed: ${JSON.stringify(e)}`);
    }
    bytes += luaCount;

    const marker: fs.File = fs.openSync(sharedPath + '/' + MARKER,
      fs.OpenMode.READ_WRITE | fs.OpenMode.CREATE | fs.OpenMode.TRUNC);
    try {
      fs.writeSync(marker.fd, DATA_VERSION);
    } finally {
      fs.closeSync(marker);
    }
    console.info(`${TAG} data ${DATA_VERSION} released: ` +
      `${SHARED_FILES.length + USER_FILES.length} files + lua tree, ` +
      `${bytes} B, ${Date.now() - t0} ms -> ${sharedPath} | ${userPath}`);
    RimeDataInstaller.punctProbe(sharedPath + '/default.yaml', 'released shared');
  }

  /** H-276(Qoder 2026-10-30)：标点配置指纹。真机沙箱 hdc 读不到（Permission denied），
   *  只能让应用自己把 punctuator/half_shape 块的形状打进 hilog：
   *  lists = 值是列表（`["…"]`）的键数——列表值会进候选栏（要再点/按空格），
   *  单值（`"…": "…"`）才直接上屏。M-368 验收的 9 个键就靠这个数判有没有生效。 */
  private static punctProbe(path: string, tag: string): void {
    try {
      if (!fs.accessSync(path)) {
        console.info(`${TAG} punct ${tag}: absent`);
        return;
      }
      const text: string = fs.readTextSync(path);
      const start: number = text.indexOf('\n  half_shape:');
      if (start < 0) {
        console.info(`${TAG} punct ${tag}: no half_shape (${text.length} B)`);
        return;
      }
      const lines: string[] = text.substring(start + 1).split('\n');
      let keys: number = 0;
      let lists: number = 0;
      let shown: string = '';
      for (let i = 1; i < lines.length; i++) {
        const ln: string = lines[i];
        if (ln.trim().length === 0 || ln.trim().startsWith('#')) {
          continue;
        }
        if (!ln.startsWith('    ')) {
          break;   // 缩进退回半角块结束（下一个键或下一节）
        }
        const sep: number = ln.indexOf(':');
        if (sep < 0) {
          continue;
        }
        keys++;
        if (ln.indexOf('[', sep) >= 0) {
          lists++;
        }
        if (shown.length < 200) {
          shown += ln.trim() + ' ';
        }
      }
      console.info(`${TAG} punct ${tag}: half_shape keys=${keys} lists=${lists} ` +
        `bytes=${text.length} | ${shown}`);
    } catch (e) {
      console.warn(`${TAG} punct ${tag} failed: ${JSON.stringify(e)}`);
    }
  }

  /**
   * 按 rawfile/rime/lua-files.txt 里的名单，把 lua/ 目录整棵树释放到 user 目录。
   * 返回写出的字节数。
   *
   * 为什么清单在包里而不是写死在 ArkTS 里：桌面每加一个 Lua 辅助模块，
   * 写死的清单就会漏（run6/run13 的教训：齿轮缺失的表现是「预编辑正常、候选 0 条」，
   * 不报错，只能靠「清单 == 实际文件数」这种机械核对发现）。
   * 清单由 scripts/port_rime_data.py 扫 rawfile/rime/lua/ 生成，
   * ArkTS 只负责照单释放；清单缺失时退化成「只放桩版 rime.lua」，主链路仍然通。
   */
  private static releaseLuaTree(ctx: common.Context, userPath: string): number {
    const raw: Uint8Array = ctx.resourceManager.getRawFileContentSync('rime/' + LUA_MANIFEST);
    const text: string = RimeDataInstaller.decodeUtf8(raw);
    const files: string[] = text.split('\n');
    let bytes: number = 0;
    let count: number = 0;
    for (const rel of files) {
      const name: string = rel.trim();
      if (name.length === 0) {
        continue;
      }
      bytes += RimeDataInstaller.release(ctx, userPath, name);
      count++;
    }
    console.info(`${TAG} lua tree: ${count} files -> ${userPath}/lua`);
    return bytes;
  }

  /** Uint8Array → string（ArkTS 没有内置 TextDecoder，这里按 UTF-8 手工解）。 */
  private static decodeUtf8(bytes: Uint8Array): string {
    let out: string = '';
    let i: number = 0;
    while (i < bytes.length) {
      const b0: number = bytes[i];
      let code: number = b0;
      let len: number = 1;
      if (b0 >= 0xF0) {
        code = b0 & 0x07;
        len = 4;
      } else if (b0 >= 0xE0) {
        code = b0 & 0x0F;
        len = 3;
      } else if (b0 >= 0xC0) {
        code = b0 & 0x1F;
        len = 2;
      }
      for (let k: number = 1; k < len && i + k < bytes.length; k++) {
        code = (code << 6) | (bytes[i + k] & 0x3F);
      }
      i += len;
      if (code > 0xFFFF) {
        const c: number = code - 0x10000;
        out += String.fromCharCode(0xD800 + (c >> 10), 0xDC00 + (c & 0x3FF));
      } else {
        out += String.fromCharCode(code);
      }
    }
    return out;
  }

  /**
   * 先探测再创建。两个真机实证坑：
   * ① H-039：目录已存在时 `mkdirSync(path, true)` 仍抛 "File exists"，不能靠异常控制流；
   * ② M3 14:07 init 报 13900002（ENOENT）：`accessSync(path)` 的契约是**返回 boolean**，
   *    文件/目录不存在时它不抛，所以旧写法「try accessSync / catch mkdirSync」
   *    在目录缺失时根本不会 mkdir，后面 openSync 就找不到路径。
   * 因此必须读返回值决定是否创建，创建本身再兜一次异常（并发/已存在）。
   */
  private static ensureDir(path: string): void {
    if (madeDirs.has(path)) {
      return;
    }
    if (!fs.accessSync(path)) {
      try {
        fs.mkdirSync(path);
      } catch (e) {
        const err = e as Error;
        console.warn(`${TAG} mkdirSync ${path}: ${err.message}`);
      }
    }
    madeDirs.add(path);
  }

  /**
   * H-274(CodeArts)：递归删除目录及其内容。
   * ArkTS 的 fs.rmdirSync 只能删空目录，所以先递归删子项再删自身。
   * 用于 DATA_VERSION 变化时清除 build 缓存，确保引擎重新 deploy。
   */
  private static removeDirRecursive(path: string): void {
    try {
      if (!fs.accessSync(path)) {
        return;
      }
    } catch (e) {
      return;
    }
    try {
      const names: string[] = fs.listFileSync(path);
      for (const name of names) {
        const childPath: string = path + '/' + name;
        try {
          fs.unlinkSync(childPath);
        } catch (e) {
          // unlinkSync 失败说明是目录，递归删除
          RimeDataInstaller.removeDirRecursive(childPath);
        }
      }
      fs.rmdirSync(path);
      console.info(`${TAG} removed build cache: ${path}`);
    } catch (e) {
      console.warn(`${TAG} removeDirRecursive ${path}: ${JSON.stringify(e)}`);
    }
  }

  /** 释放单个文件（支持 a/b.ext 这种带子目录的路径），返回写出的字节数。 */
  /** H-274 排障（2026-10-29 Qoder）：把滤镜写在 stderr 的 [ENW] 计时捞进 hilog。 */
  private static dumpEnwProbe(path: string): void {
    try {
      if (!fs.accessSync(path)) {
        console.info(`${TAG} enw probe: no stderr file yet`);
        return;
      }
      const txt: string = fs.readTextSync(path);
      const lines: string[] = txt.split('\n');
      let hit: number = 0;
      for (const l of lines) {
        if (l.indexOf('[ENW]') >= 0) {
          console.info(`SSEnwProbe ${l}`);
          hit++;
        }
      }
      console.info(`${TAG} enw probe: ${hit} ENW line(s) in ${lines.length} line(s)`);
    } catch (e) {
      console.warn(`${TAG} enw probe failed: ${JSON.stringify(e)}`);
    }
  }

  private static release(ctx: common.Context, baseDir: string, relName: string): number {    const slash: number = relName.lastIndexOf('/');
    if (slash > 0) {
      RimeDataInstaller.ensureDir(baseDir + '/' + relName.substring(0, slash));
    }
    const raw: Uint8Array = ctx.resourceManager.getRawFileContentSync('rime/' + relName);
    const dest: string = baseDir + '/' + relName;
    // H-272（Qoder 2026-10-29）：主人自己的数据不许被随包版本覆盖。
    // 这次换英文链数据改了 DATA_VERSION，会触发一次全量重铺；以前 release() 是无条件 TRUNC，
    // 重铺一次就把主人在手机上攒的自造短语冲成随包那份。只有 Custom_phrase.txt 是用户数据
    // （rime.lua 等其余项必须跟着包更新），所以只对它做「已存在就跳过」。
    if (relName === 'Custom_phrase.txt') {
      try {
        if (fs.accessSync(dest)) {
          console.info(`${TAG} keep user file ${dest}`);
          return 0;
        }
      } catch (e) {
        // 不存在 ⇒ 照常释放随包版本
      }
    }
    const file: fs.File = fs.openSync(dest,
      fs.OpenMode.READ_WRITE | fs.OpenMode.CREATE | fs.OpenMode.TRUNC);
    try {
      fs.writeSync(file.fd, raw.buffer as ArrayBuffer);
    } finally {
      fs.closeSync(file);
    }
    console.info(`${TAG} released ${dest}: ${raw.byteLength} B`);
    return raw.byteLength;
  }
}
