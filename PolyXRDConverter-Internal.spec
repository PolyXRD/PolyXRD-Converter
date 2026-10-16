# -*- mode: python ; coding: utf-8 -*-
# PolyXRD Converter —— 内部评估版 (onefile 单文件, 不含注册机制)
#
# 与 PolyXRDConverter-Setup.spec 的唯一差别:
#   * excludes 剔除 polyxrd_converter.registration
#     -> 运行时 ui_main 里 import 失败, registration=None,
#        无启动提示 / 无「输入注册码」菜单, 状态栏右侧显示「内部评估版本」。
#   * exe 名 PolyXRD-Converter-Internal。
# 交付形态: 单文件 exe (onefile), 双击即用, 供内部自用。

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
        # 注册模块: 内部评估版不带 (ui_main 以 try/except ImportError 兜底)
        'polyxrd_converter.registration',
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
    name='PolyXRD-Converter-Internal',
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
