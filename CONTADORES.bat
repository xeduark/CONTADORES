@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Primero ejecuta INSTALAR.bat
    pause
    exit /b 1
)
rem En un bloque: la actualizacion puede cambiar este mismo archivo mientras se ejecuta.
rem Las claves del SMTP van en contadores_config.bat (no se sube a git)
(
    ".venv\Scripts\python.exe" actualizar.py
    if exist contadores_config.bat call contadores_config.bat
    ".venv\Scripts\python.exe" contadores.py
    if not "%1"=="auto" pause
    exit /b
)
