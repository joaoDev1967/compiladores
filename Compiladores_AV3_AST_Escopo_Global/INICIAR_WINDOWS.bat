@echo off
setlocal
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
set "AV3_FONTE=%~f1"
if not defined AV3_FONTE set "AV3_FONTE=exemplos\demonstracao_tokens.c"
set "AV3_PYTHON=py -3"
py -3 --version >nul 2>nul
if errorlevel 1 set "AV3_PYTHON=python"
%AV3_PYTHON% compilador.py "%AV3_FONTE%"
set "AV3_RESULTADO=%ERRORLEVEL%"
echo.
echo Para analisar outro arquivo .c ou .java, arraste-o sobre este .bat.
echo Codigo de saida: %AV3_RESULTADO%
pause
exit /b %AV3_RESULTADO%
