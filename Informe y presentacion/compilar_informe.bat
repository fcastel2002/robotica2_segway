@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PDFLATEX=pdflatex"
where pdflatex >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe" (
        set "PDFLATEX=%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"
    ) else (
        echo [ERROR] No se encontro pdflatex en esta PC.
        pause
        exit /b 1
    )
)

echo === Compilando Informe Tecnico Final (pasada 1 de 2)... ===
"%PDFLATEX%" -interaction=nonstopmode informe_tecnico_final.tex

echo === Compilando Informe Tecnico Final (pasada 2 de 2 para el indice)... ===
"%PDFLATEX%" -interaction=nonstopmode informe_tecnico_final.tex

if exist "informe_tecnico_final.pdf" (
    echo.
    echo [OK] PDF generado exitosamente: informe_tecnico_final.pdf
    start "" "informe_tecnico_final.pdf"
) else (
    echo.
    echo [ERROR] No se pudo generar el PDF. Revisa informe_tecnico_final.log
    pause
)
