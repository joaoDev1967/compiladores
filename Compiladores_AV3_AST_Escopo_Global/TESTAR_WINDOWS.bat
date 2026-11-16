@echo off
setlocal
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%~dp0"
set "AV3_PYTHON=py -3"
py -3 --version >nul 2>nul
if errorlevel 1 set "AV3_PYTHON=python"
%AV3_PYTHON% -m unittest discover -s tests -t . -v
set "AV3_RESULTADO=%ERRORLEVEL%"
echo.
pause
exit /b %AV3_RESULTADO%
