"""GUI 冒烟测试 (离屏运行)。

不需要真实屏幕: 用 QT_QPA_PLATFORM=offscreen 构造窗口, 走一遍
"加载样本 → 表格填充 → 预览渲染 → 转换落盘 → 轴不可信拦截" 的关键路径,
任何一步抛异常都算失败。

    python tests/smoke_gui.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from polyxrd_converter import __version__  # noqa: E402
from polyxrd_converter.app import _STYLE  # noqa: E402
from polyxrd_converter.converter import convert_file, probe  # noqa: E402
from polyxrd_converter.loader import load_pattern  # noqa: E402
from polyxrd_converter.ui_main import MainWindow  # noqa: E402
from polyxrd_converter.ui_preview import SpectrumView, _nice_step  # noqa: E402

OK, FAIL = [], []


def check(cond: bool, msg: str) -> None:
    (OK if cond else FAIL).append(msg)
    print(("  ✓ " if cond else "  ✗ ") + msg)


def pump(ms: int = 120) -> None:
    """跑一小段事件循环, 让 QThread 的回调有机会执行。"""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


XR = Path(r"D:/Project/XRD")
SAMPLES = {
    "shimadzu": XR / "XRData" / "Shimadzu Data" / "Std" / "Si" / "Si.RAW",
    "rigaku": XR / "XRData" / "csuHJW" / "Data007：铜衍射谱系列.raw",
    "raw2": XR / "test_xrd" / "geshi" / "4-1.raw",
    "bruker_bad": XR / "XRData" / "csuHJW" / "data035：硬质合金深冷处理后WC相的残余应力.raw",
    "txt": XR / "XRData" / "csuHJW" / "data006：AlCoO-750C.TXT",
}


def main() -> int:
    print("=" * 78)
    print(f"PolyXRD Converter GUI 冒烟测试 (v{__version__})")
    print("=" * 78)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(_STYLE)

    # --- 0) 纯函数: 刻度 ---
    print("\n=== 0) 预览刻度算法 ===")
    check(_nice_step(55.0) in (10.0, 20.0), f"_nice_step(55)={_nice_step(55.0)}")
    check(_nice_step(0) == 1.0, "_nice_step(0) 兜底为 1")

    # --- 1) 构造主窗口 ---
    print("\n=== 1) 构造主窗口 ===")
    win = MainWindow()
    win.resize(1180, 720)
    win.show()
    pump()
    check(win.isVisible(), "MainWindow 构造并显示成功")
    check(win.windowTitle() == "PolyXRD Converter" or bool(win.windowTitle()),
          f"窗口标题 = {win.windowTitle()!r}")
    check(win._table.columnCount() == 6, "文件表 6 列")
    check(win._btn_convert.isEnabled() is False, "无文件时转换按钮禁用")

    # --- 2) 加载真实样本 (混合 3 种 RAW 变体 + 1 个文本) ---
    print("\n=== 2) 加载真实样本 (RAW 自动识别) ===")
    paths = [p for p in SAMPLES.values() if p.exists()]
    if not paths:
        print("  样本不存在, 跳过 (无法验证 GUI 数据流)"); FAIL.append("样本缺失")
    win.add_paths(paths)
    pump()
    n_loaded = win._table.rowCount()
    check(n_loaded == len(paths), f"表格载入 {n_loaded}/{len(paths)} 个文件")
    check(win._btn_convert.isEnabled() is True, "有文件时转换按钮启用")

    rows = {r.path.name: r for r in win._rows}
    for tag, p in SAMPLES.items():
        if not p.exists():
            continue
        r = rows.get(p.name)
        if r is None:
            check(False, f"{tag}: 行缺失"); continue
        check(r.points > 0 and r.format_label not in ("", "?"),
              f"{tag}: {p.name[:26]:28s} fmt={r.format_label!r} n={r.points} "
              f"x={r.x_range}")
        # 与后台 probe 结果一致性
        pr = probe(p)
        check(pr.points == r.points, f"{tag}: 表格点数与 probe 一致 ({r.points})")

    # Jade/MDI 文本导出: 头里 start/step/stop/npoints, 单列定宽强度
    tj = rows.get(SAMPLES["txt"].name) if SAMPLES["txt"].exists() else None
    if tj is not None:
        check(tj.points == 2201 and tj.x_range.startswith("15.000"),
              f"Jade .txt 正确解析 n={tj.points} x={tj.x_range} (期望 2201 / 15.000)")
        check("Jade" in tj.format_label,
              f"Jade .txt 格式标签 = {tj.format_label!r}")

    # 岛津 Shimadzu 私有容器 (int32 强度 + 变长头)
    sx = rows.get(SAMPLES["shimadzu"].name) if SAMPLES["shimadzu"].exists() else None
    if sx is not None:
        check("Shimadzu" in sx.format_label and sx.points == 5751,
              f"Shimadzu .RAW 正确解析 fmt={sx.format_label!r} n={sx.points}")
        check(sx.x_range.startswith("25.000") and sx.axis_confident,
              f"Shimadzu .RAW 角度轴 = {sx.x_range}")

    # --- 3) 预览渲染 ---
    print("\n=== 3) 谱图预览渲染 ===")
    rigaku = rows.get(SAMPLES["rigaku"].name)
    if rigaku and rigaku.data is not None:
        # 显式选中该样本所在行 (不要依赖行序)
        win._table.selectRow(next(i for i, r in enumerate(win._rows)
                                  if r.path == rigaku.path))
        pump()
        sv = win._preview
        check(isinstance(sv, SpectrumView), "预览控件类型正确")
        check(sv._x is not None and sv._x.size == rigaku.points,
              f"预览已装载 {0 if sv._x is None else sv._x.size} 个点")
        # 真正触发 paintEvent: 渲染到一张离屏图
        from PySide6.QtGui import QPixmap
        pm = QPixmap(600, 360)
        sv.resize(600, 360)
        sv.render(pm)
        img = pm.toImage()
        # 非全白 => 画出了东西
        nonwhite = 0
        for xx in range(0, 600, 5):
            for yy in range(0, 360, 5):
                c = img.pixelColor(xx, yy)
                if c.red() < 250 or c.green() < 250 or c.blue() < 250:
                    nonwhite += 1
        check(nonwhite > 20, f"paintEvent 实际画出内容 (非空白像素采样 {nonwhite})")
        # 缩放/复位不崩
        sv._zoom(0.5)
        sv.reset_view()
        check(sv._ylim is not None, "缩放/复位后视图范围有效")
    else:
        print("  Rigaku 样本缺失, 跳过预览")

    # --- 4) 轴不可信样本: 预览打标 & 转换被拦 ---
    print("\n=== 4) 角度轴不可信样本 (Bruker data035) ===")
    bp = SAMPLES["bruker_bad"]
    if bp.exists():
        br = rows.get(bp.name)
        check(br is not None and br.axis_confident is False,
              "Bruker 样本被标为 axis_confident=False")
        check(br is not None and br.status == "bad_axis",
              f"表格状态 = {br.status if br else None!r} (期望 bad_axis)")
        try:
            convert_file(bp, Path(tempfile.gettempdir()) / "should_not_write.xy")
            check(False, "轴不可信却允许转换 (应被拦)")
        except Exception as e:  # noqa: BLE001
            check("角度轴不可信" in str(e), f"转换被正确拦截: {str(e)[:48]}…")
    else:
        print("  Bruker 样本缺失, 跳过")

    # --- 5) 批量转换落盘 (Rigaku + RAW2 + txt → xrdml / csv) ---
    print("\n=== 5) 批量转换落盘 ===")
    with tempfile.TemporaryDirectory() as td:
        outdir = Path(td) / "out"
        win._outdir.setText(str(outdir))
        win._overwrite.setChecked(True)
        want = []
        for i, row in enumerate(win._rows):
            if row.data is not None and row.axis_confident:
                want.append(i)

        # 目标格式切到 xrdml
        idx = win._fmt.findData("xrdml")
        check(idx >= 0, "目标格式下拉包含 xrdml")
        win._fmt.setCurrentIndex(idx)

        win._on_convert()
        # 等后台线程结束 (最多 10s)
        waited = 0
        while win._thread is not None and waited < 10000:
            pump(100); waited += 100
        check(win._thread is None, f"后台转换线程正常结束 (等待 {waited}ms)")

        produced = sorted(outdir.glob("*.xrdml")) if outdir.exists() else []
        check(len(produced) == len(want),
              f"落盘 {len(produced)}/{len(want)} 个 .xrdml")
        # 回读: 按主名把源与产出配对, 逐一点数/峰位守恒
        by_stem = {p.stem: p for p in produced}
        for row in win._rows:
            if row.data is None or not row.axis_confident:
                continue
            out = by_stem.get(row.path.stem)
            if out is None:
                check(False, f"{row.path.name}: 产出缺失"); continue
            d0 = load_pattern(row.path)
            d1 = load_pattern(out)
            same = (len(d0) == len(d1)
                    and np.allclose(d0.two_theta, d1.two_theta, atol=1e-5)
                    and np.allclose(d0.intensity, d1.intensity, atol=1e-2))
            check(same, f"{row.path.name[:22]:24s} -> xrdml 守恒 "
                        f"(n={len(d0)}->{len(d1)})")
        # 表格状态应更新为 ok
        ok_rows = [r for r in win._rows if r.status == "ok"]
        check(len(ok_rows) == len(want), f"表格状态更新为 ok 的行数 = {len(ok_rows)}")

    # --- 6) 语言切换不崩 ---
    print("\n=== 6) 语言切换 & 清理 ===")
    win._act_en.setChecked(True)
    check(True, "英文动作创建成功")
    win._on_clear()
    pump()
    check(win._table.rowCount() == 0, "清空列表后表格为 0 行")
    check(win._btn_convert.isEnabled() is False, "清空后转换按钮回到禁用")

    win.close()

    print("\n" + "=" * 78)
    print(f"通过 {len(OK)}  /  失败 {len(FAIL)}")
    if FAIL:
        print("\n失败明细:")
        for m in FAIL:
            print("  ✗", m)
    print("=" * 78)
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
