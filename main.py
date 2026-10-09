"""PolyXRD Converter 启动入口。

供 PyInstaller 与 ``python main.py`` 两种方式使用。
"""
import sys
from pathlib import Path

# 从源码运行时把 src 加进路径 (冻结环境下该目录不存在, 加了也无害)
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from polyxrd_converter.app import run  # noqa: E402

if __name__ == "__main__":
    sys.exit(run())
