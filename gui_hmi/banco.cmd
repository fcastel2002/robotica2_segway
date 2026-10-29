@echo off
rem Banco de pruebas del Segway: doble clic, o desde la consola
rem   gui_hmi\banco [-Grabar] [-Puerto COM5] [-Simular]
rem Todo lo hace banco.ps1; esto solo evita la politica de ejecucion de PowerShell.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0banco.ps1" %*
if errorlevel 1 pause
