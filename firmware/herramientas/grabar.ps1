# Graba el firmware (segway_v03 salvo -Proyecto segway_v02) por el cable USB (CH343) rápido y sin que la ESP32 se reinicie por baja tensión.
#
#   powershell -ExecutionPolicy Bypass -File firmware\herramientas\grabar.ps1 [-Puerto COM7] [-Compilar]
#
# Por qué tardaba 1,5 min (11/11): con solo el USB, el stub de esptool (lo que usa "idf.py flash") hace
# reiniciar la ESP32 por baja tensión (BROWNOUT_RST, "Invalid head of packet"), así que se pasó a
# --no-stub... pero a 115200 baudios y sin compresión: 964 kB × 10 bits / 115200 = 84 s de puro cable.
# Lo que aceleraba "idf.py flash" no era el stub sino la velocidad (460800) y la compresión.
#
# Esto: sin stub (no se reinicia), a 921600 baudios (el cargador de la ROM del S3 cambia de velocidad
# igual), y con --diff-with: compara con lo último que se grabó y solo reescribe los sectores que
# cambiaron. Si falla a 921600 baja a 460800 y después a 115200. Con batería, -ConStub usa lo de siempre.
param(
    [string]$Puerto = 'COM7',
    [string]$Proyecto = 'segway_v03',   # 12/11: la versión con todo (la de Francisco + el salto)
    [int[]]$Baudios = @(921600, 460800, 115200),
    [switch]$Compilar,
    [switch]$ConStub,        # con batería: el stub con compresión es lo más rápido
    [switch]$Comprimir       # sin stub, probar también comprimido (la ROM del S3 lo acepta; no probado aún)
)
$ErrorActionPreference = 'Stop'
$perfil = Get-ChildItem 'C:\Espressif\tools\Microsoft.v*.PowerShell_profile.ps1' | Sort-Object Name | Select-Object -Last 1
. $perfil.FullName *> $null
$fw = Join-Path $PSScriptRoot "..\$Proyecto" | Resolve-Path
$py = 'C:\Espressif\tools\python\v6.1\venv\Scripts\python.exe'

if ($Compilar) {
    Set-Location $fw
    $salida = idf.py build 2>&1 | Out-String -Width 300
    if ($salida -notmatch 'Project build complete') {
        ($salida -split "`n") | Select-String -Pattern ' error|FAILED' | Select-Object -Last 10
        throw 'no compiló'
    }
}
Set-Location (Join-Path $fw 'build')

# Lo último que se grabó, sector por sector (lo mantiene este script e idf.py flash)
$pares = @(
    @('bootloader/bootloader.bin', 'bootloader/bootloader_flashed.bin'),
    @('partition_table/partition-table.bin', 'partition_table/partition-table_flashed.bin'),
    @("$Proyecto.bin", "$Proyecto`_flashed.bin")
)
$diff = @()
if (($pares | Where-Object { -not (Test-Path $_[1]) }).Count -eq 0) {
    $diff = @('--diff-with') + ($pares | ForEach-Object { $_[1] })
}
$stub = @(); if (-not $ConStub) { $stub += '--no-stub' }
$comp = @(); if ($Comprimir -or $ConStub) { $comp += '--compress' }

$ok = $false
foreach ($b in $Baudios) {
    $t = Get-Date
    Write-Output "grabando por $Puerto a $b baudios$(if ($ConStub) { ' con stub' } else { ' sin stub' })$(if ($diff) { ', solo lo que cambió' })..."
    $ErrorActionPreference = 'Continue'     # esptool escribe en stderr: que no lo corte PowerShell
    $s = & $py -m esptool --chip esp32s3 -p $Puerto -b $b --before default-reset --after hard-reset @stub `
        write-flash @comp '@flash_args' @diff 2>&1 | Out-String -Width 300
    $codigo = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    ($s -split "`n") | Select-String -Pattern 'error|Wrote|Skipped|Hash of data|could not open' | Select-Object -Last 6
    if ($codigo -eq 0 -and $s -match 'Hard resetting') {
        $ok = $true
        Write-Output ("listo en {0:N0} s" -f ((Get-Date) - $t).TotalSeconds)
        break
    }
    if ($s -match 'could not open|PermissionError') { throw "$Puerto no está o está ocupado: ¿enchufado? ¿lo tiene abierto el puente o un monitor?" }
}
if (-not $ok) { throw 'no se pudo grabar a ninguna velocidad' }
foreach ($p in $pares) { Copy-Item $p[0] $p[1] -Force }
& $py -m esptool --chip esp32s3 merge-bin -o "$Proyecto`_completo.bin" '@flash_args' *> $null
