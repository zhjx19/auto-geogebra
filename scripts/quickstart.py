#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""auto-geogebra · 一键自检 / 导出 demo（新手 3 分钟看到结果）。

用法：
    python scripts/quickstart.py                    # 校验自带示例 demo1（L1 语法 + L2 语义）
    python scripts/quickstart.py --list             # 列出自带示例
    python scripts/quickstart.py <指令.txt>          # 校验指定的指令文件
    python scripts/quickstart.py <指令.txt> --export [--png]   # 再真机导出 .ggb（可加预览图）

设计：
    - 默认只做**静态双验证**——离线、只用 Python 标准库、不改动任何文件；
    - `--export` 才调用 `node tools/ggb-export` 真机导出（需 Node 18+ 与本机 Chrome/Edge，首次联网）；
    - 全程只读取指令文件、把 .ggb/.png 写到与指令文件同名的位置，不做删除等破坏性操作。
跨平台：Windows / macOS / Linux 均可；Python 3.8+。
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXAMPLES = os.path.join(ROOT, "examples")
EXPORT_DIR = os.path.join(ROOT, "tools", "ggb-export")


def run_json(script_name, target):
    """跑一个验证器，返回其 JSON。"""
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, script_name), target],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        return json.loads(proc.stdout)
    except Exception:
        return {"_raw": proc.stdout, "_err": proc.stderr, "_rc": proc.returncode}


def list_examples():
    return sorted(glob.glob(os.path.join(EXAMPLES, "*.txt")))


def main():
    ap = argparse.ArgumentParser(description="auto-geogebra 一键自检 / 导出 demo")
    ap.add_argument("cmds", nargs="?", default=os.path.join(EXAMPLES, "demo1-derivative-definition.txt"),
                    help="指令文件（默认：自带示例 demo1）")
    ap.add_argument("--list", action="store_true", help="列出自带示例后退出")
    ap.add_argument("--export", action="store_true", help="真机导出 .ggb（需 Node 18+ 与本机 Chrome/Edge）")
    ap.add_argument("--png", action="store_true", help="同时导出预览图（配合 --export）")
    ap.add_argument("--out", default=None, help=".ggb 输出路径（默认与指令文件同名）")
    args = ap.parse_args()

    if args.list:
        print("自带示例（examples/）：")
        for f in list_examples():
            print("  -", os.path.basename(f))
        return 0

    cmds = os.path.abspath(args.cmds)
    if not os.path.exists(cmds):
        print("[!] 找不到指令文件：", cmds)
        print("    用 --list 看自带示例，或传入你自己的指令文件路径。")
        return 2

    rel = os.path.relpath(cmds, ROOT)
    print("== 指令文件：%s" % rel)

    l1 = run_json("validate_commands.py", cmds)
    l2 = run_json("validate_types.py", cmds)
    ok1 = l1.get("ok")
    errs = l1.get("errors", [])
    warns = l1.get("warnings", [])
    se = l2.get("semanticErrors")
    print("  L1 语法：ok=%s，错 %d，警 %d" % (ok1, len(errs), len(warns)))
    print("  L2 语义：semanticErrors=%s" % se)
    for e in errs:
        print("     L1 E:", e.get("message"))
    for w in warns:
        print("     L1 W:", w.get("message"))
    for e in l2.get("errors", []):
        print("     L2 E:", e.get("message"))

    if not (ok1 and se == 0):
        print("\n[!] 静态双验证未通过——先按上面的提示修正，再导出。")
        return 1

    if not args.export:
        print("\n[✓] 静态双验证通过。要生成真机 .ggb，加 --export：")
        print("    python scripts/quickstart.py \"%s\" --export" % rel)
        print("    （真机导出需 Node 18+ 与本机 Chrome/Edge；无环境时可到 https://ggbgen.pages.dev/ 在线批量执行）")
        return 0

    node = shutil.which("node")
    if not node:
        print("\n[!] 未找到 node——真机导出需要 Node 18+。")
        print("    可改用 https://ggbgen.pages.dev/ 在线批量执行后下载 .ggb。")
        return 3

    out = os.path.abspath(args.out) if args.out else os.path.splitext(cmds)[0] + ".ggb"
    cmd = [node, os.path.join(EXPORT_DIR, "export_ggb.mjs"),
           "--page", os.path.join(EXPORT_DIR, "page.html"),
           "--cmds", cmds, "--out", out]
    if args.png:
        cmd += ["--png", os.path.splitext(out)[0] + ".png"]

    print("\n== 真机导出中（首次需联网加载官方引擎）…")
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    d = None
    for stream in (proc.stdout, proc.stderr):
        try:
            d = json.loads(stream)
            break
        except Exception:
            continue
    if d is not None:
        print("  EXPORT ok=%s failed=%s soft=%s" % (d.get("ok"), d.get("failed"), d.get("softFailures")))
        for r in d.get("failedList", []):
            print("     FAIL:", r.get("cmd"), "|", r.get("err") or r.get("note"))
        if d.get("error"):
            print("  导出器报错：", d.get("error"))
            print("  （多为网络原因：真机导出需联网加载官方引擎 deployggb.js；无网时可用 https://ggbgen.pages.dev/ 在线执行）")
    else:
        print("  导出原始输出：", (proc.stdout or "")[:400])
        if proc.stderr:
            print("  stderr：", proc.stderr[:200])
    if os.path.exists(out):
        print("  输出：%s（%d bytes）" % (os.path.relpath(out, ROOT), os.path.getsize(out)))
    return 0 if proc.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
