"""
写出层: 把 :class:`XRDData` 写成各种目标格式
==========================================
- :data:`TARGET_FORMATS` —— 目标格式声明, UI 下拉与过滤器都从这里取, 避免漂移
- :func:`write_pattern`  —— 按格式 key 写出, 返回实际路径
"""
from __future__ import annotations

import csv
import json
import struct
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import numpy as np

from polyxrd_converter.model import XRDData

__all__ = ["TARGET_FORMATS", "TARGET_EXTS", "write_pattern", "DataFormatError"]

from polyxrd_converter.loader import DataFormatError

#: (key, 扩展名, 展示名)。顺序 = UI 下拉顺序, 常用的放前面。
TARGET_FORMATS: tuple[tuple[str, str, str], ...] = (
    ("xy", ".xy", "两列文本 2θ/I (.xy)"),
    ("txt", ".txt", "两列文本 2θ/I (.txt)"),
    ("dat", ".dat", "两列文本 2θ/I (.dat)"),
    ("csv", ".csv", "CSV 带表头 (.csv)"),
    ("mdi", ".mdi", "MDI / Jade (.mdi)"),
    ("raw", ".raw", "RAW2 二进制 (.raw)"),
    ("xrdml", ".xrdml", "Bruker XRDML (.xrdml)"),
    ("json", ".json", "PolyXRD 谱图 JSON (.json)"),
)

TARGET_EXTS: dict[str, str] = {k: e for k, e, _ in TARGET_FORMATS}

# RAW2 头内固定偏移 (与 raw_formats.ScintagRaw2Parser 的读端成对)
_RAW2_HDR_LEN = 316
_RAW2_ANODE_OFF = 0x100     # 2 字节靶材记号 ("Cu"), 供读回时还原波长
_RAW2_COUNT_OFF = 0x102     # int16 LE: 点数
_RAW2_STEP_OFF = 0x10C      # float32 LE: 步长
_RAW2_START_OFF = 0x110     # float32 LE: 起始 2θ
_RAW2_COUNT_MAX = 32767     # int16 上限 —— RAW2 格式自带限制

#: 描述文本**不能**出现 CU/CO/CR/FE/MN/NI/MO/AG 这类字母组合, 否则读回时会被
#: 当成靶材记号 (读端是子串匹配)。"PolyXRD pattern export" 已逐项核对过。
_RAW2_BANNER = b"PolyXRD pattern export"


def _uniform_step(two_theta: np.ndarray) -> float:
    """取等间距 2θ 的步长; 非等间距时抛错 (MDI/RAW2 是等间距通道格式)。"""
    diffs = np.diff(np.asarray(two_theta, dtype=float))
    if diffs.size == 0:
        raise DataFormatError("数据点不足, 无法写入等间距格式")
    step = float(np.median(diffs))
    if step <= 0 or not np.allclose(diffs, step, rtol=1e-6, atol=step * 1e-6):
        raise DataFormatError(
            "数据不是等间距 2θ, 无法写入 MDI/RAW2; 请改用 .xy/.txt/.dat/.csv"
        )
    return step


def _fmt_pair(x: float, y: float) -> str:
    """两列文本的一行。

    整数强度按整数列写 (与原厂 .dat/.txt/.xy 导出同构); 含小数时保留 3 位。

    两列之间靠「左填充空格」天然分隔: x 固定 8 宽、y 固定 10 宽, 正常 y 值
    首字符是空格, 列边界清晰。但当 y 值大到占满 10 字符场宽 (首字符不再是
    空格, 如 126727.648 或 10 位整数) 时, 列边界会塌缩成单列, 下游
    np.loadtxt 报 "columns changed"。此时补一个显式分隔空格即可 —— 只在
    溢出时才补, 正常样本保持与原厂字节一致 (不破坏往返字节对拍)。
    """
    x_field = f"{x:8.3f}"
    if abs(y - round(y)) < 1e-9:
        y_field = f"{int(round(y)):10d}"
    else:
        y_field = f"{y:10.3f}"
    sep = "" if y_field[0] == " " else " "
    return x_field + sep + y_field


def _write_two_column(data: XRDData, path: Path) -> None:
    """写 .xy/.txt/.dat: 两列定宽文本 (CRLF, 与原厂导出一致)。

    ``newline=""`` 不能省 —— 否则 Windows 文本模式会把 ``\\n`` 再翻成 ``\\r\\n``,
    写出 ``\\r\\r\\n`` 的坏行尾。
    """
    lines = [_fmt_pair(float(x), float(y)) for x, y in zip(data.two_theta, data.intensity)]
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")


def _write_csv(data: XRDData, path: Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["2theta", "intensity"])
        for x, y in zip(data.two_theta, data.intensity):
            writer.writerow([f"{float(x):.6f}", f"{float(y):.6f}"])


def _write_mdi(data: XRDData, path: Path, anode: str = "Cu") -> None:
    """写 MDI 文本格式。

    结构: 行1 ``日期 样品名``; 行2 ``start step scale anode wavelength stop count``;
    其余为定宽整数强度 (每行 8 个, 栏宽 8)。start/stop 按实际首末 2θ 写, 这样
    读回时不会再被"丢首点校正"整体平移。
    """
    x = np.asarray(data.two_theta, dtype=float)
    y = np.asarray(data.intensity, dtype=float)
    step = _uniform_step(x)
    n = int(x.size)
    start, stop = float(x[0]), float(x[-1])
    wl = float(data.wavelength or 1.5406)

    head0 = "       %s %s" % (datetime.now().strftime("%m/%d/%y"), "Sample ID")
    head1 = (
        f"{start:9.5f}{step:10.6f}{1.0:5.1f} {anode[:2]:2}"
        f"{wl:10.6f}{stop:9.4f}{n:7d}"
    )

    body: list[str] = []
    row: list[str] = []
    for value in y:
        row.append(f"{int(round(value)):8d}")
        if len(row) == 8:
            body.append("".join(row))
            row = []
    if row:
        body.append("".join(row))

    path.write_text("\r\n".join([head0, head1, *body]) + "\r\n", encoding="utf-8", newline="")


def _write_raw(data: XRDData, path: Path, anode: str = "Cu") -> None:
    """写 RAW2 二进制: 316 字节定长头 + n 个 little-endian float32 强度。

    与本工具的 RAW2 读端成对, 保证自读自写可无损往返。
    """
    x = np.asarray(data.two_theta, dtype=float)
    y = np.asarray(data.intensity, dtype=float)
    step = _uniform_step(x)
    n = int(x.size)
    if n > _RAW2_COUNT_MAX:
        raise DataFormatError(
            f"RAW2 点数上限 {_RAW2_COUNT_MAX} (int16), 当前 {n} 点; 请改用 .xy/.txt/.dat/.csv"
        )

    header = bytearray(_RAW2_HDR_LEN)
    header[0:4] = b"RAW2"
    header[4:4 + len(_RAW2_BANNER)] = _RAW2_BANNER
    header[_RAW2_ANODE_OFF:_RAW2_ANODE_OFF + 2] = anode[:2].ljust(2).encode("ascii")
    struct.pack_into("<h", header, _RAW2_COUNT_OFF, n)
    struct.pack_into("<f", header, _RAW2_STEP_OFF, float(step))
    struct.pack_into("<f", header, _RAW2_START_OFF, float(x[0]))

    with open(path, "wb") as fh:
        fh.write(bytes(header))
        fh.write(np.asarray(y, dtype="<f4").tobytes())


def _write_xrdml(data: XRDData, path: Path) -> None:
    """写 Bruker 风格 .xrdml (XRDMeasurement 2.1)。

    等间距时写成 ``startPosition/endPosition`` (标准且紧凑, 强度个数隐含点数);
    非等间距才把整条 2θ 轴铺进 ``<positions>`` 的文本里。
    """
    x = np.asarray(data.two_theta, dtype=float)
    y = np.asarray(data.intensity, dtype=float)
    try:
        uniform = _uniform_step(x) is not None
    except DataFormatError:
        uniform = False

    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        fh.write('<xrdMeasurement xmlns="http://www.xrdml.com/XRDMeasurement/2.1">\n')
        fh.write("  <scan>\n    <dataPoints>\n")
        if uniform:
            fh.write('      <positions axis="2Theta" unit="deg">\n')
            fh.write(f"        <startPosition>{float(x[0]):.6f}</startPosition>\n")
            fh.write(f"        <endPosition>{float(x[-1]):.6f}</endPosition>\n")
            fh.write("      </positions>\n")
        else:
            fh.write('      <positions axis="2Theta" unit="deg">')
            fh.write(" ".join(f"{float(v):.6f}" for v in x))
            fh.write("</positions>\n")
        fh.write('      <intensities unit="counts">')
        # 整数强度按整数写 (与原厂导出同构); 含小数时给 9 位有效数字 —— float32
        # 源数据约 7.2 位十进制精度, 9 位足以无损往返 (用 .1f 会把小数强度削掉)。
        fh.write(" ".join(
            f"{int(round(float(v)))}" if abs(float(v) - round(float(v))) < 1e-9
            else f"{float(v):.9g}"
            for v in y
        ))
        fh.write("</intensities>\n")
        fh.write("    </dataPoints>\n  </scan>\n</xrdMeasurement>\n")


def _write_json(data: XRDData, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data.to_dict(), fh, indent=2, ensure_ascii=False, default=str)


_WRITERS = {
    "xy": _write_two_column,
    "txt": _write_two_column,
    "dat": _write_two_column,
    "csv": _write_csv,
    "mdi": _write_mdi,
    "raw": _write_raw,
    "xrdml": _write_xrdml,
    "json": _write_json,
}


def write_pattern(
    data: XRDData,
    path: Union[str, Path],
    fmt: Optional[str] = None,
) -> Path:
    """按 ``fmt`` (缺省取扩展名) 写出谱图, 返回实际写入路径。"""
    p = Path(path)
    key = (fmt or p.suffix.lstrip(".")).lower()
    if key not in TARGET_EXTS:
        raise DataFormatError(
            "不支持的导出格式: %s (可选: %s)" % (key, ", ".join(TARGET_EXTS))
        )
    if not p.suffix:
        p = p.with_suffix(TARGET_EXTS[key])
    p.parent.mkdir(parents=True, exist_ok=True)
    _WRITERS[key](data, p)
    return p
