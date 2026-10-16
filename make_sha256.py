"""写构建产物的 SHA-256 校验文件 (build.bat 步骤 6)。

用法::

    python make_sha256.py <产物1> <产物2> ... <输出文件>

输出格式与既有约定一致 (两空格分隔, 可被 ``sha256sum -c`` 解析)::

    <哈希>  <文件名>
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("用法: python make_sha256.py <产物1> [产物2...] <输出文件>")
        return 2
    *paths, out = argv[1:]
    lines: list[str] = []
    for raw in paths:
        p = Path(raw)
        if not p.is_file():
            print(f"[错误] 缺少产物: {p}")
            return 1
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{digest}  {p.name}")
    # newline="\n": Windows 文本模式默认会把 \n 翻译成 \r\n,
    # 而 sha256sum -c 无法解析带 \r 的行尾 (v1.5.0 构建实测踩坑)。
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    print(f"已写: {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))
