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
    rem En automatico queda todo en registro.log, para saber si el envio se hizo
    if "%1"=="auto" (
        echo ===== %date% %time% >> registro.log
        ".venv\Scripts\python.exe" contadores.py >> registro.log 2>&1
        if errorlevel 1 (echo RESULTADO: FALLO >> registro.log) else (echo RESULTADO: ENVIADO >> registro.log)
    ) else (
        ".venv\Scripts\python.exe" contadores.py
        pause
    )
    exit /b
)
