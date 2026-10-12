"""
应用入口
========
QApplication 引导 + 全局异常处理 + 命令行参数 (可直接把文件拖到 exe 上打开)。
"""
from __future__ import annotations

import sys
import tempfile
import traceback
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from polyxrd_converter import __app_name__, __version__
from polyxrd_converter.i18n import tr
from polyxrd_converter.ui_main import MainWindow

# 日文字体要在 Microsoft YaHei 之后兜上, 否则 Win 中文系统上日文会掉字形回退成宋体风
_STYLE = """
QWidget { font-family: "Microsoft YaHei UI","Yu Gothic UI","Meiryo UI","Segoe UI",sans-serif; font-size: 9.5pt; }
QMainWindow, QDialog { background: #f4f6fa; }
QGroupBox { background: #ffffff; border: 1px solid #dfe4ec; border-radius: 6px;
            margin-top: 6px; padding: 10px 8px 6px 8px; }
QTableWidget { background: #ffffff; border: 1px solid #dfe4ec; border-radius: 6px;
               gridline-color: #eef1f6; }
QHeaderView::section { background: #eef2f8; border: none; border-right: 1px solid #dfe4ec;
                       border-bottom: 1px solid #dfe4ec; padding: 5px 8px; font-weight: 600;
                       color: #334155; }
QTableWidget::item:selected { background: #dceafd; color: #10233d; }
QPushButton { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 5px;
              padding: 5px 12px; color: #23364d; }
QPushButton:hover { background: #eef4ff; border-color: #9dbcf0; }
QPushButton:disabled { color: #a8b3c2; background: #f4f6fa; }
QPushButton#primary { background: #1f6feb; border-color: #1a5fd0; color: #ffffff;
                      font-weight: 600; }
QPushButton#primary:hover { background: #3b82f6; }
QPushButton#primary:disabled { background: #a9c4ef; border-color: #a9c4ef; }
QLineEdit, QComboBox, QDoubleSpinBox { background: #ffffff; border: 1px solid #cbd5e1;
                                       border-radius: 5px; padding: 4px 7px; }
QPlainTextEdit { background: #fbfcfe; border: 1px solid #dfe4ec; border-radius: 6px;
                 font-family: Consolas,"Cascadia Mono",monospace; }
QProgressBar { border: 1px solid #dfe4ec; border-radius: 5px; background: #ffffff;
               text-align: center; height: 18px; }
QProgressBar::chunk { background: #1f6feb; border-radius: 4px; }
"""


def _excepthook(exc_type, exc, tb) -> None:
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    sys.stderr.write(text)
    try:
        app = QApplication.instance()
        if app is not None:
            QMessageBox.critical(None, tr("err.crash_title"), text[-4000:])
    except Exception:
        pass


def _selftest(argv: list[str]) -> int:
    """无界面自检 (给冻结 exe 用, console=False 时 stdout 不可见, 走报告文件)。

    用法: ``PolyXRD-Converter.exe --selftest a.raw b.txt --report out.txt``
    对每个给定文件做 探测 → 转换 (xrdml) → 回读 点数守恒 检查;
    轴不可信的文件期望被拒。退出码: 0 = 全过, 1 = 有失败。
    """
    from polyxrd_converter.converter import convert_file, probe

    args = argv[1:]
    report_path: Optional[Path] = None
    files: list[Path] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--report" and i + 1 < len(args):
            report_path = Path(args[i + 1])
            i += 2
            continue
        if a.startswith("--"):
            i += 1
            continue
        files.append(Path(a))
        i += 1

    lines = [f"PolyXRD Converter {__version__} self-test", f"files: {len(files)}"]
    ok = fail = 0
    tmp = Path(tempfile.mkdtemp(prefix="polyxrd_selftest_"))
    for f in files:
        r = probe(f)
        if not r.ok:
            fail += 1
            lines.append(f"[FAIL] {f.name}: {r.message}")
            continue
        lines.append(f"[ OK ] {f.name}: {r.format_label} n={r.points} "
                     f"x=[{r.x_min:.3f},{r.x_max:.3f}] axis_confident={r.axis_confident} "
                     f"truncated={r.truncated}")
        if r.axis_confident:
            try:
                out = convert_file(f, tmp / (f.stem + ".xrdml"))
                back = probe(out)
                if back.ok and back.points == r.points:
                    ok += 1
                    lines.append(f"       -> xrdml 回读 n={back.points} OK")
                else:
                    fail += 1
                    lines.append(f"       -> xrdml 回读点数不符: {back.points} vs {r.points}")
            except Exception as exc:  # noqa: BLE001
                fail += 1
                lines.append(f"       -> 转换失败: {exc}")
        else:
            try:
                convert_file(f, tmp / (f.stem + ".xy"))
                fail += 1
                lines.append("       -> BUG: 轴不可信却允许转换")
            except Exception:  # noqa: BLE001
                ok += 1
                lines.append("       -> 轴不可信, 正确拒绝转换")

    lines.append(f"RESULT ok={ok} fail={fail}")
    text = "\n".join(lines)
    if report_path is not None:
        report_path.write_text(text, encoding="utf-8")
    else:
        try:
            sys.stdout.write(text + "\n")
        except Exception:  # noqa: BLE001 - 冻结窗口程序无 stdout
            pass
    return 1 if fail else 0


def run(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if "--selftest" in argv:
        return _selftest(argv)
    app = QApplication(argv)
    app.setApplicationName(__app_name__)
    app.setOrganizationName("PolyXRD")
    app.setApplicationVersion(__version__)
    app.setStyleSheet(_STYLE)
    app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)
    sys.excepthook = _excepthook

    icon_path = Path(__file__).with_name("resources") / "icon.ico"
    if icon_path.exists():
        from PySide6.QtGui import QIcon

        app.setWindowIcon(QIcon(str(icon_path)))

    win = MainWindow()
    files = [Path(a) for a in argv[1:] if Path(a).exists()]
    if files:
        win.add_paths(files)
    win.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run())
