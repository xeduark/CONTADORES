@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Las claves del SMTP van en contadores_config.bat (no se sube a git)
if exist contadores_config.bat call contadores_config.bat

if not exist ".venv\Scripts\python.exe" (
    call :buscar_python
    if not defined PY (
        echo Instalando Python...
        winget install -e --id Python.Python.3.13 --accept-package-agreements --accept-source-agreements --override "/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1"
        call :buscar_python
    )
    if not defined PY (
        echo No se encontro Python. Cierra esta ventana y abre CONTADORES.bat otra vez.
        pause
        exit /b 1
    )
    echo Creando entorno e instalando librerias...
    %PY% -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
)
".venv\Scripts\python.exe" contadores.py
pause
exit /b

rem Busca un Python real. El "python" de la Microsoft Store no cuenta: falla al ejecutar codigo.
:buscar_python
set "PY="
python -c "import sys" >nul 2>&1 && set "PY=python" && exit /b
py -3 -c "import sys" >nul 2>&1 && set "PY=py -3" && exit /b
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set PY="%%D\python.exe"
exit /b
