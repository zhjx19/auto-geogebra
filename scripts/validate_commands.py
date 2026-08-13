#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GeoGebra 指令静态验证脚本（Claude Code 版）

移植自 aardio autos.skills.geogebra 的 validateCommands 逻辑。

用法：
    python validate_commands.py <文件路径>
    echo "a = Slider(-3,3,0.1)" | python validate_commands.py

输出：JSON 报告，含 ok / errors / warnings / info 字段。
"""
import sys
import os
import json
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(SCRIPT_DIR, "..", "data", "commands-index.json")

# 旧名/常见误写 → 正确命令名的别名映射（与 zh-command-aliases.json 命名口径一致）
COMMAND_ALIASES = {
    "CurveCartesian": "Curve",
    "Mirror": "Reflect",
    "StudentT": "TDistribution",
    "TaylorSeries": "TaylorPolynomial",
    "FitLineY": "FitLine",
    "StandardDeviation": "SD",
    "SampleStandardDeviation": "SampleSD",
    "CircleArc": "CircularArc",
    "CircleSector": "CircularSector",
    "Textfield": "InputBox",
}


def load_command_index():
    """加载 GeoGebra 指令索引（不强制）。"""
    path = os.path.normpath(INDEX_PATH)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return None


def normalize_commands(text):
    """将输入文本规范化为非空、非注释的行数组。"""
    lines = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        t = raw.strip()
        if t and not t.startswith("//"):
            lines.append(t)
    return lines


def levenshtein(s1, s2):
    """编辑距离（用于拼写检查）。"""
    if len(s1) == 0:
        return len(s2)
    if len(s2) == 0:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1, 1):
        cur = [i]
        for j, c2 in enumerate(s2, 1):
            cur.append(min(
                prev[j] + 1,
                cur[j - 1] + 1,
                prev[j - 1] + (c1 != c2)
            ))
        prev = cur
    return prev[-1]


def validate_commands(text):
    """静态验证 GeoGebra 指令脚本。

    检查：括号配对、SetColor 颜色范围、Text() 换行、Slider 参数、
    未知命令、未定义变量引用。返回 dict。
    """
    result = {
        "ok": True,
        "lineCount": 0,
        "errors": [],
        "warnings": [],
        "info": [],
        "checkedCommands": [],
    }

    lines = normalize_commands(text)
    result["lineCount"] = len(lines)

    cmd_index = load_command_index()
    cmd_names = None
    if cmd_index and isinstance(cmd_index.get("commands"), list):
        cmd_names = [c.get("name") for c in cmd_index["commands"] if isinstance(c, dict)]

    # 第一遍：解析变量定义
    defined_vars = {}
    for i, line in enumerate(lines, 1):
        m = re.match(r"^([\w_]+)\s*[:=]", line)
        if m:
            defined_vars[m.group(1)] = i

    # 第二遍：逐行检查
    for i, line in enumerate(lines, 1):
        # 1. 括号配对
        for ch_open, ch_close, name in (("(", ")", "()"), ("[", "]", "[]")):
            bal = line.count(ch_open) - line.count(ch_close)
            if bal != 0:
                msg = f"括号 {name} 不配对"
                if bal > 0:
                    msg += f"：多 {bal} 个 '{ch_open}'"
                else:
                    msg += f"：多 {-bal} 个 '{ch_close}'"
                result["errors"].append({"line": i, "severity": "error", "rule": "unbalanced-" + ("parentheses" if name == "()" else "brackets"), "message": msg, "text": line})
                result["ok"] = False

        # 2. 提取命令名
        cmd_name = None
        m = re.match(r"^([A-Z][\w]*)\s*\(", line)
        if m:
            cmd_name = m.group(1)
        else:
            m = re.match(r"^[\w_]+\s*=\s*([A-Z][\w]*)\s*\(", line)
            if m:
                cmd_name = m.group(1)
        if cmd_name:
            result["checkedCommands"].append({"line": i, "name": cmd_name})

        # 3. SetColor 颜色范围检查 (0-1)
        if cmd_name == "SetColor":
            m = re.search(r"SetColor\s*\(([^,]+),\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)", line)
            if m:
                obj, r, g, b = m.group(1).strip(), float(m.group(2)), float(m.group(3)), float(m.group(4))
                if max(r, g, b) > 1:
                    sug = "SetColor({}, {:.2f}, {:.2f}, {:.2f})".format(
                        obj, min(r / 255, 1), min(g / 255, 1), min(b / 255, 1))
                    result["warnings"].append({
                        "line": i, "severity": "warning", "rule": "setcolor-range",
                        "message": f"SetColor RGB 值疑似使用 0-255 范围 ({r:.1f}, {g:.1f}, {b:.1f})。GeoGebra 脚本中 SetColor 使用 0-1 范围，大于 1 的值会被钳制，可能导致颜色错误。如：(0,0,255)→改用(0,0,1)",
                        "text": line, "suggestion": sug,
                    })

        # 4. Text() 中的 \n 检查
        if cmd_name == "Text":
            m = re.search(r'Text\s*\(\s*"([^"]*)"', line)
            if m:
                str_arg = m.group(1)
                if re.search(r"\\n[^A-Za-z]", str_arg) or str_arg.endswith("\\n"):
                    result["errors"].append({
                        "line": i, "severity": "error", "rule": "text-backslash-n",
                        "message": "Text() 不支持 \\n 换行！LaTeX 模式下应使用 \\\\ 换行。",
                        "text": line,
                    })
                    result["ok"] = False

        # 5. Slider 参数检查
        if cmd_name == "Slider":
            m = re.search(r"Slider\s*\(\s*([\d.-]+)\s*,\s*([\d.-]+)\s*,\s*([\d.]+)", line)
            if m:
                mn, mx, step = float(m.group(1)), float(m.group(2)), float(m.group(3))
                if mn >= mx:
                    result["errors"].append({
                        "line": i, "severity": "error", "rule": "slider-range",
                        "message": f"Slider 最小值 ({mn:g}) >= 最大值 ({mx:g})", "text": line,
                    })
                    result["ok"] = False
                if step <= 0:
                    result["errors"].append({
                        "line": i, "severity": "error", "rule": "slider-step",
                        "message": f"Slider 步长 ({step:g}) 必须大于 0", "text": line,
                    })
                    result["ok"] = False

        # 6. 未知命令检查
        if cmd_name and cmd_names:
            if cmd_name not in cmd_names:
                suggestions = []
                alias_target = COMMAND_ALIASES.get(cmd_name)
                if alias_target:
                    suggestions.append(alias_target)
                for name in cmd_names:
                    # 放宽相似度：长度比在 0.5~2 之间，且编辑距离不超过 max(2, 长度差+1)
                    len_ratio = len(cmd_name) / max(len(name), 1)
                    if 0.5 <= len_ratio <= 2.0:
                        dist = levenshtein(cmd_name.lower(), name.lower())
                        if dist <= max(2, abs(len(name) - len(cmd_name)) + 1):
                            suggestions.append(name)
                suggestions = sorted(set(suggestions), key=lambda s: levenshtein(cmd_name.lower(), s.lower()))
                result["warnings"].append({
                    "line": i, "severity": "warning", "rule": "unknown-command",
                    "message": f"命令 '{cmd_name}' 未在 GeoGebra 指令索引中找到。可能拼写有误。",
                    "text": line, "suggestions": suggestions[:5],
                })

        # 7. 未定义变量引用检查（简化版）
        if not cmd_name:
            for var_name in re.findall(r"[a-zA-Z]\w*", line):
                if var_name in ("pi", "e", "i", "x", "y", "true", "false", "undefined"):
                    continue
                if var_name + "(" in line:
                    continue  # 函数调用不算引用
                if var_name in defined_vars:
                    continue
                if re.match(r"^" + re.escape(var_name) + r"\s*=", line):
                    continue  # 本行定义
                # 跳过文本字符串内的内容
                stripped = re.sub(r'"[^"]*"', "", line)
                if var_name not in stripped:
                    continue
                result["warnings"].append({
                    "line": i, "severity": "warning", "rule": "undefined-variable",
                    "message": f"变量 '{var_name}' 可能在第 {i} 行使用前未定义。", "text": line,
                })
                break  # 每行只报一个

    if not result["errors"] and not result["warnings"]:
        result["info"].append({"message": "✓ 未检测到常见错误。"})
    return result


def main():
    # Windows 下确保 stdout 使用 UTF-8，避免 GBK 编码错误
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if not os.path.exists(path):
            print(json.dumps({"ok": False, "errors": [{"rule": "file-not-found", "message": f"文件不存在：{path}"}], "warnings": [], "info": []}, ensure_ascii=False, indent=2))
            return
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    report = validate_commands(text)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
