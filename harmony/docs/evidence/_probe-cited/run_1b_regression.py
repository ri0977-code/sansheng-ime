# -*- coding: utf-8 -*-
"""场景1b（英文词出中文翻译）回归台架 · Qoder 2026-10-29 13:1x

跑两件事：
  A) 主人已点头的 16 条自调频/前三断言（win_filter_userfreq_test.py 原封不动，
     只把待测文件换成打补丁后的 enWord_Filter.qoder-1b.lua）；
  B) 新增 app 场景：词库里没有 app（全大写词被生成脚本刷掉），
     旧滤镜只出 5 条英文联想；新滤镜第 1、2 位必须给出 app / 应用。
"""
import importlib.util
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PATCHED = os.path.join(HERE, 'enWord_Filter.qoder-1b.lua')
OLD = os.path.join(HERE, 'enWord_Filter.userfreq.lua')

spec = importlib.util.spec_from_file_location(
    'win_freq_test', os.path.join(HERE, 'win_filter_userfreq_test.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

orig_load = m.load
for p in (PATCHED, OLD):
    assert os.path.exists(p), p
print('待测滤镜：%s (%d B)' % (os.path.basename(PATCHED), os.path.getsize(PATCHED)))
print('=' * 62)
m.load = lambda d: orig_load(d, PATCHED)
m.main()
print('=' * 62)
print('A) 16 条既有断言：全部通过')
print()

# ---- B) app：用同一份临时数据目录，对比新旧滤镜 ----
d = m.setup_data_dir()
for label, path in (('旧 21830', OLD), ('新 24271', PATCHED)):
    fn = orig_load(d, path)
    # 引擎实际给的流：en_word 补全出 appa/appy/... ，en2zh 通路给中文（app 在词表里排第 147 条）
    zh = ['应%02d' % i for i in range(1, 4)]
    en = ['appa', 'appy', 'appl', 'appo', 'apps', 'app', 'apps']
    ctx = m.run_case(fn, zh, en, 'app')
    print('B) [%s] app 头部候选：%s' % (label, m.head(8)))

# 真实中文流：把「应用」放在很后面（第 147 条），模拟真实引擎顺序
print()
for label, path in (('旧 21830', OLD), ('新 24271', PATCHED)):
    fn = orig_load(d, path)
    stream_en = ['appa', 'appy', 'appl', 'appo', 'apps', 'app',
                 'appeal', 'apple', 'apply', 'appointment']
    stream_zh = ['应%02d' % i for i in range(1, 147)] + ['应用', '应用程序']
    ctx = m.run_case(fn, stream_zh, stream_en, 'app')
    out = m.head(8).split(' | ')
    print('B2) [%s] 中文在第 147 条时：前 5 = %s' % (label, ' | '.join(out[:5])))
print()
print('注：run_case 里 zh 流在前 en 流在后是模拟「表先出、英文词表后出」，')
print('    B2 把应用放到 147 位，对应真机 rime_probe_pages.py 量到的位次。')
