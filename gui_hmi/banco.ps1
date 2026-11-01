<#
Banco de pruebas del Segway en un solo comando (Windows). Desde la raíz del repo:

    gui_hmi\banco                 puente + página en Chrome/Edge + conexión USB automática
    gui_hmi\banco -Grabar         antes compila y graba firmware/segway_v01 (detecta el puerto)
    gui_hmi\banco -Grabar -Puerto COM5
    gui_hmi\banco -Simular        sin robot, con datos falsos

También con doble clic en banco.cmd. Ctrl+C cierra el puente.
#>
param([switch]$Grabar, [switch]$Simular, [string]$Puerto)
$ErrorActionPreference = 'Stop'

# El puerto serie de la placa: el único que haya, o el del conversor USB-serie (CH343 del conector UART)
function Buscar-Puerto {
    $puertos = @(Get-CimInstance Win32_PnPEntity -Filter "Name LIKE '%(COM%'" |
        Where-Object { $_.Name -match '\((COM\d+)\)' } |
        ForEach-Object { [pscustomobject]@{ Com = $Matches[1]; Nombre = $_.Name } })
    if ($puertos.Count -eq 0) { throw 'No hay ningún puerto serie: ¿está enchufada la placa por el conector UART?' }
    if ($puertos.Count -eq 1) { return $puertos[0].Com }
    $usb = @($puertos | Where-Object { $_.Nombre -match 'CH34|CP210|USB.*SERIAL|UART' })
    if ($usb.Count -eq 1) { return $usb[0].Com }
    $lista = ($puertos | ForEach-Object { "  $($_.Com)  $($_.Nombre)" }) -join "`n"
    throw "Hay varios puertos; elegir uno con -Puerto:`n$lista"
}

if ($Grabar) {
    if (-not $Puerto) { $Puerto = Buscar-Puerto }
    if (-not (Get-Command idf.py -ErrorAction SilentlyContinue)) {
        # Instalación de ESP-IDF hecha con el instalador EIM
        $perfil = Get-ChildItem 'C:\Espressif\tools\Microsoft.v*.PowerShell_profile.ps1' -ErrorAction SilentlyContinue |
            Sort-Object Name | Select-Object -Last 1
        if (-not $perfil) { throw 'No encuentro ESP-IDF: abrir la terminal de ESP-IDF y correr esto desde ahí.' }
        Write-Host 'Activando ESP-IDF...'
        . $perfil.FullName *> $null
    }
    Write-Host "Compilando y grabando firmware/segway_v01 por $Puerto..."
    # build/ es la misma carpeta que usa la extensión de VS Code (idf.buildPath)
    Push-Location (Join-Path $PSScriptRoot '..\firmware\segway_v01')
    try {
        idf.py -p $Puerto build flash
        if ($LASTEXITCODE) { throw "Falló la compilación o la grabación (código $LASTEXITCODE)." }
    } finally {
        Pop-Location
    }
}

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { $python = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $python) { throw 'No encuentro Python 3: instalarlo desde python.org.' }
$argumentos = @(Join-Path $PSScriptRoot 'puente.py')
if ($Simular) { $argumentos += '--simular' }
& $python @argumentos
