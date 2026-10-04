@echo off
chcp 65001 >nul
rem Open-LLM-VTuber Launcher (Qt6 native)
rem 优先使用已打包的 exe，其次使用启动器专用构建环境，最后回退到系统 Python。
cd /d "%~dp0"

if exist "Open-LLM-VTuber-Launcher.exe" (
    start "" "Open-LLM-VTuber-Launcher.exe"
    goto :eof
)

if exist ".venv-launcher\Scripts\pythonw.exe" (
    start "" ".venv-launcher\Scripts\pythonw.exe" -m launcher_qt
    goto :eof
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw -m launcher_qt
    goto :eof
)

echo [提示] 未找到可用的图形化 Python 环境。
echo        请先创建启动器环境：
echo            uv venv .venv-launcher --python 3.13
echo            uv pip install --python .venv-launcher\Scripts\python.exe pyside6-essentials pyinstaller pillow ruamel.yaml
echo        或直接双击 build_launcher.bat 打包成 exe。
pause
