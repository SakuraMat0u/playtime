@echo off
REM ============================================================
REM  编译两个启动器（普通 / 请求管理员），只依赖系统自带 csc。
REM  产物：release\Playtime_x64\Playtime.exe
REM        release\Playtime_x64\Playtime_admin.exe
REM  图标：assets\app.ico   源码：tools\launcher.cs
REM ============================================================
setlocal
cd /d "%~dp0.."

set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "%CSC%" (
    echo [FAIL] 找不到 csc.exe（需要 .NET Framework 4.x）
    pause
    exit /b 1
)

set "OUT=release\Playtime_x64"
if not exist "%OUT%" (
    echo [FAIL] 找不到 %OUT%，请先打包并组装发布目录
    pause
    exit /b 1
)

echo [1/2] 普通启动器
"%CSC%" /nologo /target:winexe /platform:anycpu /optimize+ /win32icon:assets\app.ico ^
  /out:"%OUT%\Playtime.exe" tools\launcher.cs
if errorlevel 1 goto failed

echo [2/2] 管理员启动器
"%CSC%" /nologo /target:winexe /platform:anycpu /optimize+ /define:ADMIN /win32icon:assets\app.ico ^
  /out:"%OUT%\Playtime_admin.exe" tools\launcher.cs
if errorlevel 1 goto failed

echo [OK] %CD%\%OUT%\Playtime.exe
echo [OK] %CD%\%OUT%\Playtime_admin.exe
exit /b 0

:failed
echo [FAIL] 编译失败
pause
exit /b 1