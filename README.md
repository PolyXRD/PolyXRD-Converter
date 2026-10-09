# PolyXRD Converter

**XRD 谱图格式转换器** —— 从 [PolyXRD](https://github.com/PolyXRD/PolyXRD) 独立剥离的轻量小工具：把各种厂商/软件导出的谱图文件互转成你需要的目标格式，**多厂商 RAW 二进制自动识别**，双击即用，无需安装。

![icon](src/polyxrd_converter/resources/icon.png)

## 功能

- **读入**：`xy` `txt` `dat` `csv` `smz` `mdi` `xrdml/xml` `brml` `json`，以及多厂商二进制 `RAW`（自动识别，见下表）；岛津项目的 `.ORG/.RSM/.RBG/.RK1/.RAX/.RLZ/.RFI` 与 `.RAW` 同结构，一并支持
- **写出**：`xy` `txt` `dat` `csv` `mdi` `raw` `xrdml` `json`
- **批量转换**：拖入整个目录，后台线程逐个转换，实时进度
- **谱图预览**：手绘曲线（不依赖 matplotlib），滚轮缩放 / 拖拽平移 / 双击复位 / 最强峰标记
- **角度轴护栏**：RAW 头参数损坏时**宁可标记不可信也不硬猜**——拒绝自动转换并引导人工指定 `(起始 2θ, 步长)`，杜绝产出峰位错误的谱图
- **双语界面**：中文 / English

## RAW 多厂商自动识别

| 厂商/格式 | 魔数 | 识别要点 |
|---|---|---|
| 岛津 Shimadzu XRD | `Shimadzu XRD` | 私有容器：变长头 + **int32 LE** 强度。点数取头里 `u32@0x34 ÷ 4`（权威），数据起始 = `u32@0x30 + 56`（头长可变，有的文件把嵌入的源路径也算进头里）。起始/终止/步长为 `i32@0x12C/0x130/0x134 ×1e-4`（**有符号**，可支持 θ 负角扫描）。`0x20` 记录类型区分 `.RAW/.ORG/.RSM/.RBG/.RK1/.RAX/.RLZ/.RFI`（同结构，均可读）与 `PKR/PKK/PKS/PSE/PKF`（峰表，**明确拒绝**）。**截断防护**：声明数据区超出文件尾时钳到实际可用点数、标记 `truncated` 并高亮提示，绝不把头部字节当强度读入；截断文件的角度轴强制转人工指定 |
| 理学 Rigaku (RINT/SmartLab) | `FI\x00\x00` | 定长 3162 字节头 + 变长 float32 强度，轴参数在 0xB92；点数双证据（n_axis vs n_fixed）一致性校验 |
| Scintag RAW2 | `RAW2` | 316 字节头；点数(int16)@0x102、步长(float32)@0x10C、起始 2θ(float32)@0x110 |
| Bruker/Siemens RAW v1 | `RAW1.01` / `RAW1.00` / `RAW ` | 定长字符串头 + 10 条 ×892 字节区间记录 + 末尾 float32 强度；轴按严格判据匹配（step 0.005~0.5°、span≥1°、end≤180°），匹配不上则标不可信 |
| MDI / Jade 文本导出 | —（两行头） | 头行 `start step mode anode λ stop npoints`，单列定宽强度；靶材记号与波长交叉校验后才按头建轴 |
| 未知 RAW | — | 兜底解析（最长可信 float32 后缀），轴一律标不可信 |

> **设计原则**：解析器按"魔数分流 + 可信度标记"组织。头参数损坏（如 end > 180°、点数不自洽）时产出 `axis_confident=False`，GUI 高亮警告，转换被拦截，直到人工给出角度轴。

### 岛津容器的四种约定（都已处理）

- **步长字段被截断**：`Std/Search.RAW` 头里写 0.0213，实际是 0.0212644（4 位小数截断）。点数自洽校验不过时，按 `(end − start)/(n − 1)` 反推步长。
- **头里的 end 差一个步长**：部分样本 `end = start + step×n`（如 `Stress/Heikei-Test`：34.0 + 0.05×80 = 38.0 精确闭合），另一部分是 `start + step×(n−1)`。以头里 `0x34` 声明的点数与步长字段为准，两种约定都能接受——统一按 `(end−start)/(n−1)` 重排会在这一类文件上把轴拉伸出固件不可能的步长（如 0.05063291）。
- **波长字段可能过期**：`Stress/std-sokkei.RAW` 靶材已是 Cr 但波长字段残留 Cu 1.5406 —— 以靶材元素记号查表为准。
- **文件被截断**：头里声明的数据区装不进实际文件时（传输不完整等），钳到可用点数、标记 `truncated` 并在列表里高亮「文件不完整」；截断文件的 `end` 对应声明点数而非实际点数，角度轴不可信，须人工指定后才能转换。

## 使用

### 图形界面

双击 `PolyXRDConverter.exe`（或 `python main.py`）：

1. 把文件/文件夹拖进窗口（或点「添加文件」）
2. 表格自动识别每个文件的格式、点数、2θ 范围、最强峰强度
3. 选中任一行即可在右侧预览谱图
4. 选目标格式 + 输出目录 → 「开始转换」

带参启动（拖文件到 exe 图标上等效）：

```
PolyXRDConverter.exe D:\data\spectrum.raw D:\data\another.xy
```

### 命令行 / 作为库

```python
from polyxrd_converter.loader import load_pattern
from polyxrd_converter.converter import convert_file

data = load_pattern("spectrum.raw")          # 自动识别格式
print(len(data), data.two_theta[0], data.two_theta[-1])

convert_file("spectrum.raw", "spectrum.xrdml")   # 单文件转换
```

## 验证

真实样本全量交叉校验（与同谱其它格式导出逐点比对）：

```
python tests/validate_samples.py     # 247 项断言
python tests/smoke_gui.py            # GUI 离屏冒烟 40 项
```

覆盖：
- **岛津**：`XRData/Shimadzu Data` 72 个 `.RAW` 全解析成功（角度轴全部可信），其中 5 组与厂商官方 ASCII 导出逐点比对 —— **强度完全相等**、2θ 差 <3e-14；含 5 个边界样本回归（负角 θ 扫描、步长截断、end 差一步长、Cr 靶、变长头）与峰表拒绝、合成截断文件回归
- **岛津全量对拍（v1.1.0）**：`XRData` 全库 305 个岛津容器文件（含 1608/976 字节变长头子类型）解析成功，其中 26 个真实截断文件正确标记并拦截；与 PolyXRD 主体 `DataLoader._load_shimadzu_raw` 逐点对拍 206 个文件，**强度全等**；`smz geshi` 13 对 `.RAW`↔PCXRD ASCII 导出逐点对拍（含 θ 单轴摇摆扫描），强度全等、2θ 差 <1.5e-14
- **理学**：Rigaku FI 39 个（与 `.txt` 逐点一致）
- **Scintag**：RAW2 33 个（与 `.dat/.txt/.xy` 逐点全等）
- **Bruker**：RAW v1 轴损坏样本正确拦截
- **Jade**：文本导出按头建轴 + 峰位交叉
- 8 种格式往返守恒

## 开发

```bash
python -m venv venv
venv\Scripts\pip install -e . pyinstaller
python main.py                 # 源码运行
build.bat                      # 打包单文件 exe
```

## 依赖

运行仅需 `numpy` + `PySide6`（预览用 QPainter 手绘，刻意不引入 matplotlib/pyqtgraph，控制单文件体积与启动速度）。

## 许可

版权所有 (c) 2026 PolyXRD Team。

本软件可供学术研究与教学免费使用。
未经版权持有人单独书面许可，禁止用于商业用途。
软件按原样提供，不提供任何担保。

完整条款见 [`LICENSE`](LICENSE)（英文）与 [`LICENSE-CN`](LICENSE-CN)（中文）；商业授权联系：sshztx@outlook.com。
使用时请同时遵守上游 PySide6 (LGPL/GPL)、numpy (BSD) 等第三方许可证条款。

---

<div align="right">
  <i>PolyXRD Team · 2025 — 2026 · 联系：sshztx@outlook.com</i>
</div>
