"""
主窗口
======
单文件/批量 XRD 谱图格式转换。左侧文件清单 (自动识别格式 + 探测结果), 右侧谱图预览,
底部选目标格式/输出目录并一键转换。

线程模型: 探测(读头)在 UI 线程同步做 (文件都很小); 真正的批量转换放在 QThread 里,
通过信号回报进度, 避免大文件时界面卡死。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PySide6.QtCore import QObject, Qt, QThread, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QDesktopServices,
    QDragEnterEvent,
    QDropEvent,
    QIcon,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from polyxrd_converter import __version__
from polyxrd_converter.converter import probe
from polyxrd_converter.i18n import LANGS, fmt_label, lang_name, language, set_language, tr
from polyxrd_converter.loader import detect_format
from polyxrd_converter.raw_formats import detect_raw_parser
from polyxrd_converter.ui_preview import SpectrumView
from polyxrd_converter.writers import TARGET_EXTS, TARGET_FORMATS

_STATUS_KEYS = {
    "ready": "status.ready",
    "ok": "status.ok",
    "fail": "status.fail",
    "bad_axis": "status.bad_axis",
    "truncated": "status.truncated",
    "error": "status.read_error",
}

_SCAN_EXTS = {".raw", ".xy", ".txt", ".dat", ".csv", ".mdi", ".xrdml", ".xml",
              ".brml", ".json", ".smz", ".asc",
              # GSAS-II 系文本格式 (谱图):
              ".gsas", ".fxye", ".gda", ".gsa", ".gss",
              ".ras", ".rasx", ".xye", ".qye", ".chi", ".qchi",
              # 岛津 Shimadzu 私有容器的伴随扩展名 (与 .RAW 同结构, 均为扫描谱):
              # .org 原始 / .rsm 平滑 / .rbg 背底 / .rk1 Kα1 剥离 / .rlz / .rax / .rfi
              ".org", ".rsm", ".rbg", ".rk1", ".rlz", ".rax", ".rfi"}


@dataclass
class Row:
    """文件清单里的一行。"""

    path: Path
    points: int = 0
    format_label: str = ""
    fmt_key: str = ""        # i18n 用的格式 key (RAW 时是 raw_variant), 切语言时重查
    x_range: str = ""
    peak: str = ""
    status: str = "ready"
    message: str = ""
    axis_confident: bool = True
    truncated: bool = False
    manual_axis: Optional[tuple[float, float]] = None
    data: object = None          # XRDData, 惰性保留给预览


# ----------------------------------------------------------------------
# 手动指定角度轴
# ----------------------------------------------------------------------

class AxisDialog(QDialog):
    """RAW 角度轴不可信时的人工兜底: 填起始 2θ 与步长。"""

    def __init__(self, parent: QWidget, row: Row) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.axis.title"))
        self.setMinimumWidth(420)
        self._n = row.points

        root = QVBoxLayout(self)
        hint = QLabel(tr("dlg.axis.hint", name=row.path.name, n=row.points)
                      + "\n\n" + tr("tip.rocking_scan"))
        hint.setWordWrap(True)
        root.addWidget(hint)

        form = QFormLayout()
        self._start = QDoubleSpinBox()
        self._start.setRange(0.0, 179.0)
        self._start.setDecimals(4)
        self._start.setSingleStep(0.1)
        self._start.setValue(10.0)
        self._step = QDoubleSpinBox()
        self._step.setRange(0.0001, 5.0)
        self._step.setDecimals(4)
        self._step.setSingleStep(0.01)
        self._step.setValue(0.02)
        form.addRow(tr("dlg.axis.start"), self._start)
        form.addRow(tr("dlg.axis.step"), self._step)
        root.addLayout(form)

        self._end = QLabel("")
        root.addWidget(self._end)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._start.valueChanged.connect(self._sync)
        self._step.valueChanged.connect(self._sync)
        self._sync()

    def _sync(self) -> None:
        end = self._start.value() + self._step.value() * max(self._n - 1, 0)
        self._end.setText(tr("dlg.axis.end", end=f"{end:.3f}"))

    def _on_ok(self) -> None:
        end = self._start.value() + self._step.value() * max(self._n - 1, 0)
        if self._step.value() <= 0 or end > 180.0:
            QMessageBox.warning(self, tr("dlg.warning"), tr("dlg.axis_invalid"))
            return
        self.accept()

    def values(self) -> tuple[float, float]:
        return float(self._start.value()), float(self._step.value())


# ----------------------------------------------------------------------
# 转换线程
# ----------------------------------------------------------------------

class ConvertWorker(QObject):
    """在后台线程里逐个转换。"""

    progress = Signal(int, int, str)
    one_done = Signal(int, bool, str, str)   # index, ok, dst-or-msg, err
    finished = Signal(int, int)              # ok, fail

    def __init__(self, jobs: list[tuple[int, Path, Path, str, Optional[tuple[float, float]]]]) -> None:
        super().__init__()
        self._jobs = jobs

    def run(self) -> None:
        from polyxrd_converter.converter import convert_file

        ok = fail = 0
        total = len(self._jobs)
        for i, (index, src, dst, fmt, axis) in enumerate(self._jobs, 1):
            self.progress.emit(i, total, src.name)
            try:
                out = convert_file(src, dst, fmt, manual_axis=axis)
                ok += 1
                self.one_done.emit(index, True, str(out), "")
            except Exception as exc:  # noqa: BLE001
                fail += 1
                self.one_done.emit(index, False, "", str(exc))
        self.finished.emit(ok, fail)


# ----------------------------------------------------------------------
# 主窗口
# ----------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(tr("app.title"))
        self.resize(1180, 720)
        self.setAcceptDrops(True)

        self._rows: list[Row] = []
        self._thread: Optional[QThread] = None
        self._worker: Optional[ConvertWorker] = None

        self._build_ui()
        self._build_menu()
        self._update_buttons()

    # ---- UI ----------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        top = QHBoxLayout()
        self._btn_add = QPushButton(tr("btn.add_files"))
        self._btn_dir = QPushButton(tr("btn.add_dir"))
        self._btn_rm = QPushButton(tr("btn.remove"))
        self._btn_clear = QPushButton(tr("btn.clear"))
        for b in (self._btn_add, self._btn_dir, self._btn_rm, self._btn_clear):
            top.addWidget(b)
        top.addStretch(1)
        self._filecount = QLabel("")
        self._filecount.setStyleSheet("color:#5b6b7f;")
        top.addWidget(self._filecount)
        root.addLayout(top)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        # 左: 文件表
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels([
            tr("col.file"), tr("col.format"), tr("col.points"),
            tr("col.range"), tr("col.peak"), tr("col.status"),
        ])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in range(1, 6):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        splitter.addWidget(self._table)

        # 右: 预览
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(4)
        self._cap_preview = QLabel(tr("lbl.preview"))
        self._cap_preview.setStyleSheet("color:#1f2d3d;font-weight:600;")
        rl.addWidget(self._cap_preview)
        self._preview = SpectrumView()
        rl.addWidget(self._preview, 1)
        self._preview_info = QLabel("")
        self._preview_info.setWordWrap(True)
        self._preview_info.setStyleSheet("color:#5b6b7f;")
        rl.addWidget(self._preview_info)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)

        # 底部: 目标格式 + 输出目录 + 转换
        box = QGroupBox()
        bl = QVBoxLayout(box)
        line1 = QHBoxLayout()
        self._lbl_target = QLabel(tr("lbl.target"))
        line1.addWidget(self._lbl_target)
        self._fmt = QComboBox()
        self._fill_targets()
        line1.addWidget(self._fmt, 2)
        line1.addSpacing(12)
        self._lbl_outdir = QLabel(tr("lbl.outdir"))
        line1.addWidget(self._lbl_outdir)
        self._outdir = QLineEdit()
        self._outdir.setPlaceholderText(tr("lbl.outdir_same"))
        line1.addWidget(self._outdir, 4)
        self._btn_outdir = QPushButton(tr("btn.browse"))
        line1.addWidget(self._btn_outdir)
        bl.addLayout(line1)

        line2 = QHBoxLayout()
        self._overwrite = QCheckBox(tr("lbl.overwrite"))
        self._overwrite.setChecked(True)
        line2.addWidget(self._overwrite)
        line2.addStretch(1)
        self._progress = QProgressBar()
        self._progress.setMaximumWidth(260)
        self._progress.setValue(0)
        line2.addWidget(self._progress)
        self._btn_convert = QPushButton(tr("btn.convert"))
        self._btn_convert.setObjectName("primary")
        self._btn_convert.setMinimumWidth(120)
        line2.addWidget(self._btn_convert)
        self._btn_open = QPushButton(tr("btn.open_out"))
        line2.addWidget(self._btn_open)
        bl.addLayout(line2)
        root.addWidget(box)

        # 日志
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(2000)
        self._log.setFixedHeight(120)
        root.addWidget(self._log)

        # 连接
        self._btn_add.clicked.connect(self._on_add_files)
        self._btn_dir.clicked.connect(self._on_add_dir)
        self._btn_rm.clicked.connect(self._on_remove)
        self._btn_clear.clicked.connect(self._on_clear)
        self._btn_convert.clicked.connect(self._on_convert)
        self._btn_open.clicked.connect(self._on_open_outdir)
        self._btn_outdir.clicked.connect(self._on_browse_outdir)
        # 用选择变化而非"当前单元格变化": selectRow()/程序化选中不会改当前单元格,
        # 只连 currentCellChanged 会导致选中行却不刷新预览。
        self._table.itemSelectionChanged.connect(self._update_preview)
        self._table.customContextMenuRequested.connect(self._on_context_menu)

        self._log.appendPlainText(tr("lbl.empty_hint"))

    def _fill_targets(self) -> None:
        """目标格式下拉: 文案取自 i18n, 切语言时重填并保住当前选中项。"""
        cur = self._fmt.currentData()
        self._fmt.blockSignals(True)
        self._fmt.clear()
        for key, _ext, label in TARGET_FORMATS:
            self._fmt.addItem(tr(label), key)
        if cur:
            i = self._fmt.findData(cur)
            if i >= 0:
                self._fmt.setCurrentIndex(i)
        self._fmt.blockSignals(False)

    def _update_filecount(self) -> None:
        n = len(self._rows)
        self._filecount.setText("" if not n else tr("lbl.filecount", n=n))

    def _row_label(self, row: Row) -> str:
        """行的格式展示名: 按当前语言重查 (RAW 变体走 raw_variant)。"""
        return fmt_label(row.fmt_key, fallback=row.format_label) or "…"

    def _build_menu(self) -> None:
        bar = self.menuBar()
        mf = bar.addMenu(tr("menu.file"))
        a1 = QAction(tr("menu.file.add"), self)
        a1.triggered.connect(self._on_add_files)
        a2 = QAction(tr("menu.file.add_dir"), self)
        a2.triggered.connect(self._on_add_dir)
        a3 = QAction(tr("menu.file.exit"), self)
        a3.triggered.connect(self.close)
        mf.addActions([a1, a2])
        mf.addSeparator()
        mf.addAction(a3)

        ml = bar.addMenu(tr("menu.lang"))
        # 由 i18n.LANGS 生成, 新增语言只需改 i18n 一处; 名称用母语写法, 不翻译。
        grp = QActionGroup(self)
        grp.setExclusive(True)
        self._lang_actions: dict[str, QAction] = {}
        for code in LANGS:
            act = QAction(lang_name(code), self, checkable=True)
            act.setChecked(code == language())
            act.triggered.connect(lambda _c=False, c=code: self._switch_lang(c))
            ml.addAction(act)
            grp.addAction(act)
            self._lang_actions[code] = act

        mh = bar.addMenu(tr("menu.help"))
        ab = QAction(tr("menu.help.about"), self)
        ab.triggered.connect(self._on_about)
        mh.addAction(ab)

    def _switch_lang(self, lang: str) -> None:
        """切换界面语言: 菜单/控件/清单/预览全部即时重译, 无需重启。"""
        set_language(lang)
        self._retranslate_ui()
        self._log.appendPlainText(tr("tip.lang_switched", lang=lang_name(lang)))

    def _retranslate_ui(self) -> None:
        # 1) 菜单栏重建 (文案写在 QAction 里, 重建最省心)
        self.menuBar().clear()
        self._build_menu()
        # 2) 静态控件文案
        self.setWindowTitle(tr("app.title"))
        self._btn_add.setText(tr("btn.add_files"))
        self._btn_dir.setText(tr("btn.add_dir"))
        self._btn_rm.setText(tr("btn.remove"))
        self._btn_clear.setText(tr("btn.clear"))
        self._btn_convert.setText(tr("btn.convert"))
        self._btn_open.setText(tr("btn.open_out"))
        self._btn_outdir.setText(tr("btn.browse"))
        self._lbl_target.setText(tr("lbl.target"))
        self._lbl_outdir.setText(tr("lbl.outdir"))
        self._outdir.setPlaceholderText(tr("lbl.outdir_same"))
        self._overwrite.setText(tr("lbl.overwrite"))
        self._cap_preview.setText(tr("lbl.preview"))
        self._table.setHorizontalHeaderLabels([
            tr("col.file"), tr("col.format"), tr("col.points"),
            tr("col.range"), tr("col.peak"), tr("col.status"),
        ])
        self._fill_targets()
        self._update_filecount()
        # 3) 依赖语言的行内容 (状态列 + 预览副标题/提示)
        self._refresh_table()
        self._update_preview()
        self._preview.update()

    # ---- 文件清单 ----------------------------------------------------

    def add_paths(self, paths: list[Path]) -> None:
        files: list[Path] = []
        for p in paths:
            p = Path(p)          # 容忍 str 入参 (作为库调用时常见)
            if p.is_dir():
                files.extend(sorted(
                    f for f in p.rglob("*")
                    if f.is_file() and f.suffix.lower() in _SCAN_EXTS
                ))
            elif p.is_file():
                files.append(p)
        existing = {str(r.path.resolve()).lower() for r in self._rows}
        added = 0
        for f in files:
            key = str(f.resolve()).lower()
            if key in existing:
                continue
            existing.add(key)
            self._rows.append(Row(path=f))
            added += 1
        if added:
            self._probe_rows()
        self._refresh_table()
        self._update_filecount()

    def _probe_rows(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for row in self._rows:
                if row.format_label:
                    continue
                r = probe(row.path)
                row.points = r.points
                row.format_label = r.format_label if r.ok else (
                    f"{r.format_key}?" if r.format_key else "?"
                )
                row.message = r.message
                row.data = r.data
                row.fmt_key = str(
                    (row.data.metadata if row.data is not None else {}).get("raw_variant")
                    or r.format_key or ""
                )
                row.axis_confident = r.axis_confident
                row.truncated = r.truncated
                if not r.ok:
                    row.status = "error"
                    row.x_range = row.peak = "—"
                else:
                    row.x_range = f"{r.x_min:.3f} – {r.x_max:.3f}"
                    row.peak = f"{r.y_max:.0f}"
                    if not r.axis_confident:
                        row.status = "bad_axis"
                    elif r.truncated:
                        # 文件被截断: 数据是真的但比头里声明少, 提示而非拦截
                        row.status = "truncated"
                        _m = row.data.metadata if row.data is not None else {}
                        row.message = tr("tip.truncated",
                                         declared=_m.get("declared_points", "?"),
                                         kept=r.points)
                    else:
                        row.status = "ready"
        finally:
            QApplication.restoreOverrideCursor()

    def _refresh_table(self) -> None:
        cur = self._table.currentRow()
        self._table.blockSignals(True)
        self._table.setRowCount(len(self._rows))
        for i, row in enumerate(self._rows):
            values = [
                row.path.name,
                self._row_label(row) if row.fmt_key or row.format_label else "…",
                f"{row.points:,}" if row.points else "—",
                row.x_range or "—",
                row.peak or "—",
                tr(_STATUS_KEYS.get(row.status, "status.ready")),
            ]
            for c, text in enumerate(values):
                item = QTableWidgetItem(text)
                if c == 0:
                    item.setToolTip(str(row.path))
                if c == 5:
                    if row.status == "bad_axis":
                        item.setForeground(Qt.GlobalColor.darkYellow)
                        item.setToolTip(tr("tip.axis_warn", n=row.points)
                                       + "\n\n" + tr("tip.rocking_scan"))
                    elif row.status == "truncated":
                        item.setForeground(Qt.GlobalColor.darkYellow)
                        item.setToolTip(row.message)
                    elif row.status == "ok":
                        item.setForeground(Qt.GlobalColor.darkGreen)
                    elif row.status in ("fail", "error"):
                        item.setForeground(Qt.GlobalColor.red)
                        item.setToolTip(row.message)
                    if row.manual_axis:
                        item.setToolTip(tr("tip.axis_manual",
                                           x0=f"{row.manual_axis[0]:g}",
                                           step=f"{row.manual_axis[1]:g}"))
                self._table.setItem(i, c, item)
        self._table.blockSignals(False)
        if 0 <= cur < self._table.rowCount():
            self._table.selectRow(cur)
        elif self._table.rowCount() > 0 and not self._table.selectedIndexes():
            # 首次载入/清空后没有选中行时, 自动选第一行, 让预览立刻有内容
            self._table.selectRow(0)
        self._update_buttons()

    def _update_buttons(self) -> None:
        has = bool(self._rows)
        self._btn_convert.setEnabled(has)
        self._btn_rm.setEnabled(has)
        self._btn_clear.setEnabled(has)
        self._btn_outdir.setEnabled(True)

    # ---- 预览 --------------------------------------------------------

    def _current_rows(self) -> list[Row]:
        idx = sorted({i.row() for i in self._table.selectedIndexes()})
        return [self._rows[i] for i in idx if 0 <= i < len(self._rows)]

    def _update_preview(self) -> None:
        rows = self._current_rows()
        if not rows:
            self._preview.set_data(None, None)
            self._preview_info.setText("")
            return
        row = rows[0]
        if row.data is None:
            self._preview.set_data(None, None)
            self._preview_info.setText(row.message or "")
            return
        data = row.data
        sub = (f"{self._row_label(row)}   ·   {len(data):,} pts   ·   "
               f"{row.x_range}°   ·   λ={data.wavelength or 0:.4f} Å")
        note = ""
        if not row.axis_confident:
            note = "⚠"
        self._preview.set_data(data.two_theta, data.intensity,
                               title=row.path.name, subtitle=sub, note=note)
        if not row.axis_confident:
            self._preview_info.setText(
                (tr("tip.axis_warn", n=len(data)) if not row.manual_axis
                 else tr("tip.axis_manual", x0=f"{row.manual_axis[0]:g}",
                         step=f"{row.manual_axis[1]:g}"))
                + "\n\n" + tr("tip.rocking_scan")
            )
        else:
            self._preview_info.setText("")
        if len(rows) > 1:
            self._preview_info.setText(
                self._preview_info.text()
                + "\n" + tr("tip.multi_preview", n=len(rows)))

    # ---- 交互 --------------------------------------------------------

    def _on_add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, tr("menu.file.add"), str(Path.home()), tr("filter.open")
        )
        if paths:
            self.add_paths([Path(p) for p in paths])

    def _on_add_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, tr("filter.dirtitle"), str(Path.home()))
        if d:
            self.add_paths([Path(d)])

    def _on_remove(self) -> None:
        idx = sorted({i.row() for i in self._table.selectedIndexes()}, reverse=True)
        for i in idx:
            if 0 <= i < len(self._rows):
                self._rows.pop(i)
        self._refresh_table()
        self._update_preview()

    def _on_clear(self) -> None:
        self._rows.clear()
        self._refresh_table()
        self._update_preview()

    def _on_browse_outdir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, tr("lbl.outdir"), str(Path.home()))
        if d:
            self._outdir.setText(d)

    def _on_open_outdir(self) -> None:
        p = self._outdir.text().strip()
        target = Path(p) if p else (self._rows[0].path.parent if self._rows else Path.home())
        if target.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    def _on_context_menu(self, pos) -> None:
        rows = self._current_rows()
        if not rows:
            return
        menu = QMenu(self)
        act_axis = menu.addAction(tr("dlg.axis.title"))
        act_axis.setEnabled(rows[0].data is not None)
        menu.addSeparator()
        act_open = menu.addAction(tr("ctx.open_dir"))
        act_rm = menu.addAction(tr("btn.remove"))
        chosen = menu.exec(self._table.viewport().mapToGlobal(pos))
        if chosen is act_axis:
            self._set_manual_axis(rows[0])
        elif chosen is act_open:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(rows[0].path.parent)))
        elif chosen is act_rm:
            self._on_remove()

    def _set_manual_axis(self, row: Row) -> None:
        dlg = AxisDialog(self, row)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        start, step = dlg.values()
        row.manual_axis = (start, step)
        r = probe(row.path, manual_axis=row.manual_axis)
        row.points = r.points
        row.data = r.data
        row.axis_confident = r.axis_confident
        row.x_range = f"{r.x_min:.3f} – {r.x_max:.3f}" if r.ok else "—"
        row.peak = f"{r.y_max:.0f}" if r.ok else "—"
        row.status = "ready" if r.ok else "error"
        self._refresh_table()
        self._update_preview()
        self._log.appendPlainText(tr("tip.axis_manual", x0=f"{start:g}", step=f"{step:g}")
                                  + f"  [{row.path.name}]")

    # ---- 转换 --------------------------------------------------------

    def _on_convert(self) -> None:
        if self._thread is not None:
            return
        if not self._rows:
            QMessageBox.warning(self, tr("dlg.warning"), tr("dlg.need_files"))
            return

        fmt = str(self._fmt.currentData())
        ext = TARGET_EXTS[fmt]
        outdir_text = self._outdir.text().strip()
        outdir = Path(outdir_text) if outdir_text else None
        if outdir is not None:
            outdir.mkdir(parents=True, exist_ok=True)

        jobs: list[tuple[int, Path, Path, str, Optional[tuple[float, float]]]] = []
        skipped: list[Path] = []
        existing: list[Path] = []
        for i, row in enumerate(self._rows):
            if row.data is None:
                continue
            src = row.path
            dst = (outdir / (src.stem + ext)) if outdir else src.with_suffix(ext)
            try:
                if dst.resolve() == src.resolve():
                    skipped.append(src)
                    continue
            except OSError:
                pass
            if dst.exists():
                if not self._overwrite.isChecked():
                    skipped.append(dst)
                    continue
                existing.append(dst)
            jobs.append((i, src, dst, fmt, row.manual_axis))

        if not jobs:
            self._log.appendPlainText(tr("log.no_files"))
            return

        if existing:
            ans = QMessageBox.question(
                self, tr("dlg.confirm"), tr("dlg.overwrite_q", n=len(existing))
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        for s in skipped:
            self._log.appendPlainText(f"— 跳过 (suffix collision): {s.name}")

        self._progress.setValue(0)
        self._progress.setMaximum(len(jobs))
        self._set_busy(True)
        self._log.appendPlainText(tr("log.batch", n=len(jobs), fmt=fmt))

        self._thread = QThread(self)
        self._worker = ConvertWorker(jobs)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.one_done.connect(self._on_one_done)
        self._worker.finished.connect(self._on_finished)
        self._thread.start()

    def _on_progress(self, i: int, n: int, name: str) -> None:
        self._progress.setValue(i)
        self._progress.setFormat(f"{i}/{n}  {name}")

    def _on_one_done(self, index: int, ok: bool, dst: str, err: str) -> None:
        if not (0 <= index < len(self._rows)):
            return
        row = self._rows[index]
        if ok:
            row.status = "ok"
            self._log.appendPlainText(tr("log.converted", src=row.path.name,
                                         dst=Path(dst).name))
        else:
            row.status = "fail"
            row.message = err
            self._log.appendPlainText(tr("log.failed", src=row.path.name, err=err))

    def _on_finished(self, ok: int, fail: int) -> None:
        self._thread.quit()
        self._thread.wait()
        self._thread = None
        self._worker = None
        self._set_busy(False)
        self._refresh_table()
        self._log.appendPlainText(tr("log.summary", ok=ok, fail=fail))
        if self._outdir.text().strip() == "" and ok:
            pass

    def _set_busy(self, busy: bool) -> None:
        self._btn_convert.setEnabled(not busy)
        self._btn_add.setEnabled(not busy)
        self._btn_dir.setEnabled(not busy)
        self._btn_clear.setEnabled(not busy)
        if not busy:
            self._progress.setFormat("")
            self._progress.setValue(0)

    # ---- 拖放 --------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths = [Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.add_paths(paths)
            event.acceptProposedAction()

    # ---- 其它 --------------------------------------------------------

    def _on_about(self) -> None:
        QMessageBox.about(self, tr("menu.help.about"), tr("dlg.about", version=__version__))
