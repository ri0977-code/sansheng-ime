/*
 * 三生输入法 · M3 真机自检页（引擎 + 数据 + 智能九键）
 * 归属：Qoder（仅测试用，正常启动不会进入本页；键盘 UI 与 IME 面板都不经过）。
 *
 * 为什么要它：主人明确要求「不要让我验，连着 Mate 80 你自己验每一步」。
 * 引擎用例（五笔/拼音/英文/互译/简繁/T9/ascii_mode）在这页里直接调
 * EngineProvider，结果写在屏上并同步进 hilog（TAG=SSM3Probe），
 * 我可以用 uitest dumpLayout / screenCap / hilog 三种方式取证据，
 * 不需要人肉在九宫格上按一下看一下。
 *
 * 启动：aa start -b com.sansheng.ime -a EntryAbility --ps m3_probe 1
 *
 * 注意：本页验的是「引擎+数据」这一层。候选栏显示、翻页手势、空格上屏
 * 这些 UI 行为仍要走 IME 面板（KeyboardIndex），两者不能互相替代。
 */
import { common } from '@kit.AbilityKit';
import { fileIo as fs } from '@kit.CoreFileKit';
import { EngineProvider } from '../engine/EngineProvider';
import { RimeCandidate, RimeContext, RimeEngine } from '../engine/RimeEngine';

@Entry
@Component
struct M3Probe {
  @State report: string = '初始化中…';
  @State running: boolean = false;
  private engine: RimeEngine = EngineProvider.get();
  private lines: string[] = [];

  private log(line: string): void {
    this.lines.push(line);
    // 同步一份到 hilog，方便 hdc hilog | grep SSM3Probe 取机器可读证据
    console.info(`[SSM3Probe] ${line}`);
    this.report = this.lines.join('\n');
  }

  /** 逐字符送入编码，返回最后一次 context。 */
  private typeSeq(coding: string): RimeContext {
    let ctx: RimeContext = this.engine.clear();
    for (let i = 0; i < coding.length; i++) {
      ctx = this.engine.processKey(coding.charAt(i));
    }
    return ctx;
  }

  /** 逐字符送入编码但**不清码**（自造词要「连续上屏」，中间不能断）。 */
  private typeSeqRaw(coding: string): RimeContext {
    let ctx: RimeContext = this.engine.getContext();
    for (let i = 0; i < coding.length; i++) {
      ctx = this.engine.processKey(coding.charAt(i));
    }
    return ctx;
  }

  private firstPage(ctx: RimeContext, limit: number): string {
    const parts: string[] = [];
    const n: number = Math.min(limit, ctx.candidates.length);
    for (let i = 0; i < n; i++) {
      const c: RimeCandidate = ctx.candidates[i];
      parts.push(c.comment !== undefined && c.comment.length > 0 ? `${c.text}[${c.comment}]` : c.text);
    }
    return parts.join(' / ');
  }

  private has(ctx: RimeContext, word: string): boolean {
    for (let i = 0; i < ctx.candidates.length; i++) {
      if (ctx.candidates[i].text === word) {
        return true;
      }
    }
    return false;
  }

  /** 候选词在当前页里的下标，找不到返回 -1。 */
  private indexOf(ctx: RimeContext, word: string): number {
    for (let i = 0; i < ctx.candidates.length; i++) {
      if (ctx.candidates[i].text === word) {
        return i;
      }
    }
    return -1;
  }

  /** 当前页全部候选（含 comment），一行拉平，方便在 hilog 里核对条数与内容。 */
  private allCandidates(ctx: RimeContext): string {
    const parts: string[] = [];
    for (let i = 0; i < ctx.candidates.length; i++) {
      const c: RimeCandidate = ctx.candidates[i];
      parts.push(c.comment !== undefined && c.comment.length > 0 ? `${c.text}[${c.comment}]` : c.text);
    }
    return parts.join(' / ');
  }

  /** 一条用例：期望某个词出现在候选里。 */
  private expectCand(title: string, coding: string, word: string, expect: boolean): RimeContext {
    const ctx: RimeContext = this.typeSeq(coding);
    const got: boolean = this.has(ctx, word);
    const verdict: string = (got === expect ? 'PASS' : 'FAIL');
    this.log(`${verdict} ${title}: 输入"${coding}" 预编辑"${ctx.preedit}" ` +
      `${expect ? '含' : '不含'}"${word}"=${got} ｜ ${this.firstPage(ctx, 6)}`);
    return ctx;
  }

  /**
   * 扫桥重定向的进程 stderr（<user>/napi_stderr.txt），把异常行挑出来。
   * 返回异常行条数。
   *
   * 为什么要在**每轮末尾**再扫一次：0.6 那次扫描发生在任何提交之前，
   * 而用户词典、编码反查这些"提交时才发生"的问题（userdb 打不开、
   * dict 编译失败）只会在后半程才写进 stderr —— 扫早了等于没扫。
   */
  private stderrScan(tag: string): number {
    const userPath: string = `${getContext(this).filesDir}/rime_user`;
    let bad: string[] = [];
    let total: number = 0;
    try {
      const txt: string = fs.readTextSync(userPath + '/napi_stderr.txt');
      const lines: string[] = txt.split('\n');
      for (const line of lines) {
        const trimmed: string = line.trim();
        if (trimmed.length === 0) {
          continue;
        }
        total++;
        const low: string = trimmed.toLowerCase();
        if (low.indexOf('error') >= 0 || low.indexOf('fail') >= 0 ||
          low.indexOf('traceback') >= 0 || low.indexOf('nil value') >= 0 ||
          low.indexOf('func type') >= 0) {
          if (bad.length < 12) {
            bad.push(trimmed);
          }
        }
      }
    } catch (e) {
      this.log(`INFO ${tag}: 读 napi_stderr.txt 失败（引擎可能还没写过 stderr）: ${JSON.stringify(e)}`);
      return 0;
    }
    this.log(`${bad.length === 0 ? 'PASS' : 'FAIL'} stderr 异常行(${tag}): ${bad.length} 条` +
      `${bad.length > 0 ? ' ｜ ' + bad.join(' ｜ ') : ''}（stderr 全文 ${total} 行）`);
    return bad.length;
  }

  /**
   * M4 ①：Lua 齿轮真模块是否真的加载上了。
   *
   * 判据：桥把进程 stderr 重定向到 <user>/napi_stderr.txt（fanxing_napi.cpp），
   * 而 rime.lua 里每个齿轮加载失败都会写一行 "[sansheng-lua] stub <名字>"。
   * 所以「stub 行数 == 0」= 15 级齿轮全部用上了真模块；> 0 = 还在跑桩，
   * 少的那几级能力（拼音注释/短语释义/自定义短语/中英对照/编码反查…）就没上线。
   *
   * 【v14 增补】光看 stub 行数不够：2026-10-21 22:35 查出「候选只剩 2 条」的真凶是
   * `lua_translator@rawEcho_translator` 这个全局在 rime.lua 里从来没定义过 ——
   * 它不产生 stub 行（压根没进 need() 列表），但每次调用都抛
   * "func type error expect function"，抛错的 LuaTranslation::Next 会把整条候选队列打断。
   * 所以这里额外把 stderr 里带 error/fail/nil 的行原样打出来，异常自己会喊。
   */
  private luaModuleCheck(filesDir: string): void {
    const userPath: string = filesDir + '/rime_user';
    // ① 齿轮文件是否真的释放到沙箱
    let luaFiles: number = 0;
    try {
      const names: string[] = fs.listFileSync(userPath + '/lua');
      luaFiles = names.length;
    } catch (e) {
      this.log(`FAIL lua 目录未释放: ${JSON.stringify(e)}`);
      return;
    }
    // ② stderr 里的 stub 行
    let stubs: number = 0;
    let errLines: string[] = [];
    try {
      const txt: string = fs.readTextSync(userPath + '/napi_stderr.txt');
      const lines: string[] = txt.split('\n');
      for (const line of lines) {
        if (line.indexOf('[sansheng-lua] stub') >= 0) {
          stubs++;
          if (errLines.length < 4) {
            errLines.push(line.trim());
          }
        }
      }
      this.log(`${stubs === 0 ? 'PASS' : 'FAIL'} Lua 齿轮: 沙箱 lua/ 共 ${luaFiles} 个文件, ` +
        `stderr 里 stub 行 ${stubs} 条（0 = 15 级真模块全部加载）` +
        `${stubs > 0 ? ' ｜ ' + errLines.join(' / ') : ''}`);
    } catch (e) {
      this.log(`INFO 读 napi_stderr.txt 失败（引擎可能还没写过 stderr）: ${JSON.stringify(e)}`);
    }
    this.stderrScan('初始化后');
  }

  /**
   * M4 ②：候选分页连续性自检（v0.2.0 引擎分页契约）。
   *
   * 要验的是「翻页不重、不跳」：把同一编码的候选逐页翻完，
   * 收集每一页的候选文本，判据是
   *   ① 页内无重复；
   *   ② 跨页无重复（旧算法 abs_start = ui_page * page_size 在 N 除不尽时会跳条）；
   *   ③ 翻到 Rime 菜单页边界后仍然不重不跳（跨页连续）。
   * 每页 5 条，'nihao' 在 wubi_pinyin 下有 50 条候选（Rime 菜单页大小 = 50），
   * 正好翻 10 页；再多翻 2 页跨过 Rime 菜单页边界。
   */
  private pagingSelfTest(): void {
    const ctx: RimeContext = this.typeSeq('nihao');
    const all: number = ctx.allCandidates.length;
    const seen: string[] = [];
    let dup: string = '';
    let pages: number = 0;
    let cur: RimeContext = ctx;
    const push = (c: RimeContext): void => {
      for (const cand of c.candidates) {
        if (seen.indexOf(cand.text) >= 0 && dup === '') {
          dup = cand.text;
        }
        seen.push(cand.text);
      }
    };
    push(cur);
    pages = 1;
    let guard: number = 0;
    while (cur.hasNext && guard < 14) {
      cur = this.engine.flipPage(1);
      push(cur);
      pages++;
      guard++;
    }
    this.log(`${dup === '' ? 'PASS' : 'FAIL'} 分页连续性: 编码 nihao 全量 ${all} 条, ` +
      `翻了 ${pages} 页共收集 ${seen.length} 条, 重复项=${dup === '' ? '无' : dup} ` +
      `｜首页 ${this.firstPage(ctx, 5)}`);
  }

  /** 候选列表带下标，方便在 hilog 里核对位次（自调频就靠这个下标判前后）。 */
  private indexedCandidates(ctx: RimeContext): string {
    const parts: string[] = [];
    for (let i = 0; i < ctx.candidates.length; i++) {
      const c: RimeCandidate = ctx.candidates[i];
      parts.push(`#${i}:${c.text}`);
    }
    return parts.join(' ');
  }

  /**
   * 把用户词典的**明文**文件打到 hilog。
   *
   * wubi_pinyin 的用户词典是 tabledb（db_class: tabledb，user_dict: user），
   * 落在 <user>/user.txt，行格式是「词 \t 编码 \t 上屏次数」（table_db.cc 的
   * rime_table_entry_formatter）。第 3 列就是 commit_count —— 频率涨没涨，
   * 看这一列最实在，比看候选顺序更硬。
   */
  private dumpUserDbFiles(filesDir: string, tag: string): void {
    const userPath: string = filesDir + '/rime_user';
    const names: string[] = ['user.txt', 'Custom_phrase.txt'];
    for (const n of names) {
      let rows: string[] = [];
      try {
        const txt: string = fs.readTextSync(userPath + '/' + n);
        const lines: string[] = txt.split('\n');
        for (const l of lines) {
          const t: string = l.trim();
          if (t.length > 0) {
            rows.push(t);
          }
        }
        this.log(`INFO userdb[${tag}] ${n}: ${rows.length} 行 ｜ ${rows.slice(0, 15).join(' ｜ ')}`);
      } catch (e) {
        this.log(`INFO userdb[${tag}] ${n}: 读不到（tabledb 时代才是明文文件；v17 起主词典是 user.userdb/）`);
      }
    }
    // v17（D-010）：db_class 换成 userdb 后，用户词典是 LevelDB 目录 <user>/user.userdb/。
    // 它是二进制 + 日志，读不了内容，但**有非空数据文件就证明落盘了**，所以这里列文件名和字节数。
    const dbPath: string = userPath + '/user.userdb';
    let dbNames: string[] = [];
    try {
      dbNames = fs.listFileSync(dbPath);
    } catch (e) {
      this.log(`INFO userdb[${tag}] user.userdb/: 读不到（LevelDb 还没建）`);
      return;
    }
    let total: number = 0;
    const detail: string[] = [];
    for (const n of dbNames) {
      let size: number = -1;
      try {
        size = fs.statSync(dbPath + '/' + n).size;
      } catch (e) {
        size = -1;
      }
      if (size > 0) {
        total += size;
      }
      detail.push(`${n}:${size}B`);
    }
    this.log(`${total > 0 ? 'PASS' : 'FAIL'} userdb[${tag}] user.userdb/: ${dbNames.length} 项，数据 ${total} B ｜ ` +
      detail.join(' '));
  }

  /**
   * M4 ③：用户词典（自调频）落盘 + 频率真的会上调。
   *
   * librime 的 table_translator 开了 enable_user_dict（wubi_pinyin.schema.yaml:79），
   * 用户选中过的词会写进 <user>/user.txt，重启后该词的频率会自己上调。
   *
   * v13 的写法有个致命缺陷：目标词「尚贤」压根不在 'shangxian' 的候选里 ⇒
   * 一次学习事件都没制造出来，等于测了个寂寞（userdb 里只有 pinyin_simp 那个）。
   * v14 改成两轮闭环，但只在提交后**立刻**列目录，抓不到落盘后的样子。
   * v16 改成三层证据：
   *   ① 跨会话位次：读上轮状态 → 本轮位次前移 = 频率已上调
   *   ② 同会话位次：连着提交同一个词 3 次 → 立刻再打一次看位次
   *   ③ 明文行：把 user.txt 的行（词 \t 编码 \t 上屏次数）原样打出来
   * 三条里只要有一条给出正信号，就能定位到「是没落盘」还是「落了但没生效」。
   */
  private userDictCheck(filesDir: string): void {
    const statePath: string = filesDir + '/m4-userdict-state.txt';
    const code: string = 'nihao';
    let oldText: string = '';
    let oldIndex: number = -1;
    let oldTop: boolean = false;
    try {
      const raw: string = fs.readTextSync(statePath).trim();
      const parts: string[] = raw.split('\t');
      if (parts.length >= 3) {
        oldText = parts[1];
        oldIndex = parseInt(parts[2]);
      }
      if (parts.length >= 4) {
        oldTop = parts[3] === '1';
      }
    } catch (e) {
      this.log('INFO 自调频: 没有历史状态文件（这是第一轮），本轮只制造学习事件');
    }
    // ① 跨会话：打同一个编码，看上一轮那个词现在排第几
    const ctx: RimeContext = this.typeSeq(code);
    this.log(`INFO 自调频: 编码 ${code} 候选 ${ctx.candidates.length} 条 ｜ ${this.indexedCandidates(ctx)}`);
    if (oldText.length > 0) {
      const now: number = this.indexOf(ctx, oldText);
      const moved: boolean = now >= 0 && (now < oldIndex || (oldTop && now === 0));
      this.log(`${moved ? 'PASS' : 'FAIL'} 自调频(跨会话): 上轮「${oldText}」位次 ${oldIndex}` +
        `${oldTop ? '(已到首位)' : ''} → 本轮 ${now}` +
        `${now < 0 ? '（本轮候选里没有它）' : (moved ? '（前移/守住首位 = 频率已上调）' : '（没前移）')}`);
    }
    // ② 同会话：连着提交同一个词 3 次（真实用户反复选同一个词，频率就是这么涨的）
    const target: string = oldText.length > 0 ? oldText : 'hello';
    let committed: number = 0;
    let firstIdx: number = -1;
    let lastIdx: number = -1;
    for (let round = 0; round < 3; round++) {
      const c: RimeContext = this.typeSeq(code);
      const idx: number = this.indexOf(c, target);
      if (idx < 0) {
        this.log(`INFO 自调频: 第 ${round + 1} 次提交前「${target}」不在候选里（${this.firstPage(c, 5)}），停`);
        break;
      }
      if (firstIdx < 0) {
        firstIdx = idx;
      }
      lastIdx = idx;
      const out: string = this.engine.selectCandidate(idx);
      committed++;
      this.log(`INFO 自调频: 第 ${round + 1} 次提交「${target}」（提交前位次 ${idx}，上屏"${out}"）`);
    }
    // 提交完立刻再打一次：频率是内存里就生效的，这里能区分「没落盘」和「没生效」。
    // 判据用**第一次提交前**的位次（firstIdx）比，不是最后一次 —— 词一旦升到首位，
    // 后面的提交都在首位，比 lastIdx 永远是「没前移」。
    // v18：如果第一笔提交前就已经在首位，本来就没有前移空间，不能判 FAIL。
    const after: RimeContext = this.typeSeq(code);
    const nowIdx: number = this.indexOf(after, target);
    if (committed > 0 && firstIdx === 0 && nowIdx === 0) {
      this.log(`INFO 自调频(同会话): 提交 ${committed} 次前后「${target}」都在首位，无前移空间` +
        `（跨会话位次才是判据）｜ ${this.indexedCandidates(after)}`);
    } else {
      const movedInSession: boolean = committed > 0 && nowIdx >= 0 && firstIdx >= 0 && nowIdx < firstIdx;
      this.log(`${committed > 0 ? (movedInSession ? 'PASS' : 'FAIL') : 'INFO'} ` +
        `自调频(同会话): 提交 ${committed} 次后「${target}」位次 ${firstIdx} → ${nowIdx} ｜ ${this.indexedCandidates(after)}`);
    }
    // ③ 写状态：下一轮拿它对比位次（第 4 段记「是否已到首位」，到首位就算守住）
    const stateIdx: number = nowIdx >= 0 ? nowIdx : lastIdx;
    const reachedTop: string = stateIdx === 0 ? '1' : '0';
    try {
      const state: string = `${code}\t${target}\t${stateIdx}\t${reachedTop}`;
      const f: fs.File = fs.openSync(statePath,
        fs.OpenMode.READ_WRITE | fs.OpenMode.CREATE | fs.OpenMode.TRUNC);
      try {
        fs.writeSync(f.fd, state);
      } finally {
        fs.closeSync(f);
      }
    } catch (e) {
      this.log(`WARN 写状态文件失败: ${JSON.stringify(e)}`);
    }
    // ④ **提交之后**再列 userdb —— v14 之前的写法是在提交前列，
    // 于是「本轮刚建出来的 userdb」永远看不到（看起来像没落盘，其实是没查到）。
    this.dumpUserDir(filesDir);
    this.dumpUserDbFiles(filesDir, '提交后');
  }

  /**
   * 把沙箱里的关键目录列出来：user 目录（找 *.userdb）、rime 目录（找 build/ 编译产物）。
   * 自调频查不出来的第一嫌疑就是「userdb 根本没建」，所以每次提交后都要看一眼。
   */
  private dumpUserDir(filesDir: string): void {
    const userPath: string = filesDir + '/rime_user';
    let names: string[] = [];
    try {
      names = fs.listFileSync(userPath);
    } catch (e) {
      this.log(`FAIL 读 user 目录失败: ${JSON.stringify(e)}`);
      return;
    }
    const dbs: string[] = [];
    for (const n of names) {
      if (n.indexOf('.userdb') >= 0) {
        dbs.push(n);
      }
      if (n.indexOf('.bin') >= 0 || n.indexOf('build') >= 0) {
        // build 目录在 shared 侧，这里只做提示
      }
    }
    this.log(`INFO 沙箱 user 目录: 共 ${names.length} 项 ｜ userdb=[${dbs.join(',')}]` +
      `｜ 全部=[${names.join(',')}]`);
    // shared 侧：build/ 里应该有编译出来的 .bin
    try {
      const shared: string[] = fs.listFileSync(filesDir + '/rime');
      let binCount: number = 0;
      for (const n of shared) {
        if (n.indexOf('.bin') >= 0) {
          binCount++;
        }
      }
      this.log(`INFO 沙箱 shared 目录: 共 ${shared.length} 项，其中 .bin ${binCount} 个` +
        `｜ 顶层=[${shared.join(',')}]`);
    } catch (e) {
      this.log(`INFO 读 shared 目录失败: ${JSON.stringify(e)}`);
    }
  }

  /**
   * M4 ④：自造词（连打造句）真的落盘并在下一轮还在。
   *
   * 机制：schema 的 translator 开了 enable_encoder + encode_commit_history
   * （wubi_pinyin.schema.yaml:76-77）——连续上屏的词会被合并成一个词条，
   * 连同**当时打的编码**写进用户词典；下一轮打同一串编码，合并词就会出现在候选里。
   *
   * 两轮闭环：
   *   ① 第一轮：打 mqj（刚）→ 空格上屏；紧接着打 fdm（需）→ 空格上屏。
   *      中间**不能清码**（清了就断成两次独立上屏，encoder 不会合并），
   *      所以这里用 typeSeqRaw 而不是 typeSeq。
   *   ② 第二轮：打合并后的编码 mqjfdm，期望候选里有「刚需」。
   * 状态文件：<filesDir>/m4-phrase-state.txt（写下已造的编码）。
   */
  private phraseSelfMakeCheck(filesDir: string): void {
    const statePath: string = filesDir + '/m4-phrase-state.txt';
    // v18：改用字典里没有的生僻词「鑫淼」（qqq + iiiu），并且**造之前先确认它不存在**。
    // 旧词「刚需」有可能是 rime 的连句候选（系统自己拼出来的），那样 PASS 就是假阳性；
    // 鑫淼没有任何词库条目，能出现只可能是用户词典里被 encoder 合并出来的。
    const mergedCode: string = 'qqqiiiu';
    const mergedWord: string = '鑫淼';
    // 上一轮已经造过？这一轮就只验「还在不在」
    let made: boolean = false;
    try {
      const raw: string = fs.readTextSync(statePath).trim();
      made = raw.indexOf(mergedCode) >= 0;
    } catch (e) {
      made = false;
    }
    if (made) {
      const ctx: RimeContext = this.typeSeq(mergedCode);
      const got: boolean = this.has(ctx, mergedWord);
      this.log(`${got ? 'PASS' : 'FAIL'} 自造词(跨会话): 打"${mergedCode}" 期望含"${mergedWord}"=${got} ` +
        `｜ ${this.firstPage(ctx, 6)}`);
      return;
    }
    // 前置检查：造之前它必须不存在，否则这组词当不了证据
    const pre: RimeContext = this.typeSeq(mergedCode);
    if (this.has(pre, mergedWord)) {
      this.log(`WARN 自造词: 打"${mergedCode}"本来就有「${mergedWord}」，这组不能当证据（${this.firstPage(pre, 5)}）`);
      return;
    }
    this.log(`INFO 自造词: 前置检查通过——"${mergedCode}"原本没有「${mergedWord}」，开始造`);
    // 第一轮：造它
    this.engine.clear();
    const c1: RimeContext = this.typeSeqRaw('qqq');
    const i1: number = this.indexOf(c1, '鑫');
    if (i1 < 0) {
      this.log(`INFO 自造词: 'qqq' 候选里没有「鑫」（${this.firstPage(c1, 5)}），本轮造不了`);
      return;
    }
    const t1: string = this.engine.selectCandidate(i1);
    // 关键：不 clear，接着打第二个词
    const c2: RimeContext = this.typeSeqRaw('iiiu');
    const i2: number = this.indexOf(c2, '淼');
    if (i2 < 0) {
      this.log(`INFO 自造词: 'iiiu' 候选里没有「淼」（${this.firstPage(c2, 5)}），本轮造不了`);
      return;
    }
    const t2: string = this.engine.selectCandidate(i2);
    // 同会话立刻验一次：能查到 = encoder 真的合并了（而不是等下一轮碰运气）
    const now: RimeContext = this.typeSeq(mergedCode);
    const madeNow: boolean = this.has(now, mergedWord);
    this.log(`${madeNow ? 'PASS' : 'INFO'} 自造词(同会话已造出): 连续上屏「${t1}」「${t2}」后打"${mergedCode}"` +
      ` 含「${mergedWord}」=${madeNow} ｜ ${this.firstPage(now, 6)}`);
    this.log(`INFO 自造词: 等下次启动打"${mergedCode}"验证跨会话（用户词典 <user>/user.userdb/）`);
    try {
      const f: fs.File = fs.openSync(statePath,
        fs.OpenMode.READ_WRITE | fs.OpenMode.CREATE | fs.OpenMode.TRUNC);
      try {
        fs.writeSync(f.fd, mergedCode);
      } finally {
        fs.closeSync(f);
      }
    } catch (e) {
      this.log(`WARN 写状态文件失败: ${JSON.stringify(e)}`);
    }
  }

  /**
   * M4 ④：/ 通道（rawEcho_translator + 三生符号斜杠码）能不能触发。
   *
   * 桌面端 rawEcho_translator 的用法是打 "/5g" → 出「5G「第五代移动通信」」，
   * "/ri0977" → 出原文与大写。前提是 **"/" 这个键要进 Rime 的组词串**。
   * 鸿蒙桥（fanxing_napi.cpp ProcessKey）现在的策略是：
   *   字母 → 送 Rime；数字 → 先送 Rime，接不住就直出；**其它单字符（标点）→ 一律直出**。
   * 所以 "/" 根本到不了 Rime，recognizer 的 rawNum 规则也就无从匹配。
   * 这条用例就是把这个事实量出来（真机证据，不是推断）。
   */
  private rawEchoCheck(): void {
    this.engine.clear();
    const steps: string[] = [];
    const seq: string[] = ['/', '5', 'g'];
    for (const ch of seq) {
      const k: RimeContext = this.engine.processKey(ch);
      steps.push(`"${ch}"→预编辑"${k.preedit}"上屏"${k.commitText ?? ''}"候选${k.candidates.length}`);
    }
    const joined: string = steps.join(' ｜ ');
    this.log(`INFO / 通道: ${joined}`);
    this.log(`INFO / 通道判定: 桥把非字母非数字的单字符直接上屏 ⇒ Rime 收不到 "/" ⇒ ` +
      `rawEcho_translator 与斜杠符号表在鸿蒙上暂时触发不了（详见 INTERFACE.md 的 H-064）`);
    this.engine.clear();
  }

  private async run(): Promise<void> {
    if (this.running) {
      return;
    }
    this.running = true;
    this.lines = [];
    this.log(`M3 自检开始 ${new Date().toLocaleTimeString()}`);

    // 0) 初始化（含 17MB 数据释放 + 首次词库编译），耗时是关键指标
    const ctx0: common.Context = getContext(this) as common.Context;
    const t0: number = Date.now();
    try {
      await this.engine.init(ctx0.filesDir + '/rime', ctx0);
      this.log(`PASS init: ${Date.now() - t0} ms（含数据释放与首次编译）`);
    } catch (e) {
      this.log(`FAIL init: ${JSON.stringify(e)} (${Date.now() - t0} ms)`);
      this.running = false;
      return;
    }

    // 0.5) H-044 结案回归（run13 起诊断方案 zzd_* 全部下线，换成这条）：
    // 光看「候选不为 0」分不清「13 级齿轮真挂上且无害」和「齿轮根本没挂」，
    // 所以两条一起验：① 发布后的 yaml 里确实有 lua_filter@/lua_translator@ 行；
    // ② 挂着它们的 wubi_pinyin 出词和摘链时逐条一致（下面第 3 个用例）。
    const rimeDir: string = `${getContext(this).filesDir}/rime`;
    let gears: number = 0;
    const gearFiles: string[] = ['wubi_pinyin.schema.yaml', 'wubi_pinyin.custom.yaml'];
    for (const f of gearFiles) {
      try {
        const txt: string = fs.readTextSync(`${rimeDir}/${f}`);
        const hits: string[] | null = txt.match(/lua_(filter|translator)@/g);
        gears += hits === null ? 0 : hits.length;
      } catch (e) {
        this.log(`FAIL 读 ${f} 失败: ${JSON.stringify(e)}`);
      }
    }
    this.log(`${gears >= 13 ? 'PASS' : 'FAIL'} Lua 齿轮已挂载: 发布件里 lua_filter@/lua_translator@ 共 ${gears} 行` +
      `（桌面基线 13 级 = 2 translator + 11 filter，run13 真机验证挂满后候选 4 条不变）`);
    this.engine.selectSchema('wubi_pinyin');

    // 0.6) M4：真模块有没有真的加载上（stub 行数 == 0 才算全量上齐）
    this.luaModuleCheck(getContext(this).filesDir);

    // 1) 拼音混输（wubi_pinyin 通过 import_tables 带拼音词）
    this.expectCand('拼音混输', 'nihao', '你好', true);
    this.expectCand('拼音词（H-042 的样本）', 'nihaoma', '你好吗', true);

    // 2) 五笔：你好 = 你(WQ)+好(VB) 前两码
    this.expectCand('五笔词码', 'wqvb', '你好', true);

    // 3) 英→中（en2zh_v2：打英文出中文释义）
    this.expectCand('英→中', 'dog', '狗', true);

    // 4) 中→英（zh2en_pinyin：打拼音出英文）
    const z2e: RimeContext = this.typeSeq('haoma');
    this.log(`INFO 中→英(拼音) "haoma": ${this.firstPage(z2e, 8)}`);

    // 5) 智能九键 T9：n=6 i=4 h=4 a=2 o=6
    const switched: boolean = this.engine.selectSchema('sansheng_t9');
    this.log(`${switched ? 'PASS' : 'FAIL'} selectSchema(sansheng_t9)=${switched}`);
    if (switched) {
      this.expectCand('九宫格 T9', '64426', '你好', true);
      this.expectCand('九宫格 T9 数字直入', '986', '九', false);
      const t9: RimeContext = this.typeSeq('746');
      this.log(`INFO T9 "746"(=p?o?i?): 预编辑"${t9.preedit}" ${this.firstPage(t9, 8)}`);
      this.engine.selectSchema('wubi_pinyin');
      this.log('INFO 已切回 wubi_pinyin');
    }

    // 6) 简繁（H-041 之一）
    this.engine.setOption('zh_trad', false);
    const simp: RimeContext = this.expectCand('简体基线', 'zhongguo', '中国', true);
    this.engine.setOption('zh_trad', true);
    const trad: RimeContext = this.typeSeq('zhongguo');
    this.log(`INFO 繁体开关后: 简体首选"${simp.candidates.length > 0 ? simp.candidates[0].text : ''}" ` +
      `→ 现在"${trad.candidates.length > 0 ? trad.candidates[0].text : ''}" ${this.firstPage(trad, 6)}`);
    this.log(`INFO 简繁开关读回（v0.1.8 getOption）：开着的值=${this.engine.getOption('zh_trad')} ` +
      `关着读回=${this.engine.getOption('ascii_mode') === false ? 'ascii_mode=false 正常' : '异常'}`);
    this.engine.setOption('zh_trad', false);

    // 7) ascii_mode（H-041 之二）：英文模式下字母应直接上屏。
    // run10 的 FAIL 是探针自己的锅：上一步 `typeSeq('zhongguo')` 的编码还活着，
    // librime 的 ascii_composer 在「编码非空」时**故意**不直出（怕把用户正打的字打断），
    // 于是 'x' 被追加成 "zhongguox"。必须先 clear() 再从空编码按。
    this.engine.clear();
    this.engine.setOption('ascii_mode', true);
    const asciiOn: boolean = this.engine.getOption('ascii_mode');
    const asciiCtx: RimeContext = this.engine.processKey('x');
    this.log(`${asciiCtx.commitText !== undefined && asciiCtx.commitText.length > 0 ? 'PASS' : 'FAIL'} ` +
      `ascii_mode: setOption 后 getOption=${asciiOn} processKey('x') ` +
      `commitText="${asciiCtx.commitText ?? ''}" 预编辑"${asciiCtx.preedit}" 候选${asciiCtx.candidates.length}条`);
    // 大写走的是 shift+字母（桥里的 mask 分支），单独再验一次
    const asciiUpper: RimeContext = this.engine.processKey('X');
    this.log(`INFO ascii_mode 大写: commitText="${asciiUpper.commitText ?? ''}" ` +
      `预编辑"${asciiUpper.preedit}" 候选${asciiUpper.candidates.length}条`);
    // 7a) 连打：产品语义是「英文模式下按一个字母上屏一个」，所以还要验连续两次
    //（桥里的兜底只要不吞前一次就合格；hilog 里 [Rime-Napi] ascii probe 给的是原始现场）。
    let joined: string = '';
    const seqChars: string[] = ['h', 'i'];
    for (const c of seqChars) {
      const k: RimeContext = this.engine.processKey(c);
      joined += (k.commitText ?? '');
    }
    this.log(`${joined === 'hi' ? 'PASS' : 'FAIL'} ascii_mode 连打"hi": 上屏合计"${joined}"`);
    this.engine.setOption('ascii_mode', false);
    this.log(`INFO ascii_mode 关掉后 getOption=${this.engine.getOption('ascii_mode')}`);
    // 7b) 对照实验：同一个开关换到 pinyin_simp（桌面自带的纯净方案）再按一次。
    // 如果那边字母直出、wubi_pinyin 这边不直出，锅就在 wubi_pinyin 的 processors
    // （ascii_composer 缺失或被别的 processor 吞掉），不在桥、也不在开关本身。
    // 注意 selectSchema 会重置开关，所以必须先切方案再 setOption。
    this.engine.clear();
    const swapOk: boolean = this.engine.selectSchema('pinyin_simp');
    this.engine.setOption('ascii_mode', true);
    const psCtx: RimeContext = this.engine.processKey('x');
    this.log(`INFO ascii_mode 对照 pinyin_simp(selectSchema=${swapOk} ` +
      `getOption=${this.engine.getOption('ascii_mode')}): commitText="${psCtx.commitText ?? ''}" ` +
      `预编辑"${psCtx.preedit}" 候选${psCtx.candidates.length}条`);
    this.engine.setOption('ascii_mode', false);
    this.engine.selectSchema('wubi_pinyin');
    this.engine.clear();

    // 8) 反查入口：` 前缀（拼音反查五笔码，comment 需要 M3b 的 lua 滤镜才完整）
    this.engine.clear();
    const rev: RimeContext = this.typeSeq("`ni");
    this.log(`INFO 反查 \`ni: 预编辑"${rev.preedit}" ${this.firstPage(rev, 6)}`);

    // 9) M4：分页连续性（v0.2.0 引擎分页契约：翻页不重、不跳）
    this.engine.clear();
    this.pagingSelfTest();

    // 10) M4：用户词典（自调频）落盘 + 制造一次学习事件
    this.engine.clear();
    this.userDictCheck(getContext(this).filesDir);

    // 11) M4：自造词（连打造句）落盘
    this.engine.clear();
    this.phraseSelfMakeCheck(getContext(this).filesDir);

    // 12) M4：/ 通道（rawEcho / 斜杠符号表）当前能不能触发
    this.engine.clear();
    this.rawEchoCheck();

    // 13) 收尾再扫一次 stderr：用户词典、编码反查这类"提交时才发生"的错误
    // 只会在后半程写进 stderr，开头那一次扫描看不到。
    this.stderrScan('全部用例跑完后');

    // 14) 收尾再列一次用户词典：rime 的 db 落盘是**延时 100ms 的异步提交**，
    // 提交完立刻看是看不到结果的（v15 就栽在这）。这一轮跑完已经过了好几秒，
    // 这时候再看 user.txt，commit_count 才是真值。
    this.dumpUserDir(getContext(this).filesDir);
    this.dumpUserDbFiles(getContext(this).filesDir, '全部用例跑完后');

    this.engine.clear();
    this.log(`M3 自检结束 ${new Date().toLocaleTimeString()}（共 ${this.lines.length} 行）`);
    this.running = false;
  }

  /** 自动化优先：进页面就自己跑一轮，uitest 只需要等 + 截图，不需要人（或脚本）点按钮。 */
  aboutToAppear(): void {
    // m4_phrase_reset=1 启动参数：清掉自造词状态，重新走「造词 → 杀进程 → 重开 → 还在」
    if (AppStorage.get<boolean>('m4PhraseReset') === true) {
      try {
        fs.unlinkSync(getContext(this).filesDir + '/m4-phrase-state.txt');
        console.info('[SSM3Probe] m4_phrase_reset: state cleared');
      } catch (e) {
        console.info('[SSM3Probe] m4_phrase_reset: nothing to clear');
      }
    }
    this.run();
  }

  build() {
    Column({ space: 12 }) {
      Text('M3 引擎自检')
        .fontSize(22)
        .fontWeight(FontWeight.Bold)
      Button(this.running ? '运行中…' : '运行 M3 用例')
        .onClick(() => {
          this.run();
        })
      Scroll() {
        Text(this.report)
          .fontSize(13)
          .fontFamily('monospace')
          .width('100%')
      }
      .layoutWeight(1)
      .width('100%')
      .align(Alignment.TopStart)
    }
    .width('100%')
    .height('100%')
    .padding({ left: 16, right: 16, top: 16, bottom: 16 })
    .alignItems(HorizontalAlign.Start)
  }
}
