# PolyXRD Converter 转交记录（Handover）— 截至 v1.4.0

> 撰写日期：2026-10-10 ｜ 最近更新：2026-10-12 ｜ 当前对应版本：**v1.4.0**（commit `fc11da4`，Release id 409972391）
> 读者：接手本项目的后续开发者 / 协作模型。读完本文应能独立完成"改一个解析器 → 验证 → 发版"全流程。
> 维护约定：本文是**持续更新的活文档**（文件名不挂版本号），每次发版只需更新 §1 能力矩阵、§4.1 断言数、§5 进展表、§7 已知问题；§6 踩坑只增不删。

---

## 1. 项目定位与目标

**PolyXRD Converter** 是从 [PolyXRD 主项目](https://github.com/PolyXRD/PolyXRD)（PySide6 MVVM 大型 XRD 分析软件）中**独立剥离**的谱图格式转换小工具，仓库 `github.com/PolyXRD/PolyXRD-Converter`。

- **做什么**：把各种厂商/软件导出的 XRD 谱图文件互转成目标格式；**多厂商二进制 RAW 自动识别**是核心卖点。
- **不做什么**：不做物相检索/精修/数据库（那是主项目的事）。与主项目**零耦合**，只依赖 `numpy` + `PySide6`。
- **分发形态**：PyInstaller **单文件 exe**（约 55 MB），双击即用免安装；GitHub Release 发布 exe + SHA256。
- **用户群**：Windows 实验室用户；界面三语（简体中文 / English / 日本語），即时切换。

### 格式能力矩阵

| 方向 | 格式 |
|---|---|
| 读（文本） | `xy` `txt` `dat` `csv` `smz` `mdi`(Jade) `xrdml/xml` `brml` `json`；GSAS 粉末数据 `gsas/fxye/gda/gsa/gss`（FXYE/FXY/ESD/STD 四种 BANK 类型，TOF/EDS 明确拒绝）；FullProf `dat`（start/step/stop 头自洽判定）；理学 `ras`/`rasx`（zip 内存直读）；Topas `xye/qye`；Fit2D `chi/qchi`（Q 轴按 λ 换算 2θ） |
| 读（二进制 RAW，魔数自动分流） | 岛津 `Shimadzu XRD` 容器（`.RAW/.ORG/.RSM/.RBG/.RK1/.RAX/.RLZ/.RFI` 同结构）；理学 Rigaku `FI\x00\x00`；Scintag `RAW2`；Bruker/Siemens `RAW1.01/RAW1.00/RAW `；未知魔数兜底 |
| 写 | `xy` `txt` `dat` `csv` `mdi` `raw` `xrdml` `json` |

---

## 2. 架构与设计思路

### 2.1 模块分层（src/polyxrd_converter/，13 个文件）

```
main.py                 启动入口（源码运行把 src 加 path）
app.py                  QApplication 引导 + 全局异常钩子 + CLI（拖文件/--selftest 自检）
model.py                XRDData 数据类（two_theta/intensity/wavelength/metadata）
loader.py               统一读取入口 load_pattern()：格式探测 → 分发 → 波长/手动轴处理
raw_formats.py          ★ 核心：RAW 二进制多厂商解析器注册表
writers.py              写出各格式（TARGET_EXTS 表驱动）
converter.py            对 UI 只暴露 probe()（试读不落盘）与 convert_file()/convert_batch()
ui_main.py              主窗口（文件表/批量线程/状态灯/手动轴对话框）
ui_preview.py           手绘谱图预览（QPainter，刻意不用 matplotlib，控体积与启动速度）
i18n.py                 中/英/日三语字典 tr(key, **kw) + LANGS 注册表
__init__.py             __version__ 单源（唯一版本号出处）
```

### 2.2 核心设计：RAW 解析器注册表（raw_formats.py）

不同厂商的 `.raw` 是**完全不同的二进制格式**，只能靠文件头魔数分流：

- `RawParser` 基类：`matches(raw) -> bool` + `parse(raw, path) -> RawParseResult`，附 `_f32/_i32/_u32/_text/_plausible` 工具。
- `PARSERS` 元组**顺序即优先级**，`GenericRawParser`（未知魔数兜底）必须永远排最后（`matches` 恒真）。
- `RawParseResult` 关键字段：`two_theta / intensity / format_key / format_label / axis_confident / truncated / meta`。
- **新增一种格式 = 写一个子类 + 追加到 PARSERS 末尾**，不动任何现有代码。

### 2.3 设计红线（接手者必须遵守）

1. **数据保真 > 明确报错 > 标记不可信 > 猜测**。头参数损坏时宁可 `axis_confident=False` 拦截转换引导人工指定，**绝不硬猜产出峰位错误的谱图**；强度能救出来就给，轴给不了就标不可信。
2. **与厂商官方 ASCII 导出逐点全等**是解析器的最高验收标准；任何解析改动都要能通过存量真值对拍。
3. **格式逆向知识写在代码里**：每个 parser 类头部注释必须包含实测 offset 表、字节类型、验证来源（多少个文件、哪批数据、和什么对拍）。这是唯一比文档可靠的载体。
4. 拦截规则：`convert_file()` 遇 `format=raw 且 axis_confident=False` 不写盘；目标=源文件时防呆拒绝。
5. 继承主项目红线：commit/push 需用户显式批准；commit 信息"更新代码修正：…"风格；**禁止 `git add -A`**；中文 commit 用 UTF-8 文件 + `git commit -F`；受版权数据（如 ICDD PDF2）永不入库。

---

## 3. 步骤拆分原则与方法（面向低能力执行模型）

本项目的任务手册式拆分经验，目标是每个子步骤小到"低智商大模型也能做对、且做没做对一测便知"：

1. **一个格式变体 = 一个独立类**。绝不在现有 parser 里加 if 分支兼容新格式；新魔数新类。类粒度 100–200 行，方法粒度到叶子（`_data_block` / `_axis` / `_text` 各司其职，单一职责）。
2. **每个子任务给足五要素**：涉及文件路径、函数签名（I/O 类型）、算法描述、边界条件、验收断言。缺一项就先补齐再动手。
3. **先只读验证，再动手改**。任何修改前先跑一遍存量验证拿到基线（如"247/247"），改完对比基线，杜绝无意识回退。
4. **探路用临时脚本**：复杂的逆向/对拍先写 `_tmp_*.py` 最小脚本跑通，结论沉淀进 parser 注释与正式测试，临时脚本**验证完立刻删除**。
5. **一 commit 一件事**：解析改动、UI 透出、文档更新分开提交；commit 信息说清"改了什么 + 为什么"。
6. **对拍优先于单测**：有厂商 ASCII 真值就用逐点全等对拍（最强断言），没有真值才退而求其次用合成样本测边界。

---

## 4. 每个拆分步骤的测试边界与验收方法

### 4.1 验收矩阵（tests/validate_samples.py，当前 607 项断言全绿）

| 验收块 | 数据来源 | 断言边界 |
|---|---|---|
| Rigaku FI | `XRData/csuHJW` 39 个 .raw | 与同名 .txt 逐点一致；铜 fcc 峰 43.3/50.4° 命中；data006 轴损坏样本（end=195°>180°）标不可信并拦截（KNOWN_BAD_AXIS 回归） |
| Scintag RAW2 | `XRData/IUCr` + `test_xrd/geshi` 33 个 | 与 .dat/.txt/.xy 逐点全等（geshi 4-1: 7251 点） |
| Bruker RAW v1 | csuHJW/data035 | 轴匹配判据（step 0.005~0.5、span≥1°、end≤180°）失败时 `axis_confident=False`，强度照给 |
| 岛津容器 | `XRData/Shimadzu Data` 72 个 .RAW + 39 个伴随扩展名 | 全解析成功且轴全部可信；**5 组与厂商 ASCII 导出逐点比对：强度全等、2θ 差 <3e-14**；峰表（PKR 等）明确拒绝；负角/步长截断/变长头边界回归；**合成截断回归**（手工 struct.pack 构造完整/截断文件：钳点数、truncated=True、axis_confident=False、保留点逐值全等） |
| 往返守恒 | 8 种格式 | 任意 读→写→读 点数与数值守恒 |
| MDI/Jade | 文本导出 | 按头建轴 + 靶材记号/波长交叉校验 |
| `_fmt_pair` 两列粘连 | 合成 | 正常行字节一致；强度占满 10 字符场宽时补分隔符；端到端 `np.loadtxt` 仍能读到 2 列 |
| GSAS-II 系格式 | 14 个合成样本 + GSAS-II 本体 oracle | 5 类格式（FXYE/FXY/ESD/STD、FullProf、ras/rasx、xye/qye、chi/qchi）逐点读入正确；TOF(TIME_MAP) 明确拒绝；自写两列 `.dat` 仍按纯文本读（FP 误判守卫） |
| 三语一致性 | i18n 三张表 | 139 个 key 三表齐平；占位符同名同数量且每条都能 `format` 通；占位符不与 `tr()` 形参撞名；格式名/目标格式名三语均有译文；抽 6 条核心文案做「三语互不相同」守卫 |

### 4.2 真值从哪来（后续加格式时的关键）

- `D:/Project/XRD/XRData/` 是真机样本库：`smz geshi/`（13 对岛津 `.RAW`↔PCXRD ASCII `.txt`，**最强真值**）、`Shimadzu Data/`（72 RAW + 各子目录 txt/）、`csuHJW/`、`IUCr/`；`D:/Project/XRD/test_xrd/geshi/`（含 4-1.mdi/.raw 等）。
- 对拍方法：正则抽取 ASCII Dump 的 `<2Theta> <I>`（或 `<Theta> <I>`）两列 → 与解析结果 `np.array_equal(强度)` + `max|Δ2θ| < 1e-6`。θ 单轴扫描（QiangLin.RAW）按 θ 原轴对拍。
- 注意：各目录下的 `txt/` 子文件夹是主项目批量转换的**产物**（循环依赖），不能当真值；只有厂商原始 ASCII Dump 可当真值。

### 4.3 分层验收流水线（每步必跑）

```bash
venv/Scripts/python.exe tests/validate_samples.py   # 1) 全量断言（需 XRData 在位）
venv/Scripts/python.exe tests/smoke_gui.py          # 2) GUI 离屏冒烟 50 项
# 3) 冻结 exe（构建后）：--selftest 真样本 --report out.txt，exit 0 + RESULT ok=N
./dist/PolyXRDConverter.exe --selftest "样本A" "样本B" --report selftest_report.txt
# 4) GUI 存活冒烟：启动 exe → 12s 后 tasklist 有进程 → taskkill
# 5) 发版后：Release 资产回下载，SHA-256 与本地一致
```

GUI 冒烟覆盖：拖放探测/格式识别/预览出图/转换落盘回读守恒/状态灯/三语切换/清空。

---

## 5. 当前进展（截至 2026-10-12）

| 版本 | 日期 | commit | 内容 | 验证 |
|---|---|---|---|---|
| v1.0.0 | 2026-10-09 | `5ffe15e` | 初版：多厂商 RAW 魔数识别 + 全部读写格式 + GUI 批量/预览/手动轴 + 双语 | 243 断言 + 冒烟 40 |
| v1.1.0 | 2026-10-10 | `86d27cd` | **岛津 .RAW 解析精度升级**：截断文件防护（钳点数+`truncated` 全链路透出）、截断轴强制转人工、「end 差一步长」约定精确化 | 247 断言 + 冒烟 40 + 主项目对拍 206 文件强度全等 + smz geshi 13 对逐点全等 |
| v1.2.0 | 2026-10-10 | `4b33f48` | **P1 + P2**：修复 `writers._fmt_pair` 两列粘连（高强度/大整数样本不再塌缩成单列）；新增 θ 单轴摇摆扫描 GUI 提示 | 252 断言 + 冒烟 40 + 冻结 exe 真样本自检 10/10 全过 |
| v1.3.0 | 2026-10-10 | `bf6707a` | **GSAS-II 系格式移植**：新增 gsas / fp_dat / ras(.rasx) / xye / chi 五类文本读取器（格式知识参考 GSAS-II 开源 importer，按其许可注明来源） | 311 断言 + 冒烟 40 + 冻结 exe 自检 10/10；另与 GSAS-II 本体 oracle 对拍 |
| v1.4.0 | 2026-10-12 | `fc11da4` | **界面三语化 + 即时切换**：新增日本語；原来切语言只改全局量、控件要重启才更新，现由 `_retranslate_ui()` 重译菜单/控件/清单/预览；格式名与目标格式名改由 key 动态翻译；读取层 30 条报错全部入表 | 607 断言（含三语一致性专项）+ 冒烟 50 + 冻结 exe 自检 10/10 |

**发布状态**：v1.4.0 已推送 GitHub 并发布 Release（exe + SHA256，哈希回下载闭环一致）。工作树干净（仅 `.workbuddy/` 未跟踪），无未推送提交，无遗留任务。

**文档同步状态（2026-10-12 全量核对）**：README（版本/下载/三语/文档入口）、本文、GitHub 仓库简介与 topics、各版本 Release 正文均已对齐 v1.4.0；顺带修掉 v1.3.0/v1.4.0 Release 里误写的「MIT」许可口径（见 §8 备忘）。

**GSAS-II oracle 对拍**（v1.3.0 一次性验证，结论沉淀在此）：用 `C:/gsas2main/python.exe` + `sys.path` 指其 `GSAS-II` 目录可调 GSAS-II 的 importer 当参考实现；14 个合成样本中 **10 个与 GSAS-II 逐点全等（dx=dy=0）**，4 个 SKIP 均为 GSAS-II 自身缺陷（见 §6.4）。

**验证能力现状**：XRData 全库 305 个岛津容器文件解析成功（26 个真实截断全部正确标记拦截、1 个零点截断明确报错）；岛津解析与主项目 `DataLoader._load_shimadzu_raw` 强度 100% 全等。

---

## 6. 踩坑与经验教训（接手者重点阅读）

### 6.1 岛津 .RAW 格式逆向（核心资产，写在 ShimadzuRawParser 类注释里）

1. **旧误判教训**（主项目早期踩过）："0xCDCDCDCD 填充、缺起始角、不可解析"——错在把变长头当定长 968。真实结构：**变长头（968/976/1608 字节三子类型，头里嵌入源路径时更长）**，数据块位置必须用头里 `u32@0x30+56` 与文件长度互校。
2. **截断静默损坏**：旧实现用 `len - nbytes` 尾推数据块，截断文件会把头部字节当强度读进来且无任何标记 → 现以声明偏移为准、钳到可用点数并标 `truncated`。
3. **反推的自满足陷阱**：`(end-start)/(n-1)` 反推步长对**任意 n 都能过 5% 容差**（构造上恒成立），截断文件上会把轴拉伸误标可信 → 截断时必须强制轴不可信。凡"用结果验证自己"的判据都要警惕。
4. **两种 end 约定**：`end = start + step×(n-1)` 与 `end = start + step×n`（端点不含）并存。**统一按 (end-start)/(N-1) 重排会在后者上产生固件不可能的步长**（实测 0.05 被拉伸成 0.05063291，末端峰位错 0.05°）——以头里步长字段为准（自洽闭合即接受，两种约定都吃）。
5. **步长字段 4 位小数截断**（Search.RAW：头里 0.0213 实际 0.0212644）→ 点数自洽校验失败时才允许反推。
6. **波长字段会过期**（Cr 靶残留 Cu 1.5406）→ 以靶材元素记号（@0xDC）查表优先，波长字段兜底。
7. **峰表不是谱图**：`0x20` 记录类型 21~25（PKR/PKK/PKS/PSE/PKF）内含峰位/峰强清单，当谱图解析会造出完全虚假的曲线 → 明确报错拒绝并提示改用同目录 .RAW。
8. **θ 单轴摇摆扫描**（QiangLin.RAW 记录轴是 θ）：二进制**无标志位**，只有配对 ASCII 的列头 `<Theta>` vs `<2Theta>` 能判。转换器定位是保留原轴照转；主项目用 `theta_mode=True` ×2 折算。将来若要自动判别需外部信息。
9. **浮点/定点噪声归一**：×1e4 定点与 float32 都有存储噪声（0.02→0.0199999…），乘几千个序号累积漂移可达 3e-6° → 统一 `float(f"{v:.8g}")` 抹噪。

### 6.2 写出格式

10. ⚠ 历史上的已知隐患（P1，**已于 2026-10-10 修复**，见 §7）：原 `writers._fmt_pair` 两列**定宽无分隔符**，强度占满 10 字符场宽时前导空格消失 → 输出单列，下游 `np.loadtxt` 报 "columns changed"。主项目 `pattern_convert.py` 同款 bug 已在 commit `b0fdec7` 修复（仅溢出时补显式分隔符），**移植时必须保住"与原厂文件字节一致"的往返测试**——无脑加空格会打破它们。
11. Windows 文本模式写 CRLF 必须 `open(..., newline="")`，否则 `\n` 再翻成 `\r\n` 产出 `\r\r\n` 坏行尾。

### 6.3 工程与环境

12. **中文 build.bat + Git Bash 管道 = 解析灾难**：`echo. | cmd //c build.bat` 会把 UTF-8 bat 拆成碎片乱执行。改分步跑：`build_icon.py` → `PyInstaller spec --noconfirm` → 手工算 SHA-256。
13. **GitHub 间歇性 SNI 阻断**（TLS reset + DNS 超时，baidu 却正常）：DoH（`https://223.5.5.5/resolve?name=github.com&type=A`）可解析 IP 但直连仍被 reset → 只能等自愈；期间 `python urllib` 通道可能比 curl 更可用；token 用 `git credential fill` 从凭据库取（离线可用）。本机 2080 端口的 `NodeBabyLinkService.exe` 是加速器不是通用代理，别当代理用。
14. 图标重新生成（`build_icon.py`）字节幂等，不产生 git diff。
15. 主项目移植经验（同样适用本项目）：批量输出同主名冲突会**永久振荡**（两源互相覆盖互判陈旧）；"已存在就跳过"的幂等会永久保留坏数据，应升级为"陈旧自检"（比对点数/轴/强度不一致才重写）。

### 6.4 GSAS-II 系格式移植（v1.2.0 之后，§6 只增不删）

16. **GSAS-II 本体可当对拍 oracle**：`C:/gsas2main/python.exe` + `sys.path` 指向 `C:/gsas2main/GSAS-II` 即可脱离 GUI 调 `GSASII.imports.*ReaderClass` 的 ContentsValidator/Reader；合成样本"双实现逐点对拍"是最强验收（比纯合成断言强一档）。
17. **GSAS-II 参考实现的四个坑**（我们均规避）：① STD 分支 `Nch=int(cons[2])` 对 "BANK 1 STD …" 直接 `int('STD')` 崩溃；② Fit2D 头 `Array: chi_2theta` 会被其误判为 pyFAI minimalHeader，导致 Reader 把首行标题当数据解析失败；③ rasx 的 `Profile0.txt` **硬编码 `seek(3)` 跳 BOM**（真文件带 UTF-8 BOM；我们用 `utf-8-sig` 有 BOM 剥、无 BOM 不坏）；④ `.qchi` 波长提取 `S.split()[1:]` 对 `# q λ` 三段式注释取到 '#' 而越界。我们的 chi 数据行提取为"全文件恰好两列数值行"，头行数不硬编码（硬编码 `lines[4:]` 会丢 pyFAI 两行头文件的前两个数据点——oracle 对拍踩过）。
18. **`/* */` 单行注释的 got_c 置位缺陷**：GSAS-II 的 FP reader/validator 遇单行 `/* … */` 会把块注释态永久置位、吞掉后续所有行；本实现检测 `*/` 是否同行再决定是否进入块注释态。
19. **`.dat` 四义判定顺序**（detect_format）：Jade 两行头 → GSAS BANK → FullProf 头（需全量数据做 `start+step*(n-1)≈stop` 自洽校验，4KB 头嗅探不够）→ 普通两列文本。自写两列 `.dat` 的往返守恒是回归基线（FP 误判守卫）。

### 6.5 三语化与发布侧（v1.4.0，§6 只增不删）

20. **文案占位符绝不能叫 `{key}`**：`tr(key, **kwargs)` 的第一个形参就叫 `key`，`tr("err.unsupported_target", key="xyz")` 会直接抛 `TypeError: got multiple values for argument 'key'` —— 而且只在这个冷门分支被走到时才炸，肉眼审不出来。现统一改名 `{fmt}`，并在 `validate_i18n()` 里加了「占位符不与 tr() 形参撞名」的断言；另加「三张表 key 集合齐平 + 占位符同名同数量 + 每条都能 format 通」三项守卫 —— 漏 key 时 `tr()` 会静默回退中文，日语界面蹦中文极难被人眼发现，必须机器把关。
21. **别把展示名写死在数据声明里**：原先 `loader.FORMAT_LABELS` 和 `writers.TARGET_FORMATS` 的第三项是中文成品文案，多语言下必然漂移。现一律改成 i18n key（`fmt.*` / `tgt.*`），由 UI 在显示时用 `fmt_label()` / `tr()` 解析；Detector 返回值仍是成品文案（对外契约不变），便于日志与自检报告。
22. **切语言要"即时生效"就得重译，不能只改全局量**：旧实现 `set_language()` 后只更新了菜单勾选态，控件文案是构造时用 `tr()` 写的，必须重启。解法是 `MainWindow._retranslate_ui()`：重建菜单栏 + 逐个 setText + 重填目标格式下拉（先存 `currentData` 再回填）+ `_refresh_table()` / `_update_preview()`。凡是在构造期就用 `tr()` 定死的 UI 文案，加语言前必须先确认有这条重译通路。
23. **Release 上传资产的 URL 不能拼 `api.github.com` 前缀**：`POST /repos/.../releases` 返回的 `upload_url` 主机已是 `uploads.github.com`，再拼前缀会得到 `https://api.github.comhttps://uploads.github.com/...`，报错却是看不出根因的 `getaddrinfo failed`。脚本要支持绝对 URL；Release 已存在时应按 tag 先查、存在则复用并 PATCH 正文，避免重复创建留下空 Release。
24. **`tasklist //FI "IMAGENAME eq xxx.exe"` 会把进程名截到 25 字符**：`PolyXRDConverter-v1.3.0.exe` 被截成 `PolyXRDConverter-v1.3.0.e`，过滤器查不到（会误判成"启动即退出"）。存活冒烟改用 `tasklist | grep -i polyxrd`，清理用 `taskkill //IM <全名> //F`。

---

## 7. 已知问题与下一步计划

| 优先级 | 事项 | 说明 |
|---|---|---|
| ~~**P1**~~ ✅ 已解决 (2026-10-10) | `writers._fmt_pair` 两列粘连修复 | 照搬主项目 `b0fdec7` 思路：仅当 y 字段首字符非空格（占满 10 字符场宽，如 `126727.648` 或 10 位整数）时补一个显式分隔空格；正常样本保持与原厂字节一致。新增 P1 回归 5 项（`tests/validate_samples.py::validate_fmt_pair`）；`validate` 252/252、冒烟 40/40 全绿 |
| ~~P2~~ ✅ 已解决 (2026-10-10) | θ 单轴扫描的用户提示 | 二进制无法自动判别；已在 `i18n.tip.rocking_scan`（中/英/日）新增文案，并透出到手动定轴对话框、坏轴状态 tooltip、坏轴预览说明三处轴提示 |
| ~~P3~~ ◐ 部分完成 (2026-10-10) | 新厂商格式 | **GSAS-II 系文本格式已入**（gsas/fp_dat/ras/xye/chi，含 GSAS-II oracle 对拍）；Bruker RAW v2/v3、理学 RAS 二进制等仍按用户样本再逆向；流程见 §3/§4 |
| P4 | 发版流程脚本化 | 把 §4.3 流水线 + Release 脚本（幂等：tag 已存在跳过、资产 sha256 比对）固化为 tools/release.py |

---

## 8. 备忘

- **仓库/远程**：`github.com/PolyXRD/PolyXRD-Converter.git`（HTTPS），凭据走 git credential store；Release 仅发 exe + SHA256。
- **文档清单（改版本号/加格式时，这几处要一起改）**：① `README.md`（功能/版本下载/验证断言数）；② 本文（§1 能力矩阵、§4.1 断言数与验收块、§4.3 冒烟项数、§5 进展表、§7 已知问题）；③ `pyproject.toml`（description / keywords）；④ GitHub 仓库简介与 topics；⑤ 新版本的 Release 正文。
- **许可口径（别写错）**：本项目是**双许可**（学术研究/教学免费，商业用途须单独书面授权），**不是 MIT**。v1.3.0 / v1.4.0 的 Release 正文曾误写成 "MIT（见 LICENSE）"，2026-10-12 已纠正；写 Release/文档时照抄 `README.md` 的「许可」一节最稳。GSAS-II 系读取器另有上游署名要求（UChicago Argonne, LLC）。。
- **本地路径**：项目 `D:/Project/XRD/PolyXRD-Converter`；真机样本 `D:/Project/XRD/XRData`、`D:/Project/XRD/test_xrd`；主项目 `D:/Project/XRD/PolyXRD`（其 venv 可用于跨项目对拍，numpy 兼容）。
- **环境**：项目自带 `venv/`（Python 3.10.11，numpy + PySide6 + pyinstaller）；Git Bash 为主 shell；Python 一律 `venv/Scripts/python.exe`。
- **构建**：`build.bat`（或分步）→ `dist/PolyXRDConverter.exe`；版本号单源 `src/polyxrd_converter/__init__.py`，build.bat 动态读取。
- **常用命令**：见 §4.3。VERBOSE=1 可看逐条断言。
- **协作红线**：commit/push 需用户批准；commit 信息"更新代码修正：…"、不含竞品字样；push 后 `git ls-remote` 校验 HEAD；文档变更先审阅再入库。
- **本文档维护**：随版本更新"当前进展"与"已知问题"两节即可，§6 踩坑只增不删。
