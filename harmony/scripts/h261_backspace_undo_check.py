# -*- coding: utf-8 -*-
"""H-261 守卫：退格删掉的宿主文本框文字必须可撤销。

主人 2026-10-28 16:0x 原话：「现在退格单删连删删除的文字，下滑反不回，下滑加上针对退格返回，
顶栏的返回和重做也不针对退格单删和连删」。

三处判据（都读 KeyboardController.ets 的真实方法体）：
  A1 单删入账：onBackspace 的编辑框删除路径先 `getForwardSync(1)` 取光标前 1 字（命名坑同 H-210：
     getForwardSync 才是光标**前**文＝deleteForwardSync 删的那侧），再 `pushUndo({type:'clear', ...})`。
  A2 顶栏撤销认退格：undoCommit 的弹栈条件必须同时收 'commit' 与 'clear'，且对 'clear' 走 insertText 还原。
  A3 顶栏重做认退格：redoCommit 对 'clear' 记录走 deleteEditor 再删（与撤销对称）。
  A4 旧「只认 commit」的死写法不得回潮。

判据变更记录：本守卫首版（H-261，2026-10-28 16:0x）。下滑还原不需要改 undoLastAction——
它本来就只弹 'clear'，单删只要记成 'clear' 它自然就能还原。
"""
import io
import re
import sys

SRC = r'F:\qoderwork\sansheng-ime-harmony\entry\src\main\ets\inputmethod\KeyboardController.ets'


def extract_method(text, sig):
    """按大括号配对，从 `sig` 起取整个方法体（含花括号）。找不到返回 ''。"""
    i = text.find(sig)
    if i < 0:
        return ''
    j = text.find('{', i)
    if j < 0:
        return ''
    depth = 0
    k = j
    while k < len(text):
        c = text[k]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[i:k + 1]
        k += 1
    return ''


def check(text):
    """返回 (结果列表, 是否全过)。结果元素 = (名称, ok, 说明)。"""
    out = []
    ob = extract_method(text, 'onBackspace(): void {')
    uc = extract_method(text, 'undoCommit(): void {')
    rc = extract_method(text, 'redoCommit(): void {')

    out.append(('A1 单删入账',
                bool(ob) and 'getForwardSync(1)' in ob
                and re.search(r"pushUndo\(\{\s*type:\s*'clear',\s*text:\s*removed\s*\}\)", ob) is not None,
                'onBackspace 编辑框删除前必须 getForwardSync(1) 取字并 pushUndo 成 clear 记录'))

    out.append(('A2 顶栏撤销认退格',
                bool(uc) and re.search(r"r\.type === 'commit' \|\| r\.type === 'clear'", uc) is not None
                and 'this.insertText(rec.text' in uc,
                'undoCommit 弹栈须同时认 commit/clear，clear 走 insertText 还原'))

    out.append(('A3 顶栏重做认退格',
                bool(rc) and 'this.deleteEditor(rec.text.length)' in rc,
                'redoCommit 对 clear 记录须 deleteEditor 再删（与撤销对称）'))

    # A4 旧死写法：弹栈条件只认 'commit'
    out.append(('A4 旧只认commit不回来',
                re.search(r"if \(r !== undefined && r\.type === 'commit'\) \{", text) is None,
                'undoCommit 不得退回「只认 commit」的旧写法'))

    # A5 撤销/重做插回时不得清空重做栈（否则重做只做一次，与撤销不统一）
    out.append(('A5 撤销重做插回不清空重做栈',
                bool(uc) and 'this.insertText(rec.text, false)' in uc
                and bool(rc) and 'this.insertText(rec.text, false)' in rc
                and re.search(r"if \(recordUndo\) \{\s*\n\s*this\.pushUndo", text) is not None,
                'insertText 须有 recordUndo 开关；undoCommit(clear)/redoCommit(commit) 插回须传 false——'
                '否则 insertText 内 pushUndo 会 redoStack=[] 清空重做栈 ⇒ 重做只能做一次'))
    return out


def report(results, tag=''):
    ok = True
    for name, passed, hint in results:
        print('  %s %s%s' % ('PASS' if passed else 'FAIL', name, ('  ← ' + hint) if not passed else ''))
        if not passed:
            ok = False
    return ok


def selftest(text):
    """正控（当前文件）+ 三个已知坏样本必须按预期触发。"""
    good = check(text)
    ok = report(good, 'good')
    if not ok:
        print('SELFTEST: 当前文件本该全过却红了')
        return False

    # 坏样本 1：onBackspace 回退成「不入账」
    bad1 = text.replace(
        "    if (removed.length > 0) {\n      this.deleteEditor(1);\n      this.pushUndo({ type: 'clear', text: removed });\n    } else {\n      // 已在行首（光标前无字）：只清编码，不记撤销\n      this.deleteEditor(0);\n    }",
        "    this.deleteEditor(1);", 1)
    # 坏样本 2：undoCommit 退回只认 commit
    bad2 = text.replace("(r.type === 'commit' || r.type === 'clear')", "(r.type === 'commit')", 1)
    # 坏样本 3：redoCommit 去掉 clear 再删分支
    bad3 = text.replace("      // 'clear'（退格单删／整框清空）重做＝把刚还原的字再删掉\n      this.deleteEditor(rec.text.length);", "      this.insertText(rec.text);", 1)
    # 坏样本 4：redoCommit 的 commit 重做退回默认 insertText（会 pushUndo 清空重做栈 ⇒ 重做只一次）
    bad4 = text.replace("      this.insertText(rec.text, false);\n    } else {\n      // 'clear'（退格单删／整框清空）重做",
                        "      this.insertText(rec.text);\n    } else {\n      // 'clear'（退格单删／整框清空）重做", 1)

    cases = [('bad1 onBackspace不入账', bad1, 'A1 单删入账'),
             ('bad2 undoCommit只认commit', bad2, 'A2 顶栏撤销认退格'),
             ('bad3 redoCommit无clear分支', bad3, 'A3 顶栏重做认退格'),
             ('bad4 redoCommit清空重做栈', bad4, 'A5 撤销重做插回不清空重做栈')]
    allok = True
    for label, mutant, target in cases:
        if mutant == text:
            print('  SELFTEST FAIL %s：坏样本没造出来（锚点漂了）' % label)
            allok = False
            continue
        res = dict((n, p) for n, p, _ in check(mutant))
        if res.get(target) is False:
            print('  SELFTEST OK %s：按预期判红（%s）' % (label, target))
        else:
            print('  SELFTEST FAIL %s：坏样本没被抓住（%s 仍 PASS）' % (label, target))
            allok = False
    return allok


def main():
    text = io.open(SRC, encoding='utf-8').read()
    if '--selftest' in sys.argv:
        ok = selftest(text)
        print('结论：%s' % ('判据可信（正控+3 坏样本全部按预期）' if ok else '自测失败'))
        sys.exit(0 if ok else 1)
    results = check(text)
    ok = report(results)
    print('结论：%s' % ('退格删除已可撤销（下滑/顶栏撤销/重做三路齐全）' if ok else 'H-261 判据未满足'))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
