@echo off
TITLE Distrito 0 - Launcher
cd /d "%~dp0"

:: --- BLOQUE DE VERIFICACIÓN E INSTALACIÓN ---
IF NOT EXIST "venv" (
    echo ========================================================
    echo  NO SE DETECTO ENTORNO VIRTUAL. CREANDO UNO NUEVO...
    echo  (Esto solo pasa la primera vez y puede tardar unos minutos)
    echo ========================================================
    echo.
    
    :: 1. Crear la carpeta venv
    python -m venv venv
    
    :: 2. Activar
    call venv\Scripts\activate
    
    :: 3. Instalar librerías
    echo.
    echo Instalando librerias necesarias...
    pip install -r requirements.txt
    
    echo.
    echo Instalacion completada!
    timeout /t 3
    cls
) ELSE (
    :: Si ya existe, solo activamos
    call venv\Scripts\activate
)

:: --- BLOQUE DE EJECUCIÓN ---
echo ==========================================
echo      INICIANDO DISTRITO 0 APP
echo ==========================================
echo.

streamlit run app.py

:: Si hay error al cerrar, pausa para leerlo
if %ERRORLEVEL% NEQ 0 pause