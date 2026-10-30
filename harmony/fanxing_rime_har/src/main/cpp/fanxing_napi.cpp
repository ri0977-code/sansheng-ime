/*
 * =====================================================================================
 * 📢 【开源使用声明 / Open Source Disclaimer】
 * 以下所有的 C++ (NAPI) 桥接代码仅作为 Rime 引擎在鸿蒙系统上运行的基础示例（Demo）。
 * 开发者在实际接入 Rime 引擎时，完全无需局限于本文件的逻辑，可根据业务自由修改。
 * * ⚠️ 【极其重要的商用避坑指南：关于混淆编译】 ⚠️
 * 当您准备打 Release 正式签名包时，鸿蒙底层默认会开启极为严格的代码混淆！
 * 这里的 NAPI 暴露接口（如 initEngine, getCandidates 等）如果在 ArkTS 端被混淆，
 * 您的应用在 Release 模式下调用 C++ 层时将直接闪退或无响应！
 * * 💡 解决方案：
 * 务必在您的鸿蒙工程的混淆配置文件（如 obfuscation-rules.txt 或 consumer-rules.txt）中，
 * 加入 `-keep` 规则，强制保留这些与 C++ 交互的接口名称和相关数据结构不被混淆。
 * =====================================================================================
 */

#include "napi/native_api.h"
#include <rime_api.h>
#include <hilog/log.h>
#include <string>
#include <sys/stat.h>
#include <vector>
#include <algorithm>
#include <stdlib.h> 

#undef LOG_TAG
#undef LOG_DOMAIN
#define LOG_TAG "RIME_NAPI"
#define LOG_DOMAIN 0x0001

RimeSessionId g_session_id = 0;

// 1. 基础引擎初始化
static napi_value InitEngine(napi_env env, napi_callback_info info) {
    // 强制输出 Rime 底层 Glog 日志到控制台，方便开发者调试
    setenv("GLOG_logtostderr", "1", 1);
    setenv("GLOG_minloglevel", "0", 1);

    OH_LOG_INFO(LOG_APP, "[Rime-Napi] 🚀 ================== Engine Initialization ==================");
    try {
        size_t argc = 1; 
        napi_value args[1] = {nullptr};
        napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);

        char shared_path[512] = {0};
        size_t path_len;
        napi_get_value_string_utf8(env, args[0], shared_path, 512, &path_len);

        std::string user_path = std::string(shared_path) + "_user";
        mkdir(user_path.c_str(), 0777); 

        RimeApi* rime = rime_get_api();
        if (!rime) {
            OH_LOG_ERROR(LOG_APP, "[Rime-Napi] ❌ Failed to get Rime API!");
            return nullptr;
        }

        RIME_STRUCT(RimeTraits, traits);
        traits.shared_data_dir = shared_path;
        traits.user_data_dir = user_path.c_str();
        traits.app_name = "rime.harmonyos"; 
        traits.distribution_name = "Rime";
        traits.distribution_code_name = "HarmonyOS_Port";
        traits.distribution_version = "1.0.0";
        traits.min_log_level = 0; 

        rime->setup(&traits);
        OH_LOG_INFO(LOG_APP, "[Rime-Napi] 🧠 Engine setup complete, starting initialization...");
        
        rime->initialize(&traits);
        rime->start_maintenance(true);

        g_session_id = 0; 
        OH_LOG_INFO(LOG_APP, "[Rime-Napi] ✅ Basic engine deployment finished!");
    } catch (...) {
        OH_LOG_ERROR(LOG_APP, "[Rime-Napi] ❌ Critical exception during initialization!");
    }
    return nullptr;
}

// 2. 状态查询
static napi_value CheckStatus(napi_env env, napi_callback_info info) {
    (void)info; // 消除 unused 警告
    napi_value result;
    try {
        RimeApi* rime = rime_get_api();
        bool is_maintenance = rime ? rime->is_maintenance_mode() : false;
        napi_create_int32(env, is_maintenance ? 1 : 0, &result);
    } catch (...) {
        napi_create_int32(env, -1, &result);
    }
    return result;
}

// 3. 切换输入方案 (Schema)
static napi_value SwitchSchema(napi_env env, napi_callback_info info) {
    napi_value result;
    try {
        size_t argc = 1;
        napi_value args[1] = {nullptr};
        napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);
        
        char schema_id[128] = {0};
        size_t len;
        napi_get_value_string_utf8(env, args[0], schema_id, 128, &len);

        OH_LOG_INFO(LOG_APP, "[Rime-Napi] 🔄 Switching schema to: [%{public}s]", schema_id);

        RimeApi* rime = rime_get_api();
        if (rime) {
            if (g_session_id == 0) g_session_id = rime->create_session();
            bool res = rime->select_schema(g_session_id, schema_id);
            OH_LOG_INFO(LOG_APP, "[Rime-Napi] 🔄 Schema switch result: %{public}d", res);
            napi_create_int32(env, res ? 1 : 0, &result);
            return result;
        }
    } catch (...) {}
    napi_create_int32(env, 0, &result);
    return result;
}

// 4. 获取候选词列表
static napi_value GetCandidates(napi_env env, napi_callback_info info) {
    napi_value result_obj;
    napi_create_object(env, &result_obj);

    napi_value cand_array, pinyin_choices_array, preedit_str;
    napi_create_array(env, &cand_array);
    napi_create_array(env, &pinyin_choices_array);
    napi_create_string_utf8(env, "", NAPI_AUTO_LENGTH, &preedit_str);

    napi_set_named_property(env, result_obj, "candidates", cand_array);
    napi_set_named_property(env, result_obj, "preedit", preedit_str);
    napi_set_named_property(env, result_obj, "pinyinChoices", pinyin_choices_array);

    try {
        size_t argc = 1;
        napi_value args[1] = {nullptr};
        napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);

        char input[512] = {0};
        size_t input_len = 0;
        napi_get_value_string_utf8(env, args[0], input, sizeof(input), &input_len);
        
        RimeApi* rime = rime_get_api();
        if (!rime || g_session_id == 0) return result_obj; 
        
        rime->clear_composition(g_session_id);
        for (size_t i = 0; i < input_len; i++) {
            rime->process_key(g_session_id, input[i], 0);
        }

        int limit = 50; 
        int total_fetched = 0;
        bool preedit_extracted = false;
        
        std::vector<std::string> unique_pinyins;
        uint32_t pinyin_idx = 0;

        while (total_fetched < limit) {
            RIME_STRUCT(RimeContext, context);
            if (!rime->get_context(g_session_id, &context)) break;
            
            if (!preedit_extracted) {
                if (context.composition.preedit != nullptr) {
                    napi_create_string_utf8(env, context.composition.preedit, NAPI_AUTO_LENGTH, &preedit_str);
                    napi_set_named_property(env, result_obj, "preedit", preedit_str);
                }
                preedit_extracted = true; 
            }
            
            if (context.menu.num_candidates == 0) {
                rime->free_context(&context);
                break;
            }
            
            for (int i = 0; i < context.menu.num_candidates && total_fetched < limit; i++) {
                const char* cand_text = context.menu.candidates[i].text ? context.menu.candidates[i].text : "";
                
                napi_value val;
                napi_create_string_utf8(env, cand_text, NAPI_AUTO_LENGTH, &val);
                napi_set_element(env, cand_array, total_fetched, val);

                if (context.menu.candidates[i].comment != nullptr) {
                    std::string current_pinyin = context.menu.candidates[i].comment;
                    if (std::find(unique_pinyins.begin(), unique_pinyins.end(), current_pinyin) == unique_pinyins.end()) {
                        unique_pinyins.push_back(current_pinyin);
                        napi_value py_val;
                        napi_create_string_utf8(env, current_pinyin.c_str(), NAPI_AUTO_LENGTH, &py_val);
                        napi_set_element(env, pinyin_choices_array, pinyin_idx, py_val);
                        pinyin_idx++; // 消除 side-effect 警告
                    }
                }
                total_fetched++; // 消除 side-effect 警告
            }
            
            bool is_last = (context.menu.is_last_page != 0);
            rime->free_context(&context);
            if (is_last) break;
            rime->process_key(g_session_id, '=', 0); 
        }
    } catch (...) {
        OH_LOG_ERROR(LOG_APP, "[Rime-Napi] ❌ Uncaught exception in GetCandidates!");
    }
    
    return result_obj;
}

// 5. 选中候选词并上屏
static napi_value SelectCandidate(napi_env env, napi_callback_info info) {
    napi_value result;
    napi_create_int32(env, 0, &result);
    
    try {
        size_t argc = 1;
        napi_value args[1] = {nullptr};
        napi_get_cb_info(env, info, &argc, args, nullptr, nullptr);

        int target_index = 0;
        napi_get_value_int32(env, args[0], &target_index);

        RimeApi* rime = rime_get_api();
        if (rime && g_session_id != 0) {
            int current_absolute_start = 0;
            bool select_res = false;
            
            while (true) {
                RIME_STRUCT(RimeContext, context);
                if (!rime->get_context(g_session_id, &context)) break;
                
                int num_cands = context.menu.num_candidates;
                if (num_cands == 0) {
                    rime->free_context(&context);
                    break;
                }
                
                if (target_index < current_absolute_start + num_cands) {
                    int local_index = target_index - current_absolute_start;
                    select_res = rime->select_candidate_on_current_page(g_session_id, local_index);
                    rime->free_context(&context);
                    break;
                }
                
                current_absolute_start += num_cands;
                bool is_last = (context.menu.is_last_page != 0);
                rime->free_context(&context);
                
                if (is_last) break;
                rime->process_key(g_session_id, '=', 0); 
            }
            
            if (select_res) {
                rime->commit_composition(g_session_id);
            }
            
            napi_create_int32(env, select_res ? 1 : 0, &result);
        }
    } catch (...) {
        OH_LOG_ERROR(LOG_APP, "[Rime-Napi] ❌ Exception in SelectCandidate!");
    }
    return result;
}

// 模块注册抛出接口
static napi_value Init(napi_env env, napi_value exports) {
    napi_property_descriptor desc[] = {
        {"initEngine", nullptr, InitEngine, nullptr, nullptr, nullptr, napi_default, nullptr},
        {"checkStatus", nullptr, CheckStatus, nullptr, nullptr, nullptr, napi_default, nullptr},
        {"switchSchema", nullptr, SwitchSchema, nullptr, nullptr, nullptr, napi_default, nullptr},
        {"getCandidates", nullptr, GetCandidates, nullptr, nullptr, nullptr, napi_default, nullptr},
        {"selectCandidate", nullptr, SelectCandidate, nullptr, nullptr, nullptr, napi_default, nullptr}
    };
    napi_define_properties(env, exports, sizeof(desc) / sizeof(desc[0]), desc);
    return exports;
}

// 注意这里 .nm_modname 已严丝合缝对齐 CMakeLists.txt 的 "fanxing_rime"
static napi_module fanxing_module = { .nm_version = 1, .nm_flags = 0, .nm_register_func = Init, .nm_modname = "fanxing_rime" };
extern "C" __attribute__((constructor)) void RegisterModule(void) { napi_module_register(&fanxing_module); }