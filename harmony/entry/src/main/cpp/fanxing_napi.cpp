/*
 * 三生输入法 · Rime NAPI 桥（M2）
 * 归属：Qoder。
 *
 * 版权与许可：本文件为 Apache License 2.0（见仓库根 LICENSE）。
 * 本文件相对上游 chuanis/harmonyos-next-rime-har（MIT）的同名 demo 桥
 * **整体重写**（Apache-2.0 第 4(b) 条要求的改动声明）：
 *   - 上游 demo：initEngine + processKey 两个函数，进程内共享单例。
 *   - 本文件：按 docs/INTERFACE.md v0.1.8 实现 initEngine / checkStatus /
 *     switchSchema（ArkTS 侧对外叫 selectSchema）/ processKey /
 *     selectCandidate / deleteBackward / flipPage / clear / getContext /
 *     setOption / getOption / setPageSize，并做句柄校验与错误返回；
 *     页大小由 UI 侧 setPageSize 驱动（g_page_size），不再固定切片。
 * 上游 MIT 版权与许可声明见 LICENSES/MIT-harmonyos-next-rime-har.txt。
 *
 * 与 M1 的 demo 桥不同，这里按 docs/INTERFACE.md v0.1.5 实现：
 *   initEngine / processKey / selectCandidate / deleteBackward /
 *   flipPage / clear / getContext / setOption / setPageSize
 *
 * 分页策略（v0.2.0 修正）：
 *   - Rime 自己的菜单页大小由部署配置决定（default.yaml 设为 50）；
 *   - 桥把候选按**绝对下标**编号：全局第 k 个候选 = 第 k/rime_page_size 个
 *     Rime 菜单页里的第 k%rime_page_size 个。UI 的第 p 页从 `g_page_start`
 *     这个绝对下标开始，翻页时按「上一页实际取到的条数」往后接，
 *     因此**跨 Rime 菜单页时不会跳条也不会重条**（v0.1.x 的
 *     `ui_page * page_size` 算法在 N 除不尽菜单页大小时会跳条，已废）；
 *   - v0.2.0 起 context 额外带 `allCandidates`（当前 Rime 菜单页的**全部**候选）
 *     与 `baseIndex`（它的起始绝对下标），让 UI 能按**全量**候选量宽算分页，
 *     不再从「当页内容」反推页大小——后者会单调棘轮下落到 1 条（H-050 回归）。
 *
 * 数字/标点语义（H-024）：单字符数字与标点不进 Rime（避免 selector 把 1-9
 * 当成选词键），直接作为 commitText 交回 UI 上屏；翻页只由 flipPage 驱动。
 */

#include "napi/native_api.h"
#include <rime_api.h>
#include <hilog/log.h>
#include <string>
#include <vector>
#include <algorithm>
#include <cctype>
#include <cstring>
#include <dirent.h>
#include <chrono>
#include <sys/stat.h>
#include <unistd.h>
#include <stdlib.h>

#undef LOG_TAG
#undef LOG_DOMAIN
#define LOG_TAG "RIME_NAPI"
#define LOG_DOMAIN 0x0001

// X11 keysyms（Rime 用它们识别控制键；不是 Linux keycode）
static const int XK_BackSpace = 0xFF08;
static const int XK_Return = 0xFF0D;
static const int XK_Escape = 0xFF1B;
static const int XK_space = 0x20;
static const int XK_Page_Up = 0xFF55;
static const int XK_Page_Down = 0xFF56;
static const int kShiftMask = 1 << 0;

static const int DEFAULT_PAGE_SIZE = 5;
static const int MAX_PAGE_SIZE = 50;
static const char* SCHEMA_ID = "wubi_pinyin";

static RimeApi* g_rime = nullptr;
static RimeSessionId g_session = 0;
static bool g_ready = false;
static bool g_init_started = false;
static int g_page_size = DEFAULT_PAGE_SIZE;
static int g_ui_page = 0;
/** v0.2.0：当前 UI 页第一个候选的**全局绝对下标**（跨 Rime 菜单页连续编号）。 */
static int g_page_start = 0;
/** v0.2.0：历史页的起始绝对下标栈，供 flipPage(-1) 精确回退（不靠乘法反推）。 */
static std::vector<int> g_page_history;
/** v0.2.0：当页实际取到的条数——翻页据此接续，跨 Rime 菜单页才不会跳条。 */
static int g_page_take = 0;

/** 编码变化 / 清空 / 改页大小时，页码回到第 1 页。 */
static void ResetPaging() {
  g_ui_page = 0;
  g_page_start = 0;
  g_page_take = 0;
  g_page_history.clear();
}

struct CandidateData {
  std::string text;
  std::string comment;
};

struct ContextData {
  std::string preedit;
  std::vector<CandidateData> candidates;      // 当页切片（长度 ≤ g_page_size）
  std::vector<CandidateData> all_candidates;  // v0.2.0：当前 Rime 菜单页的全部候选
  int base_index = 0;                         // v0.2.0：all_candidates[0] 的全局绝对下标
  int take = 0;                               // v0.2.0：本次实际取到的条数（翻页据此接续）
  int page = 0;
  bool has_next = false;
  std::string commit;
};

static std::string GetStringArg(napi_env env, napi_value value) {
  size_t len = 0;
  if (napi_get_value_string_utf8(env, value, nullptr, 0, &len) != napi_ok) {
    return std::string();
  }
  std::vector<char> buf(len + 1, '\0');
  napi_get_value_string_utf8(env, value, buf.data(), buf.size(), &len);
  return std::string(buf.data(), len);
}

static napi_value MakeString(napi_env env, const std::string& text) {
  napi_value value;
  napi_create_string_utf8(env, text.c_str(), text.size(), &value);
  return value;
}

static std::string TakeCommit() {
  std::string out;
  if (g_rime == nullptr || g_session == 0) {
    return out;
  }
  RIME_STRUCT(RimeCommit, commit);
  if (g_rime->get_commit(g_session, &commit)) {
    if (commit.text != nullptr) {
      out = commit.text;
    }
    g_rime->free_commit(&commit);
  }
  return out;
}

struct MenuInfo {
  int page_no = 0;
  int page_size = MAX_PAGE_SIZE;
  int num_candidates = 0;
  bool is_last = true;
  std::string preedit;
};

static bool ReadMenu(MenuInfo& info) {
  if (g_rime == nullptr || g_session == 0) {
    return false;
  }
  RIME_STRUCT(RimeContext, ctx);
  if (!g_rime->get_context(g_session, &ctx)) {
    return false;
  }
  info.page_no = ctx.menu.page_no;
  info.page_size = ctx.menu.page_size > 0 ? ctx.menu.page_size : MAX_PAGE_SIZE;
  info.num_candidates = ctx.menu.num_candidates;
  info.is_last = ctx.menu.is_last_page != 0;
  if (ctx.composition.preedit != nullptr) {
    info.preedit = ctx.composition.preedit;
  }
  g_rime->free_context(&ctx);
  return true;
}

/** 仅用于桥内部把 Rime 菜单页移到目标页；失败时保持原页。 */
static void EnsureRimePage(int target_page) {
  MenuInfo info;
  if (!ReadMenu(info)) {
    return;
  }
  int guard = 0;
  while (info.page_no < target_page && guard++ < 100) {
    g_rime->process_key(g_session, XK_Page_Down, 0);
    MenuInfo next;
    if (!ReadMenu(next) || next.page_no == info.page_no) {
      return;
    }
    info = next;
  }
  while (info.page_no > target_page && guard++ < 100) {
    g_rime->process_key(g_session, XK_Page_Up, 0);
    MenuInfo next;
    if (!ReadMenu(next) || next.page_no == info.page_no) {
      return;
    }
    info = next;
  }
}

/**
 * 诊断：把 Rime 菜单页的真实规模打到 hilog（只在数值变化时打，避免刷屏）。
 * v0.2.0 用来核对「Rime 一页到底给几条候选」，这是候选栏弹性分页的输入。
 */
static void LogMenuState(const MenuInfo& info, const ContextData& ctx) {
  static int last_page_size = -1;
  static int last_num = -1;
  static int last_last = -1;
  int last_flag = info.is_last ? 1 : 0;
  if (info.page_size == last_page_size && info.num_candidates == last_num &&
      last_flag == last_last) {
    return;
  }
  last_page_size = info.page_size;
  last_num = info.num_candidates;
  last_last = last_flag;
  OH_LOG_INFO(LOG_APP,
              "[Rime-Napi] menu pageSize=%{public}d num=%{public}d isLast=%{public}d "
              "all=%{public}d base=%{public}d take=%{public}d start=%{public}d",
              info.page_size, info.num_candidates, last_flag,
              (int)ctx.all_candidates.size(), ctx.base_index, ctx.take, g_page_start);
}

/**
 * H-276(Qoder 2026-10-30)：符号键「按下去没有直接上屏」只能由引擎自报。
 * M-368 验收口径：`'` `"` `#` `$` `^` `` ` `` `_` `[` `]` 这 9 个键必须在
 * **没有任何候选菜单**的情况下一击直出（hilog 应该看到 commit='<符号>' menu=0）。
 * 若 menu=1 num=1 且 cand0 就是那个符号，说明 punctuator 该项仍是**列表值**
 * （librime 只要值是 list，长度 1 也会弹候选菜单），要回去查 default.yaml。
 */
static void LogPunctState(const std::string& key, bool handled,
                          const std::string& before, const std::string& after,
                          const std::string& commit, const MenuInfo& menu,
                          bool has_menu) {
  std::string cand0;
  if (has_menu && g_rime != nullptr && g_session != 0) {
    RimeCandidateListIterator it;   // 无 data_size 字段，不能用 RIME_STRUCT 初始化
    std::memset(&it, 0, sizeof(it));
    if (g_rime->candidate_list_begin(g_session, &it)) {
      if (it.candidate.text != nullptr) {
        cand0 = it.candidate.text;
      }
      g_rime->candidate_list_end(&it);
    }
  }
  OH_LOG_INFO(LOG_APP,
              "[Rime-Napi] punct key='%{public}s' handled=%{public}d input='%{public}s'->'%{public}s' "
              "commit='%{public}s' menu=%{public}d num=%{public}d preedit='%{public}s' cand0='%{public}s'",
              key.c_str(), handled ? 1 : 0, before.c_str(), after.c_str(), commit.c_str(),
              has_menu ? 1 : 0, menu.num_candidates, menu.preedit.c_str(), cand0.c_str());
}

/**
 * 取从绝对下标 abs_start 开始的一页候选（v0.2.0）。
 * - 先按 abs_start 定位它落在 Rime 的哪个菜单页（必要时 Page_Down / Page_Up）；
 * - 若那个 Rime 菜单页的候选不够（末页短页），自动往后翻 Rime 页接着取，
 *   因此**跨 Rime 菜单页时既不跳条也不重条**；
 * - 同时给出当前 Rime 菜单页的**全部**候选（all_candidates）和它的起始绝对下标
 *   （base_index），供 UI 按全量候选量宽算分页；
 * - has_next = 本页之后还有候选（当前 Rime 页没取完，或后面还有 Rime 页）。
 */
static ContextData BuildContext(int abs_start, int ui_page, const std::string& commit) {
  ContextData out;
  out.commit = commit;
  if (!g_ready || g_rime == nullptr || g_session == 0) {
    return out;
  }
  MenuInfo info;
  if (!ReadMenu(info)) {
    return out;
  }
  out.preedit = info.preedit;

  for (int guard = 0; guard < 20; ++guard) {
    int rime_page_size = info.page_size > 0 ? info.page_size : MAX_PAGE_SIZE;
    int target_rime_page = abs_start / rime_page_size;
    if (target_rime_page != info.page_no) {
      EnsureRimePage(target_rime_page);
      if (!ReadMenu(info)) {
        return out;
      }
      out.preedit = info.preedit;
      continue;
    }

    RIME_STRUCT(RimeContext, ctx);
    if (!g_rime->get_context(g_session, &ctx)) {
      return out;
    }
    int actual_page_size = ctx.menu.page_size > 0 ? ctx.menu.page_size : rime_page_size;
    int page_no = ctx.menu.page_no;
    int num_candidates = ctx.menu.num_candidates;
    bool is_last_page = ctx.menu.is_last_page != 0;
    int local = abs_start - page_no * actual_page_size;
    if (local < 0) {
      local = 0;
    }

    // v0.2.0：当前 Rime 菜单页的全部候选 + 它的起始绝对下标
    out.all_candidates.clear();
    for (int i = 0; i < num_candidates; ++i) {
      CandidateData c;
      const RimeCandidate& raw = ctx.menu.candidates[i];
      if (raw.text != nullptr) {
        c.text = raw.text;
      }
      if (raw.comment != nullptr) {
        c.comment = raw.comment;
      }
      out.all_candidates.push_back(c);
    }
    out.base_index = page_no * actual_page_size;

    if (local >= num_candidates) {
      // 这个 Rime 菜单页取完了：还有 Rime 页就翻过去接着取
      g_rime->free_context(&ctx);
      if (!is_last_page) {
        EnsureRimePage(page_no + 1);
        if (!ReadMenu(info)) {
          return out;
        }
        out.preedit = info.preedit;
        continue;
      }
      out.page = ui_page;
      out.has_next = false;
      return out;
    }

    int take = std::min(g_page_size, num_candidates - local);
    for (int i = 0; i < take; ++i) {
      CandidateData c;
      const RimeCandidate& raw = ctx.menu.candidates[i + local];
      if (raw.text != nullptr) {
        c.text = raw.text;
      }
      if (raw.comment != nullptr) {
        c.comment = raw.comment;
      }
      out.candidates.push_back(c);
    }
    out.take = take;
    out.page = ui_page;
    out.has_next = (local + take < num_candidates) || !is_last_page;
    if (ctx.composition.preedit != nullptr) {
      out.preedit = ctx.composition.preedit;
    }
    g_rime->free_context(&ctx);
    LogMenuState(info, out);
    if (abs_start == g_page_start) {
      g_page_take = take;
    }
    return out;
  }
  out.page = ui_page;
  return out;
}

static napi_value ContextToNapi(napi_env env, const ContextData& data) {
  napi_value obj;
  napi_create_object(env, &obj);
  napi_set_named_property(env, obj, "preedit", MakeString(env, data.preedit));

  napi_value arr;
  napi_create_array_with_length(env, data.candidates.size(), &arr);
  for (size_t i = 0; i < data.candidates.size(); ++i) {
    napi_value cand;
    napi_create_object(env, &cand);
    napi_set_named_property(env, cand, "text", MakeString(env, data.candidates[i].text));
    if (!data.candidates[i].comment.empty()) {
      napi_set_named_property(env, cand, "comment", MakeString(env, data.candidates[i].comment));
    }
    napi_set_element(env, arr, i, cand);
  }
  napi_set_named_property(env, obj, "candidates", arr);

  // v0.2.0：当前 Rime 菜单页的全部候选（UI 按它量宽算分页，别从当页反推页大小）
  napi_value allArr;
  napi_create_array_with_length(env, data.all_candidates.size(), &allArr);
  for (size_t i = 0; i < data.all_candidates.size(); ++i) {
    napi_value cand;
    napi_create_object(env, &cand);
    napi_set_named_property(env, cand, "text", MakeString(env, data.all_candidates[i].text));
    if (!data.all_candidates[i].comment.empty()) {
      napi_set_named_property(env, cand, "comment", MakeString(env, data.all_candidates[i].comment));
    }
    napi_set_element(env, allArr, i, cand);
  }
  napi_set_named_property(env, obj, "allCandidates", allArr);

  napi_value baseIndex;
  napi_create_int32(env, data.base_index, &baseIndex);
  napi_set_named_property(env, obj, "baseIndex", baseIndex);

  napi_value page;
  napi_create_int32(env, data.page, &page);
  napi_set_named_property(env, obj, "page", page);

  napi_value has_next;
  napi_get_boolean(env, data.has_next, &has_next);
  napi_set_named_property(env, obj, "hasNext", has_next);

  if (!data.commit.empty()) {
    napi_set_named_property(env, obj, "commitText", MakeString(env, data.commit));
  }
  return obj;
}

static napi_value EmptyContext(napi_env env) {
  ContextData empty;
  return ContextToNapi(env, empty);
}

// ---------------- init（异步） ----------------

/**
 * M3 诊断用：librime 1.16 把部署事件（deploy start/success/failure）通过
 * notification handler 往外发，glog 的 stderr 在 HAP 进程里进不了 hilog，
 * 所以这是唯一能在真机上看到部署结论的通道。
 */
static void RimeNotify(void* context_object, RimeSessionId session_id,
                       const char* message_type, const char* message_value) {
  (void)context_object;
  if (message_type == nullptr) {
    return;
  }
  OH_LOG_INFO(LOG_APP, "[Rime-Napi] notify session=%{public}d type=%{public}s value=%{public}s",
              (int)session_id, message_type, message_value ? message_value : "");
}

/** 数一个目录下的普通文件个数（部署有没有真产出，用这个量化判断）。 */
static int CountFiles(const std::string& dir) {
  DIR* d = opendir(dir.c_str());
  if (d == nullptr) {
    return -1;
  }
  int n = 0;
  struct dirent* ent = nullptr;
  while ((ent = readdir(d)) != nullptr) {
    if (ent->d_name[0] == '.') {
      continue;
    }
    ++n;
  }
  closedir(d);
  return n;
}

// 排障用：把目录里的文件名拼成一行，方便在 hilog 里直接看到部署产物
// （是只有 default.yaml，还是真的出了 wubi_pinyin.prism.bin / .table.bin / .bin）。
static std::string FilesBrief(const std::string& dir, int limit = 12) {
  std::string out;
  DIR* d = opendir(dir.c_str());
  if (d == nullptr) {
    return "<none>";
  }
  int n = 0;
  struct dirent* ent = nullptr;
  while ((ent = readdir(d)) != nullptr) {
    if (ent->d_name[0] == '.') {
      continue;
    }
    if (n > 0) {
      out += ",";
    }
    out += ent->d_name;
    if (++n >= limit) {
      out += "…";
      break;
    }
  }
  closedir(d);
  return out;
}

struct InitWork {
  napi_env env = nullptr;
  napi_async_work work = nullptr;
  napi_deferred deferred = nullptr;
  std::string shared_path;
  bool ok = false;
  std::string error;
};

static void ExecuteInit(napi_env env, void* data) {
  (void)env;
  InitWork* w = static_cast<InitWork*>(data);

  OH_LOG_INFO(LOG_APP, "[Rime-Napi] init start, shared=%{public}s", w->shared_path.c_str());
  struct stat st;
  if (stat(w->shared_path.c_str(), &st) != 0 || !S_ISDIR(st.st_mode)) {
    w->error = "rime shared dir missing: " + w->shared_path;
    return;
  }
  std::string user_path = w->shared_path + "_user";
  mkdir(user_path.c_str(), 0777);

  // M3 诊断：librime 的部署结论只写在 glog 里，而 HAP 进程的 stderr 进不了 hilog。
  // 所以把 stderr 重定向到沙箱文件，再把 glog 配成「立刻写、写 stderr」，
  // 之后用 hdc file recv 取回来读。日志文件名 napi_stderr.txt 只给排障用，
  // 真机取证（docs/evidence）读的就是它。
  setenv("GLOG_logtostderr", "1", 1);
  setenv("GLOG_minloglevel", "0", 1);
  setenv("GLOG_logbuflevel", "-1", 1);
  setenv("GLOG_stderrthreshold", "0", 1);
  setenv("GLOG_v", "1", 1);
  const std::string stderr_path = user_path + "/napi_stderr.txt";
  if (freopen(stderr_path.c_str(), "w", stderr) != nullptr) {
    setvbuf(stderr, nullptr, _IONBF, 0);
  }
  OH_LOG_INFO(LOG_APP, "[Rime-Napi] stderr -> %{public}s", stderr_path.c_str());

  g_rime = rime_get_api();
  if (g_rime == nullptr) {
    w->error = "rime_get_api failed";
    return;
  }

  RIME_STRUCT(RimeTraits, traits);
  traits.shared_data_dir = w->shared_path.c_str();
  traits.user_data_dir = user_path.c_str();
  traits.app_name = "rime.sansheng";
  traits.distribution_name = "Sansheng IME";
  traits.distribution_code_name = "sansheng_ime";
  traits.distribution_version = "0.4.0-m3";
  traits.min_log_level = 0;

  g_rime->setup(&traits);
  // 这一版 librime 的 initialize() 返回 void，失败只能靠后续 create_session 观察
  g_rime->initialize(&traits);
  const char* rime_version = g_rime->get_version();
  if (rime_version == nullptr) {
    w->error = "rime initialize failed";
    return;
  }
  OH_LOG_INFO(LOG_APP, "[Rime-Napi] librime %{public}s", rime_version);

  // 部署事件先接上，后面 prebuild/deploy 的结论才有地方看
  g_rime->set_notification_handler(RimeNotify, nullptr);

  // 先把 librime 自己算出来的 4 个目录打出来：M3 排障的关键问题是
  // 「部署到底写在哪、有没有写」，不能靠我们猜 user_path + "/build"。
  // 注意每个 getter 要各自的缓冲区，共用一个 buffer 的话只剩最后一个值。
  char buf_shared[512], buf_user[512], buf_prebuilt[512], buf_staging[512], buf_sync[512];
  const char* dirs[5] = {"-", "-", "-", "-", "-"};
  if (g_rime->get_shared_data_dir_s != nullptr) {
    buf_shared[0] = '\0';
    g_rime->get_shared_data_dir_s(buf_shared, sizeof(buf_shared));
    dirs[0] = buf_shared;
  }
  if (g_rime->get_user_data_dir_s != nullptr) {
    buf_user[0] = '\0';
    g_rime->get_user_data_dir_s(buf_user, sizeof(buf_user));
    dirs[1] = buf_user;
  }
  if (g_rime->get_prebuilt_data_dir_s != nullptr) {
    buf_prebuilt[0] = '\0';
    g_rime->get_prebuilt_data_dir_s(buf_prebuilt, sizeof(buf_prebuilt));
    dirs[2] = buf_prebuilt;
  }
  if (g_rime->get_staging_dir_s != nullptr) {
    buf_staging[0] = '\0';
    g_rime->get_staging_dir_s(buf_staging, sizeof(buf_staging));
    dirs[3] = buf_staging;
  }
  if (g_rime->get_sync_dir_s != nullptr) {
    buf_sync[0] = '\0';
    g_rime->get_sync_dir_s(buf_sync, sizeof(buf_sync));
    dirs[4] = buf_sync;
  }

  const std::string staging = user_path + "/build";
  OH_LOG_INFO(LOG_APP, "[Rime-Napi] dirs: shared=%{public}s user=%{public}s prebuilt=%{public}s "
              "staging=%{public}s sync=%{public}s",
              dirs[0] ? dirs[0] : "-", dirs[1] ? dirs[1] : "-", dirs[2] ? dirs[2] : "-",
              dirs[3] ? dirs[3] : "-", dirs[4] ? dirs[4] : "-");
  OH_LOG_INFO(LOG_APP, "[Rime-Napi] staging=%{public}s files_before=%{public}d",
              staging.c_str(), CountFiles(staging));

  // M3 实测坑：这一版 librime（1.16，带 lever/deployment_tasks）里
  // start_maintenance(True) 只做「Basic engine deployment finished!」那一层，
  // 5 ms 就返回，词库/方案一个 .bin 都不产（真机证据：m3-probe-run2 全部候选为空，
  // run3 直接给出 deploy start→failure）。
  // 真正编译词库要走 deployer API：deployer_initialize → prebuild → deploy。
  // 桌面端（小狼毫）是 Deployer 线程干这活的，鸿蒙这边由我们在 worker 线程同步做。
  g_rime->deployer_initialize(&traits);
  const auto t_pre0 = std::chrono::steady_clock::now();
  const Bool prebuilt = g_rime->prebuild();
  const auto t_dep0 = std::chrono::steady_clock::now();
  const Bool deployed = g_rime->deploy();
  const auto t_dep1 = std::chrono::steady_clock::now();
  const long pre_ms = (long)std::chrono::duration_cast<std::chrono::milliseconds>(t_dep0 - t_pre0).count();
  const long dep_ms = (long)std::chrono::duration_cast<std::chrono::milliseconds>(t_dep1 - t_dep0).count();
  OH_LOG_INFO(LOG_APP, "[Rime-Napi] prebuild=%{public}d (%{public}ld ms) files=%{public}d | "
              "deploy=%{public}d (%{public}ld ms) files=%{public}d",
              (int)prebuilt, pre_ms, CountFiles(staging),
              (int)deployed, dep_ms, CountFiles(staging));

  // 分方案单独试：pinyin_simp 是无 Lua 依赖的最小方案（M2 用它跑通过），
  // wubi_pinyin 带 custom 补丁和一堆 lua_* 组件。两者结论一对比，
  // 就知道失败是「部署机制不通」还是「某个方案本身编译不过」。
  // M3 真机根因（14:38 run4）：deploy_schema 的参数是**路径**，不是方案 id——
  // 传裸文件名时 librime 走 `DeploymentTasks::UpdateSchema(path)`，
  // exists() 相对进程 cwd 找不到，直接 "Error updating schema: nonexistent file
  // 'wubi_pinyin.schema.yaml'" 返回 0，于是 build/ 里只有 default.yaml、
  // 没有任何 prism/table .bin，引擎加载方案成功但每次 processKey 出 0 候选。
  // 所以这里必须给 shared 目录下的绝对路径。
  const std::string shared = w->shared_path;
  const Bool c0 = g_rime->deploy_config_file((shared + "/default.yaml").c_str(), "config_version");
  const int f0 = CountFiles(staging);
  const Bool s1 = g_rime->deploy_schema((shared + "/pinyin_simp.schema.yaml").c_str());
  const int f1 = CountFiles(staging);
  const Bool s2 = g_rime->deploy_schema((shared + "/wubi_pinyin.schema.yaml").c_str());
  const int f2 = CountFiles(staging);
  const Bool s3 = g_rime->deploy_schema((shared + "/sansheng_t9.schema.yaml").c_str());
  OH_LOG_INFO(LOG_APP, "[Rime-Napi] deploy default=%{public}d(files %{public}d) pinyin_simp=%{public}d(files %{public}d) "
              "wubi_pinyin=%{public}d(files %{public}d) sansheng_t9=%{public}d files=%{public}d",
              (int)c0, f0, (int)s1, f1, (int)s2, f2, (int)s3, CountFiles(staging));

  // H-044 的诊断部署循环（zzd_* 逐个 deploy_schema）结案后删除：
  // 契约已量完（rime-lua 滤镜是协程生成器，靠 yield 出候选），
  // 见 scripts/port_rime_data.py 文件头与 docs/evidence/2026-10-21/m3-run11-contract.md。
  OH_LOG_INFO(LOG_APP, "[Rime-Napi] build dir now: %{public}s", FilesBrief(staging).c_str());

  const Bool maintaining = g_rime->start_maintenance(True);
  g_rime->join_maintenance_thread();
  OH_LOG_INFO(LOG_APP, "[Rime-Napi] maintenance started=%{public}d staging_files_after=%{public}d prebuilt_files=%{public}d",
              (int)maintaining, CountFiles(staging),
              dirs[2] ? CountFiles(dirs[2]) : -1);

  g_session = g_rime->create_session();
  if (g_session == 0) {
    w->error = "create_session failed";
    return;
  }
  if (!g_rime->select_schema(g_session, SCHEMA_ID)) {
    OH_LOG_WARN(LOG_APP, "[Rime-Napi] select_schema(%{public}s) failed", SCHEMA_ID);
  } else {
    OH_LOG_INFO(LOG_APP, "[Rime-Napi] schema %{public}s selected", SCHEMA_ID);
  }

  g_page_size = DEFAULT_PAGE_SIZE;
  ResetPaging();
  g_ready = true;
  w->ok = true;
  OH_LOG_INFO(LOG_APP, "[Rime-Napi] init ok, session=%{public}d", (int)g_session);
}

static void CompleteInit(napi_env env, napi_status status, void* data) {
  InitWork* w = static_cast<InitWork*>(data);
  if (w->ok && status == napi_ok) {
    napi_value result;
    napi_get_undefined(env, &result);
    napi_resolve_deferred(env, w->deferred, result);
  } else {
    std::string msg = w->error.empty() ? "rime init failed" : w->error;
    OH_LOG_ERROR(LOG_APP, "[Rime-Napi] init failed: %{public}s", msg.c_str());
    napi_value error;
    napi_value message = MakeString(env, msg);
    napi_create_error(env, nullptr, message, &error);
    napi_reject_deferred(env, w->deferred, error);
    // 失败后允许重试：否则一次失败就把引擎永久卡在「正在初始化」
    g_init_started = false;
    g_ready = false;
  }
  napi_delete_async_work(env, w->work);
  delete w;
}

static napi_value InitEngine(napi_env env, napi_callback_info info) {
  size_t argc = 1;
  napi_value args[1] = {nullptr};
  napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);

  napi_value promise;
  napi_deferred deferred;
  napi_create_promise(env, &deferred, &promise);
  if (g_ready) {
    napi_value result;
    napi_get_undefined(env, &result);
    napi_resolve_deferred(env, deferred, result);
    return promise;
  }
  if (g_init_started) {
    napi_value error;
    napi_value message = MakeString(env, "init already in progress");
    napi_create_error(env, nullptr, message, &error);
    napi_reject_deferred(env, deferred, error);
    return promise;
  }
  if (argc < 1) {
    napi_value error;
    napi_value message = MakeString(env, "sharedPath required");
    napi_create_error(env, nullptr, message, &error);
    napi_reject_deferred(env, deferred, error);
    return promise;
  }
  InitWork* w = new InitWork();
  w->env = env;
  w->deferred = deferred;
  w->shared_path = GetStringArg(env, args[0]);
  g_init_started = true;
  napi_create_async_work(env, nullptr, MakeString(env, "rimeInit"), ExecuteInit, CompleteInit, w, &w->work);
  napi_queue_async_work(env, w->work);
  return promise;
}

// ---------------- 按键 ----------------

static napi_value ProcessKey(napi_env env, napi_callback_info info) {
  size_t argc = 1;
  napi_value args[1] = {nullptr};
  napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
  if (argc < 1 || !g_ready) {
    return EmptyContext(env);
  }
  std::string key = GetStringArg(env, args[0]);
  if (key.empty()) {
    return ContextToNapi(env, BuildContext(g_page_start, g_ui_page, ""));
  }

  std::string commit;
  MenuInfo before;
  bool have_menu = ReadMenu(before);
  bool composing = have_menu && !before.preedit.empty();

  if (key == "Backspace" || key == "BackSpace" || key == "Del") {
    if (composing) {
      g_rime->process_key(g_session, XK_BackSpace, 0);
    }
    // 编码为空时交回 UI：由键盘决定是否删除编辑器字符（INTERFACE v0.1.4）
    ResetPaging();
    return ContextToNapi(env, BuildContext(0, 0, ""));
  }

  if (key == "Space" || key == " ") {
    if (composing) {
      g_rime->process_key(g_session, XK_space, 0);
      commit = TakeCommit();
    } else {
      commit = " ";
    }
    ResetPaging();
    return ContextToNapi(env, BuildContext(0, 0, commit));
  }

  if (key == "Enter" || key == "Return") {
    if (composing) {
      // H-214②(Qoder 2026-10-27)：主人原话「回车不是上屏输入的字母，是候选，改成字母」。
      // 真机铁证：五笔打 ghos 按回车，正文里出现的是候选「下灯」——commit_composition
      // 在表转写（wubi）下提交的是**当前选中候选**，不是原始编码。
      // 改成与三生安卓 CommitComment 同语义：get_input 拿原始编码直接上屏＋清组合；
      // 万一拿不到编码（异常态）再退回旧路径兜底。
      const char* input = g_rime->get_input(g_session);
      commit = input != nullptr ? input : "";
      g_rime->clear_composition(g_session);
      if (commit.empty()) {
        g_rime->commit_composition(g_session);
        commit = TakeCommit();
      }
    } else {
      commit = "\n";
    }
    ResetPaging();
    return ContextToNapi(env, BuildContext(0, 0, commit));
  }

  if (key == "Escape") {
    g_rime->clear_composition(g_session);
    ResetPaging();
    return ContextToNapi(env, BuildContext(0, 0, ""));
  }

  // H-061：符号页（H-057）的标点/emoji 是多字节 UTF-8（「，」3 字节、emoji 4 字节），
  // keycode 表达不了，Rime 也接不住。这类键的语义就是「把显示的这个字符原样上屏」，
  // 直接提交，不进引擎；否则会落到函数末尾 commit 为空，点符号没反应。
  if (key.size() > 1) {
    ResetPaging();
    return ContextToNapi(env, BuildContext(0, 0, key));
  }

  // M-368②(H-277, Qoder 2026-10-30)：` 在三个方案里都是**反查触发符**
  // （recognizer/patterns/reverse_lookup: "^`[a-z]*'?$"），单独按下去被引擎吞成
  // 预编辑「`〔拼音〕」+ 1 条空候选 ⇒ 键面"没反应"，桥的兜底（输入串没变）也不成立。
  // 真机铁证见 hilog：punct key='`' handled=1 input=''->'`' commit='<none>' menu=1 num=1。
  // 这个字符在手机上只有符号面板〈英文〉页能按出来，用户意图就是插入一个反引号
  // （与安卓端面板字符走 commitText 同义）⇒ 与多字节面板字一样直接上屏，不进引擎。
  // 注：反查功能本身不依赖这里——手机键盘上没有别的 ` 键。
  if (key == "`") {
    LogPunctState(key, true, "", "", key, MenuInfo(), false);
    ResetPaging();
    return ContextToNapi(env, BuildContext(0, 0, key));
  }

  if (key.size() == 1) {
    unsigned char ch = static_cast<unsigned char>(key[0]);
    bool is_lower = ch >= 'a' && ch <= 'z';
    bool is_upper = ch >= 'A' && ch <= 'Z';
    bool is_digit = ch >= '0' && ch <= '9';
    if (is_lower || is_upper) {
      bool ascii_mode = g_rime->get_option(g_session, "ascii_mode");
      // H-214①(Qoder 2026-10-27)：主人原话「大写在不切英文时简繁状态下打上不去，上档键也不管用」。
      // 原实现把大写 tolower 后送 Rime（mask 只在 ascii_mode 才给 shift），中文态下
      // 上档+字母 = 打小写编码 ⇒ 上档键形同虚设。中文态收到大写字母 = 用户要的是
      // 这个字母本身：直接上屏、不进编码（预编辑原样保留，与安卓中文 IME 同语义）。
      if (is_upper && !ascii_mode) {
        ResetPaging();
        return ContextToNapi(env, BuildContext(0, 0, key));
      }
      int keycode = is_upper ? std::tolower(ch) : ch;
      int mask = (ascii_mode && is_upper) ? kShiftMask : 0;
      const char* in_before = g_rime->get_input(g_session);
      std::string input_before = in_before != nullptr ? in_before : "";
      const bool handled = g_rime->process_key(g_session, keycode, mask);
      commit = TakeCommit();
      const char* in_after = g_rime->get_input(g_session);
      std::string input_after = in_after != nullptr ? in_after : "";
      MenuInfo after_menu;
      const bool has_menu = ReadMenu(after_menu) && after_menu.num_candidates > 0;
      // H-041 ② 排障探针（run13 实测：ascii_mode=1 时 processKey('x') 上屏/预编辑/候选全空，
      // 且换成 pinyin_simp 一模一样 ⇒ 锅不在 wubi_pinyin 的 processor 组合，是引擎/桥这一层）。
      // handled 是 librime 的返回值：false=没有任何 processor 吃掉这个键，true=吃掉了但没产出。
      // 两者对产品的修法完全不同，所以先量一次再修。
      if (ascii_mode) {
        OH_LOG_INFO(LOG_APP, "[Rime-Napi] ascii probe key=%{public}s handled=%{public}d "
                    "input=\"%{public}s\"->\"%{public}s\" commit=\"%{public}s\" menu=%{public}d",
                    key.c_str(), (int)handled, input_before.c_str(), input_after.c_str(),
                    commit.c_str(), (int)has_menu);
      }
      // 英文模式直出兜底：ascii_composer 这一层在鸿蒙上没给出东西（上面已记录现场），
      // 但用户按「中/英」后要的就是字母原样上屏。和 H-024 数字直出同一个道理：
      // 桥在 Rime 没接住时补一发，且只在「不在组词中」时补，不干扰正常拼音/五笔。
      if (ascii_mode && commit.empty() && !has_menu && input_after.empty()) {
        commit = key;
      }
    } else if (is_digit) {
      // H-024 的铁律是「数字直出」：不能因为 selector 把 1–9 当选词键就吞掉数字。
      // 但 H-028 ① 的智能九键（sansheng_t9）把数字写进了 speller/alphabet，
      // 这时候数字必须进 Rime 才拼得出拼音。
      // 做法：先送进 Rime，再看它有没有「吃掉」这个键——
      // 输入串没变、没候选、也没上屏 ⇒ 当前方案不认数字 ⇒ 退回直出语义。
      // 这样 26 键方案（wubi_pinyin）里数字仍然直出，九键方案里数字参与拼写，
      // 桥里不用硬编码「哪个方案收数字」。
      const char* in_before = g_rime->get_input(g_session);
      std::string input_before = in_before != nullptr ? in_before : "";
      g_rime->process_key(g_session, ch, 0);
      commit = TakeCommit();
      const char* in_after = g_rime->get_input(g_session);
      std::string input_after = in_after != nullptr ? in_after : "";
      MenuInfo after_menu;
      bool has_menu = ReadMenu(after_menu) && after_menu.num_candidates > 0;
      if (input_after == input_before && commit.empty() && !has_menu) {
        commit = key;
      }
      ResetPaging();
      return ContextToNapi(env, BuildContext(0, 0, commit));
    } else {
      // CR-20261022-01（Qoder 批复合入，2026-10-22）：单字节标点先送 Rime，没吃掉再直出。
      // 原注释「数字/标点不交给 Rime」只对数字成立（H-024 selector 抢 1-9），标点是另一回事：
      // H-079/M-059 把 symbols.yaml + punctuator/import_preset: symbols 的数据修对了，
      // 但这条分支把 `/` `[` `'` 拦在桥里直接上屏，引擎永远收不到键 ⇒ /xx 符号直出全灭（H-081）。
      // 判定与数字分支（H-024 直出 / H-028 九键拼写）完全同语义：
      // 输入串没变、没候选、没上屏 ⇒ 当前方案不认这个键 ⇒ 退回直出，英文模式行为不变。
      const char* in_before = g_rime->get_input(g_session);
      std::string input_before = in_before != nullptr ? in_before : "";
      bool handled = g_rime->process_key(g_session, ch, 0) != 0;
      std::string rime_commit = TakeCommit();
      commit = rime_commit;
      const char* in_after = g_rime->get_input(g_session);
      std::string input_after = in_after != nullptr ? in_after : "";
      MenuInfo after_menu;
      bool has_menu = ReadMenu(after_menu) && after_menu.num_candidates > 0;
      bool bridge_fallback = input_after == input_before && commit.empty() && !has_menu;
      if (bridge_fallback) {
        commit = key;
      }
      // H-276(Qoder 2026-10-30)：M-368「符号点了不能直接上屏」只能靠引擎自报（沙箱 hdc 读不到）。
      // 只在**被引擎吞掉**时打日志（正常直出不刷屏）：有候选菜单，或既没上屏也没兜底。
      if (has_menu || (rime_commit.empty() && !bridge_fallback)) {
        LogPunctState(key, handled, input_before, input_after,
                      rime_commit.empty() ? std::string("<none>") : rime_commit,
                      after_menu, has_menu);
      }
      ResetPaging();
      return ContextToNapi(env, BuildContext(0, 0, commit));
    }
  }

  ResetPaging();
  return ContextToNapi(env, BuildContext(0, 0, commit));
}

/** 按全局绝对下标选中候选，返回上屏文本（空串 = 没选中）。 */
static std::string SelectCandidateByAbs(int abs_index) {
  std::string out;
  if (!g_ready || g_rime == nullptr || g_session == 0 || abs_index < 0) {
    return out;
  }
  MenuInfo menu;
  if (!ReadMenu(menu)) {
    return out;
  }
  int rime_page_size = menu.page_size > 0 ? menu.page_size : MAX_PAGE_SIZE;
  EnsureRimePage(abs_index / rime_page_size);
  if (!ReadMenu(menu)) {
    return out;
  }
  int local = abs_index - menu.page_no * rime_page_size;
  if (local >= 0 && local < menu.num_candidates) {
    bool ok = g_rime->select_candidate_on_current_page(g_session, static_cast<size_t>(local));
    if (!ok) {
      ok = g_rime->select_candidate(g_session, static_cast<size_t>(abs_index));
    }
    if (ok) {
      out = TakeCommit();
    }
    if (out.empty()) {
      g_rime->commit_composition(g_session);
      out = TakeCommit();
    }
  }
  return out;
}

/** 选词：index 是**当页内**下标（页内 0 起）。 */
static napi_value SelectCandidate(napi_env env, napi_callback_info info) {
  size_t argc = 1;
  napi_value args[1] = {nullptr};
  napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
  if (argc < 1 || !g_ready) {
    return MakeString(env, std::string());
  }
  int32_t index = 0;
  napi_get_value_int32(env, args[0], &index);
  if (index < 0) {
    return MakeString(env, std::string());
  }
  std::string out = SelectCandidateByAbs(g_page_start + index);
  ResetPaging();
  return MakeString(env, out);
}

/**
 * v0.2.0：按**全局绝对下标**选词。
 * UI 若自己按实测宽度分页（页与页条数不必相等），就用这个接口选词，
 * 免得页内下标与引擎切片对不上。
 */
static napi_value SelectCandidateAbs(napi_env env, napi_callback_info info) {
  size_t argc = 1;
  napi_value args[1] = {nullptr};
  napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
  if (argc < 1 || !g_ready) {
    return MakeString(env, std::string());
  }
  int32_t index = 0;
  napi_get_value_int32(env, args[0], &index);
  if (index < 0) {
    return MakeString(env, std::string());
  }
  std::string out = SelectCandidateByAbs(index);
  ResetPaging();
  return MakeString(env, out);
}

static napi_value DeleteBackward(napi_env env, napi_callback_info info) {
  (void)info;
  if (!g_ready) {
    return EmptyContext(env);
  }
  MenuInfo menu;
  if (ReadMenu(menu) && !menu.preedit.empty()) {
    g_rime->process_key(g_session, XK_BackSpace, 0);
  }
  ResetPaging();
  return ContextToNapi(env, BuildContext(0, 0, ""));
}

static napi_value FlipPage(napi_env env, napi_callback_info info) {
  size_t argc = 1;
  napi_value args[1] = {nullptr};
  napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
  int32_t direction = 0;
  if (argc >= 1) {
    napi_get_value_int32(env, args[0], &direction);
  }
  if (!g_ready) {
    return EmptyContext(env);
  }
  if (direction > 0) {
    // 下一页的起点 = 当页起点 + 当页**实际取到的条数**：
    // 用实际条数（而不是页大小）接续，跨 Rime 菜单页时才不会跳条/重条。
    int next_start = g_page_start + g_page_take;
    ContextData next = BuildContext(next_start, g_ui_page + 1, "");
    if (!next.candidates.empty()) {
      g_page_history.push_back(g_page_start);
      g_page_start = next_start;
      g_ui_page += 1;
      g_page_take = next.take;
      return ContextToNapi(env, next);
    }
    return ContextToNapi(env, BuildContext(g_page_start, g_ui_page, ""));
  }
  if (direction < 0) {
    if (!g_page_history.empty()) {
      int prev_start = g_page_history.back();
      g_page_history.pop_back();
      if (g_ui_page > 0) {
        g_ui_page -= 1;
      }
      g_page_start = prev_start;
      ContextData prev = BuildContext(g_page_start, g_ui_page, "");
      g_page_take = prev.take;
      return ContextToNapi(env, prev);
    }
    return ContextToNapi(env, BuildContext(g_page_start, g_ui_page, ""));
  }
  return ContextToNapi(env, BuildContext(g_page_start, g_ui_page, ""));
}

static napi_value Clear(napi_env env, napi_callback_info info) {
  (void)info;
  if (g_ready && g_rime != nullptr) {
    g_rime->clear_composition(g_session);
  }
  ResetPaging();
  return ContextToNapi(env, BuildContext(0, 0, ""));
}

static napi_value GetContext(napi_env env, napi_callback_info info) {
  (void)info;
  return ContextToNapi(env, BuildContext(g_page_start, g_ui_page, ""));
}

/**
 * v0.5.0（M4）：引擎收尾 —— 销毁 session + 销毁引擎。
 *
 * 为什么必须有这个口子：librime 的用户词典分两种落盘方式
 *   · tabledb（纯文本 TextDb）：**全部数据只在内存里**，只有 db 对象析构
 *     （Close() → SaveToFile）时才写回 <user>/user.txt。桌面端 Rime 退出时
 *     会 RimeFinalize()，所以那边看着一切正常；鸿蒙这边 IME 进程是常驻的，
 *     桥上从来没有 finalize ⇒ user.txt 永远只有 5 行表头，
 *     自造词与自调频跨会话全部丢失（2026-10-21 run16 实测）。
 *   · userdb（LevelDb）：每次提交立刻写 WAL，不依赖收尾。
 *
 * 现在 schema 已改用 userdb（见 D-010），但本接口仍然保留：它是「引擎干净
 * 收尾」的正规出口（释放 Lua 脚本、OpenCC、LevelDb 句柄），也让 IME 销毁时
 * 有地方调。
 *
 * 注意：调用后 g_ready = false，引擎需要重新 initEngine 才能再用。
 */
static napi_value FinalizeEngine(napi_env env, napi_callback_info info) {
  (void)info;
  if (g_rime != nullptr) {
    if (g_session != 0) {
      g_rime->destroy_session(g_session);
      g_session = 0;
    }
    g_rime->finalize();
    g_rime = nullptr;
  }
  g_ready = false;
  ResetPaging();
  OH_LOG_INFO(LOG_APP, "[Rime-Napi] finalize ok (session destroyed, engine finalized)");
  napi_value result;
  napi_get_boolean(env, true, &result);
  return result;
}

static napi_value GetOption(napi_env env, napi_callback_info info) {
  size_t argc = 1;
  napi_value args[1] = {nullptr};
  napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
  bool value = false;
  if (argc >= 1 && g_ready) {
    std::string name = GetStringArg(env, args[0]);
    value = g_rime->get_option(g_session, name.c_str()) == True;
  }
  napi_value result;
  napi_get_boolean(env, value, &result);
  return result;
}

static napi_value SetOption(napi_env env, napi_callback_info info) {
  size_t argc = 2;
  napi_value args[2] = {nullptr, nullptr};
  napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
  if (argc >= 2 && g_ready) {
    std::string name = GetStringArg(env, args[0]);
    bool value = false;
    napi_get_value_bool(env, args[1], &value);
    g_rime->set_option(g_session, name.c_str(), value ? True : False);
    OH_LOG_INFO(LOG_APP, "[Rime-Napi] option %{public}s=%{public}d", name.c_str(), value ? 1 : 0);
  }
  napi_value result;
  napi_get_undefined(env, &result);
  return result;
}

static napi_value SetPageSize(napi_env env, napi_callback_info info) {
  size_t argc = 1;
  napi_value args[1] = {nullptr};
  napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
  int32_t size = DEFAULT_PAGE_SIZE;
  if (argc >= 1) {
    napi_get_value_int32(env, args[0], &size);
  }
  if (size < 1) {
    size = 1;
  }
  if (size > MAX_PAGE_SIZE) {
    size = MAX_PAGE_SIZE;
  }
  g_page_size = size;
  ResetPaging();
  OH_LOG_INFO(LOG_APP, "[Rime-Napi] pageSize=%{public}d", g_page_size);
  return ContextToNapi(env, BuildContext(0, 0, ""));
}

static napi_value CheckStatus(napi_env env, napi_callback_info info) {
  (void)info;
  napi_value result;
  napi_create_int32(env, g_ready ? 0 : 1, &result);
  return result;
}

static napi_value SwitchSchema(napi_env env, napi_callback_info info) {
  size_t argc = 1;
  napi_value args[1] = {nullptr};
  napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
  napi_value result;
  napi_get_boolean(env, false, &result);
  if (argc < 1 || !g_ready) {
    return result;
  }
  std::string schema = GetStringArg(env, args[0]);
  bool ok = g_rime->select_schema(g_session, schema.c_str());
  ResetPaging();
  napi_get_boolean(env, ok, &result);
  return result;
}

/** H-178（主人 2026-10-25 16:5x「对照安卓抄」）：读当前方案 id。
 *  用途：安卓底栏那颗 `Rime(五)` 显示**当前方案名**并可切方案；我们此前只有
 *  select_schema（写）没有读 ⇒ 空格位只能固定显示「三生」。
 *  rime_api.h:347 的 get_current_schema 一直都在，只是没接。 */
static napi_value GetSchemaId(napi_env env, napi_callback_info info) {
  (void)info;
  if (!g_ready) {
    return MakeString(env, "");
  }
  // 方案 id 很短（wubi_pinyin / sansheng_t9 / luna_pinyin 之类），256 足够
  char buf[256] = {0};
  if (g_rime->get_current_schema(g_session, buf, sizeof(buf))) {
    return MakeString(env, buf);
  }
  return MakeString(env, "");
}

static napi_value Init(napi_env env, napi_value exports) {
  napi_property_descriptor desc[] = {
    {"initEngine", nullptr, InitEngine, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"checkStatus", nullptr, CheckStatus, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"switchSchema", nullptr, SwitchSchema, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"getSchemaId", nullptr, GetSchemaId, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"processKey", nullptr, ProcessKey, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"selectCandidate", nullptr, SelectCandidate, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"selectCandidateAbs", nullptr, SelectCandidateAbs, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"deleteBackward", nullptr, DeleteBackward, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"flipPage", nullptr, FlipPage, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"clear", nullptr, Clear, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"getContext", nullptr, GetContext, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"finalizeEngine", nullptr, FinalizeEngine, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"setOption", nullptr, SetOption, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"getOption", nullptr, GetOption, nullptr, nullptr, nullptr, napi_default, nullptr},
    {"setPageSize", nullptr, SetPageSize, nullptr, nullptr, nullptr, napi_default, nullptr}
  };
  napi_define_properties(env, exports, sizeof(desc) / sizeof(desc[0]), desc);
  return exports;
}

napi_module fanxing_module = {
  .nm_version = 1,
  .nm_flags = 0,
  .nm_register_func = Init,
  .nm_modname = "fanxing_rime"
};
extern "C" __attribute__((constructor)) void RegisterModule(void) {
  napi_module_register(&fanxing_module);
}
