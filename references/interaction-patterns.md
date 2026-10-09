# 交互增强模式库（按钮 / 动画 / 模拟）

> 把「经典展示型演示」升级为「交互演示」的可复用模式。
> 素材来源：作者手工案例库（教学创新赛·抛硬币/几何概率系列、直方图等·Probabilities balls、实变函数·CantorSet 等，共 219+ 案全库联学）+ 本技能真机实测。自 v1.4 起启用。

## 0. 引擎事实（真机实测，编写按钮/脚本前必读）

- **按钮创建**：`Button()`、`Button("标题")` 均可经指令创建，支持命名（`btnReset = Button("重置")`）。
- **带脚本的二参形式 `Button("标题","脚本")` 经命令注入不受支持**（真机实测：静默失败，按钮不会被创建）。
  正确姿势：先用 `Button("标题")` 创建 → `export_ggb.mjs` 真机导出 → `ggb_patch.py` 注入脚本。
- **脚本语言（GGBScript）要点**：
  - 多语句用**换行**分隔（`;` 不是分隔符——真机实测只执行第一句）；
  - 方括号经典写法与圆括号均可（`SetValue[a,1]` ＝ `SetValue(a,1)`）；
  - 脚本命令（SetValue / StartAnimation 等）经 API 执行时返回 false 属正常现象，**看效果不看返回值**。
- **脚本存储位置**：.ggb 内 `geogebra.xml` 中 `<ggbscript val="…"/>`（点击）/ `<ggbscript onUpdate="…"/>`（对象更新时）。

## 1. 重置按钮（最常用）

```json
{"label": "btnReset", "event": "onClick", "script": "SetValue(a, 1)\nSetValue(h, 0.8)"}
```

- 列表类清空：`results = {}` 或 `SetValue[plist, {}]`（作者案例：Coin Toss 的 Restart、几何概率的 clear）。
- 约定：打开的初始状态 ＝ 重置后的状态（孩子按一下就知道回到了起点）。

## 2. 重抽 / 换一批（随机模拟）

```json
{"label": "btnRand", "event": "onClick", "script": "SetValue(a, RandomUniform(-2, 2))"}
```

- 重排列表：`BlueRandomList = Shuffle[BlueList]`（作者案例：Probabilities balls）。
- 单次抽样并累积：`event = Random(0,1)` + `SetValue(results, Append(results, event))`（作者案例：Coin Toss）。

## 3. 开始/停止对 + 自动运行（进阶，作者体系）

作者案例（几何概率系列）的"动画驱动模拟"三件套：

1. 一个滑块（如 `kk`）设为动画（`playing=true`），且动画速度指向变量 `speed`（`<animation speed="speed">`）；
2. 该滑块挂 `onUpdate` 脚本：每动画步执行一次模拟，并 `If[sum==n, SetValue[speed,0]]` 自动停止；
3. 两个按钮 + **条件显隐**：「开始」按钮 `SetValue[speed,3]`（同时重置计数），显示条件 `speed ≟ 0`；
   「停止」按钮 `speed=0`，显示条件 `speed > 0`。

> 本技能现状：上述 .ggb 结构可生成（onUpdate 经 `ggb_patch.py` 注入）；完整自动运行的视觉行为建议导出后在本机 GeoGebra 实跑确认。

## 4. 累积/迭代按钮

`SetValue(results, Append(results, event))` —— 每次点击往列表追加一个元素；
配合 `CountIf` / `TableText` 即时做统计表（作者案例风格）。

## 5. 输入框参数（Textfield）

`txtN = Textfield(n)` —— 让教师/学生直接改参数（作者库 28 案使用）。
真机导出后可用 `getValue` / `setValue` 核验初值。

## 6. 生成与验证流程（本技能）

1. 指令文件中用**单参**创建按钮：`btnReset = Button("重置")`；
2. 静态双验证（L1/L2）→ `export_ggb.mjs` 真机导出（按钮对象随文件保存）；
3. `python ggb_patch.py --ggb base.ggb --spec scripts.json --out final.ggb` 注入脚本；
4. 回读验证：脚本数量（geogebra.xml 中 ggbscript）、对象清单、脚本语句可执行性。

> 完整样例：`tools/ggb-export/example-buttons.txt` ＋ `example-buttons.scripts.json`（割线演示 + 重置/换点按钮）。

## 7. 按钮定位

按钮默认会堆叠在同一位置（互相遮挡）。用 `SetCoords(btnReset, x, y)` 设置像素位置（以画布左上角为原点）。该脚本命令返回值照例不可信（false），但效果真实生效——导出器已内置 `labelOffset` 核验：

```
SetCoords(btnReset, 40, 80)
SetCoords(btnRand, 40, 140)
```

## 8. 重新抽样 / 重绘（tick 变量驱动重算）

GeoGebra 的 `RandomNormal` / `RandomUniform` 只在表达式**重新求值**时才重掷。
让一个按钮强制重掷的做法：引入一个"脏变量" `tick`，把它以 `+ 0 * tick` 的形式塞进随机表达式，按钮只改 `tick` —— 依赖链被推动，随机数就重掷了：

```
tick = 0
samples = Sequence(RandomNormal(mu, sigma) + 0 * tick, j, 1, n)
```

```json
{"label": "btnRedraw", "event": "onClick", "script": "SetValue(tick, tick + 1)"}
```

- 注意：随机结果每次打开 .ggb 都不同，属正常；课堂讲"频率稳定"时反而要强调这一点。
- 本章模式来自 T5 置信区间覆盖率演示的真机实现（v1.5.0）。

## 9. 视图窗口控制（大范围内容防"跑出屏幕"）

当演示里最长/最高的对象把坐标系撑得很大（例如 40 条置信区间竖排到 y=40），默认视图会把主体挤成一条缝。用 4 参数 `ZoomIn` 显式设定视图窗口：

```
ZoomIn(-3, -0.5, 3, 10.5)
```

- `ZoomIn(<Min x>, <Min y>, <Max x>, <Max y>)` 把可视区固定到这个矩形（x 与 y 比例可不同）。
- 竖排 N 条区间时，先把纵向间距设为 `h = 10 / N`、用 `k * h` 作纵坐标，就能让总高度恒定，`ZoomIn` 的窗口不用随 N 变。
- 真机验证方式：读 .ggb 里 `geogebra.xml` 的 `<euclidianView>`（`scale` / `xZero` / `yZero`）确认窗口正确——**这比截图可靠**（无头预览截图可能抓错画布，见 anti-patterns 说明）。
