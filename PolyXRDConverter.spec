# -*- mode: python ; coding: utf-8 -*-
# PolyXRD Converter —— PyInstaller 单文件打包
#
# 交付形态: 单文件 exe (onefile), 双击即用, 无需安装。
# 与主体 PolyXRD 不同: 本工具零数据库、零 scipy/matplotlib,
# 靠 PyInstaller 内置的 PySide6/numpy hook 即可, 不用 collect_all
# (避免把 WebEngine 等未用组件拖进来, exe 体积差 3 倍)。

datas = [
    ('src/polyxrd_converter/resources', 'polyxrd_converter/resources'),
]
binaries = []
hiddenimports = [
    'polyxrd_converter',
    'polyxrd_converter.raw_formats',
    'polyxrd_converter.loader',
    'polyxrd_converter.writers',
    'polyxrd_converter.converter',
]

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 明确排除用不到的大件, 控制单文件体积
        'matplotlib', 'scipy', 'pandas', 'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets', 'PySide6.QtQml', 'PySide6.QtQuick',
        'tkinter', 'unittest', 'pydoc_data',
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PolyXRDConverter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,              # UPX 常触发杀软误报, 不用
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['src/polyxrd_converter/resources/icon.ico'],
)
