@echo off
rem Abre el visor de la bajada de escalon en el navegador. Para cerrarlo, cerrar esta ventana.
cd /d "%~dp0..\..\.."
python simulacion\escalon\visor\visor.py
pause
