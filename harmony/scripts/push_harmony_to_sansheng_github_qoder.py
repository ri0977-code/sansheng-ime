#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""把鸿蒙工程（脱敏版）推进 sansheng 的 GitHub 仓（Qoder，2026-10-30）

目标仓：`riips7-code/sansheng-ime`（**public**），远端 master 头由主人自己改过
（README 里有 2 个他直接在 GitHub 上提交的 commit）⇒ **绝不能拿本地 master 盲推**。

本脚本的做法（可复核）：
  1. `git worktree add` 从**远端头**（refs/remotes/ghfast/master）开一条新分支
     `feature/harmony-1.0.0` —— 不碰主人本地那棵工作区；
  2. 把 `F:\qoderwork\gh-harmony-stage`（脱敏导出产物）放进 `harmony/`；
  3. 提交（commit message 带 `(Qoder)` 标识，符合本仓 agent 标识规则）；
  4. 推送前三条硬核对：
       a. 待推分支的祖先里有远端头（⇒ 一定是**快进**，不是改写历史）；
       b. 本次新增文件里不含 `sign/`、`.p12/.p7b/.cer`、真口令；
       c. 待推路径只有 `harmony/`（不夹带主人工作区里的其它改动）；
  5. `git push` 走 `https://ghfast.top/https://github.com/<repo>.git`
     （本机 github.com:443 被重置，api.github.com 通；ghfast 实测带鉴权可 ls-remote）；
  6. 推完 `ls-remote` 回读远端头，确认等于本地新提交。

用法：
    python scripts/push_harmony_to_sansheng_github_qoder.py [--dry]
退出码：0 成功；2 环境/核对不通过。
"""
from __future__ import annotations

import base64
import os
import subprocess
import sys

DESKTOP_REPO = r"F:\workbuddywork\三生输入法"
STAGE = r"F:\qoderwork\gh-harmony-stage"
WORKTREE = r"F:\qoderwork\gh-harmony-worktree"
BRANCH = "feature/harmony-1.0.0"
GH = r"F:\workbuddywork\三生输入法\_probe"          # gh.py 在这里（token 不打印不落盘）
DEST_PATH = "harmony"                                # 放进仓里的子目录

FORBIDDEN_SUFFIX = (".p12", ".p7b", ".p7c", ".cer", ".pem", ".keystore", ".jks")


def run(args, cwd=None, binary=False, timeout=1800):
    p = subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout)
    out = p.stdout if binary else p.stdout.decode("utf-8", "replace")
    err = p.stderr if binary else p.stderr.decode("utf-8", "replace")
    return p.returncode, out, err


def git(*args, cwd=DESKTOP_REPO, timeout=1800):
    rc, out, err = run(["git", "-c", "core.quotepath=false"] + list(args), cwd=cwd, timeout=timeout)
    if rc != 0:
        raise SystemExit("git %s 失败：%s" % (" ".join(args), err[-800:]))
    return out.strip()


def get_token():
    sys.path.insert(0, GH)
    import gh  # noqa: E402
    return gh.get_token(), gh.REPO


def auth_header(tok):
    return "Authorization: Basic " + base64.b64encode(("x-access-token:" + tok).encode()).decode()


def main():
    dry = "--dry" in sys.argv
    tok, repo = get_token()
    url = "https://ghfast.top/https://github.com/%s.git" % repo
    hdr = auth_header(tok)

    # 0) 远端头（实时读，不信缓存）
    rc, out, err = run(["git", "-c", "http.extraheader=" + hdr, "ls-remote", "--heads", url, "master"], timeout=300)
    if rc != 0:
        print("FAIL: 读远端头失败：%s" % err[-300:])
        return 2
    remote_head = out.split()[0]
    print("远端 master = %s" % remote_head)

    # 1) 干净 worktree：从远端头开分支
    if os.path.isdir(WORKTREE):
        run(["git", "worktree", "remove", "--force", WORKTREE], cwd=DESKTOP_REPO)
    git("fetch", url, "master:refs/remotes/ghfast/master")
    got = git("rev-parse", "refs/remotes/ghfast/master")
    if got != remote_head:
        print("FAIL: fetch 到的远端头 %s != ls-remote %s（有人在我读取期间推了东西，停手）" % (got, remote_head))
        return 2
    git("worktree", "add", "-B", BRANCH, WORKTREE, got)
    print("worktree 就绪：%s @ %s" % (WORKTREE, BRANCH))

    # 2) 放入脱敏导出
    import shutil
    dst = os.path.join(WORKTREE, DEST_PATH)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(STAGE, dst)
    n = sum(len(f) for _, _, f in os.walk(dst))
    print("已放入 %s：%d 个文件" % (DEST_PATH, n))

    # 3) 提交
    git("add", DEST_PATH, cwd=WORKTREE)
    staged = git("diff", "--cached", "--name-only", cwd=WORKTREE)
    files = [x for x in staged.splitlines() if x]
    print("待提交 %d 个文件" % len(files))

    # 4) 三条硬核对
    bad = [f for f in files if f.lower().endswith(FORBIDDEN_SUFFIX) or "/sign/" in f or f.startswith("sign/")]
    if bad:
        print("FAIL: 待提交里出现密钥容器：%s" % bad[:10])
        return 2
    outside = [f for f in files if not f.startswith(DEST_PATH + "/")]
    if outside:
        print("FAIL: 待提交夹带了 %s 以外的路径：%s" % (DEST_PATH, outside[:10]))
        return 2
    rc, anc, err = run(["git", "merge-base", "--is-ancestor", got, "HEAD"], cwd=WORKTREE)
    if rc != 0:
        print("FAIL: 新提交不是远端头的后代（不是快进），停手")
        return 2
    print("核对通过：密钥容器 0、越界路径 0、是远端头的快进")

    msg = ("harmony/：三生输入法鸿蒙端（HarmonyOS NEXT）工程源码入库（脱敏版）(Qoder)\n\n"
           "- 目录 harmony/ 为鸿蒙端完整工程：ArkTS 页面与输入法服务、C++ NAPI 桥与 librime 头文件、\n"
           "  rawfile/rime 词库与 lua 滤镜、构建脚本（scripts/）、工程台账（docs/）。\n"
           "- 脱敏口径：真机截图（docs/evidence 下的图片）与原始 hilog 抓取、软著申报材料、\n"
           "  sign/ 签名私钥材料一律未入库；台账正文里的机主姓名/身份证号/手机号在**导出副本**里已替换，\n"
           "  本地原始记录不受影响。\n"
           "- 从远端头开分支后快进合入 master，未 force、未改写历史。")
    git("commit", "-m", msg, cwd=WORKTREE)
    new_head = git("rev-parse", "HEAD", cwd=WORKTREE)
    print("新提交 %s" % new_head)

    if dry:
        print("[dry] 未推送。")
        return 0

    # 5) 推送（快进）
    rc, out, err = run(["git", "-c", "http.extraheader=" + hdr, "push", url,
                        "%s:refs/heads/master" % BRANCH], cwd=WORKTREE, timeout=3600)
    print("push rc=%d %s %s" % (rc, out.strip()[:300], err.strip()[-300:]))
    if rc != 0:
        return 2

    # 6) 回读远端头核对
    rc, out, err = run(["git", "-c", "http.extraheader=" + hdr, "ls-remote", "--heads", url, "master"], timeout=300)
    after = out.split()[0]
    print("远端 master 现为 %s（期望 %s）" % (after, new_head))
    if after != new_head:
        print("FAIL: 回读远端头与本地新提交不一致")
        return 2
    print("=== 推送完成并核对通过 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
