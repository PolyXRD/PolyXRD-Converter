"""
极简 i18n
=========
本工具只有中/英两套文案, 用两个字典直接查表, 不引入 Qt Linguist 那套重流程。
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
        "PolyXRD Team · 2025 — 2026<br>"
        "联系：<a href='mailto:sshztx@outlook.com'>sshztx@outlook.com</a> · "
        "<a href='https://github.com/PolyXRD'>github.com/PolyXRD</a>"
    ),

    "log.summary": "完成：成功 {ok} 个，失败 {fail} 个。",
    "log.converted": "✓ {src} → {dst}",
    "log.failed": "✗ {src}: {err}",
    "log.progress": "正在转换 {i}/{n}：{name}",

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
        "PolyXRD Team · 2025 — 2026<br>"
        "Contact: <a href='mailto:sshztx@outlook.com'>sshztx@outlook.com</a> · "
        "<a href='https://github.com/PolyXRD'>github.com/PolyXRD</a>"
    ),

    "log.summary": "Finished: {ok} succeeded, {fail} failed.",
    "log.converted": "✓ {src} → {dst}",
    "log.failed": "✗ {src}: {err}",
    "log.progress": "Converting {i}/{n}: {name}",

    "filter.open": "XRD patterns (*.raw *.RAW *.org *.rsm *.rbg *.rk1 *.rax *.rlz *.rfi *.xy *.txt *.TXT *.dat *.csv *.mdi *.xrdml *.xml *.brml *.json *.gsas *.fxye *.gda *.gsa *.gss *.ras *.rasx *.xye *.qye *.chi *.qchi);;All files (*)",
    "filter.dirtitle": "Choose a folder containing pattern files",
}

_LANGS = {"zh": ZH, "en": EN}
_current = "zh"


def set_language(lang: str) -> None:
    global _current
    if lang in _LANGS:
        _current = lang


def language() -> str:
    return _current


def tr(key: str, **kwargs: Any) -> str:
    """取当前语言的文案; 缺 key 时回退中文再回退 key 本身。"""
    table = _LANGS.get(_current, ZH)
    text = table.get(key) or ZH.get(key) or key
    return text.format(**kwargs) if kwargs else text
