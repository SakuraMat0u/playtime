@echo off
REM ============================================================
REM  Playtime 打包脚本（Windows）
REM  在已装 PySide6 / PyInstaller(>=6.11) 的环境里运行：
REM    build.bat            目录版 -> dist\Playtime\{Playtime.exe, files\}
REM    build.bat onefile    单文件 -> dist\Playtime.exe（自动请求管理员权限）
REM ============================================================
setlocal
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo [1/2] 检查打包环境：%PY%
"%PY%" -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo [FAIL] 未安装 PyInstaller，请先执行：
    echo        "%PY%" -m pip install -r requirements.txt
    pause
    exit /b 1
)

set "MODE=--contents-directory files"
set "LABEL=目录版（免提权，推荐）"
if /i "%~1"=="onefile" (
    set "MODE=--onefile --uac-admin"
    set "LABEL=单文件（自动请求管理员权限）"
)

echo [2/2] 开始打包：%LABEL%
"%PY%" -m PyInstaller --noconfirm --clean --windowed %MODE% ^
  --name Playtime ^
  --icon assets\app.ico ^
  --version-file version_info.txt ^
  --add-data "assets\fonts;assets\fonts" ^
  --exclude-module PySide6.QtWebEngineCore ^
  --exclude-module PySide6.QtWebEngineWidgets ^
  --exclude-module PySide6.QtWebEngineQuick ^
  --exclude-module PySide6.QtPdf ^
  --exclude-module PySide6.QtPdfWidgets ^
  --exclude-module PySide6.Qt3DCore ^
  --exclude-module PySide6.Qt3DRender ^
  --exclude-module PySide6.QtQuick ^
  --exclude-module PySide6.QtQml ^
  --exclude-module PySide6.QtCharts ^
  --exclude-module PySide6.QtMultimedia ^
  --exclude-module PySide6.QtBluetooth ^
  --exclude-module PySide6.QtSerialPort ^
  --exclude-module PySide6.QtSql ^
  --exclude-module PySide6.QtNetwork ^
  --exclude-module PySide6.QtTest ^
  --exclude-module PySide6.QtSvg ^
  --exclude-module tkinter ^
  --exclude-module numpy ^
  --exclude-module pandas ^
  main.py

echo.
if exist "dist\Playtime\Playtime.exe" (
    echo [OK] 目录版：%CD%\dist\Playtime\Playtime.exe
    echo      发布包组装到 release\Playtime_x64\ 后压缩分发
    exit /b 0
)
if exist "dist\Playtime.exe" (
    for %%F in ("dist\Playtime.exe") do echo [OK] 单文件：%CD%\dist\Playtime.exe  ^(%%~zF 字节^)
    exit /b 0
)
echo [FAIL] 未生成产物
exit /b 1