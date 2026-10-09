"""生成 PolyXRD Converter 应用图标。

与 PolyXRD 主体同族 (2026-10-09 重绘):
- 背景 = 主程序 app-icon.png 的**同一条对角渐变** (左上 #0D233B → 右下 #0377B4,
  t = (x/w + y/h)/2, 实测采样拟合);
- 白色**尖顶六边形**与主程序同几何 (外接圆半径 ≈ 0.245×边长, 居中);
- 内部 motif 由主程序的"衍射曲线"换成 **⇄ 双向箭头**, 颜色取 hero-banner 的
  青色 (#10F0F0 系) —— 同一晶格记号 + 换成"互转"语义, 一眼看出是同一家族。

    python build_icon.py

产出:
    src/polyxrd_converter/resources/icon.ico   (7 档多分辨率, 供窗口/EXE 用)
    src/polyxrd_converter/resources/icon.png   (512px, 供 README 用)
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

S = 512
OUT = Path(__file__).resolve().parent / "src" / "polyxrd_converter" / "resources"

# ── 品牌色 (自 PolyXRD 主体资源实测采样) ────────────────────────────
#: 主程序 app-icon.png 的对角渐变两端 (左上 → 右下)
_BRAND_DARK = (13, 35, 59)      # #0D233B
_BRAND_LIGHT = (3, 119, 180)    # #0377B4
#: hero-banner.jpg 的青色衍射峰/晶体 (采样峰值 #10F0F0~#20F0F0)
_CYAN = (53, 224, 240)          # #35E0F0
_WHITE = (255, 255, 255, 255)


def _rounded_mask(size: int, radius: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def _brand_gradient(size: int) -> Image.Image:
    """主程序图标的对角线性渐变: t = (x/w + y/h)/2, 左上暗 → 右下亮。"""
    g = Image.new("RGB", (size, size))
    px = g.load()
    dr = _BRAND_LIGHT[0] - _BRAND_DARK[0]
    dg = _BRAND_LIGHT[1] - _BRAND_DARK[1]
    db = _BRAND_LIGHT[2] - _BRAND_DARK[2]
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2.0 * (size - 1))
            px[x, y] = (
                int(_BRAND_DARK[0] + dr * t),
                int(_BRAND_DARK[1] + dg * t),
                int(_BRAND_DARK[2] + db * t),
            )
    return g


def _hex_points(cx: float, cy: float, r: float) -> list[tuple[float, float]]:
    """尖顶六边形顶点 (与主程序 app-icon 同朝向)。"""
    import math

    return [
        (cx + r * math.cos(math.radians(a)), cy - r * math.sin(math.radians(a)))
        for a in (90, 150, 210, 270, 330, 30)
    ]


def _double_arrow(d: ImageDraw.ImageDraw, cx: float, cy: float,
                  w: float, t: float, head: float) -> None:
    """左右向双向箭头 (⇄), 以 (cx, cy) 为中心。"""
    half = w / 2
    # 主干
    d.rectangle([cx - half + head, cy - t / 2, cx + half - head, cy + t / 2], fill=_CYAN)
    # 右 / 左箭头
    d.polygon([(cx + half, cy), (cx + half - head, cy - head * 0.72),
               (cx + half - head, cy + head * 0.72)], fill=_CYAN)
    d.polygon([(cx - half, cy), (cx - half + head, cy - head * 0.72),
               (cx - half + head, cy + head * 0.72)], fill=_CYAN)


def build(size: int = S) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg = _brand_gradient(size).convert("RGBA")
    bg.putalpha(_rounded_mask(size, int(size * 0.20)))     # 主程序圆角 ≈ 20%
    img.alpha_composite(bg)

    d = ImageDraw.Draw(img)
    cx, cy = size * 0.5, size * 0.49
    hr = size * 0.245                                       # 与主程序六边形同大小
    lw = max(int(size * 0.042), 2)

    # 白色六边形描边 (同主程序; 不画内部对角线, 把空间留给箭头)
    d.polygon(_hex_points(cx, cy, hr), outline=_WHITE, width=lw)

    # 内部: ⇄ 双向箭头 (互转语义), 青色呼应 hero-banner
    _double_arrow(d, cx, cy, size * 0.30, size * 0.042, size * 0.075)

    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    master = build(S)
    master.save(OUT / "icon.png")

    sizes = [256, 128, 64, 48, 32, 24, 16]
    frames = [master.resize((s, s), Image.LANCZOS) for s in sizes]
    frames[0].save(OUT / "icon.ico", format="ICO",
                   sizes=[(s, s) for s in sizes], append_images=frames[1:])
    print(f"[icon] 写入 {OUT / 'icon.ico'}  ({len(sizes)} 档: {sizes})")
    print(f"[icon] 写入 {OUT / 'icon.png'}  ({S}x{S})")


if __name__ == "__main__":
    main()
