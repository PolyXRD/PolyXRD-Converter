"""把真实样本全量跑一遍, 交叉校验 RAW 解析结果。

可直接跑: python tests/validate_samples.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from polyxrd_converter.loader import detect_format, load_pattern  # noqa: E402
from polyxrd_converter.raw_formats import detect_raw_parser, parse_raw  # noqa: E402

OK, FAIL = [], []


def check(cond: bool, msg: str) -> None:
    if cond and os.environ.get("VERBOSE"):
        print("  ✓", msg)
    (OK if cond else FAIL).append(msg)


def load_text_pairs(d: Path) -> dict[str, np.ndarray]:
    """把目录里的两列文本 (.txt) 读成 {主名: (x, y)}。"""
    from polyxrd_converter.loader import _load_text

    out = {}
    for f in d.glob("*.txt"):
        try:
            data = _load_text(f, "txt")
            out[f.stem] = np.column_stack([data.two_theta, data.intensity])
        except Exception:
            pass
    for f in d.glob("*.TXT"):
        try:
            data = _load_text(f, "txt")
            out[f.stem] = np.column_stack([data.two_theta, data.intensity])
        except Exception:
            pass
    return out


# ---------------------------------------------------------------- Rigaku FI
#: 已知异常样本: 文件头里的 (end, step) 是坏的 (end=195° > 180°), 真值是 2θ 15→70°,
#: 275 点。parser 会把它标成"角度轴不可信"并拒绝自动转换, 这里显式断言该行为。
KNOWN_BAD_AXIS = {"data006：AlCoO-750C"}


def validate_rigaku(base: Path) -> None:
    print("\n=== 1) Rigaku FI (XRData/csuHJW) ===")
    raws = sorted(base.glob("*.raw"))
    if not raws:
        print("  样本目录不存在, 跳过"); return
    txts = load_text_pairs(base)
    n_fi = 0
    for rp in raws:
        magic = rp.read_bytes()[:4]
        parser = detect_raw_parser(rp.read_bytes())
        if parser.key != "rigaku_raw":
            print(f"  [skip] {rp.name[:28]:30s} magic={magic!r} -> {parser.key}")
            continue
        n_fi += 1
        try:
            d = load_pattern(rp)
        except Exception as e:
            check(False, f"FI {rp.name}: 读取失败 {e}")
            continue

        if rp.stem in KNOWN_BAD_AXIS:
            check(d.metadata.get("axis_confident") is False,
                  f"FI {rp.name[:26]}: 头中轴参数已损坏, 已正确标记为不可信")
            try:
                load_pattern(rp) and None
            except Exception:
                pass
            # 自动转换必须被拦住
            try:
                from polyxrd_converter.converter import convert_file
                convert_file(rp, rp.with_suffix(".xy"))
                check(False, f"FI {rp.name[:26]}: 轴不可信时竟然允许自动转换")
            except Exception:
                check(True, f"FI {rp.name[:26]}: 轴不可信时已拒绝自动转换 (要求人工指定)")
            continue

        twin = txts.get(rp.stem)
        if twin is not None and twin.shape[0] == len(d):
            dx = np.max(np.abs(twin[:, 0] - d.two_theta))
            dy = np.max(np.abs(twin[:, 1] - d.intensity))
            check(dx < 5e-4 and dy < 1e-6,
                  f"FI {rp.name[:26]}: 与 .txt 逐点一致 (n={len(d)}, dx={dx:.2e}, dy={dy:.2e})")
        else:
            check(d.metadata.get("axis_confident") is True and len(d) > 100,
                  f"FI {rp.name[:26]}: n={len(d)} x=[{d.two_theta[0]:.3f},{d.two_theta[-1]:.3f}]")
    print(f"  FI 样本 {n_fi} 个")


# ---------------------------------------------------------------- 手动定轴
def validate_manual_axis(base: Path) -> None:
    """data006 自动定轴失败 → 人工给 (起始 2θ, 步长) 后必须与真值对齐。"""
    print("\n=== 1b) 手动指定角度轴 (data006 回归) ===")
    rp = base / "data006：AlCoO-750C.raw"
    tp = base / "data006：AlCoO-750C.TXT"
    if not rp.exists() or not tp.exists():
        print("  样本不存在, 跳过"); return

    from polyxrd_converter.loader import _read_numeric_rows

    # data006.TXT 是 MDI 风格 (8F7 单列强度 + 头), 需按行拆出全部数值, 再按个数定长
    all_rows, _lines = _read_numeric_rows(tp)
    y_txt = np.array([v for row in all_rows for v in row], dtype=float)
    x_txt = 15.0 + 0.025 * np.arange(len(y_txt))

    n = len(load_pattern(rp))               # 275
    step = (70.0 - 15.0) / (n - 1)
    d = load_pattern(rp, manual_axis=(15.0, step))
    check(d.metadata.get("axis_confident") is True and d.metadata.get("axis_source") == "manual",
          "data006: 手动定轴后 axis_confident=True")

    # 手工轴下 raw 的峰位应与 txt 对齐 (逐点形状相关)
    m = d.two_theta <= x_txt[-1] + 0.5
    yi = np.interp(d.two_theta[m], x_txt, y_txt)
    corr = float(np.corrcoef(yi, d.intensity[m])[0, 1]) if m.sum() > 5 else float("nan")
    check(corr > 0.9, f"data006: 手动定轴后与同名 .TXT 形状相关 {corr:.3f} (>0.9)")


# ---------------------------------------------------------------- Scintag RAW2
def validate_raw2(dirs: list[Path]) -> None:
    print("\n=== 2) Scintag RAW2 ===")
    seen: set[str] = set()
    total = 0
    for d in dirs:
        if not d.is_dir():
            continue
        for rp in sorted(d.iterdir()):
            low = rp.name.lower()
            if not low.endswith(".raw") or low in seen:
                continue
            seen.add(low)
            if rp.read_bytes()[:4] != b"RAW2":
                continue
            total += 1
            try:
                dd = load_pattern(rp)
            except Exception as e:
                check(False, f"RAW2 {rp.name}: 读取失败 {e}")
                continue
            check(len(dd) > 100 and 0 <= dd.two_theta[0] < dd.two_theta[-1] <= 180,
                  f"RAW2 {str(d.name)}/{rp.name[:18]:20s} n={len(dd):5d} "
                  f"x=[{dd.two_theta[0]:.3f},{dd.two_theta[-1]:.3f}] ymax={dd.intensity.max():.0f}")
    print(f"  RAW2 样本 {total} 个")

    # 与同目录 .dat / .txt / .xy 逐点交叉校验 (geshi 4-1 是同一谱的多种导出)
    g = Path(r"D:/Project/XRD/test_xrd/geshi")
    if (g / "4-1.raw").exists():
        a = load_pattern(g / "4-1.raw")
        for other in ("4-1.dat", "4-1.txt", "4-1.xy"):
            if not (g / other).exists():
                continue
            b = load_pattern(g / other)
            # 强度必须逐点全等; 2θ 允许 float32 级噪声 (2.8e-14)
            same = (len(a) == len(b)
                    and np.array_equal(a.intensity, b.intensity)
                    and np.allclose(a.two_theta, b.two_theta, atol=1e-9))
            check(same, f"RAW2 4-1.raw 与 {other} 逐点一致 (n={len(a)}, "
                        f"dx={np.max(np.abs(a.two_theta - b.two_theta)):.1e})")


# ---------------------------------------------------------------- Jade/MDI 文本
def validate_jade_txt(base: Path) -> None:
    """Jade 导出的 .txt (两行头 + 单列定宽强度) 必须按头部 start/step 建轴。"""
    print("\n=== 3b) MDI / Jade 文本导出 (.txt) ===")
    rp = base / "data006：AlCoO-750C.TXT"
    if not rp.exists():
        print("  样本不存在, 跳过"); return

    d = load_pattern(rp)
    check(len(d) == 2201 and abs(d.two_theta[0] - 15.0) < 1e-6
          and abs(d.two_theta[-1] - 70.0) < 1e-6,
          f"data006.TXT: 按头建轴 n={len(d)} x=[{d.two_theta[0]:.3f},{d.two_theta[-1]:.3f}]")
    check(abs(d.wavelength - 1.5406) < 1e-6, f"data006.TXT: 靶材 Cu → λ={d.wavelength:.4f}")

    # 与同名 .raw (已知真值 15→70) 交叉: 峰位/形状必须吻合
    raw = base / "data006：AlCoO-750C.raw"
    if raw.exists():
        dr = load_pattern(raw, manual_axis=(15.0, (70.0 - 15.0) / 274))
        yi = np.interp(dr.two_theta, d.two_theta, d.intensity)
        corr = float(np.corrcoef(dr.intensity, yi)[0, 1])
        check(corr > 0.9, f"data006.TXT 与同名 .raw 形状相关 {corr:.3f} (>0.9)")
        px_txt = float(d.two_theta[int(np.argmax(d.intensity))])
        px_raw = float(dr.two_theta[int(np.argmax(dr.intensity))])
        check(abs(px_txt - px_raw) < 0.25,
              f"data006 最强峰位一致 txt={px_txt:.3f}° raw={px_raw:.3f}°")


# ---------------------------------------------------------------- 岛津 Shimadzu
def validate_shimadzu(base: Path) -> None:
    """岛津 Shimadzu 私有容器的全量解析 + 与官方 ASCII 导出逐点比对。

    结构要点 (逆向自 352 个真机文件):
      u32@0x34 = 数据字节数 (n×4) → 点数以此为准;
      u32@0x30 + 56 = 数据起始偏移 (头长可变, 有的文件把头里嵌的源路径也算进去);
      数据是 **int32** LE;  i32@0x12C/0x130/0x134 = 起始/终止/步长 (×1e4)。
    """
    print("\n=== 5) Shimadzu XRD 私有容器 ===")
    raws = sorted(base.glob("**/*.RAW"))
    if not raws:
        print("  样本目录不存在, 跳过"); return

    n_ok = 0
    for rp in raws:
        if rp.read_bytes()[:12] != b"Shimadzu XRD":
            continue
        parser = detect_raw_parser(rp.read_bytes())
        try:
            d = load_pattern(rp)
        except Exception as e:  # noqa: BLE001
            check(False, f"Shimadzu {rp.parent.name}/{rp.name}: 读取失败 {e}")
            continue
        # 头声明点数必须与取出点数一致 (0x34/4)
        n_decl = d.metadata.get("declared_points")
        check(n_decl == len(d) and len(d) >= 2,
              f"Shimadzu {rp.parent.name}/{rp.name[:18]:20s} n={len(d):5d} "
              f"kind={d.metadata.get('shimadzu_kind_name')} "
              f"x=[{d.two_theta[0]:.3f},{d.two_theta[-1]:.3f}] "
              f"axis_confident={d.metadata.get('axis_confident')}")
        n_ok += 1
    print(f"  Shimadzu .RAW 样本 {n_ok} 个")

    # 与官方 ASCII 导出逐点比对 (真值)
    def _ascii_rows(p: Path) -> np.ndarray:
        rows = []
        for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = ln.strip()
            if not s or not s[0].isdigit():
                continue
            parts = s.split()
            if len(parts) >= 2:
                try:
                    rows.append((float(parts[0]), float(parts[1])))
                except ValueError:
                    pass
        return np.asarray(rows, dtype=float)

    n_pairs = 0
    for tp in sorted(base.glob("**/*.txt")):
        rp = tp.with_suffix(".RAW")
        if not rp.exists() or rp.read_bytes()[:12] != b"Shimadzu XRD":
            continue
        t = _ascii_rows(tp)
        d = load_pattern(rp)
        same_n = len(t) == len(d)
        y_eq = same_n and np.array_equal(t[:, 1], d.intensity)
        dx = float(np.max(np.abs(t[:, 0] - d.two_theta))) if same_n else float("nan")
        check(same_n and y_eq and dx < 1e-6,
              f"Shimadzu {rp.name[:22]:24s} 与官方 .txt 逐点一致 "
              f"(n={len(d)}, y 全等={y_eq}, dx={dx:.1e})")
        n_pairs += 1
    print(f"  与官方 .txt 交叉校验 {n_pairs} 组")

    # 边界样本回归 (都能被头里的定点字段坑到)
    edge = {
        # 相对路径: (期望 n, 期望 x0, 期望 x1, 期望阳极, 说明)
        r"Stress\Theta\Theta.RAW": (101, -1.0, 1.0, "Cu", "起始角是负的 (i32, 非 u32)"),
        r"Std\Search\Search.RAW": (1741, 23.0, 60.0, "Cu",
                                   "步长字段被截断到 4 位小数, 需按 (end-start)/(n-1) 反推"),
        r"Stress\Heikei-Test\Heikei-Test.RAW": (80, 34.0, 37.95, "Cu",
                                                "头里 end=38 比末点大 1 个步长"),
        r"Stress\std-sokkei\std-sokkei.RAW": (626, 150.0, 162.5, "Cr",
                                              "波长字段残留 Cu, 应以靶材记号 Cr 为准"),
        r"ENVCAL\053\053.RAW": (1210, 25.001, 43.983, "Cu",
                                "头长可变 (含有嵌入路径, 数据起始 0x390+56)"),
    }
    for rel, (n, x0, x1, anode, why) in edge.items():
        rp = base / rel
        if not rp.exists():
            continue
        d = load_pattern(rp)
        check(len(d) == n and abs(d.two_theta[0] - x0) < 5e-3
              and abs(d.two_theta[-1] - x1) < max(5e-3, (x1 - x0) * 1e-3),
              f"Shimadzu 边界 {rp.stem:22s} n={len(d)} x=[{d.two_theta[0]:.3f},"
              f"{d.two_theta[-1]:.3f}]  ({why})")
        check(str(d.metadata.get("anode", "")).upper() == anode.upper(),
              f"Shimadzu 边界 {rp.stem:22s} 靶材={d.metadata.get('anode')!r} → "
              f"λ={d.wavelength:.5f}")

    # 峰表类 (PKR/PKK/PKS/PSE/PKF) 必须被明确拒绝, 不能产出假谱
    pk = next((p for p in sorted(base.glob("**/*.PKR"))), None)
    if pk is not None:
        try:
            load_pattern(pk)
            check(False, f"Shimadzu {pk.name}: 峰表文件竟然被当成谱图读入")
        except Exception as e:  # noqa: BLE001
            check("峰表" in str(e), f"Shimadzu {pk.name}: 峰表已正确拒绝 ({str(e)[:30]}…)")

    # 合成截断回归: 声明数据区超出文件尾时, 必须保持声明偏移、钳到可用
    # 点数并标记 truncated —— 绝不能把头部字节当强度读进来 (旧版用
    # len-nbytes 尾推, 截断文件会被静默读错且无标记)
    import struct as _struct

    _n, _hlen = 100, 968
    _buf = bytearray(b"Shimadzu XRD\x00\x00\x00\x00Ver 0.00".ljust(0x30, b"\x00"))
    _buf += _struct.pack("<I", _hlen - 56)          # 0x30 头部基址
    _buf += _struct.pack("<I", _n * 4)              # 0x34 数据字节数
    _buf += b"TruncTest Cu".ljust(_hlen - len(_buf), b"\x00")
    _vals = [1000 + 7 * i for i in range(_n)]
    _buf[0x20:0x24] = _struct.pack("<I", 1)         # kind = RAW
    _buf[0x12C:0x130] = _struct.pack("<i", 200_000)  # 20.0°
    _buf[0x130:0x134] = _struct.pack("<i", 219_500)  # 21.95°
    _buf[0x134:0x138] = _struct.pack("<i", 200)      # 0.02°
    _buf[624:628] = _struct.pack("<i", _n)
    _buf += _struct.pack(f"<{_n}i", *_vals)
    _full = bytes(_buf)
    _trunc = _full[: len(_full) - 10 * 4]           # 截掉尾部 10 点

    _d = parse_raw(_full, base / "_synth_full.RAW")
    check(len(_d.intensity) == _n and _d.truncated is False,
          f"Shimadzu 合成完整文件 n={len(_d.intensity)} truncated={_d.truncated}")
    _d = parse_raw(_trunc, base / "_synth_trunc.RAW")
    _kept = _n - 10
    check(len(_d.intensity) == _kept and _d.truncated is True
          and _d.meta.get("declared_points") == _n,
          f"Shimadzu 合成截断文件 n={len(_d.intensity)}/{_n} truncated={_d.truncated} "
          f"declared={_d.meta.get('declared_points')}")
    check(_d.axis_confident is False,
          f"Shimadzu 合成截断文件轴必须标记不可信 (confident={_d.axis_confident}) —— "
          "截断时 end 对应声明点数, (end-start)/(n-1) 反推会把轴拉伸")
    check(np.array_equal(_d.intensity, np.asarray(_vals[:_kept], dtype=float)),
          "Shimadzu 合成截断文件保留点与原值全等 (未混入头部字节)")

    # 伴随扩展名同结构 (org/rsm/rbg/rk1/rlz/rax/rfi) 也应能读
    sib = 0
    for ext in ("*.ORG", "*.RSM", "*.RBG", "*.RK1", "*.RAX", "*.RLZ", "*.RFI"):
        for p in list(base.glob(f"**/{ext}"))[:6]:
            if p.read_bytes()[:12] != b"Shimadzu XRD":
                continue
            try:
                d = load_pattern(p)
                check(len(d) >= 2, f"Shimadzu 伴随 {p.suffix} {p.name[:20]:22s} "
                                   f"n={len(d)}")
                sib += 1
            except Exception as e:  # noqa: BLE001
                # 允许"头部空壳/无数据"的少数文件明确报错
                check("过短" in str(e) or "超出文件长度" in str(e) or "数据段" in str(e)
                      or "数据被截断" in str(e),
                      f"Shimadzu 伴随 {p.suffix} {p.name[:20]}: {str(e)[:40]}")
    print(f"  伴随扩展名样本 {sib} 个可读")


# ---------------------------------------------------------------- Bruker v1
def validate_bruker(base: Path) -> None:
    print("\n=== 3) Bruker/Siemens RAW v1 (RAW1.01) ===")
    for rp in sorted(base.glob("*.raw")):
        magic = rp.read_bytes()[:8]
        if not magic.startswith(b"RAW1"):
            continue
        parser = detect_raw_parser(rp.read_bytes())
        print(f"  {rp.name[:34]:36s} -> {parser.key}")
        try:
            d = load_pattern(rp)
            print(f"      n={len(d)} ymax={d.intensity.max():.0f} "
                  f"axis_confident={d.metadata.get('axis_confident')} "
                  f"x=[{d.two_theta[0]:.3f},{d.two_theta[-1]:.3f}]")
            check(d.intensity.max() > 0, f"Bruker {rp.name}: 强度数据非空")
            check(d.metadata.get("axis_confident") is False,
                  f"Bruker {rp.name}: 已正确标记角度轴不可信 (未硬猜)")
        except Exception as e:
            check(False, f"Bruker {rp.name}: {e}")


# ---------------------------------------------------------------- 写出格式 P1
def validate_fmt_pair() -> None:
    """P1 回归: writers._fmt_pair 两列粘连修复。

    正常 y 值 (首字符为空格) 必须保持与原厂字节一致 (不加分隔符);
    溢出 10 字符场宽 (首字符非空格, 如 126727.648 或 10 位整数) 时,
    必须补一个显式分隔空格, 否则下游 np.loadtxt 会把整行读成单列而报
    "columns changed"。本测试不依赖真机样本, 始终可跑。
    """
    print("\n=== 0) writers._fmt_pair 两列粘连 (P1 回归) ===")
    from polyxrd_converter.model import XRDData
    from polyxrd_converter.writers import write_pattern, _fmt_pair
    import tempfile

    # 1) 字节一致性: 正常行不得多出分隔符 (保住与原厂字节一致的往返)
    normal = _fmt_pair(10.0, 500.0)
    check(normal == "  10.000       500",
          f"P1: 正常行字节一致 (got {normal!r})")
    # 2) 小数 / 大整数溢出行必须补分隔符 (首字符非空格)
    dec_over = _fmt_pair(20.0, 126727.648)
    check(dec_over == "  20.000 126727.648",
          f"P1: 小数溢出行已补分隔符 (got {dec_over!r})")
    big_int = _fmt_pair(30.0, 1234567890.0)
    check(big_int == "  30.000 1234567890",
          f"P1: 大整数行已补分隔符 (got {big_int!r})")

    # 3) 端到端: 写出 .txt 后 np.loadtxt 应为 2 列且数值正确
    x = np.array([10.0, 20.0, 30.0], dtype=float)
    y = np.array([500.0, 126727.648, 1234567890.0], dtype=float)
    d = XRDData(two_theta=x, intensity=y, wavelength=1.5406)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "p1_sample.txt"
        write_pattern(d, p, "txt")
        arr = np.loadtxt(str(p))
        check(arr.shape == (3, 2),
              f"P1: 端到端 np.loadtxt 读回为 2 列 (shape={arr.shape})")
        check(np.allclose(arr[:, 0], x)
              and np.allclose(arr[:, 1], y, atol=1e-3),
              "P1: 端到端回读数值正确")


# ---------------------------------------------------------------- GSAS-II 系文本
def make_gsas2_samples(td: Path) -> dict:
    """生成 GSAS-II 系新格式 (gsas/fp_dat/ras/xye/chi) 的合成样本。

    返回 ``{文件名: dict(x=真值2θ, y=真值强度, key=期望识别, q=是否Q模式, note=说明)}``。
    公共真值: 2θ 从 20.000° 步长 0.02° 共 100 点; 强度 100+7i 全为正
    (避开 GSAS-II 把 ≤0 清零的语义差异, 便于与 GSAS-II oracle 逐点对拍)。
    """
    n = 100
    x = 20.0 + 0.02 * np.arange(n)
    y = 100.0 + 7.0 * np.arange(n)
    wl = 1.5406
    q = 4.0 * np.pi * np.sin(np.radians(x) / 2.0) / wl
    out: dict = {}

    def put(name: str, text: str, info: dict) -> None:
        (td / name).write_text(text, encoding="ascii", newline="")
        out[name] = info

    # 1) GSAS FXYE: x 为百分度显式列 + y + esd
    lines = ["Synthetic GSAS FXYE (PolyXRD Converter test)",
             "BANK 1 FXYE 100 101 2000 2 3980"]
    for i in range(n):
        lines.append(f"{round(x[i] * 100):d} {y[i]:.1f} {10.0 + 0.05 * i:.2f}")
    put("synth_fxye.gsas", "\n".join(lines) + "\n",
        dict(x=x, y=y, key="gsas", note="FXYE 显式 x 百分度列"))

    # 2) GSAS FXY: x 百分度 + y 两列
    lines = ["Synthetic GSAS FXY", "BANK 1 FXY 100 101 2000 2 3980"]
    for i in range(n):
        lines.append(f"{round(x[i] * 100):d} {y[i]:.1f}")
    put("synth_fxy.gsas", "\n".join(lines) + "\n",
        dict(x=x, y=y, key="gsas", note="FXY 两列"))

    # 3) GSAS ESD: 定宽 16 字符组 (8y+8esd), x 由 BANK start/step (百分度) 重建
    lines = ["Synthetic GSAS ESD", "BANK 1 ESD 100 101 2000 2 3980"]
    for base in range(0, n, 5):
        row = ""
        for k in range(5):
            i = base + k
            if i >= n:
                break
            row += f"{y[i]:8.1f}{10.0 + 0.05 * i:8.2f}"
        lines.append(row)
    put("synth_esd.gsas", "\n".join(lines) + "\n",
        dict(x=x, y=y, key="gsas", note="ESD 定宽重建轴"))

    # 4) GSAS STD: 定宽 8 字符组 (2 归一计数 + 6 原始计数), 每行 10 组, 强度存整数
    lines = ["Synthetic GSAS STD", "BANK 1 STD 100 101 2000 2 3980"]
    for base in range(0, n, 10):
        row = ""
        for k in range(10):
            i = base + k
            if i >= n:
                break
            row += f"01{int(round(y[i])):6d}"
        lines.append(row)
    put("synth_std.gsas", "\n".join(lines) + "\n",
        dict(x=x, y=np.round(y), key="gsas", note="STD 定宽 (整数计数)"))

    # 5) FullProf .dat 单列
    lines = ["/* Synthetic FullProf (PolyXRD Converter test) */",
             "lambda 1.5406", "20.00 0.02 21.98"]
    for v in y:
        lines.append(f"{v:.1f}")
    put("synth_fp1.dat", "\n".join(lines) + "\n",
        dict(x=x, y=y, key="fp_dat", note="FP 单列 + lambda 行"))

    # 6) FullProf .dat 5 列
    lines = ["# Synthetic FullProf 5col", "20.00 0.02 21.98"]
    for base in range(0, n, 5):
        lines.append(" ".join(f"{y[base + k]:.1f}" for k in range(5) if base + k < n))
    put("synth_fp5.dat", "\n".join(lines) + "\n",
        dict(x=x, y=y, key="fp_dat", note="FP 5 列"))

    # 7) Rigaku .ras: 头带波长, 数据块 + 应被忽略的第二块
    lines = ["*RAS_DATA_START", "*RAS_HEADER_START", "*XRAY_WAVELENGTH 1.5406",
             "*RAS_HEADER_END", "*RAS_INT_START"]
    for i in range(n):
        lines.append(f"{x[i]:.3f}  {y[i]:.1f}")
    lines += ["*RAS_INT_END", "*RAS_INT_START", "19.000  1.0", "*RAS_INT_END"]
    put("synth.ras", "\n".join(lines) + "\n",
        dict(x=x, y=y, key="ras", note="第一扫描块 (第二块被忽略)"))

    # 8) Rigaku .rasx: zip 容器 (Profile + 测量条件 XML)
    import zipfile as _zf
    prof = "\n".join(f"{x[i]:.3f}  {y[i]:.1f}" for i in range(n)) + "\n"
    xml = ('<?xml version="1.0"?><Setup><XRay>'
           "<Wavelength>1.5406</Wavelength></XRay></Setup>")
    with _zf.ZipFile(td / "synth.rasx", "w") as z:
        # 真 rasx 的 Profile0.txt 带 UTF-8 BOM (GSAS-II 参考实现甚至硬编码 seek(3) 跳它)
        z.writestr("Data0/Profile0.txt", b"\xef\xbb\xbf" + prof.encode("utf-8"))
        z.writestr("Data0/MesurementConditions0.xml", xml)
    out["synth.rasx"] = dict(x=x, y=y, key="ras", note="rasx zip 内存直读")

    # 9) Topas .xye (3 列, esd 忽略)
    lines = ["# Synthetic Topas xye"]
    for i in range(n):
        lines.append(f"{x[i]:.3f}  {y[i]:.1f}  {10.0 + 0.05 * i:.2f}")
    put("synth.xye", "\n".join(lines) + "\n",
        dict(x=x, y=y, key="xye", note="Topas xye 3 列"))

    # 10) Topas .qye (Q 轴 + #wavelength 注释; 三段式写法兼容 GSAS-II oracle)
    lines = ["# wavelength 1.5406", "# Synthetic Topas qye"]
    for i in range(n):
        lines.append(f"{q[i]:.6f}  {y[i]:.1f}")
    put("synth.qye", "\n".join(lines) + "\n",
        dict(x=x, y=y, key="xye", q=True, note="qye Q→2θ 换算"))

    # 11) Fit2D .chi (2θ)
    lines = ["Fit2d exchange format v1.0", "", "Array: chi_2theta", "2-theta  I"]
    for i in range(n):
        lines.append(f"{x[i]:.3f}  {y[i]:.1f}")
    put("synth.chi", "\n".join(lines) + "\n",
        dict(x=x, y=y, key="chi", note="Fit2D chi 2θ"))

    # 12) Fit2D .qchi (Q + 头行波长; 'q λ' 写法兼容 GSAS-II oracle)
    lines = ["Fit2d exchange format v1.0", "", "Array: q", "q 1.5406"]
    for i in range(n):
        lines.append(f"{q[i]:.6f}  {y[i]:.1f}")
    put("synth.qchi", "\n".join(lines) + "\n",
        dict(x=x, y=y, key="chi", q=True, note="qchi Q→2θ 换算"))

    # 13) pyFAI 简化头 .chi / .qchi (头只有 2 行注释; 供 GSAS-II oracle 对拍)
    lines = ["# chi_2theta", "# position (deg)  intensity"]
    for i in range(n):
        lines.append(f"{x[i]:.4f}  {y[i]:.1f}")
    put("synth_pyfai.chi", "\n".join(lines) + "\n",
        dict(x=x, y=y, key="chi", note="pyFAI 简化头 chi"))
    lines = ["# q 1.5406", "# synthetic qchi pyFAI-style"]
    for i in range(n):
        lines.append(f"{q[i]:.6f}  {y[i]:.1f}")
    put("synth_pyfai.qchi", "\n".join(lines) + "\n",
        dict(x=x, y=y, key="chi", q=True, note="pyFAI 简化头 qchi"))

    # 14) TOF 拒绝样本 (不进 samples 断言, 单独测)
    (td / "synth_tof.gsas").write_text(
        "Synthetic TOF\nBANK 1 FXYE 10 101 0 1 10\nTIME_MAP 1 10 1 1\n",
        encoding="ascii", newline="")
    return out


def validate_gsas2_formats() -> None:
    """GSAS-II 系新格式回归: 合成样本全格式读取 + 边界 (TOF 拒绝 / FP 误判守卫)。

    真机样本不在位时的降级方案; 另用 GSAS-II 本体 (C:/gsas2main) 作为
    oracle 逐点对拍 (一次性验证, 结论沉淀在本函数注释与交接记录)。
    """
    print("\n=== 6) GSAS-II 系文本格式 (gsas/fp_dat/ras/xye/chi) ===")
    from polyxrd_converter.loader import DataFormatError, detect_format
    from polyxrd_converter.model import XRDData
    from polyxrd_converter.writers import write_pattern
    import tempfile

    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        samples = make_gsas2_samples(td)
        for name, info in samples.items():
            p = td / name
            key, _ = detect_format(p)
            check(key == info["key"], f"{name[:22]:24s} 识别为 {key} (期望 {info['key']})")
            try:
                d = load_pattern(p)
            except DataFormatError as e:
                check(False, f"{name[:22]:24s} 读取失败: {e}")
                continue
            atol_x = 1e-3 if info.get("q") else 1e-9
            check(len(d) == len(info["x"]),
                  f"{name[:22]:24s} 点数 {len(d)} == {len(info['x'])} ({info['note']})")
            check(np.allclose(d.two_theta, info["x"], atol=atol_x),
                  f"{name[:22]:24s} 2θ 轴逐点一致 "
                  f"(max|dx|={np.max(np.abs(d.two_theta - info['x'])):.2e})")
            check(np.allclose(d.intensity, info["y"], atol=1e-9),
                  f"{name[:22]:24s} 强度逐点一致")

        # TOF 必须明确拒绝 (横轴不是 2θ, 绝不硬猜)
        try:
            load_pattern(td / "synth_tof.gsas")
            check(False, "TOF GSAS (TIME_MAP) 竟被当成 2θ 谱读入")
        except DataFormatError:
            check(True, "TOF GSAS (TIME_MAP) 已明确拒绝")

        # 自写两列 .dat 不得被 FullProf 判定误吞 (往返守恒是 P1 修复的回归基线)
        p_dat = td / "guard.dat"
        write_pattern(XRDData(two_theta=info["x"], intensity=info["y"],
                              wavelength=1.5406), p_dat, "dat")
        key, _ = detect_format(p_dat)
        check(key == "dat", f"自写两列 .dat 仍识别为普通文本 (got {key})")
        d2 = load_pattern(p_dat)
        check(np.allclose(d2.two_theta, info["x"], atol=1e-6)
              and np.allclose(d2.intensity, info["y"], atol=1e-3),
              "自写两列 .dat 往返数值一致 (FP 误判守卫)")


# ---------------------------------------------------------------- 通用互通
def validate_roundtrip(samples: list[Path]) -> None:
    print("\n=== 4) 格式互转往返 ===")
    import tempfile
    from polyxrd_converter.writers import TARGET_EXTS, write_pattern

    with tempfile.TemporaryDirectory() as td:
        for sp in samples:
            if not sp.exists():
                continue
            try:
                d0 = load_pattern(sp)
            except Exception as e:
                check(False, f"往返 {sp.name}: 源读取失败 {e}")
                continue
            for key in ("xy", "txt", "dat", "csv", "json", "xrdml"):
                out = Path(td) / f"{sp.stem}.{key}.{TARGET_EXTS[key].lstrip('.')}"
                try:
                    write_pattern(d0, out, key)
                    d1 = load_pattern(out)
                    same = (len(d0) == len(d1)
                            and np.allclose(d0.two_theta, d1.two_theta, atol=1e-6)
                            and np.allclose(d0.intensity, d1.intensity, atol=1e-3))
                    check(same, f"往返 {sp.name[:18]:20s} -> {key:5s} n={len(d1)}")
                except Exception as e:
                    check(False, f"往返 {sp.name[:18]} -> {key}: {e}")
            # 等间距格式另测 (MDI/RAW2 是整数/通道格式, 允许 1 个 LSB 的取整误差)
            for key, tol in (("mdi", 1.0), ("raw", 1e-3)):
                try:
                    out = Path(td) / f"{sp.stem}.{key}"
                    write_pattern(d0, out, key)
                    d1 = load_pattern(out)
                    same = (len(d0) == len(d1)
                            and np.allclose(d0.two_theta, d1.two_theta, atol=5e-3)
                            and np.allclose(d0.intensity, d1.intensity, atol=tol))
                    check(same, f"往返 {sp.name[:18]:20s} -> {key:4s} n={len(d1)} "
                                f"(y 最大偏差 {np.max(np.abs(d0.intensity - d1.intensity)):.3g})")
                except Exception as e:
                    check(False, f"往返 {sp.name[:18]} -> {key}: {e}")


def validate_i18n() -> None:
    """中/英/日三语文案一致性: key 集合齐平的证据全在这里。

    漏 key 时 tr() 会静默回退到中文 —— 界面在日语下蹦出中文很不容易被人眼发现,
    所以必须机器把关。占位符不对齐则更糟: 是 KeyError 级别的运行时崩。
    """
    print("\n=== 7) 三语文案一致性 (zh / en / ja) ===")
    from polyxrd_converter.i18n import EN, JA, LANGS, ZH, set_language, tr
    from polyxrd_converter.loader import FORMAT_LABELS
    from polyxrd_converter.writers import TARGET_FORMATS

    tables = {"zh": ZH, "en": EN, "ja": JA}
    zk = set(ZH)
    print(f"  key 总数 {len(zk)}（每种语言）")

    for code, table in tables.items():
        missing = sorted(zk - set(table))
        extra = sorted(set(table) - zk)
        check(not missing and not extra,
              f"{code}: key 集合与 zh 完全一致"
              f"（缺 {len(missing)} / 多 {len(extra)}）"
              + (f" 缺项={missing[:6]}" if missing else "")
              + (f" 多项={extra[:6]}" if extra else ""))

    # 占位符必须三种语言同名同数量
    def placeholders(s: str) -> tuple[str, ...]:
        return tuple(sorted(re.findall(r"\{(\w+)\}", s)))

    for k in sorted(zk):
        pz, pe, pj = (placeholders(t[k]) for t in (ZH, EN, JA))
        check(pz == pe == pj,
              f"{k}: 占位符一致 {pz}" if pz == pe == pj
              else f"{k}: 占位符不一致 zh={pz} en={pe} ja={pj}")
        # tr(key, **kwargs) 的形参就叫 key —— 占位符再叫 {key} 会直接 TypeError
        check("key" not in pz,
              f"{k}: 占位符不与 tr(key=...) 撞名" if "key" not in pz
              else f"{k}: 占位符 key 与 tr() 形参撞名 (必须改名)")

    # 每张表的每个占位符都能真的 format 通 (format(**kwargs) 全填)
    for code, table in tables.items():
        set_language(code)
        bad = []
        for k in sorted(zk):
            names = placeholders(table[k])
            try:
                tr(k, **{n: "X" for n in names})
            except Exception as e:  # noqa: BLE001 - 测试要的是"任一语言都不能炸"
                bad.append(f"{k}({e})")
        check(not bad, f"{code}: 全部 {len(zk)} 条文案 format 不报错"
                       + (f" 异常={bad[:5]}" if bad else ""))

    # 格式名 / 目标格式名在三语下都必须有译文 —— 否则界面会退回原始 English 标签
    set_language("zh")
    all_fmt = set(FORMAT_LABELS) | {"rigaku_raw", "scintag_raw2", "bruker_raw_v1",
                                    "shimadzu_raw", "raw_generic"}
    for code in LANGS:
        set_language(code)
        missing = [k for k in sorted(all_fmt) if tr(f"fmt.{k}") == f"fmt.{k}"]
        check(not missing, f"{code}: 全部 {len(all_fmt)} 个读取格式名都有译文"
                           + (f" 缺={missing}" if missing else ""))
        missing = [k for k, _e, _l in TARGET_FORMATS if tr(f"tgt.{k}") == f"tgt.{k}"]
        check(not missing, f"{code}: 全部 {len(TARGET_FORMATS)} 个写出格式名都有译文"
                           + (f" 缺={missing}" if missing else ""))

    # 三种语言的按钮/菜单文案必须真的不一样 (防止整表复制粘贴没改)
    keys = ["btn.convert", "btn.add_files", "menu.file", "status.bad_axis",
            "dlg.about", "tip.axis_warn", "statusbar.internal"]
    for k in keys:
        vals = {tables[c][k] for c in LANGS}
        check(len(vals) == 3, f"{k}: 三语译文互不相同")

    set_language("zh")


def main() -> int:
    xr = Path(r"D:/Project/XRD")
    print("=" * 78)
    print("PolyXRD Converter —— RAW 解析与格式互转验证")
    print("=" * 78)

    validate_fmt_pair()
    validate_gsas2_formats()
    validate_i18n()
    validate_rigaku(xr / "XRData" / "csuHJW")
    validate_manual_axis(xr / "XRData" / "csuHJW")
    validate_raw2([xr / "XRData" / "IUCr", xr / "test_xrd" / "geshi",
                   xr / "test_xrd" / "raw"])
    validate_jade_txt(xr / "XRData" / "csuHJW")
    validate_bruker(xr / "XRData" / "csuHJW")
    validate_shimadzu(xr / "XRData" / "Shimadzu Data")
    validate_roundtrip([
        xr / "test_xrd" / "geshi" / "4-1.dat",
        xr / "test_xrd" / "geshi" / "4-1.mdi",
        xr / "XRData" / "csuHJW" / "Data007：铜衍射谱系列.raw",
        xr / "XRData" / "IUCr" / "CPD-1A.RAW",
    ])

    print("\n" + "=" * 78)
    print(f"通过 {len(OK)}  /  失败 {len(FAIL)}")
    if FAIL:
        print("\n失败明细:")
        for m in FAIL[:40]:
            print("  ✗", m)
    print("=" * 78)
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
