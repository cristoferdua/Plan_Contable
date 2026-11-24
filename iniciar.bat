@echo off
setlocal
chcp 65001 >nul
title Plan Contable
cd /d "%~dp0"

echo.
echo  ================================================
echo     PLAN CONTABLE - Sistema de contabilidad PCGE
echo  ================================================
echo.

rem ---------- 1. Entorno de Python (solo la primera vez) ----------
if exist "venv\Scripts\python.exe" goto :dependencias

echo  [1/3] Preparando el sistema por primera vez. Esto tarda unos minutos...
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY (
    echo.
    echo  ERROR: No se encontro Python.
    echo  Instala Python 3.12 desde https://www.python.org/downloads/
    echo  y marca la casilla "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)
%PY% -m venv venv
if errorlevel 1 (
    echo  ERROR: No se pudo crear el entorno de Python.
    pause
    exit /b 1
)

:dependencias
rem ---------- 2. Dependencias (la primera vez o si cambiaron) ----------
fc /b requirements.txt "venv\requirements.instalado" >nul 2>&1
if not errorlevel 1 goto :configuracion
echo  [2/3] Instalando componentes...
"venv\Scripts\python.exe" -m pip install --upgrade pip --quiet --disable-pip-version-check
"venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo.
    echo  ERROR: No se pudieron instalar los componentes. Revisa tu conexion a internet.
    pause
    exit /b 1
)
copy /y requirements.txt "venv\requirements.instalado" >nul

:configuracion
rem ---------- 3. Configuracion (.env) ----------
if not exist ".env" (
    echo  [3/3] Creando la configuracion inicial...
    copy /y ".env.example" ".env" >nul
)

rem ---------- Iniciar ----------
echo.
echo  Sistema listo. Se abrira el navegador en http://127.0.0.1:5000
echo  Para otras PCs de la red usa la direccion que aparece abajo ("Running on").
echo.
echo  NO CIERRES ESTA VENTANA mientras uses el sistema.
echo  Para apagarlo, cierra esta ventana o presiona Ctrl+C.
echo.
if not defined ABRIR_NAVEGADOR set "ABRIR_NAVEGADOR=1"
"venv\Scripts\python.exe" app.py
if errorlevel 1 (
    echo.
    echo  El sistema se detuvo con un error. Revisa el mensaje de arriba.
    pause
)
endlocal
