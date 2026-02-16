@echo off
title Subir a GitHub - Distrito 0

:: Asegurar que estamos en la carpeta correcta (donde esta este archivo)
cd /d "%~dp0"

:: Verificar si existe la carpeta .git
if exist .git goto :GIT_EXISTE

:: --- BLOQUE DE AUTO-CONFIGURACION (Solo si no existe .git) ---
echo [!] No se encontro configuracion de Git. Inicializando ahora...
echo.
git init
git branch -M main

:: Vinculamos al repo
git remote add origin https://github.com/Zitioz/Distrito-0.git

echo [INFO] Configurando para subir todo y REEMPLAZAR el repositorio remoto...
git add .
git commit -m "Configuracion inicial automatica"

echo.
echo [INFO] Subiendo archivos (esto puede tardar un poco)...
git push -u origin main --force

echo.
echo [EXITO] Repositorio configurado y subido correctamente.
pause
exit

:GIT_EXISTE

echo ---------------------------------------------------
echo  ESTADO ACTUAL DEL REPOSITORIO
echo ---------------------------------------------------
git status
echo.
echo ---------------------------------------------------

set /p confirm="Quieres subir estos cambios? (S/N): "
if /i "%confirm%" neq "S" goto :EOF

echo.
echo [1/3] Agregando archivos...
git add .

set /p msg="[2/3] Mensaje del commit (Enter para 'Actualizacion rapida'): "
if "%msg%"=="" set msg=Actualizacion rapida

git commit -m "%msg%"

echo.
echo [3/3] Subiendo a GitHub...
git push origin main

echo.
if %errorlevel% equ 0 (
    echo [EXITO] Los cambios se han subido correctamente.
) else (
    echo [ERROR] Hubo un problema al subir los cambios.
)
pause