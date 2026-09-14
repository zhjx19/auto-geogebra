# GeoGebra 指令静态验证检查清单（人工自查版）

生成 GeoGebra 指令后，按以下清单逐项自查。优先用脚本自动验证（推荐，更可靠）：

```
python scripts/validate_commands.py <文件>   # L1 语法
python scripts/validate_types.py    <文件>   # L2 语义（类型）
```

两道全过才算通过。下表 1–7 节对应 L1，第 8 节对应 L2。

## 1. 括号配对

每行指令的圆括号 `()` 与方括号 `[]` 必须配对。

- 左括号多或右括号多都算错误。
- 注意：`Text()` 内 LaTeX 的 `\\` 不会影响括号计数，但 LaTeX 中的花括号 `{}` 不在此检查范围。

## 2. SetColor 颜色范围

GeoGebra 脚本中 `SetColor(obj, r, g, b)` 的 RGB 值使用 **0-1 范围**，不是 0-255！

- 大于 1 的值会被钳制，导致颜色错误。
- 正确：`SetColor(A, 0, 0, 1)` （蓝色）
- 错误：`SetColor(A, 0, 0, 255)`
- 换算：`255 → 1`、`128 → 0.5`。

## 3. Text() 指令换行

`Text()` 指令**不支持 `\n` 换行**。

- 多行文本必须使用 LaTeX 语法：`\\` 表示换行。
- 推荐：`Text("line1 \\ line2", (x, y), true, true)`
- 或使用 `\begin{aligned} ... \\ ... \end{aligned}` 对齐多行。

## 4. Slider 参数

滑块必须用 `Slider(min, max, step)` 指令，且：

- `min < max`（最小值必须小于最大值）；
- `step > 0`（步长必须大于 0）；
- 步长不应掩盖关键变化（见 SKILL.md「变量设计约束」）。

## 5. 未知命令

命令名必须是合法的 GeoGebra 指令。常见错误：

- 拼写错误（如 `TangentLine` 应为 `Tangent`）；
- 自造命令（如 `SlopeOf` 应为 `Slope`）。

不确定时查询 `data/commands-index.json`（约 500 条指令索引），或按 SKILL.md 中的「中文教学意图 → 英文命令」映射联想正确命令。

## 6. 未定义变量引用

使用变量前必须先定义（赋值或创建对象）。例如：

- 错误：`B = Point(f)` 但 `f` 尚未定义；
- 正确：先 `f(x) = x^2`，再 `A = Point(f)`。

注意：
- `x`, `y`, `e`, `pi`, `i`, `true`, `false` 是内建常量/参数名，不算未定义；
- 函数调用名（如 `Point(`）不算变量引用；
- 字符串文本内的内容不算变量引用。

## 7. 其他常见问题

- 对象依赖顺序：先定义稳定的基础对象，再定义依赖对象。
- 注释用 `//` 开头，不参与执行。
- 指令用换行分隔，一行一条。

## 8. 语义（类型）检查 —— L2

L1 只查语法，**对语义错误会静态通过**。以下问题由 `scripts/validate_types.py` 自动检查，也可人工对照 `data/commands-index.json` 的签名自查。

### 8.1 参数类型不匹配

每个命令的签名规定了参数类型（如 `Slope( <Line> )`）。传入不匹配的对象会报错或得到无意义结果。

| 错误示例 | 问题 | 改正 |
|---|---|---|
| `Slope(P)`（P 是点） | Slope 只接受直线 | 先作直线，再 `Slope(line)` |
| `Derivative(poly)`（poly 是多边形） | Derivative 只接受函数/曲线/表达式 | 先定义 `f(x)=…` 再求导 |
| `Area(seg)`（seg 是线段） | Area 只接受多边形/圆锥曲线/点列 | 改用 `Length(seg)` |

### 8.2 矩阵维度错配

`ApplyMatrix` 要求矩阵维度与被作用对象维度一致。

- 错误：`ApplyMatrix({{1,2,3},{4,5,6},{7,8,9}}, poly2d)` —— 3×3 矩阵作用于 2D 多边形
- 正确：2D 变换用 2×2 矩阵 `ApplyMatrix({{a,b},{c,d}}, poly2d)`；3×3 只用于 3D 对象

### 8.3 数值列表陷阱

`Sum`/`Mean`/`Min`/`Max`/`Product`/`SD` 等统计命令的签名只写 `<List>`，但**语义上要求元素是数值**。

- 错误：`rects = Sequence(Polygon(...), i, 1, 5)` 之后 `Sum(rects)` —— 对几何对象列表求和
- 正确：要面积和就用 `Sequence(Area(Polygon(...)), i, 1, 5)` 生成**数值**列表，再 `Sum`

### 8.4 静态检查覆盖不到、必须实际执行的

GeoGebra 脚本（`SetValue`/`StartAnimation`/`OnClick`）、自定义工具、`Locus` 轨迹、3D 曲面与交线、`Zip` 嵌套、依赖顺序敏感的构造。这类只能导入 GeoGebra 实跑确认。
