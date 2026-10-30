# -*- coding: utf-8 -*-
"""真实 librime 引擎台架（Qoder 2026-10-29 09:2x）

目的：不再靠 lupa 模拟候选流，而是直接 ctypes 调 Weasel 自带 rime.dll，
      在「用户目录副本」上跑真实引擎，喂 qtal / mao，读引擎最终给出的候选表。
      这样能判定反查补位（猫→cat）到底有没有进引擎，还是被下游丢掉/根本没触发。

安全：只在 C:/Temp/rime_probe_copy 这份副本上跑，不碰 G:/RimeUser，不与
      WeaselServer 争锁；共享数据目录只读。
布局以仓内 entry/src/main/cpp/include/rime_api.h 为准（RIME_STRUCT_INIT:
data_size = sizeof - 4）。
"""
import ctypes
import os
import sys

DLL = r'D:\Program Files\Rime\weasel-0.17.4\rime.dll'
SHARED = r'D:\Program Files\Rime\weasel-0.17.4\data'
USERDIR = r'C:\Temp\rime_probe_copy'
LOGDIR = r'C:\Temp\rime_probe_log'


class RimeTraits(ctypes.Structure):
    _fields_ = [
        ('data_size', ctypes.c_int),
        ('shared_data_dir', ctypes.c_char_p),
        ('user_data_dir', ctypes.c_char_p),
        ('distribution_name', ctypes.c_char_p),
        ('distribution_code_name', ctypes.c_char_p),
        ('distribution_version', ctypes.c_char_p),
        ('app_name', ctypes.c_char_p),
        ('modules', ctypes.POINTER(ctypes.c_char_p)),
        ('min_log_level', ctypes.c_int),
        ('log_dir', ctypes.c_char_p),
        ('prebuilt_data_dir', ctypes.c_char_p),
        ('staging_dir', ctypes.c_char_p),
    ]


class RimeCandidate(ctypes.Structure):
    _fields_ = [
        ('text', ctypes.c_char_p),
        ('comment', ctypes.c_char_p),
        ('reserved', ctypes.c_void_p),
    ]


class RimeComposition(ctypes.Structure):
    _fields_ = [
        ('length', ctypes.c_int),
        ('cursor_pos', ctypes.c_int),
        ('sel_start', ctypes.c_int),
        ('sel_end', ctypes.c_int),
        ('preedit', ctypes.c_char_p),
    ]


class RimeMenu(ctypes.Structure):
    _fields_ = [
        ('page_size', ctypes.c_int),
        ('page_no', ctypes.c_int),
        ('is_last_page', ctypes.c_int),          # Bool == int
        ('highlighted_candidate_index', ctypes.c_int),
        ('num_candidates', ctypes.c_int),
        ('candidates', ctypes.POINTER(RimeCandidate)),
        ('select_keys', ctypes.c_char_p),
    ]


class RimeContext(ctypes.Structure):
    _fields_ = [
        ('data_size', ctypes.c_int),
        ('composition', RimeComposition),
        ('menu', RimeMenu),
        ('commit_text_preview', ctypes.c_char_p),
        ('select_labels', ctypes.POINTER(ctypes.c_char_p)),
    ]


lib = ctypes.CDLL(DLL)


def _decl(name, argtypes, restype):
    fn = getattr(lib, name)
    fn.argtypes = argtypes
    fn.restype = restype
    return fn


RimeSetup = _decl('RimeSetup', [ctypes.POINTER(RimeTraits)], None)
RimeInitialize = _decl('RimeInitialize', [ctypes.POINTER(RimeTraits)], None)
RimeCreateSession = _decl('RimeCreateSession', [], ctypes.c_uint64)
RimeSimulateKeySequence = _decl('RimeSimulateKeySequence',
                                [ctypes.c_uint64, ctypes.c_char_p], ctypes.c_int)
RimeGetContext = _decl('RimeGetContext',
                       [ctypes.c_uint64, ctypes.POINTER(RimeContext)], ctypes.c_int)
RimeFreeContext = _decl('RimeFreeContext', [ctypes.POINTER(RimeContext)], None)
RimeGetCurrentSchema = _decl('RimeGetCurrentSchema',
                             [ctypes.c_uint64, ctypes.c_char_p, ctypes.c_size_t], ctypes.c_int)
RimeDestroySession = _decl('RimeDestroySession', [ctypes.c_uint64], ctypes.c_int)
RimeSelectCandidate = _decl('RimeSelectCandidate', [ctypes.c_uint64, ctypes.c_size_t], ctypes.c_int)


class RimeCommit(ctypes.Structure):
    _fields_ = [
        ('data_size', ctypes.c_int),
        ('text', ctypes.c_char_p),
    ]


RimeGetCommit = _decl('RimeGetCommit', [ctypes.c_uint64, ctypes.POINTER(RimeCommit)], ctypes.c_int)
RimeFreeCommit = _decl('RimeFreeCommit', [ctypes.POINTER(RimeCommit)], None)
RimeFinalize = _decl('RimeFinalize', [], None)


def dsize(t):
    """RIME_STRUCT_INIT: data_size = sizeof - 4"""
    return ctypes.sizeof(t) - ctypes.sizeof(ctypes.c_int)


def main(inputs):
    os.makedirs(LOGDIR, exist_ok=True)
    tr = RimeTraits()
    ctypes.memset(ctypes.byref(tr), 0, ctypes.sizeof(tr))
    tr.data_size = dsize(RimeTraits)
    tr.shared_data_dir = SHARED.encode()
    tr.user_data_dir = USERDIR.encode()
    tr.log_dir = LOGDIR.encode()
    tr.app_name = b'rime.sansheng_probe'
    tr.distribution_name = b'Sansheng Probe'
    tr.distribution_code_name = b'sansheng-probe'
    tr.distribution_version = b'0.0.1'
    tr.min_log_level = 1

    RimeSetup(ctypes.byref(tr))
    RimeInitialize(ctypes.byref(tr))
    print('rime 已初始化（用户目录副本）')

    sid = RimeCreateSession()
    print('session:', sid)
    if not sid:
        print('创建会话失败（可能部署未完成）')
        RimeFinalize()
        return 3
    # 多会话台架：小狼毫每个输入窗口一个 session，调频记录的 commit_notifier 是挂在
    # 各自 Context 上的。加第二个会话专门验证「换个窗口打字也记得住」（2026-10-29 根因）。
    sid2 = RimeCreateSession()
    sessions = [sid, sid2]
    print('session2:', sid2)

    buf = ctypes.create_string_buffer(128)
    ok = RimeGetCurrentSchema(sid, buf, 128)
    print('当前方案:', buf.value.decode(errors='replace') if ok else '(未知)')

    for spec in inputs:
        if '@' in spec:                        # "s1@qtal#2" -> 用第 2 个会话；不带 @ 默认第 1 个
            which, _, spec = spec.partition('@')
            sidx = 1 if which == 's1' else 0
        else:
            sidx = 0
        sid_x = sessions[sidx]
        keys, _, pick = spec.partition('#')
        ctx = RimeContext()
        ctypes.memset(ctypes.byref(ctx), 0, ctypes.sizeof(ctx))
        ctx.data_size = dsize(RimeContext)
        ok = RimeSimulateKeySequence(sid_x, keys.encode())
        got = RimeGetContext(sid_x, ctypes.byref(ctx))
        print('\n[会话%d] 输入 %-6s 模拟=%s 取上下文=%s' % (sidx + 1, keys, ok, got))
        if got:
            print('  preedit=%r 候选数=%d page=%d' % (
                ctx.composition.preedit, ctx.menu.num_candidates, ctx.menu.page_no))
            for i in range(min(ctx.menu.num_candidates, 12)):
                c = ctx.menu.candidates[i]
                print('  %2d. %-24s | %s' % (
                    i + 1,
                    (c.text or b'').decode(errors='replace'),
                    (c.comment or b'').decode(errors='replace')))
        RimeFreeContext(ctypes.byref(ctx))
        if pick:
            idx = int(pick) - 1
            okp = RimeSelectCandidate(sid_x, idx)
            cm = RimeCommit()
            ctypes.memset(ctypes.byref(cm), 0, ctypes.sizeof(cm))
            cm.data_size = dsize(RimeCommit)
            gotc = RimeGetCommit(sid_x, ctypes.byref(cm))
            print('  选中第 %d 个：ok=%s 上屏=%r' % (
                idx + 1, okp, (cm.text or b'').decode(errors='replace') if gotc else None))
            if gotc:
                RimeFreeCommit(ctypes.byref(cm))
            print('  调频文件 qtal/mao 行：')
            fp = os.path.join(USERDIR, 'en_word_userfreq.tsv')
            if os.path.exists(fp):
                with open(fp, 'r', encoding='utf-8') as f:
                    for line in f.read().splitlines():
                        if line.split('\t', 1)[0] in ('qtal', 'mao'):
                            print('    ' + line)
        for _ in range(len(keys) + 3):
            RimeSimulateKeySequence(sid_x, b'{Escape}')

    RimeDestroySession(sid)
    RimeDestroySession(sid2)
    RimeFinalize()
    return 0


if __name__ == '__main__':
    args = sys.argv[1:] or ['qtal', 'mao']
    sys.exit(main(args))
