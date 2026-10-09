"""
PolyXRD Converter —— XRD 谱图格式转换器
========================================
从 PolyXRD 中独立剥离出来的「谱图格式互转」小工具。

- 读: 支持 xy / txt / dat / csv / mdi / xrdml / xml / brml / json
      以及多种厂商二进制 RAW (自动识别, 见 ``raw_formats``)
- 写: xy / txt / dat / csv / mdi / raw / xrdml / json
- 用: ``convert_file(src, dst, fmt)`` / ``load_pattern(path)``, 或直接跑 GUI

与 PolyXRD 主体零耦合: 只依赖 numpy 与 PySide6。
"""

__version__ = "1.0.0"
__author__ = "PolyXRD Team"
__app_name__ = "PolyXRD Converter"

__all__ = ["__version__", "__app_name__"]
