@echo off
chcp 65001 >nul
REM -- UTF-8 everywhere: 中文路径/日志不乱码
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title PolyXRD Converter v1.5.1 双形态打包构建器
echo ==============================================
echo   PolyXRD Converter - 双形态构建
echo   1. Internal 单文件 exe (无注册机制)
echo   2. Setup 安装包 (含注册机制, Inno Setup)
echo ==============================================
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

REM ── Inno Setup 定位 ──────────────────────────────────
set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" (
    echo [错误] 未找到 Inno Setup 6 (ISCC.exe), 无法构建 Setup 安装包!
    pause
    exit /b 1
)
echo [信息] 使用 Inno Setup: %ISCC%

echo.
echo [步骤 1/6] 生成应用图标...
"%PYTHON%" build_icon.py
if %errorlevel% neq 0 (
    echo [警告] 图标生成失败, 使用已有 icon.ico 继续
)

echo.
echo [步骤 2/6] 构建 Internal 单文件版 (无注册机制)...
"%PYTHON%" -m PyInstaller PolyXRDConverter-Internal.spec --noconfirm
if %errorlevel% neq 0 (
    echo [错误] Internal 版打包失败!
    pause
    exit /b 1
)
if not exist "dist\PolyXRD-Converter-Internal.exe" (
    echo [错误] Internal EXE 未生成, 构建失败!
    pause
    exit /b 1
)

echo.
echo [步骤 3/6] 构建 Setup 版 onedir (含注册机制)...
"%PYTHON%" -m PyInstaller PolyXRDConverter-Setup.spec --noconfirm
if %errorlevel% neq 0 (
    echo [错误] Setup 版打包失败!
    pause
    exit /b 1
)
if not exist "dist\PolyXRD-Converter-Setup\PolyXRD-Converter-Setup.exe" (
    echo [错误] Setup 版主程序未生成, 构建失败!
    pause
    exit /b 1
)

echo.
echo [步骤 4/6] Inno Setup 编译安装包...
"%ISCC%" /DAPP_VERSION=%APPVER% installer\PolyXRD-Converter.iss
if %errorlevel% neq 0 (
    echo [错误] Inno Setup 编译失败!
    pause
    exit /b 1
)
if not exist "dist\PolyXRD-Converter-Setup-v%APPVER%.exe" (
    echo [错误] 安装包未生成, 构建失败!
    pause
    exit /b 1
)

echo.
echo [步骤 5/6] 复制带版本号快照...
copy /Y "dist\PolyXRD-Converter-Internal.exe" "dist\PolyXRD-Converter-Internal-v%APPVER%.exe" >nul

echo.
echo [步骤 6/6] 写 SHA-256 校验文件 (两个产物合并一份)...
"%PYTHON%" make_sha256.py "dist\PolyXRD-Converter-Internal-v%APPVER%.exe" "dist\PolyXRD-Converter-Setup-v%APPVER%.exe" "dist\SHA256-v%APPVER%.txt"
if %errorlevel% neq 0 (
    echo [错误] SHA-256 校验文件写入失败!
    pause
    exit /b 1
)

echo.
echo ==============================================
echo   PolyXRD Converter v%APPVER% 构建完成!
echo ==============================================
echo.
echo 产物:
echo   dist\PolyXRD-Converter-Internal.exe                  (内部评估版, 最新, 无版本号)
echo   dist\PolyXRD-Converter-Internal-v%APPVER%.exe        (内部评估版, 带版本号)
echo   dist\PolyXRD-Converter-Setup-v%APPVER%.exe           (Setup 安装包, 含注册机制)
echo   dist\SHA256-v%APPVER%.txt                            (两产物合并校验和)
echo.
echo 人工冒烟验收建议:
echo   1. 双击 dist\PolyXRD-Converter-Internal.exe: 状态栏**居中**应显示红色加粗的
echo      「内部评估版本」, 帮助菜单只有 关于/版权 两项, 无启动提示;
echo   2. 安装 dist\PolyXRD-Converter-Setup-v%APPVER%.exe (可改安装位置):
echo      未注册启动应弹版权提示, 帮助菜单含「输入注册码」,
echo      注册成功后状态栏右下显示注册的单位部门名称;
echo   3. 两个 exe 各拖入 .raw / .txt 验证转换与预览。
echo.
pause
