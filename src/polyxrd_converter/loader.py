"""
读取层: 格式识别 + 打开谱图
===========================
- :func:`detect_format` —— 按扩展名 + 文件头嗅探, 返回 ``(key, label)``
- :func:`load_pattern`  —— 打开任意受支持的谱图文件, 返回 :class:`XRDData`

文本类格式统一走"数值行抽取 + 列选择" (能容忍表头/注释/多列);
二进制 RAW 交给 :mod:`polyxrd_converter.raw_formats` 自动分流。
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Union

import numpy as np

from polyxrd_converter.model import XRDData
from polyxrd_converter.raw_formats import parse_raw

__all__ = ["DataFormatError", "detect_format", "load_pattern", "FORMAT_LABELS"]


class DataFormatError(ValueError):
    """数据格式不支持或解析失败。"""


#: 内部 key → 界面展示名
FORMAT_LABELS: dict[str, str] = {
    "xy": "文本两列 (.xy)",
    "txt": "文本 (.txt)",
    "dat": "文本 (.dat)",
    "csv": "CSV (.csv)",
    "smz": "文本 (.smz)",
    "mdi": "MDI / Jade (.mdi)",
    "jade_txt": "MDI / Jade 文本导出 (.txt)",
    "xrdml": "Bruker XRDML (.xrdml/.xml)",
    "brml": "Bruker BRML (.brml)",
    "json": "PolyXRD 谱图 JSON (.json)",
    "shimadzu_txt": "岛津 ASCII 导出 (.txt/.asc)",
    "raw": "RAW 二进制",
}

#: 文本类格式
_TEXT_KEYS = {"xy", "txt", "dat", "csv", "smz"}

#: 靶材 → Kα1 波长 (Å)。头里通常只留 "Cu" 之类记号, 靠它还原波长比在数值堆里猜可靠。
ANODE_WAVELENGTHS: dict[str, float] = {
    "CU": 1.5406,
    "CO": 1.78897,
    "CR": 2.28970,
    "FE": 1.93604,
    "MN": 2.10314,
    "NI": 1.65791,
    "MO": 0.70930,
    "AG": 0.55941,
}

#: 文本里出现这些词说明是岛津 ASCII 导出 (带完整实验参数头)
_SHIMADZU_MARKERS = ("target", "voltage", "<2theta>")

#: Jade/MDI 文本导出的第 2 行头: start step mode anode wavelength stop npoints
_JADE_HEAD_RE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+)\s+"
    r"([A-Za-z]{1,2})\s+(\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(\d+)\s*$"
)


def _jade_head(lines: list[str]) -> Optional[dict]:
    """识别 Jade/MDI 文本导出的两行头。

    第 2 个非空行形如 ``start step mode anode wavelength stop npoints``
    (实测样本: ``15  0.025  2 CU 1.540562  70  2201``)。命中且参数自洽时
    返回参数字典, 否则 None —— 宁可漏判, 也不把普通两列文本误读成单列强度。
    """
    ne = [ln for ln in lines if ln.strip()]
    if len(ne) < 3:
        return None
    m = _JADE_HEAD_RE.match(ne[1])
    if not m:
        return None
    try:
        start = float(m.group(1))
        step = float(m.group(2))
        anode = m.group(4).upper()
        wl = float(m.group(5))
        stop = float(m.group(6))
        npts = int(m.group(7))
    except ValueError:
        return None
    if anode not in ANODE_WAVELENGTHS:
        return None
    if abs(ANODE_WAVELENGTHS[anode] - wl) > 0.02:   # 波长必须与靶材记号吻合
        return None
    if not (0.0 <= start < stop <= 180.0):
        return None
    if not (1e-4 <= step <= 5.0):
        return None
    if not (10 <= npts <= 5_000_000):
        return None
    return {"start": start, "step": step, "stop": stop, "npoints": npts,
            "anode": anode, "wavelength": wl}


def wavelength_from_text(text: str) -> Optional[float]:
    """从文件头文本里找靶材记号, 返回 Kα1 波长 (找不到返回 None)。"""
    upper = text.upper()
    for symbol, wl in ANODE_WAVELENGTHS.items():
        if re.search(rf"(?<![A-Z]){symbol}(?![A-Z])", upper):
            return wl
    return None


# ----------------------------------------------------------------------
# 格式识别
# ----------------------------------------------------------------------

def detect_format(path: Union[str, Path]) -> tuple[str, str]:
    """按扩展名 + 文件头嗅探格式。

    Returns:
        ``(key, label)`` —— ``key`` 见 :data:`FORMAT_LABELS`
    """
    p = Path(path)
    ext = p.suffix.lower()
    try:
        head = p.open("rb").read(4096)
    except OSError:
        head = b""

    if ext == ".raw":
        return "raw", FORMAT_LABELS["raw"]
    # 岛津 Shimadzu 私有容器的魔数决断: 它的 .raw/.org/.rsm/.rbg/.rk1/.rax/
    # .rlz/.rfi 共用同一结构 (见 raw_formats.ShimadzuRawParser), 靠扩展名分不干净。
    # 魔数极特异, 放最前面按魔数认, 不看扩展名。
    if head[:12] == b"Shimadzu XRD":
        return "raw", FORMAT_LABELS["raw"]
    if ext == ".brml":
        return "brml", FORMAT_LABELS["brml"]
    if ext in (".xrdml", ".xml"):
        return "xrdml", FORMAT_LABELS["xrdml"]
    if ext == ".mdi":
        return "mdi", FORMAT_LABELS["mdi"]
    if ext == ".json":
        return "json", FORMAT_LABELS["json"]

    text_head = head.decode("utf-8", "ignore").lower()
    if any(m in text_head for m in _SHIMADZU_MARKERS):
        return "shimadzu_txt", FORMAT_LABELS["shimadzu_txt"]
    if text_head.lstrip().startswith("<"):
        return "xrdml", FORMAT_LABELS["xrdml"]

    # Jade/MDI 两行头文本导出 (Jade 的 .txt/.dat 常见): 头里带 start/step/靶材。
    # 必须在"按扩展名当两列文本"之前判掉, 否则单列定宽强度会被读成两列 → 假轴。
    if _jade_head(head.decode("utf-8", "ignore").splitlines()) is not None:
        return "jade_txt", FORMAT_LABELS["jade_txt"]

    if ext in (".xy", ".txt", ".dat", ".csv", ".smz"):
        key = ext.lstrip(".")
        return key, FORMAT_LABELS[key]

    # 未知扩展名: 有数值就当两列文本
    return "txt", FORMAT_LABELS["txt"]


# ----------------------------------------------------------------------
# 文本解析
# ----------------------------------------------------------------------

def _read_numeric_rows(path: Path) -> tuple[list[list[float]], list[str]]:
    """读取纯文本 → (数值行, 原始行)。跳过注释 / 空行 / 表头。"""
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    lines = text.splitlines()
    if not lines:
        raise DataFormatError(f"空文件: {path}")

    # 防御: 拒绝 JADE/PDF 物相识别报告 (不是衍射强度数据, 误读会产生虚假峰)
    if "phase id report" in "".join(lines[:40]).lower():
        raise DataFormatError(
            f"{path} 是 JADE/PDF 物相识别报告, 不含衍射强度数据; "
            "请改用对应的 .raw / .mdi / .xy 原始谱图文件。"
        )

    rows: list[list[float]] = []
    for raw_line in lines:
        s = raw_line.strip()
        if not s or s.startswith(("#", "%", "//", ";", "!", "<", '"', "'")):
            continue
        soft = s.replace(",", " ").replace(";", " ").replace("\t", " ")
        parts = soft.split()
        vals: list[float] = []
        ok = True
        for tok in parts:
            try:
                vals.append(float(tok))
            except ValueError:
                ok = False
                break
        if ok and len(vals) >= 2:
            rows.append(vals)
    if not rows:
        raise DataFormatError(f"文件 {path} 中没有有效数值数据")
    return rows, lines


def _pick_columns(rows: list[list[float]]) -> tuple[int, int]:
    """挑 (2θ 列, 强度列)。

    两列 → (0, 1); 多列 → x 取单调首列, y 取相邻差分之和最大者 (计数率列),
    避开常量列与与首列重复的列。
    """
    ncol = len(rows[0])
    if ncol <= 2:
        return 0, 1
    arr = np.asarray(rows, dtype=float)
    diffs = np.abs(np.diff(arr, axis=0)).sum(axis=0)
    cands = [j for j in range(1, ncol) if diffs[j] > 1e-9]
    if not cands:
        cands = list(range(1, ncol))
    return 0, max(cands, key=lambda j: diffs[j])


def _load_text(path: Path, key: str) -> XRDData:
    rows, lines = _read_numeric_rows(path)
    # Jade/MDI 两行头文本: 头里有 start/step, 数据是单列定宽强度, 不能按两列读。
    if _jade_head(lines) is not None:
        return _load_mdi(path, "jade_txt")
    xc, yc = _pick_columns(rows)
    arr = np.asarray(rows, dtype=float)
    head_text = "\n".join(lines[:40])
    wl = wavelength_from_text(head_text)
    return XRDData(
        two_theta=arr[:, xc],
        intensity=arr[:, yc],
        wavelength=wl or 1.5406,
        metadata={
            "format": key,
            "x_col": xc,
            "y_col": yc,
            "num_points": int(arr.shape[0]),
            "wavelength_source": "header" if wl else "default",
        },
    )


def _load_shimadzu_txt(path: Path) -> XRDData:
    """岛津 ASCII 导出 (带 target / voltage / sampling pitch 等参数头)。"""
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    meta: dict = {"instrument": "Shimadzu"}
    patterns = {
        "target": r"target\s*[:=]\s*(\S+)",
        "voltage": r"voltage\s*[:=]\s*([\d.]+)",
        "current": r"current\s*[:=]\s*([\d.]+)",
        "scan_start": r"scan range\s*[:=]\s*([\d.]+)",
        "scan_end": r"scan range\s*[:=]\s*[\d.]+\s*-\s*([\d.]+)",
        "step": r"(?:sampling\s+pitch|sampling\s+interval|step)\s*[:=]\s*([\d.]+)",
        "preset_time": r"(?:preset\s+time|counting\s+time)\s*[:=]\s*([\d.]+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                meta[key] = float(m.group(1))
            except ValueError:
                meta[key] = m.group(1)

    wl = wavelength_from_text(text)
    rows, _ = _read_numeric_rows(path)
    xc, yc = _pick_columns(rows)
    arr = np.asarray(rows, dtype=float)
    return XRDData(
        two_theta=arr[:, xc],
        intensity=arr[:, yc],
        wavelength=wl or 1.5406,
        metadata={"format": "shimadzu_txt", "num_points": int(arr.shape[0]), **meta},
    )


def _load_mdi(path: Path, key: str = "mdi") -> XRDData:
    """MDI (Jade) 文本格式: 定宽整数强度, 头含 start/step/.../stop。

    实测坑: 该格式转换时可能丢掉**第一个**通道 (如 count=7250 却带 5.000→150.000
    的区间)。若按 start 起算整条谱会平移一个步长 (峰位全错 0.02°), 故当
    ``start + step*(n-1)`` 对不上头里的 stop 时, 改以 stop 反推 start。
    """
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        raise DataFormatError(f"MDI 文件内容不足: {path}")

    head = lines[1]
    head_nums: list[float] = []
    for tok in head.split():
        try:
            head_nums.append(float(tok))
        except ValueError:
            continue
    if len(head_nums) < 2:
        raise DataFormatError(f"MDI 文件头无法解析 start/step: {path}")
    start, step = head_nums[0], head_nums[1]

    values: list[float] = []
    for ln in lines[2:]:
        for tok in ln.split():
            try:
                values.append(float(tok))
            except ValueError:
                continue
    if len(values) < 2:
        raise DataFormatError(f"MDI 文件没有有效强度数据: {path}")
    intensity = np.asarray(values, dtype=float)
    n = len(intensity)

    if step > 0:
        want = start + step * (n - 1)
        span = step * max(n - 1, 1)
        cands = [c for c in head_nums[2:] if abs(c - want) <= 0.05 * span]
        if cands:
            stop = min(cands, key=lambda c: abs(c - want))
            if abs(start + step * (n - 1) - stop) > step / 2:
                start = stop - step * (n - 1)

    two_theta = start + step * np.arange(n, dtype=float)
    wl = wavelength_from_text(head)
    return XRDData(
        two_theta=two_theta,
        intensity=intensity,
        wavelength=wl or 1.5406,
        metadata={"format": key, "num_points": n},
    )


# ----------------------------------------------------------------------
# XML 解析 (xrdml / brml)
# ----------------------------------------------------------------------

def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _text_numbers(text: Optional[str]) -> list[float]:
    if not text:
        return []
    out: list[float] = []
    for tok in text.split():
        try:
            out.append(float(tok))
        except ValueError:
            return []
    return out


def _xml_arrays(root: ET.Element):
    """从 XML 树里取 (2θ, 强度)。

    兼容三种写法:
      1. ``<positions axis="2Theta"><startPosition/><endPosition/></positions>``
         + ``<intensities>`` (Bruker XRDML 标准写法, 按强度个数线性展开)
      2. ``<positions>`` 的文本直接是 2θ 列表
      3. PANalytical 风格: ``<positions>`` 下挂 ``<axis axisName="2Theta">``
    """
    two_theta = intensity = None
    start_pos = end_pos = None

    for element in root.iter():
        tag = _local(element.tag)
        if tag == "positions":
            vals = _text_numbers(element.text)
            if len(vals) >= 2:
                two_theta = np.asarray(vals, dtype=float)
                continue
            for child in element.iter():
                ctag = _local(child.tag)
                if ctag == "startPosition":
                    start_pos = _text_numbers(child.text)
                    start_pos = start_pos[0] if start_pos else None
                elif ctag == "endPosition":
                    end_pos = _text_numbers(child.text)
                    end_pos = end_pos[0] if end_pos else None
                elif ctag == "axis" and child.get("axisName") == "2Theta":
                    vals = _text_numbers(child.text)
                    if len(vals) >= 2:
                        two_theta = np.asarray(vals, dtype=float)
        elif tag in ("intensities", "counts"):
            vals = _text_numbers(element.text)
            if len(vals) >= 2:
                intensity = np.asarray(vals, dtype=float)

    # 只有 start/end + 强度个数 → 等间距展开
    if two_theta is None and intensity is not None and start_pos is not None \
            and end_pos is not None and len(intensity) >= 2:
        two_theta = np.linspace(float(start_pos), float(end_pos), len(intensity))

    return two_theta, intensity


def _load_xrdml(path: Path) -> XRDData:
    """Bruker/PANalytical XRDML (XML)。"""
    try:
        root = ET.parse(str(path)).getroot()
    except ET.ParseError as exc:
        raise DataFormatError(f"XML 解析失败: {path} ({exc})") from exc

    two_theta, intensity = _xml_arrays(root)

    # 备选: 把所有叶子文本里的数字按前后半分开 (老式/简化 XML)。
    # ⚠ 必须加"前半单调递增"的守卫 —— 2θ 轴一定单调, 否则会把强度序列劈成
    #   两半造出一条假谱 (本工具开发中就踩过: 7251 点被劈成 3626 点)。
    if two_theta is None or intensity is None:
        numbers: list[float] = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                numbers.extend(_text_numbers(elem.text))
        if len(numbers) >= 6:
            half = len(numbers) // 2
            first = numbers[:half]
            if all(b > a for a, b in zip(first, first[1:])):
                two_theta = np.array(first)
                intensity = np.array(numbers[half:half * 2])

    if two_theta is None or intensity is None:
        raise DataFormatError(f"无法从 XRDML 文件提取 2θ / 强度数据: {path}")

    m = min(len(two_theta), len(intensity))
    return XRDData(
        two_theta=two_theta[:m],
        intensity=intensity[:m],
        wavelength=1.5406,
        metadata={"format": "xrdml", "num_points": int(m)},
    )


def _load_brml(path: Path) -> XRDData:
    """Bruker BRML (ZIP 容器 + XML)。"""
    import io
    import zipfile

    try:
        with zipfile.ZipFile(str(path), "r") as zf:
            names = zf.namelist()
            data_files = [f for f in names if "data" in f.lower() and f.lower().endswith(".xml")]
            if not data_files:
                data_files = [f for f in names if f.lower().endswith(".xml")]
            if not data_files:
                raise DataFormatError(f"BRML 文件里找不到 XML 数据: {path}")
            xml_text = zf.read(data_files[0]).decode("utf-8-sig", "ignore")
    except zipfile.BadZipFile as exc:
        raise DataFormatError(f"BRML 解析失败 (不是合法 ZIP): {path} ({exc})") from exc

    try:
        root = ET.parse(io.StringIO(xml_text)).getroot()
    except ET.ParseError as exc:
        raise DataFormatError(f"BRML 内 XML 解析失败: {path} ({exc})") from exc

    two_theta, intensity = _xml_arrays(root)
    if two_theta is None or intensity is None:
        # BRML 常用 <Datum><Positions>/<Counts> 结构
        pos, cnt = [], []
        for elem in root.iter():
            tag = elem.tag.split("}")[-1].lower() if "}" in elem.tag else elem.tag.lower()
            txt = (elem.text or "").strip()
            if not txt:
                continue
            vals = []
            for tok in txt.split():
                try:
                    vals.append(float(tok))
                except ValueError:
                    vals = []
                    break
            if not vals:
                continue
            if "position" in tag or "2theta" in tag:
                if len(vals) > len(pos):
                    pos = vals
            elif "count" in tag or "intensit" in tag:
                if len(vals) > len(cnt):
                    cnt = vals
        two_theta = np.array(pos) if pos else None
        intensity = np.array(cnt) if cnt else None

    if two_theta is None or intensity is None:
        raise DataFormatError(f"无法从 BRML 文件提取数据: {path}")

    m = min(len(two_theta), len(intensity))
    return XRDData(
        two_theta=two_theta[:m],
        intensity=intensity[:m],
        wavelength=1.5406,
        metadata={"format": "brml", "num_points": int(m)},
    )


def _load_json(path: Path) -> XRDData:
    """本工具导出的谱图 JSON (含 two_theta / intensity 字段)。"""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DataFormatError(f"JSON 解析失败: {path} ({exc})") from exc
    if not isinstance(payload, dict) or "two_theta" not in payload:
        raise DataFormatError(f"{path} 不是谱图 JSON (缺 two_theta 字段)")
    data = XRDData.from_dict(payload)
    data.metadata.setdefault("format", "json")
    return data


# ----------------------------------------------------------------------
# 统一入口
# ----------------------------------------------------------------------

def load_pattern(
    path: Union[str, Path],
    wavelength: Optional[float] = None,
    manual_axis: Optional[tuple[float, float]] = None,
) -> XRDData:
    """打开任意受支持的谱图文件。

    Args:
        path: 文件路径
        wavelength: 显式波长 (None → 从头识别或默认 Cu Kα1)
        manual_axis: ``(起始 2θ, 步长)`` —— 仅在 RAW 角度轴不可信时使用

    Raises:
        FileNotFoundError: 文件不存在
        DataFormatError: 格式不支持 / 解析失败
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {p}")

    key, label = detect_format(p)
    try:
        if key == "raw":
            result = parse_raw(p.read_bytes(), p)
            data = XRDData(
                two_theta=result.two_theta,
                intensity=result.intensity,
                # 波长优先级: 调用方显式指定 > 解析器从文件头读到的 > 默认 Cu Kα1
                wavelength=wavelength or result.meta.get("wavelength") or 1.5406,
                metadata={
                    "format": "raw",
                    "raw_variant": result.format_key,
                    "raw_variant_label": result.format_label,
                    "axis_confident": result.axis_confident,
                    "num_points": int(result.intensity.size),
                    **result.meta,
                },
            )
            if not result.axis_confident:
                if manual_axis is not None:
                    start, step = manual_axis
                    data.two_theta = float(start) + float(step) * np.arange(
                        len(data), dtype=float
                    )
                    data.metadata["axis_confident"] = True
                    data.metadata["axis_source"] = "manual"
                else:
                    data.metadata["axis_source"] = "unknown"
            return data

        if key in ("mdi", "jade_txt"):
            data = _load_mdi(p, key)
        elif key == "xrdml":
            data = _load_xrdml(p)
        elif key == "brml":
            data = _load_brml(p)
        elif key == "json":
            data = _load_json(p)
        elif key == "shimadzu_txt":
            data = _load_shimadzu_txt(p)
        else:
            data = _load_text(p, key)
    except (DataFormatError, FileNotFoundError):
        raise
    except Exception as exc:  # noqa: BLE001 - 统一成 DataFormatError 便于 GUI 展示
        raise DataFormatError(f"读取 {p.name} 失败: {exc}") from exc

    if wavelength is not None:
        data.wavelength = wavelength
    data.metadata.setdefault("format", key)
    data.metadata["format_label"] = label
    data.metadata.setdefault("source_file", str(p))
    return data
