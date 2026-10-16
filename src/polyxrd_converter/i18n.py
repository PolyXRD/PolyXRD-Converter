"""
极简 i18n
=========
本工具有中/英/日三套文案, 用三个字典直接查表, 不引入 Qt Linguist 那套重流程。

维护约定（重要）
--------------
1. **三张表的 key 必须完全一致**。``tests/validate_samples.py`` 里有专门的断言做
   key 集合 / 占位符对齐检查；漏 key 时会静默回退到中文，肉眼很难发现。
2. 文案里的 ``{xxx}`` 占位符在三张表里必须同名、同数量，否则 ``tr(key, ...)``
   会抛 ``KeyError``。**占位符不能叫 ``{key}``** —— ``tr(key, ...)`` 的第一个形参
   就叫 ``key``，``{key}`` 会撞成 "got multiple values for argument 'key'"
   （本表的 ``err.unsupported_target`` 踩过一次，现用 ``{fmt}``）。
   该约束由 ``tests/validate_samples.py::validate_i18n`` 机器把关。
3. 添加新 key 的顺序：先写 ZH（源语言），再补 EN / JA。
4. 语言名称用 **母语写法**（简体中文 / English / 日本語），切换菜单不翻译所谓的
   "语言名"，用户看不懂目标语言时也能靠母语认路。
"""
from __future__ import annotations

from typing import Any

ZH: dict[str, str] = {
    "app.title": "PolyXRD Converter — XRD 谱图格式转换器",
    "app.subtitle": "XRD 谱图格式互转（支持多种厂商 RAW 自动识别）",

    "menu.file": "文件(&F)",
    "menu.file.add": "添加文件…",
    "menu.file.add_dir": "添加文件夹…",
    "menu.file.exit": "退出",
    "menu.lang": "语言(&L)",
    "menu.help": "帮助(&H)",
    "menu.help.about": "关于",
    "menu.help.copyright": "版权",
    "statusbar.internal": "内部评估版本",

    "lang.zh": "简体中文",
    "lang.en": "English",
    "lang.ja": "日本語",

    "btn.add_files": "添加文件",
    "btn.add_dir": "添加文件夹",
    "btn.remove": "移除选中",
    "btn.clear": "清空列表",
    "btn.convert": "开始转换",
    "btn.open_out": "打开输出目录",
    "btn.browse": "浏览…",
    "btn.view": "预览",

    "col.file": "文件",
    "col.format": "识别格式",
    "col.points": "点数",
    "col.range": "2θ 范围 (°)",
    "col.peak": "最强峰",
    "col.status": "状态",

    "lbl.target": "目标格式：",
    "lbl.outdir": "输出目录：",
    "lbl.outdir_same": "（与源文件同目录）",
    "lbl.overwrite": "覆盖同名文件",
    "lbl.preview": "谱图预览",
    "lbl.log": "转换日志",
    "lbl.filecount": "{n} 个文件",
    "lbl.empty_hint": "把 .raw / .xy / .txt / .dat / .csv / .mdi / .xrdml / .brml / .gsas / .ras 等谱图文件拖到这里，或点「添加文件」",

    "status.ready": "待转换",
    "status.ok": "已转换",
    "status.fail": "失败",
    "status.bad_axis": "需手动指定角度轴",
    "status.truncated": "文件不完整",
    "status.read_error": "无法读取",

    "tip.axis_warn": (
        "⚠ 该文件的角度轴不可信（文件头缺参数或参数异常）。\n"
        "已可靠取出 {n} 个强度点；请在列表里右键 →「手动指定角度轴」填入起始 2θ 与步长后再转换。"
    ),
    "tip.truncated": (
        "⚠ 文件不完整：头部声明 {declared} 个点，实际只读出 {kept} 个点"
        "（文件很可能被截断/传输不完整）。\n"
        "已按实际可用的数据转换；如需完整谱图请重新导出/传输该文件。"
    ),
    "tip.axis_manual": "当前使用手动指定的角度轴：起始 {x0}°，步长 {step}°",
    "tip.rocking_scan": (
        "若此文件是 θ 单轴摇摆 / 极图扫描（记录轴为 θ 而非 2θ），请在上方填 θ "
        "起始与步长；转换器按原轴照转，不会自动折算成 2θ，转换前请核对。"
    ),
    "tip.lang_switched": "界面语言已切换为「{lang}」，已立即生效。",
    "tip.multi_preview": "(已选 {n} 个文件，只预览第一个)",

    "ctx.open_dir": "打开所在文件夹",

    "dlg.axis.title": "手动指定角度轴",
    "dlg.axis.hint": (
        "文件 {name} 的角度轴无法自动确定。\n"
        "已取出 {n} 个强度点，请给出扫描的起始 2θ 与步长。"
    ),
    "dlg.axis.start": "起始 2θ (°)：",
    "dlg.axis.step": "步长 (°)：",
    "dlg.axis.end": "推算终止 2θ：{end}°",

    "dlg.warning": "提示",
    "dlg.error": "错误",
    "dlg.info": "完成",
    "dlg.confirm": "确认",
    "dlg.no_selection": "请先在列表里选中一个文件。",
    "dlg.need_files": "请先添加至少一个文件。",
    "dlg.overwrite_q": "下列 {n} 个目标文件已存在，是否覆盖？",
    "dlg.axis_invalid": "起始 2θ / 步长 必须是正数，且起始 + 步长×(点数-1) 不超过 180°。",
    "dlg.about": (
        "<b>PolyXRD Converter</b> v{version}<br><br>"
        "XRD 谱图格式互转工具，从 PolyXRD 中独立剥离。<br>"
        "读取：xy / txt / dat / csv / mdi / xrdml / brml / json，"
        "GSAS (.gsas/.fxye/.gda)、FullProf .dat、Rigaku .ras/.rasx、"
        "Topas .xye/.qye、Fit2D .chi/.qchi，"
        "以及多种厂商二进制 RAW（自动识别魔数）：<br>"
        "· 岛津 Shimadzu XRD（.RAW/.ORG/.RSM/.RBG/.RK1/.RAX/.RLZ/.RFI）<br>"
        "· 理学 Rigaku RINT（FI）<br>· Scintag RAW2<br>· Bruker/Siemens RAW v1（RAW1.01）<br>"
        "· MDI / Jade 文本导出（两行头单列强度）<br><br>"
        "写出：xy / txt / dat / csv / mdi / raw / xrdml / json<br>"
        "依赖 numpy + PySide6。<br><br>"
        "界面语言：简体中文 / English / 日本語（菜单栏「语言」即时切换）<br><br>"
        "PolyXRD Team · 2025 — 2026<br>"
        "联系：<a href='mailto:sshztx@outlook.com'>sshztx@outlook.com</a> · "
        "<a href='https://github.com/PolyXRD'>github.com/PolyXRD</a>"
    ),

    "log.summary": "完成：成功 {ok} 个，失败 {fail} 个。",
    "log.converted": "✓ {src} → {dst}",
    "log.failed": "✗ {src}: {err}",
    "log.progress": "正在转换 {i}/{n}：{name}",
    "log.no_files": "没有可转换的文件。",
    "log.batch": "→ {n} 个文件 → {fmt}",

    "preview.empty": "—  选择左侧文件即可预览  —",

    "err.crash_title": "PolyXRD Converter — 未处理异常",
    "err.file_missing": "文件不存在：{path}",
    "err.empty_file": "空文件：{path}",
    "err.jade_report": (
        "{path} 是 JADE/PDF 物相识别报告，不含衍射强度数据；"
        "请改用对应的 .raw / .mdi / .xy 原始谱图文件。"
    ),
    "err.no_numeric": "文件 {path} 中没有有效数值数据",
    "err.mdi_too_short": "MDI 文件内容不足：{path}",
    "err.mdi_head": "MDI 文件头无法解析 start/step：{path}",
    "err.mdi_no_data": "MDI 文件没有有效强度数据：{path}",
    "err.q_out_of_range": (
        "Q 值超出波长 λ={wavelength}Å 的可换算范围（λQ/4π 最大 {vmax} > 1）；"
        "波长注释可能不对，请核对后重试。"
    ),
    "err.gsas_tof": (
        "{name} 是中子飞行时间 (TOF) GSAS 数据（含 TIME_MAP），"
        "横轴是飞行时间而不是 2θ；本工具不支持。"
    ),
    "err.gsas_no_bank": "GSAS 文件没有 BANK 记录：{path}",
    "err.gsas_eds_alt": (
        "{name} 是能量色散 (EDS) 或飞行时间类 (ALT) GSAS 数据，"
        "横轴不是 2θ；本工具不支持。"
    ),
    "err.gsas_esd_fields": "ESD bank 缺 start/step 字段：{line}",
    "err.gsas_std_fields": "STD bank 缺 start/step 字段：{line}",
    "err.gsas_too_short": "GSAS 文件有效数据点不足：{path}",
    "err.fp_no_data": "FullProf .dat 没有有效数据（缺 start/step/stop 头？）：{path}",
    "err.rasx_no_member": "rasx 里找不到 Profile*.txt 成员：{path}",
    "err.rasx_bad_zip": "rasx 不是合法 ZIP：{path}（{exc}）",
    "err.ras_no_marker": "不是 Rigaku .ras 文件（缺 *RAS_DATA_START）：{path}",
    "err.ras_no_rows": "Rigaku .ras/.rasx 没有有效数据行：{path}",
    "err.xye_no_wavelength": (
        "{name} 是 Q 轴 .qye 文件，但注释里没有 '#wavelength <λ>' 行，"
        "无法换算成 2θ；请在文件头补一行 '#wavelength <波长Å>'。"
    ),
    "err.xye_no_rows": "xye/qye 文件没有有效数据行：{path}",
    "err.chi_not_fit2d": "不是 Fit2D .chi 文件（头 4 行里没有 2-theta/q 标识）：{path}",
    "err.chi_no_wavelength": (
        "{name} 是 Q 轴 .qchi 文件，但头里没给波长（应为 'q <λ>' 形式），无法换算成 2θ。"
    ),
    "err.chi_no_rows": "chi 文件没有有效数据行：{path}",
    "err.xrdml_xml_fail": "XML 解析失败：{path}（{exc}）",
    "err.xrdml_no_data": "无法从 XRDML 文件提取 2θ / 强度数据：{path}",
    "err.brml_no_xml": "BRML 文件里找不到 XML 数据：{path}",
    "err.brml_bad_zip": "BRML 解析失败（不是合法 ZIP）：{path}（{exc}）",
    "err.brml_xml_fail": "BRML 内 XML 解析失败：{path}（{exc}）",
    "err.brml_no_data": "无法从 BRML 文件提取数据：{path}",
    "err.json_parse_fail": "JSON 解析失败：{path}（{exc}）",
    "err.json_not_pattern": "{path} 不是谱图 JSON（缺 two_theta 字段）",
    "err.read_failed": "读取 {name} 失败：{exc}",
    "err.unsupported_target": "不支持的导出格式：{fmt}",
    "err.same_file": "输出文件与源文件是同一个文件，会覆盖源文件：{dst}",
    "err.too_few_points": "数据点不足，无法写入等间距格式",
    "err.not_equidistant": "数据不是等间距 2θ，无法写入 MDI/RAW2；请改用 .xy/.txt/.dat/.csv",
    "err.axis_required": (
        "{name}: 识别为 {variant}，已取出 {n} 个强度点但**角度轴不可信**；"
        "请右键该文件「手动指定角度轴」后再转换。"
    ),

    # ---- 读取侧格式名 (key 与 loader.FORMAT_LABELS 的值同名) ----
    "fmt.xy": "文本两列 (.xy)",
    "fmt.txt": "文本 (.txt)",
    "fmt.dat": "文本 (.dat)",
    "fmt.csv": "CSV (.csv)",
    "fmt.smz": "文本 (.smz)",
    "fmt.mdi": "MDI / Jade (.mdi)",
    "fmt.jade_txt": "MDI / Jade 文本导出 (.txt)",
    "fmt.gsas": "GSAS 粉末数据 (.gsas/.fxye/.gda)",
    "fmt.fp_dat": "FullProf .dat",
    "fmt.ras": "理学 Rigaku .ras/.rasx",
    "fmt.xye": "Topas .xye/.qye",
    "fmt.chi": "Fit2D .chi/.qchi",
    "fmt.xrdml": "Bruker XRDML (.xrdml/.xml)",
    "fmt.brml": "Bruker BRML (.brml)",
    "fmt.json": "PolyXRD 谱图 JSON (.json)",
    "fmt.shimadzu_txt": "岛津 ASCII 导出 (.txt/.asc)",
    "fmt.raw": "RAW 二进制",
    "fmt.rigaku_raw": "理学 Rigaku RAW (RINT/SmartLab, FI)",
    "fmt.scintag_raw2": "Scintag RAW2",
    "fmt.bruker_raw_v1": "Bruker/Siemens RAW v1",
    "fmt.shimadzu_raw": "岛津 Shimadzu XRD RAW",
    "fmt.raw_generic": "未知 RAW 变体",

    # ---- 写出侧格式名 (key 为 "tgt." + TARGET_FORMATS 的 key) ----
    "tgt.xy": "两列文本 2θ/I (.xy)",
    "tgt.txt": "两列文本 2θ/I (.txt)",
    "tgt.dat": "两列文本 2θ/I (.dat)",
    "tgt.csv": "CSV 带表头 (.csv)",
    "tgt.mdi": "MDI / Jade (.mdi)",
    "tgt.raw": "RAW2 二进制 (.raw)",
    "tgt.xrdml": "Bruker XRDML (.xrdml)",
    "tgt.json": "PolyXRD 谱图 JSON (.json)",

    "filter.open": "XRD 谱图 (*.raw *.RAW *.org *.rsm *.rbg *.rk1 *.rax *.rlz *.rfi *.xy *.txt *.TXT *.dat *.csv *.mdi *.xrdml *.xml *.brml *.json *.gsas *.fxye *.gda *.gsa *.gss *.ras *.rasx *.xye *.qye *.chi *.qchi);;所有文件 (*)",
    "filter.dirtitle": "选择包含谱图文件的文件夹",
}

EN: dict[str, str] = {
    "app.title": "PolyXRD Converter — XRD Pattern Format Converter",
    "app.subtitle": "Convert XRD patterns between formats (multi-vendor RAW auto-detection)",

    "menu.file": "&File",
    "menu.file.add": "Add files…",
    "menu.file.add_dir": "Add folder…",
    "menu.file.exit": "Exit",
    "menu.lang": "&Language",
    "menu.help": "&Help",
    "menu.help.about": "About",
    "menu.help.copyright": "Copyright",
    "statusbar.internal": "Internal Evaluation Build",

    "lang.zh": "简体中文",
    "lang.en": "English",
    "lang.ja": "日本語",

    "btn.add_files": "Add files",
    "btn.add_dir": "Add folder",
    "btn.remove": "Remove selected",
    "btn.clear": "Clear list",
    "btn.convert": "Convert",
    "btn.open_out": "Open output folder",
    "btn.browse": "Browse…",
    "btn.view": "Preview",

    "col.file": "File",
    "col.format": "Detected format",
    "col.points": "Points",
    "col.range": "2θ range (°)",
    "col.peak": "Max peak",
    "col.status": "Status",

    "lbl.target": "Target format:",
    "lbl.outdir": "Output folder:",
    "lbl.outdir_same": "(same as source file)",
    "lbl.overwrite": "Overwrite existing",
    "lbl.preview": "Pattern preview",
    "lbl.log": "Log",
    "lbl.filecount": "{n} files",
    "lbl.empty_hint": "Drag .raw / .xy / .txt / .dat / .csv / .mdi / .xrdml / .brml / .gsas / .ras files here, or click “Add files”.",

    "status.ready": "Pending",
    "status.ok": "Converted",
    "status.fail": "Failed",
    "status.bad_axis": "Needs manual axis",
    "status.truncated": "Truncated file",
    "status.read_error": "Unreadable",

    "tip.axis_warn": (
        "⚠ The 2θ axis of this file is not trustworthy (header missing/invalid).\n"
        "{n} intensity points were read reliably; right-click the row → "
        "“Specify 2θ axis manually” before converting."
    ),
    "tip.truncated": (
        "⚠ Incomplete file: header declares {declared} points, but only {kept} points "
        "could be read (the file is likely truncated / incompletely transferred).\n"
        "Converted with the actually available data; re-export/re-transfer the file "
        "if you need the full pattern."
    ),
    "tip.axis_manual": "Using manual axis: start {x0}°, step {step}°",
    "tip.rocking_scan": (
        "If this file is a θ single-axis rocking / pole-figure scan (recorded axis is "
        "θ, not 2θ), enter the θ start and step above if possible; the converter "
        "preserves the original axis and will not auto-convert it to 2θ — please "
        "verify before converting."
    ),
    "tip.lang_switched": "Language switched to “{lang}” (applied immediately).",
    "tip.multi_preview": "({n} files selected; previewing the first)",

    "ctx.open_dir": "Open containing folder",

    "dlg.axis.title": "Specify 2θ axis manually",
    "dlg.axis.hint": (
        "The 2θ axis of {name} could not be determined automatically.\n"
        "{n} intensity points were read. Please provide the start 2θ and step."
    ),
    "dlg.axis.start": "Start 2θ (°):",
    "dlg.axis.step": "Step (°):",
    "dlg.axis.end": "Implied end 2θ: {end}°",

    "dlg.warning": "Warning",
    "dlg.error": "Error",
    "dlg.info": "Done",
    "dlg.confirm": "Confirm",
    "dlg.no_selection": "Please select a file in the list first.",
    "dlg.need_files": "Please add at least one file.",
    "dlg.overwrite_q": "{n} output file(s) already exist. Overwrite?",
    "dlg.axis_invalid": "Start 2θ / step must be positive, and start + step×(n-1) must not exceed 180°.",
    "dlg.about": (
        "<b>PolyXRD Converter</b> v{version}<br><br>"
        "XRD pattern format converter, extracted from PolyXRD.<br>"
        "Reads: xy / txt / dat / csv / mdi / xrdml / brml / json, GSAS (.gsas/.fxye/.gda), "
        "FullProf .dat, Rigaku .ras/.rasx, Topas .xye/.qye, Fit2D .chi/.qchi, plus several "
        "vendor binary RAW formats (magic-based auto-detection):<br>"
        "· Shimadzu XRD (.RAW/.ORG/.RSM/.RBG/.RK1/.RAX/.RLZ/.RFI)<br>"
        "· Rigaku RINT (FI)<br>· Scintag RAW2<br>"
        "· Bruker/Siemens RAW v1 (RAW1.01)<br>"
        "· MDI / Jade text export (two-line header, single-column counts)<br><br>"
        "Writes: xy / txt / dat / csv / mdi / raw / xrdml / json<br>"
        "Requires numpy + PySide6.<br><br>"
        "UI language: 简体中文 / English / 日本語 (switch anytime from the "
        "<i>Language</i> menu; applied immediately)<br><br>"
        "PolyXRD Team · 2025 — 2026<br>"
        "Contact: <a href='mailto:sshztx@outlook.com'>sshztx@outlook.com</a> · "
        "<a href='https://github.com/PolyXRD'>github.com/PolyXRD</a>"
    ),

    "log.summary": "Finished: {ok} succeeded, {fail} failed.",
    "log.converted": "✓ {src} → {dst}",
    "log.failed": "✗ {src}: {err}",
    "log.progress": "Converting {i}/{n}: {name}",
    "log.no_files": "Nothing to convert.",
    "log.batch": "→ {n} file(s) → {fmt}",

    "preview.empty": "—  Select a file to preview  —",

    "err.crash_title": "PolyXRD Converter — Unhandled exception",
    "err.file_missing": "File not found: {path}",
    "err.empty_file": "Empty file: {path}",
    "err.jade_report": (
        "{path} looks like a JADE/PDF phase-identification report and carries no "
        "diffraction intensities; please use the original .raw / .mdi / .xy scan file."
    ),
    "err.no_numeric": "No valid numeric data found in {path}",
    "err.mdi_too_short": "MDI file too short: {path}",
    "err.mdi_head": "Cannot parse start/step from the MDI header: {path}",
    "err.mdi_no_data": "No valid intensities in the MDI file: {path}",
    "err.q_out_of_range": (
        "Q is out of the convertible range for λ={wavelength}Å "
        "(λQ/4π reaches {vmax} > 1); the wavelength comment is probably wrong — "
        "check it and retry."
    ),
    "err.gsas_tof": (
        "{name} is neutron time-of-flight (TOF) GSAS data (it has TIME_MAP); the x "
        "axis is flight time, not 2θ. Not supported."
    ),
    "err.gsas_no_bank": "No BANK record in the GSAS file: {path}",
    "err.gsas_eds_alt": (
        "{name} is energy-dispersive (EDS) or TOF-type (ALT) GSAS data; the x axis "
        "is not 2θ. Not supported."
    ),
    "err.gsas_esd_fields": "ESD bank lacks start/step: {line}",
    "err.gsas_std_fields": "STD bank lacks start/step: {line}",
    "err.gsas_too_short": "Not enough valid data points in the GSAS file: {path}",
    "err.fp_no_data": (
        "No valid data in the FullProf .dat (missing start/step/stop header?): {path}"
    ),
    "err.rasx_no_member": "No Profile*.txt member inside the rasx archive: {path}",
    "err.rasx_bad_zip": "rasx is not a valid ZIP: {path} ({exc})",
    "err.ras_no_marker": "Not a Rigaku .ras file (missing *RAS_DATA_START): {path}",
    "err.ras_no_rows": "No valid data rows in the Rigaku .ras/.rasx file: {path}",
    "err.xye_no_wavelength": (
        "{name} has a Q axis (.qye), but no '#wavelength <λ>' line was found in the "
        "comments, so it cannot be converted to 2θ; add a '#wavelength <λ in Å>' "
        "line to the file header."
    ),
    "err.xye_no_rows": "No valid data rows in the xye/qye file: {path}",
    "err.chi_not_fit2d": (
        "Not a Fit2D .chi file (no 2-theta/q marker in the first 4 lines): {path}"
    ),
    "err.chi_no_wavelength": (
        "{name} has a Q axis (.qchi) but no wavelength is given in the header "
        "(expected 'q <λ>'), so it cannot be converted to 2θ."
    ),
    "err.chi_no_rows": "No valid data rows in the chi file: {path}",
    "err.xrdml_xml_fail": "XML parsing failed: {path} ({exc})",
    "err.xrdml_no_data": "Cannot extract 2θ / intensity from the XRDML file: {path}",
    "err.brml_no_xml": "No XML data found inside the BRML file: {path}",
    "err.brml_bad_zip": "BRML parsing failed (not a valid ZIP): {path} ({exc})",
    "err.brml_xml_fail": "XML parsing failed inside the BRML container: {path} ({exc})",
    "err.brml_no_data": "Cannot extract data from the BRML file: {path}",
    "err.json_parse_fail": "JSON parsing failed: {path} ({exc})",
    "err.json_not_pattern": "{path} is not a pattern JSON (missing two_theta field)",
    "err.read_failed": "Failed to read {name}: {exc}",
    "err.unsupported_target": "Unsupported export format: {fmt}",
    "err.same_file": "Output file is the same as the source and would overwrite it: {dst}",
    "err.too_few_points": "Not enough data points for an equidistant format",
    "err.not_equidistant": "2θ is not equidistant; cannot write MDI/RAW2. Use .xy/.txt/.dat/.csv instead.",
    "err.axis_required": (
        "{name}: detected as {variant}; {n} intensity points were read but the "
        "**2θ axis is not trustworthy**. Right-click the file → “Specify 2θ axis "
        "manually” before converting."
    ),

    "fmt.xy": "Two-column text (.xy)",
    "fmt.txt": "Text (.txt)",
    "fmt.dat": "Text (.dat)",
    "fmt.csv": "CSV (.csv)",
    "fmt.smz": "Text (.smz)",
    "fmt.mdi": "MDI / Jade (.mdi)",
    "fmt.jade_txt": "MDI / Jade text export (.txt)",
    "fmt.gsas": "GSAS powder data (.gsas/.fxye/.gda)",
    "fmt.fp_dat": "FullProf .dat",
    "fmt.ras": "Rigaku .ras/.rasx",
    "fmt.xye": "Topas .xye/.qye",
    "fmt.chi": "Fit2D .chi/.qchi",
    "fmt.xrdml": "Bruker XRDML (.xrdml/.xml)",
    "fmt.brml": "Bruker BRML (.brml)",
    "fmt.json": "PolyXRD pattern JSON (.json)",
    "fmt.shimadzu_txt": "Shimadzu ASCII export (.txt/.asc)",
    "fmt.raw": "RAW binary",
    "fmt.rigaku_raw": "Rigaku RAW (RINT/SmartLab, FI)",
    "fmt.scintag_raw2": "Scintag RAW2",
    "fmt.bruker_raw_v1": "Bruker/Siemens RAW v1",
    "fmt.shimadzu_raw": "Shimadzu XRD RAW",
    "fmt.raw_generic": "Unknown RAW variant",

    "tgt.xy": "Two-column text 2θ/I (.xy)",
    "tgt.txt": "Two-column text 2θ/I (.txt)",
    "tgt.dat": "Two-column text 2θ/I (.dat)",
    "tgt.csv": "CSV with header (.csv)",
    "tgt.mdi": "MDI / Jade (.mdi)",
    "tgt.raw": "RAW2 binary (.raw)",
    "tgt.xrdml": "Bruker XRDML (.xrdml)",
    "tgt.json": "PolyXRD pattern JSON (.json)",

    "filter.open": "XRD patterns (*.raw *.RAW *.org *.rsm *.rbg *.rk1 *.rax *.rlz *.rfi *.xy *.txt *.TXT *.dat *.csv *.mdi *.xrdml *.xml *.brml *.json *.gsas *.fxye *.gda *.gsa *.gss *.ras *.rasx *.xye *.qye *.chi *.qchi);;All files (*)",
    "filter.dirtitle": "Choose a folder containing pattern files",
}

JA: dict[str, str] = {
    "app.title": "PolyXRD Converter — XRD 回折パターン変換ツール",
    "app.subtitle": "XRD パターンのフォーマット相互変換（各社 RAW を自動判別）",

    "menu.file": "ファイル(&F)",
    "menu.file.add": "ファイルを追加…",
    "menu.file.add_dir": "フォルダーを追加…",
    "menu.file.exit": "終了",
    "menu.lang": "言語(&L)",
    "menu.help": "ヘルプ(&H)",
    "menu.help.about": "バージョン情報",
    "menu.help.copyright": "著作権",
    "statusbar.internal": "内部評価版",

    "lang.zh": "简体中文",
    "lang.en": "English",
    "lang.ja": "日本語",

    "btn.add_files": "ファイルを追加",
    "btn.add_dir": "フォルダーを追加",
    "btn.remove": "選択を削除",
    "btn.clear": "リストをクリア",
    "btn.convert": "変換開始",
    "btn.open_out": "出力フォルダーを開く",
    "btn.browse": "参照…",
    "btn.view": "プレビュー",

    "col.file": "ファイル",
    "col.format": "判別フォーマット",
    "col.points": "点数",
    "col.range": "2θ 範囲 (°)",
    "col.peak": "最大ピーク",
    "col.status": "状態",

    "lbl.target": "出力フォーマット：",
    "lbl.outdir": "出力先フォルダー：",
    "lbl.outdir_same": "（ソースファイルと同じフォルダー）",
    "lbl.overwrite": "同名ファイルを上書き",
    "lbl.preview": "パターンプレビュー",
    "lbl.log": "変換ログ",
    "lbl.filecount": "{n} ファイル",
    "lbl.empty_hint": "ここに .raw / .xy / .txt / .dat / .csv / .mdi / .xrdml / .brml / .gsas / .ras などのパターンファイルをドラッグするか、「ファイルを追加」をクリックしてください",

    "status.ready": "変換待ち",
    "status.ok": "変換済み",
    "status.fail": "失敗",
    "status.bad_axis": "角度軸の手動指定が必要",
    "status.truncated": "ファイル不完全",
    "status.read_error": "読み込み不可",

    "tip.axis_warn": (
        "⚠ このファイルの角度軸は信頼できません（ヘッダーのパラメータ欠落／異常）。\n"
        "強度値は {n} 点、正常に読み出されています。リスト上で右クリック →"
        "「角度軸を手動指定」から開始 2θ とステップを入力してから変換してください。"
    ),
    "tip.truncated": (
        "⚠ ファイル不完全：ヘッダーは {declared} 点を宣言していますが、"
        "実際に読み出せたのは {kept} 点です"
        "（ファイルが途中で切れている／転送が不完全な可能性があります）。\n"
        "利用可能なデータのみで変換します。完全なパターンが必要な場合は、"
        "ファイルを再出力・再転送してください。"
    ),
    "tip.axis_manual": "手動指定の角度軸を使用中：開始 {x0}°、ステップ {step}°",
    "tip.rocking_scan": (
        "このファイルが θ 単軸のロッキングスキャン／極点測定（記録軸が 2θ ではなく θ）"
        "の場合は、上の欄に θ の開始角とステップを入力してください。"
        "本ツールは元の軸をそのまま保持し、自動的に 2θ へ換算しません。"
        "変換前に必ずご確認ください。"
    ),
    "tip.lang_switched": "表示言語を「{lang}」に変更しました（即時に反映されます）。",
    "tip.multi_preview": "({n} ファイル選択中：先頭のみプレビューします)",

    "ctx.open_dir": "ファイルの場所を開く",

    "dlg.axis.title": "角度軸を手動指定",
    "dlg.axis.hint": (
        "ファイル {name} の角度軸を自動判別できませんでした。\n"
        "強度値は {n} 点読み出されています。測定の開始 2θ とステップを入力してください。"
    ),
    "dlg.axis.start": "開始 2θ (°)：",
    "dlg.axis.step": "ステップ (°)：",
    "dlg.axis.end": "終了 2θ（推算値）：{end}°",

    "dlg.warning": "注意",
    "dlg.error": "エラー",
    "dlg.info": "完了",
    "dlg.confirm": "確認",
    "dlg.no_selection": "先にリストからファイルを 1 つ選択してください。",
    "dlg.need_files": "先にファイルを 1 件以上追加してください。",
    "dlg.overwrite_q": "次の {n} 件の出力ファイルは既に存在します。上書きしますか？",
    "dlg.axis_invalid": "開始 2θ / ステップは正の値で、開始 + ステップ×(点数-1) が 180° を超えないようにしてください。",
    "dlg.about": (
        "<b>PolyXRD Converter</b> v{version}<br><br>"
        "PolyXRD から独立抽出した XRD パターンのフォーマット変換ツール。<br>"
        "読み込み：xy / txt / dat / csv / mdi / xrdml / brml / json、"
        "GSAS (.gsas/.fxye/.gda)、FullProf .dat、Rigaku .ras/.rasx、"
        "Topas .xye/.qye、Fit2D .chi/.qchi、および各社バイナリ RAW"
        "（マジックナンバーによる自動判別）：<br>"
        "· 島津 Shimadzu XRD（.RAW/.ORG/.RSM/.RBG/.RK1/.RAX/.RLZ/.RFI）<br>"
        "· 理学 Rigaku RINT（FI）<br>· Scintag RAW2<br>"
        "· Bruker/Siemens RAW v1（RAW1.01）<br>"
        "· MDI / Jade テキスト出力（2 行ヘッダー＋強度 1 列）<br><br>"
        "書き出し：xy / txt / dat / csv / mdi / raw / xrdml / json<br>"
        "依存パッケージ：numpy + PySide6。<br><br>"
        "表示言語：简体中文 / English / 日本語（メニューバー「言語」から即時切替）<br><br>"
        "PolyXRD Team · 2025 — 2026<br>"
        "連絡先：<a href='mailto:sshztx@outlook.com'>sshztx@outlook.com</a> · "
        "<a href='https://github.com/PolyXRD'>github.com/PolyXRD</a>"
    ),

    "log.summary": "完了：成功 {ok} 件、失敗 {fail} 件。",
    "log.converted": "✓ {src} → {dst}",
    "log.failed": "✗ {src}: {err}",
    "log.progress": "変換中 {i}/{n}：{name}",
    "log.no_files": "変換対象のファイルがありません。",
    "log.batch": "→ {n} ファイル → {fmt}",

    "preview.empty": "—  左のファイルを選択するとプレビューされます  —",

    "err.crash_title": "PolyXRD Converter — 未処理の例外",
    "err.file_missing": "ファイルが見つかりません：{path}",
    "err.empty_file": "空のファイルです：{path}",
    "err.jade_report": (
        "{path} は JADE/PDF の同定結果レポートであり、回折強度データを含みません。"
        "元の .raw / .mdi / .xy の測定ファイルを使用してください。"
    ),
    "err.no_numeric": "ファイル {path} に有効な数値データがありません",
    "err.mdi_too_short": "MDI ファイルの内容が不足しています：{path}",
    "err.mdi_head": "MDI ヘッダーから開始角／ステップを取得できません：{path}",
    "err.mdi_no_data": "MDI ファイルに有効な強度データがありません：{path}",
    "err.q_out_of_range": (
        "Q 値が波長 λ={wavelength}Å で換算できる範囲を超えています"
        "（λQ/4π が最大 {vmax} > 1）。波長の記述が誤っている可能性があります。"
        "ご確認のうえ再実行してください。"
    ),
    "err.gsas_tof": (
        "{name} は中性子飛行時間 (TOF) の GSAS データです（TIME_MAP あり）。"
        "横軸は飛行時間であり 2θ ではないため、本ツールでは扱えません。"
    ),
    "err.gsas_no_bank": "GSAS ファイルに BANK レコードがありません：{path}",
    "err.gsas_eds_alt": (
        "{name} はエネルギー分散 (EDS) または飛行時間型 (ALT) の GSAS データです。"
        "横軸が 2θ ではないため、本ツールでは扱えません。"
    ),
    "err.gsas_esd_fields": "ESD bank に開始角／ステップがありません：{line}",
    "err.gsas_std_fields": "STD bank に開始角／ステップがありません：{line}",
    "err.gsas_too_short": "GSAS ファイルの有効データ点数が不足しています：{path}",
    "err.fp_no_data": (
        "FullProf .dat に有効なデータがありません"
        "（start/step/stop ヘッダーが欠落？）：{path}"
    ),
    "err.rasx_no_member": "rasx 内に Profile*.txt が見つかりません：{path}",
    "err.rasx_bad_zip": "rasx は正しい ZIP ではありません：{path}（{exc}）",
    "err.ras_no_marker": "Rigaku .ras ファイルではありません（*RAS_DATA_START がありません）：{path}",
    "err.ras_no_rows": "Rigaku .ras/.rasx に有効なデータ行がありません：{path}",
    "err.xye_no_wavelength": (
        "{name} は Q 軸の .qye ファイルですが、コメントに '#wavelength <λ>' 行がない"
        "ため 2θ に換算できません。ファイル先頭に '#wavelength <波長Å>' 行を"
        "追加してください。"
    ),
    "err.xye_no_rows": "xye/qye ファイルに有効なデータ行がありません：{path}",
    "err.chi_not_fit2d": (
        "Fit2D .chi ファイルではありません（先頭 4 行に 2-theta/q の記述がありません）：{path}"
    ),
    "err.chi_no_wavelength": (
        "{name} は Q 軸の .qchi ファイルですが、ヘッダーに波長の記述がありません"
        "（'q <λ>' 形式で記述されます）。2θ に換算できません。"
    ),
    "err.chi_no_rows": "chi ファイルに有効なデータ行がありません：{path}",
    "err.xrdml_xml_fail": "XML の解析に失敗しました：{path}（{exc}）",
    "err.xrdml_no_data": "XRDML ファイルから 2θ / 強度を取得できません：{path}",
    "err.brml_no_xml": "BRML ファイル内に XML データが見つかりません：{path}",
    "err.brml_bad_zip": "BRML の解析に失敗しました（正しい ZIP ではありません）：{path}（{exc}）",
    "err.brml_xml_fail": "BRML 内の XML 解析に失敗しました：{path}（{exc}）",
    "err.brml_no_data": "BRML ファイルからデータを取得できません：{path}",
    "err.json_parse_fail": "JSON の解析に失敗しました：{path}（{exc}）",
    "err.json_not_pattern": "{path} はパターン JSON ではありません（two_theta フィールドがありません）",
    "err.read_failed": "{name} の読み込みに失敗しました：{exc}",
    "err.unsupported_target": "サポートされていない出力フォーマット：{fmt}",
    "err.same_file": "出力先がソースファイルと同一のため、上書きされます：{dst}",
    "err.too_few_points": "データ点数が不足しているため、等間隔フォーマットに書き出せません",
    "err.not_equidistant": "2θ が等間隔ではないため MDI/RAW2 には書き出せません。.xy/.txt/.dat/.csv を使用してください。",
    "err.axis_required": (
        "{name}: {variant} として判別されました。強度値は {n} 点読み出されましたが、"
        "**角度軸は信頼できません**。ファイルを右クリック →「角度軸を手動指定」"
        "してから変換してください。"
    ),

    "fmt.xy": "2 列テキスト (.xy)",
    "fmt.txt": "テキスト (.txt)",
    "fmt.dat": "テキスト (.dat)",
    "fmt.csv": "CSV (.csv)",
    "fmt.smz": "テキスト (.smz)",
    "fmt.mdi": "MDI / Jade (.mdi)",
    "fmt.jade_txt": "MDI / Jade テキスト出力 (.txt)",
    "fmt.gsas": "GSAS 粉末データ (.gsas/.fxye/.gda)",
    "fmt.fp_dat": "FullProf .dat",
    "fmt.ras": "理学 Rigaku .ras/.rasx",
    "fmt.xye": "Topas .xye/.qye",
    "fmt.chi": "Fit2D .chi/.qchi",
    "fmt.xrdml": "Bruker XRDML (.xrdml/.xml)",
    "fmt.brml": "Bruker BRML (.brml)",
    "fmt.json": "PolyXRD パターン JSON (.json)",
    "fmt.shimadzu_txt": "島津 ASCII 出力 (.txt/.asc)",
    "fmt.raw": "RAW バイナリ",
    "fmt.rigaku_raw": "理学 Rigaku RAW (RINT/SmartLab, FI)",
    "fmt.scintag_raw2": "Scintag RAW2",
    "fmt.bruker_raw_v1": "Bruker/Siemens RAW v1",
    "fmt.shimadzu_raw": "島津 Shimadzu XRD RAW",
    "fmt.raw_generic": "不明な RAW 形式",

    "tgt.xy": "2 列テキスト 2θ/I (.xy)",
    "tgt.txt": "2 列テキスト 2θ/I (.txt)",
    "tgt.dat": "2 列テキスト 2θ/I (.dat)",
    "tgt.csv": "ヘッダー付き CSV (.csv)",
    "tgt.mdi": "MDI / Jade (.mdi)",
    "tgt.raw": "RAW2 バイナリ (.raw)",
    "tgt.xrdml": "Bruker XRDML (.xrdml)",
    "tgt.json": "PolyXRD パターン JSON (.json)",

    "filter.open": "XRD パターン (*.raw *.RAW *.org *.rsm *.rbg *.rk1 *.rax *.rlz *.rfi *.xy *.txt *.TXT *.dat *.csv *.mdi *.xrdml *.xml *.brml *.json *.gsas *.fxye *.gda *.gsa *.gss *.ras *.rasx *.xye *.qye *.chi *.qchi);;すべてのファイル (*)",
    "filter.dirtitle": "パターンファイルを含むフォルダーを選択",
}

#: 支持的语言代码 (顺序 = 菜单顺序)
LANGS: tuple[str, ...] = ("zh", "en", "ja")

_LANGS = {"zh": ZH, "en": EN, "ja": JA}
_current = "zh"


def set_language(lang: str) -> None:
    global _current
    if lang in _LANGS:
        _current = lang


def language() -> str:
    return _current


def lang_name(code: str) -> str:
    """语言名用母语写法 (简体中文 / English / 日本語), 三种语言下都长一样。"""
    table = _LANGS.get(_current, ZH)
    return table.get(f"lang.{code}") or code


def tr(key: str, **kwargs: Any) -> str:
    """取当前语言的文案; 缺 key 时回退中文再回退 key 本身。"""
    table = _LANGS.get(_current, ZH)
    text = table.get(key) or ZH.get(key) or key
    return text.format(**kwargs) if kwargs else text


def has_key(key: str) -> bool:
    """该 key 是否在**当前语言**的表里有译文 (用于格式名的「有就翻、没有就用原值」)。"""
    return key in _LANGS.get(_current, ZH)


def fmt_label(key: str, fallback: str = "") -> str:
    """格式显示名: 有 ``fmt.<key>`` 译文就翻译, 没有就用调用方给的 fallback。

    RAW 的各变体用 ``raw_variant`` (rigaku_raw / shimadzu_raw / …) 做 key,
    与 loader.FORMAT_LABELS 的取值统一走这里。
    """
    if not key:
        return fallback
    ik = f"fmt.{key}"
    if has_key(ik):
        return tr(ik)
    return fallback or key
