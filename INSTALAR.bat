@echo off
chcp 65001 >nul
title Instalar contadores
cd /d "%~dp0"

call :buscar_python
if not defined PY (
    echo Instalando Python...
    winget install -e --id Python.Python.3.13 --accept-package-agreements --accept-source-agreements --override "/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1"
    call :buscar_python
)
if not defined PY (
    echo.
    echo No se encontro Python. CIERRA esta ventana y abre INSTALAR.bat otra vez.
    echo Si vuelve a salir este mensaje, instala Python desde python.org marcando "Add python.exe to PATH".
    pause
    exit /b 1
)
echo Python encontrado: %PY%

rem Si la carpeta se copio de otro PC, el entorno viejo no sirve y se rehace.
if exist ".venv" (
    ".venv\Scripts\python.exe" -c "import sys" >nul 2>&1 || rmdir /s /q ".venv"
)
if not exist ".venv\Scripts\python.exe" (
    echo Creando el entorno de Python...
    %PY% -m venv .venv
)

echo Instalando librerias...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
".venv\Scripts\python.exe" -c "import pysnmp" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: las librerias no quedaron instaladas. Revisa el mensaje de arriba y la conexion a internet.
    pause
    exit /b 1
)

rem Git, para que el programa se actualice solo desde GitHub
set "HAYGIT="
where git >nul 2>&1 && set "HAYGIT=1"
if exist "C:\Program Files\Git\cmd\git.exe" set "HAYGIT=1"
if not defined HAYGIT (
    echo Instalando Git, para las actualizaciones automaticas...
    winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements
)

echo Creando el acceso directo en el Escritorio...
powershell -NoProfile -Command "$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'Contadores impresoras.lnk')); $s.TargetPath='%~dp0CONTADORES.bat'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%~dp0logo.ico'; $s.Save()"

echo Agendando el envio: el dia 24 de cada mes a las 9 pm...
schtasks /create /f /tn ContadoresImpresoras /sc monthly /d 24 /st 21:00 /tr "\"%~dp0CONTADORES.bat\" auto" >nul
if errorlevel 1 echo No se pudo agendar la tarea. Ejecuta INSTALAR.bat como el mismo usuario que usara el PC.

rem En un bloque: la actualizacion puede cambiar este mismo archivo mientras se ejecuta
(
    echo Configurando la actualizacion automatica...
    ".venv\Scripts\python.exe" actualizar.py --instalar
    if errorlevel 1 (
        echo Aun no se actualiza solo: sigue los pasos de arriba y abre INSTALAR.bat otra vez.
    ) else (
        echo.
        echo LISTO. Crea contadores_config.bat con las claves del SMTP y ejecuta CONTADORES.bat.
    )
    pause
    exit /b 0
)

rem Busca un Python real. El "python" de la Microsoft Store no cuenta: falla al ejecutar codigo.
:buscar_python
set "PY="
python -c "import sys" >nul 2>&1 && set "PY=python" && exit /b
py -3 -c "import sys" >nul 2>&1 && set "PY=py -3" && exit /b
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set PY="%%D\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Python\bin\python.exe" set PY="%LOCALAPPDATA%\Python\bin\python.exe"
exit /b
