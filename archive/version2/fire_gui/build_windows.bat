@echo off
setlocal
cd /d "%~dp0\..\.."

where py >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install 64-bit Python, then run this file again.
  pause
  exit /b 1
)

if not exist ".venv-windows\Scripts\python.exe" (
  py -3.11 -m venv .venv-windows
  if errorlevel 1 goto :failed
)

call ".venv-windows\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :failed
python -m pip install -r apps\fire_gui\requirements.txt -r apps\fire_gui\requirements-windows-build.txt
if errorlevel 1 goto :failed
python -m PyInstaller --noconfirm --clean --workpath artifacts\pyinstaller\build --distpath artifacts\pyinstaller\dist apps\fire_gui\IndonesiaFireGUI.spec
if errorlevel 1 goto :failed

echo.
echo Build complete: artifacts\pyinstaller\dist\IndonesiaFireGUI.exe
pause
exit /b 0

:failed
echo.
echo The Windows build failed. Review the messages above.
pause
exit /b 1
