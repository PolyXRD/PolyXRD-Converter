@echo off
chcp 65001 >nul
REM -- UTF-8 everywhere: 中文路径/日志不乱码
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title PolyXRD Converter v1.0.0 打包构建器
echo ========================================
echo   PolyXRD Converter v1.0.0
echo   单文件 exe 打包 (onefile)
echo ========================================
echo.

cd /d "%~dp0"

REM -- 从 src/polyxrd_converter/__init__.py 读版本号 (单源) --
for /f "tokens=2 delims== " %%A in ('findstr /r "^__version__" src\polyxrd_converter\__init__.py') do set APPVER=%%~A
set APPVER=%APPVER:"=%
echo [信息] 版本号: %APPVER%

REM ── Python 定位 ──────────────────────────────────────
if exist "venv\Scripts\python.exe" (
    set PYTHON=venv\Scripts\python.exe
    set PIP=venv\Scripts\pip.exe
) else (
    set PYTHON=python
    set PIP=pip
)
echo [信息] 使用 Python: %PYTHON%

"%PYTHON%" -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo [信息] 安装 PyInstaller...
    "%PIP%" install pyinstaller^>=6.0
)

echo.
echo [步骤 1/3] 生成应用图标...
"%PYTHON%" build_icon.py
if %errorlevel% neq 0 (
    echo [警告] 图标生成失败, 使用已有 icon.ico 继续
)

echo.
echo [步骤 2/3] PyInstaller 单文件打包...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
"%PYTHON%" -m PyInstaller PolyXRDConverter.spec --noconfirm
if %errorlevel% neq 0 (
    echo [错误] PyInstaller 打包失败!
    pause
    exit /b 1
)
if not exist "dist\PolyXRDConverter.exe" (
    echo [错误] EXE 未生成, 构建失败!
    pause
    exit /b 1
)

echo.
echo [步骤 3/3] 产物校验 (大小 + SHA-256)...
for %%A in ("dist\PolyXRDConverter.exe") do echo   大小:     %%~zA 字节
"%PYTHON%" -c "import hashlib,sys; p=sys.argv[1]; h=hashlib.sha256(open(p,'rb').read()).hexdigest(); print('  SHA-256: '+h)" "dist\PolyXRDConverter.exe"

echo.
echo ========================================
echo   PolyXRD Converter v%APPVER% 打包完成!
echo ========================================
echo.
echo 产物: dist\PolyXRDConverter.exe
echo.
echo 请双击 dist\PolyXRDConverter.exe 做人工冒烟验收:
echo   1. 拖入 .raw / .txt / .mdi / .xrdml 各一个
echo   2. 确认表格识别格式正确、预览出图
echo   3. 转成 .xy 与 .xrdml, 用 PolyXRD 主体回读核对
echo.
pause
