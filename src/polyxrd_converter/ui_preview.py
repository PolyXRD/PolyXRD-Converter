"""
谱图预览控件
============
用 QPainter 手绘 (不引入 matplotlib / pyqtgraph, 保持单文件 exe 体积与启动速度)。

功能: 自动量程、网格、刻度、曲线、最强峰标记; 滚轮缩放、拖拽平移、双击复位。
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from polyxrd_converter.i18n import tr

_BG = QColor("#ffffff")
_PANEL = QColor("#fbfcfe")
_AXIS = QColor("#c3cad6")
_GRID = QColor("#eaeef5")
_TEXT = QColor("#4a5568")
_TITLE = QColor("#1f2d3d")
_CURVE = QColor("#1f6feb")
_CURVE_FILL = QColor(31, 111, 235, 28)
_PEAK = QColor("#d64545")


def _nice_step(span: float, target_ticks: int = 6) -> float:
    """给一段跨度挑一个"好看"的刻度间隔 (1/2/5 × 10^k)。"""
    if span <= 0 or not math.isfinite(span):
        return 1.0
    raw = span / max(target_ticks, 1)
    exp = math.floor(math.log10(raw))
    base = raw / (10 ** exp)
    for mult in (1.0, 2.0, 2.5, 5.0, 10.0):
        if base <= mult:
            return mult * (10 ** exp)
    return 10.0 ** (exp + 1)


class SpectrumView(QWidget):
    """(2θ, 强度) 谱图显示。"""

    pointHovered = Signal(float, float)

    _MARGIN_L = 62
    _MARGIN_R = 16
    _MARGIN_T = 34
    _MARGIN_B = 34

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._x: Optional[np.ndarray] = None
        self._y: Optional[np.ndarray] = None
        self._title = ""
        self._subtitle = ""
        self._note = ""

        self._xlim: Optional[tuple[float, float]] = None
        self._ylim: Optional[tuple[float, float]] = None
        self._drag_from: Optional[QPoint] = None
        self._hover: Optional[QPointF] = None

    # ---- 数据 --------------------------------------------------------

    def set_data(
        self,
        x: Optional[np.ndarray],
        y: Optional[np.ndarray],
        title: str = "",
        subtitle: str = "",
        note: str = "",
    ) -> None:
        self._x = None if x is None else np.asarray(x, dtype=float)
        self._y = None if y is None else np.asarray(y, dtype=float)
        self._title, self._subtitle, self._note = title, subtitle, note
        self.reset_view()
        self.update()

    def reset_view(self) -> None:
        if self._x is None or self._x.size == 0:
            self._xlim = self._ylim = None
            return
        x0, x1 = float(np.min(self._x)), float(np.max(self._x))
        y0, y1 = float(np.min(self._y)), float(np.max(self._y))
        pad_x = 0.02 * (x1 - x0) if x1 > x0 else 1.0
        pad_y = 0.08 * (y1 - y0) if y1 > y0 else 1.0
        self._xlim = (x0 - pad_x, x1 + pad_x)
        self._ylim = (min(0.0, y0 - pad_y), y1 + pad_y)

    # ---- 坐标换算 ----------------------------------------------------

    def _plot_rect(self) -> QRectF:
        return QRectF(
            self._MARGIN_L,
            self._MARGIN_T,
            max(1.0, self.width() - self._MARGIN_L - self._MARGIN_R),
            max(1.0, self.height() - self._MARGIN_T - self._MARGIN_B),
        )

    def _to_px(self, x: float, y: float) -> QPointF:
        r = self._plot_rect()
        x0, x1 = self._xlim or (0.0, 1.0)
        y0, y1 = self._ylim or (0.0, 1.0)
        fx = (x - x0) / (x1 - x0) if x1 > x0 else 0.0
        fy = (y - y0) / (y1 - y0) if y1 > y0 else 0.0
        return QPointF(r.left() + fx * r.width(), r.bottom() - fy * r.height())

    def _to_data(self, pos: QPointF) -> tuple[float, float]:
        r = self._plot_rect()
        x0, x1 = self._xlim or (0.0, 1.0)
        y0, y1 = self._ylim or (0.0, 1.0)
        fx = (pos.x() - r.left()) / max(r.width(), 1.0)
        fy = (r.bottom() - pos.y()) / max(r.height(), 1.0)
        return x0 + fx * (x1 - x0), y0 + fy * (y1 - y0)

    # ---- 绘制 --------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt 命名
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), _BG)
        painter.fillRect(self._plot_rect(), _PANEL)

        if self._x is None or self._x.size == 0:
            self._draw_placeholder(painter)
            painter.end()
            return

        self._draw_grid_and_axes(painter)
        self._draw_curve(painter)
        self._draw_header(painter)
        self._draw_hover(painter)
        painter.end()

    def _draw_placeholder(self, painter: QPainter) -> None:
        painter.setPen(QPen(_AXIS, 1, Qt.PenStyle.DashLine))
        painter.drawRect(self._plot_rect())
        painter.setPen(_TEXT)
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(
            self.rect(), Qt.AlignmentFlag.AlignCenter,
            tr("preview.empty"),
        )

    def _draw_grid_and_axes(self, painter: QPainter) -> None:
        r = self._plot_rect()
        x0, x1 = self._xlim or (0.0, 1.0)
        y0, y1 = self._ylim or (0.0, 1.0)
        painter.setFont(QFont("Segoe UI", 8))

        # X 轴
        step = _nice_step(x1 - x0, 6)
        t = math.ceil(x0 / step) * step
        while t <= x1 + 1e-9:
            p = self._to_px(t, y0)
            painter.setPen(QPen(_GRID, 1))
            painter.drawLine(QPointF(p.x(), r.top()), QPointF(p.x(), r.bottom()))
            painter.setPen(_TEXT)
            painter.drawText(
                QRectF(p.x() - 34, r.bottom() + 3, 68, 16),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                f"{t:g}",
            )
            t += step

        # Y 轴
        stepy = _nice_step(y1 - y0, 5)
        ty = math.ceil(max(y0, 0.0) / stepy) * stepy
        while ty <= y1 + 1e-9:
            p = self._to_px(x0, ty)
            painter.setPen(QPen(_GRID, 1))
            painter.drawLine(QPointF(r.left(), p.y()), QPointF(r.right(), p.y()))
            painter.setPen(_TEXT)
            painter.drawText(
                QRectF(4, p.y() - 8, self._MARGIN_L - 10, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                self._fmt_tick(ty),
            )
            ty += stepy

        painter.setPen(QPen(_AXIS, 1))
        painter.drawRect(r)
        painter.setPen(_TEXT)
        painter.drawText(
            QRectF(r.left(), self.height() - 16, r.width(), 14),
            Qt.AlignmentFlag.AlignHCenter, "2θ (°)",
        )
        painter.save()
        painter.translate(12, r.center().y() + 40)
        painter.rotate(-90)
        painter.drawText(QRectF(0, 0, 90, 14), Qt.AlignmentFlag.AlignLeft, "Intensity")
        painter.restore()

    @staticmethod
    def _fmt_tick(v: float) -> str:
        if abs(v) >= 1e6:
            return f"{v / 1e6:.1f}M"
        if abs(v) >= 1e4:
            return f"{v / 1e3:.1f}k"
        if abs(v) >= 1000:
            return f"{v:.0f}"
        return f"{v:g}"

    def _draw_curve(self, painter: QPainter) -> None:
        assert self._x is not None and self._y is not None
        r = self._plot_rect()
        n = self._x.size
        # 只画落在可视区间的点, 并对超长谱图做等距抽稀 (保证交互流畅)
        x0, x1 = self._xlim or (0.0, 1.0)
        lo = int(np.searchsorted(self._x, x0, side="left"))
        hi = int(np.searchsorted(self._x, x1, side="right"))
        lo = max(0, lo - 1)
        hi = min(n, max(hi + 1, lo + 2))
        xs, ys = self._x[lo:hi], self._y[lo:hi]
        max_draw = max(int(r.width()) * 2, 600)
        if xs.size > max_draw:
            sel = np.linspace(0, xs.size - 1, max_draw).astype(int)
            xs, ys = xs[sel], ys[sel]

        path = QPainterPath()
        base = self._to_px(xs[0], max(0.0, (self._ylim or (0.0, 1.0))[0]))
        path.moveTo(base)
        for xi, yi in zip(xs, ys):
            path.lineTo(self._to_px(float(xi), float(yi)))
        path.lineTo(self._to_px(float(xs[-1]), max(0.0, (self._ylim or (0.0, 1.0))[0])))
        path.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_CURVE_FILL)
        painter.drawPath(path)

        line = QPainterPath()
        line.moveTo(self._to_px(float(xs[0]), float(ys[0])))
        for xi, yi in zip(xs, ys):
            line.lineTo(self._to_px(float(xi), float(yi)))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(_CURVE, 1.4))
        painter.drawPath(line)

        # 最强峰标记 (只在可视区间内找)
        vis = np.asarray(self._y[lo:hi], dtype=float)
        if vis.size:
            k = int(np.argmax(vis))
            px = float(self._x[lo + k])
            py = float(vis[k])
            if x0 <= px <= x1:
                pt = self._to_px(px, py)
                painter.setPen(QPen(_PEAK, 1, Qt.PenStyle.DashLine))
                painter.drawLine(QPointF(pt.x(), r.bottom()), pt)
                painter.setBrush(_PEAK)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(pt, 3.2, 3.2)
                painter.setPen(_PEAK)
                painter.drawText(
                    QRectF(pt.x() + 4, pt.y() - 18, 150, 15),
                    Qt.AlignmentFlag.AlignLeft, f"{px:.3f}°  /  {py:.0f}",
                )

    def _draw_header(self, painter: QPainter) -> None:
        painter.setPen(_TITLE)
        font = QFont("Segoe UI", 10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(self._MARGIN_L, 6, self.width() - self._MARGIN_L - 20, 16),
                         Qt.AlignmentFlag.AlignLeft, self._title)
        painter.setPen(_TEXT)
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(QRectF(self._MARGIN_L, 20, self.width() - self._MARGIN_L - 20, 14),
                         Qt.AlignmentFlag.AlignLeft, self._subtitle)

    def _draw_hover(self, painter: QPainter) -> None:
        if self._hover is None or self._x is None:
            return
        r = self._plot_rect()
        if not r.contains(self._hover):
            return
        xv, _ = self._to_data(self._hover)
        if self._x.size == 0:
            return
        k = int(np.clip(np.searchsorted(self._x, xv), 0, self._x.size - 1))
        p = self._to_px(float(self._x[k]), float(self._y[k]))
        painter.setPen(QPen(_TEXT, 1, Qt.PenStyle.DotLine))
        painter.drawLine(QPointF(p.x(), r.top()), QPointF(p.x(), r.bottom()))
        painter.setBrush(_CURVE)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(p, 3.0, 3.0)
        painter.setPen(_TITLE)
        painter.drawText(
            QRectF(min(p.x() + 6, r.right() - 130), r.top() + 4, 130, 14),
            Qt.AlignmentFlag.AlignLeft,
            f"{self._x[k]:.3f}°,  {self._y[k]:.0f}",
        )

    # ---- 交互 --------------------------------------------------------

    def wheelEvent(self, event) -> None:  # noqa: N802
        if self._xlim is None:
            return
        factor = 0.85 if event.angleDelta().y() > 0 else 1.0 / 0.85
        pos = event.position()
        cx, cy = self._to_data(pos)
        self._zoom(factor, (cx, cy))
        self.update()

    def _zoom(self, factor: float, center: Optional[tuple[float, float]] = None) -> None:
        if self._xlim is None or self._ylim is None:
            return
        cx = center[0] if center else sum(self._xlim) / 2
        cy = center[1] if center else sum(self._ylim) / 2
        for attr, c in (("_xlim", cx), ("_ylim", cy)):
            lo, hi = getattr(self, attr)
            setattr(self, attr, (c - (c - lo) * factor, c + (hi - c) * factor))

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_from = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        self._hover = event.position()
        if self._drag_from is not None and self._xlim is not None:
            r = self._plot_rect()
            dx = (event.position().toPoint().x() - self._drag_from.x()) / max(r.width(), 1.0)
            dy = (event.position().toPoint().y() - self._drag_from.y()) / max(r.height(), 1.0)
            xr = self._xlim[1] - self._xlim[0]
            yr = self._ylim[1] - self._ylim[0]
            self._xlim = (self._xlim[0] - dx * xr, self._xlim[1] - dx * xr)
            self._ylim = (self._ylim[0] + dy * yr, self._ylim[1] + dy * yr)
            self._drag_from = event.position().toPoint()
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_from = None
        self.unsetCursor()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.reset_view()
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = None
        self.update()
