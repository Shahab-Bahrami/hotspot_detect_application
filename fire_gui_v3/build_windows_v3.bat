@echo off
setlocal
cd /d "%~dp0\..\.."

where py >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install 64-bit Python, then run this file again.
  pause
  exit /b 1
)

if not exist ".venv-windows-v3\Scripts\python.exe" (
  py -3 -m venv .venv-windows-v3
  if errorlevel 1 goto :failed
)

call ".venv-windows-v3\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :failed
python -m pip install -r apps\fire_gui_v3\requirements.txt -r apps\fire_gui_v3\requirements-windows-build.txt
if errorlevel 1 goto :failed
python -m PyInstaller --noconfirm --clean --workpath artifacts\version3\pyinstaller\build --distpath artifacts\version3\pyinstaller\dist apps\fire_gui_v3\SenseNetHotspotV3.spec
if errorlevel 1 goto :failed

echo.
echo Version 3 build complete: artifacts\version3\pyinstaller\dist\SenseNetHotspotV3.exe
pause
exit /b 0

:failed
echo.
echo The Windows build failed. Review the messages above.
pause
exit /b 1
