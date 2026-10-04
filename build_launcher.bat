@echo off
chcp 65001 >nul
rem 打包 Open-LLM-VTuber Qt6 启动器为单文件 exe
cd /d "%~dp0"

if not exist ".venv-launcher\Scripts\python.exe" (
    echo [错误] 未找到 .venv-launcher 构建环境，请先执行：
    echo     uv venv .venv-launcher --python 3.13
    echo     uv pip install --python .venv-launcher\Scripts\python.exe pyside6-essentials pyinstaller pillow ruamel.yaml
    pause
    exit /b 1
)

".venv-launcher\Scripts\python.exe" "scripts\build_launcher.py" %*
set EXITCODE=%errorlevel%
echo.
if %EXITCODE%==0 (
    echo [完成] 产物位于 dist\Open-LLM-VTuber-Launcher.exe
) else (
    echo [失败] 退出码 %EXITCODE%
)
pause
exit /b %EXITCODE%
