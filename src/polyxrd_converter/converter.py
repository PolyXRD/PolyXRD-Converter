"""
转换服务: 读源 → 写目标
======================
对 GUI 只暴露两件事: 先 :func:`probe` 探一下能不能读、读出来几条点,
再 :func:`convert_file` 真转。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

import numpy as np

from polyxrd_converter.loader import DataFormatError, detect_format, load_pattern
from polyxrd_converter.model import XRDData
from polyxrd_converter.writers import TARGET_EXTS, write_pattern

__all__ = ["ProbeResult", "probe", "convert_file", "convert_batch", "ConversionOutcome"]


@dataclass
class ProbeResult:
    """一个源文件的探测结果 (供表格显示, 不写盘)。"""

    path: Path
    ok: bool
    format_key: str = ""
    format_label: str = ""
    points: int = 0
    x_min: float = 0.0
    x_max: float = 0.0
    y_max: float = 0.0
    wavelength: Optional[float] = None
    axis_confident: bool = True
    truncated: bool = False
    message: str = ""
    data: Optional[XRDData] = field(default=None, repr=False)


def probe(path: Union[str, Path], manual_axis: Optional[tuple[float, float]] = None) -> ProbeResult:
    """试读文件并把关键信息摘出来; 失败不抛异常, 而是记在 ``message`` 里。"""
    p = Path(path)
    try:
        key, _label = detect_format(p)
    except Exception:  # noqa: BLE001
        key = "?"

    if not p.exists():
        return ProbeResult(path=p, ok=False, format_key=key, message="文件不存在")

    try:
        data = load_pattern(p, manual_axis=manual_axis)
    except Exception as exc:  # noqa: BLE001 - 探测阶段不打断批量
        return ProbeResult(path=p, ok=False, format_key=key, message=str(exc))

    label = (
        data.metadata.get("raw_variant_label")
        or data.metadata.get("format_label")
        or key
    )
    return ProbeResult(
        path=p,
        ok=True,
        format_key=str(data.metadata.get("format", key)),
        format_label=str(label),
        points=len(data),
        x_min=float(data.two_theta[0]) if len(data) else 0.0,
        x_max=float(data.two_theta[-1]) if len(data) else 0.0,
        y_max=float(np.max(data.intensity)) if len(data) else 0.0,
        wavelength=data.wavelength,
        axis_confident=bool(data.metadata.get("axis_confident", True)),
        truncated=bool(data.metadata.get("truncated", False)),
        data=data,
    )


@dataclass
class ConversionOutcome:
    """单文件转换结果。"""

    src: Path
    ok: bool
    dst: Optional[Path] = None
    message: str = ""


def convert_file(
    src: Union[str, Path],
    dst: Union[str, Path, None] = None,
    fmt: Optional[str] = None,
    manual_axis: Optional[tuple[float, float]] = None,
) -> Path:
    """把 ``src`` 转成 ``dst`` (或同目录同名的另一个扩展名), 返回写出路径。

    Args:
        src: 源文件 (任意受支持的可读格式)
        dst: 目标路径; None → 与源同目录、同主名、扩展名换成 ``fmt``
        fmt: 目标格式 key; ``dst`` 给了且 ``fmt`` 为 None 时按 dst 扩展名推断
        manual_axis: ``(起始 2θ, 步长)``, 仅 RAW 角度轴不可信时使用
    """
    src = Path(src)
    data = load_pattern(src, manual_axis=manual_axis)

    if dst is None:
        key = (fmt or "xy").lower()
        if key not in TARGET_EXTS:
            raise DataFormatError(f"不支持的导出格式: {key}")
        dst = src.with_suffix(TARGET_EXTS[key])
    else:
        dst = Path(dst)

    # 防呆: 转换是"读源 → 写目标", 目标不能就是源文件本身, 否则等于静默毁掉原文件。
    try:
        same = dst.resolve() == src.resolve()
    except OSError:
        same = dst == src
    if same:
        raise DataFormatError(f"输出文件与源文件是同一个文件, 会覆盖源文件: {dst}")

    # 角度轴不可信又没给手工值时, 不写出 —— 宁可失败, 也不产出峰位错误的谱图。
    if str(data.metadata.get("format")) == "raw" and not data.metadata.get(
        "axis_confident", True
    ):
        raise DataFormatError(
            f"{src.name}: 识别为 {data.metadata.get('raw_variant_label', 'RAW')}, "
            f"已取出 {len(data)} 个强度点但**角度轴不可信**; "
            "请右键该文件「手动指定角度轴」后再转换。"
        )

    return write_pattern(data, dst, fmt)


def convert_batch(
    items: list[tuple[Union[str, Path], Union[str, Path, None], Optional[str]]],
    manual_axis: Optional[tuple[float, float]] = None,
) -> list[ConversionOutcome]:
    """批量转换。``items`` 里每项是 ``(src, dst, fmt)``; 单个失败不影响其余。"""
    outcomes: list[ConversionOutcome] = []
    for src, dst, fmt in items:
        try:
            out = convert_file(src, dst, fmt, manual_axis=manual_axis)
            outcomes.append(ConversionOutcome(Path(src), True, out))
        except Exception as exc:  # noqa: BLE001 - 批处理继续
            outcomes.append(ConversionOutcome(Path(src), False, None, str(exc)))
    return outcomes
