# -*- mode: python ; coding: utf-8 -*-
# PolyXRD Converter —— Setup 安装版 (onedir, 含注册机制)
#
# 与 PolyXRDConverter-Internal.spec 的差别:
#   * 含 polyxrd_converter.registration (未注册启动提示 / 输入注册码 /
#     状态栏右侧显示注册单位部门名称)。
#   * onedir 形态: 装进 Program Files 的程序不宜 onefile
#     (onefile 每次启动解压到 %TEMP%, 慢且不干净), 由 Inno Setup 打成安装包。
#   * exe 名 PolyXRD-Converter-Setup。
# 产物: dist/PolyXRD-Converter-Setup/ 整目录 -> installer/PolyXRD-Converter.iss 打包。

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
    'polyxrd_converter.registration',
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
        # 明确排除用不到的大件, 控制体积
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
    [],
    exclude_binaries=True,      # onedir: 二进制交给 COLLECT
    name='PolyXRD-Converter-Setup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                  # UPX 常触发杀软误报, 不用
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['src/polyxrd_converter/resources/icon.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PolyXRD-Converter-Setup',
)
