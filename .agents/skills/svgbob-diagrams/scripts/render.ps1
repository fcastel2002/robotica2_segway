[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$InputPath,

    [Parameter(Position = 1)]
    [string]$OutputPath,

    [string]$FontFamily = "Consolas, monospace",
    [double]$FontSize = 16,
    [double]$Scale = 1.5,
    [double]$StrokeWidth = 2,
    [string]$Background = "white",
    [string]$StrokeColor = "#172033",
    [string]$FillColor = "#172033",

    [switch]$SkipPng
)

$ErrorActionPreference = "Stop"

$resolvedInput = (Resolve-Path -LiteralPath $InputPath).Path
if (-not (Test-Path -LiteralPath $resolvedInput -PathType Leaf)) {
    throw "El archivo de entrada no es un archivo regular: $resolvedInput"
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $resolvedOutput = [System.IO.Path]::ChangeExtension($resolvedInput, ".svg")
} else {
    $candidateOutput = [System.IO.Path]::GetFullPath($OutputPath)
    if ([System.IO.Path]::GetExtension($candidateOutput) -ne ".svg") {
        throw "La salida debe usar la extensión .svg: $candidateOutput"
    }
    $resolvedOutput = $candidateOutput
}

if ($resolvedInput -eq $resolvedOutput) {
    throw "La entrada y la salida no pueden ser el mismo archivo."
}

$outputDirectory = Split-Path -Parent $resolvedOutput
if (-not (Test-Path -LiteralPath $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

$svgbob = Get-Command svgbob_cli -ErrorAction SilentlyContinue
if (-not $svgbob) {
    $svgbob = Get-Command svgbob -ErrorAction SilentlyContinue
}
if (-not $svgbob) {
    throw "No se encontró svgbob_cli. Instálalo con: cargo install svgbob_cli --locked"
}

$arguments = @(
    $resolvedInput,
    "--output", $resolvedOutput,
    "--font-family", $FontFamily,
    "--font-size", $FontSize.ToString([Globalization.CultureInfo]::InvariantCulture),
    "--scale", $Scale.ToString([Globalization.CultureInfo]::InvariantCulture),
    "--stroke-width", $StrokeWidth.ToString([Globalization.CultureInfo]::InvariantCulture),
    "--background", $Background,
    "--stroke-color", $StrokeColor,
    "--fill-color", $FillColor
)

& $svgbob.Source @arguments
if ($LASTEXITCODE -ne 0) {
    throw "svgbob terminó con código $LASTEXITCODE."
}

if (-not (Test-Path -LiteralPath $resolvedOutput -PathType Leaf)) {
    throw "svgbob no creó la salida esperada: $resolvedOutput"
}

$svgHeader = Get-Content -LiteralPath $resolvedOutput -Raw
if ($svgHeader -notmatch "<svg[\s>]" ) {
    throw "La salida no contiene un elemento SVG válido: $resolvedOutput"
}

$resolvedSvg = (Resolve-Path -LiteralPath $resolvedOutput).Path
Write-Output "SVG: $resolvedSvg"

if (-not $SkipPng) {
    $resvg = Get-Command resvg -ErrorAction SilentlyContinue
    if ($resvg) {
        $pngPath = [System.IO.Path]::ChangeExtension($resolvedSvg, ".png")
        if (Test-Path -LiteralPath $pngPath) {
            Remove-Item -LiteralPath $pngPath -Force
        }

        & $resvg.Source `
            --zoom 2 `
            --background $Background `
            --shape-rendering geometricPrecision `
            --text-rendering optimizeLegibility `
            $resolvedSvg `
            $pngPath

        if ($LASTEXITCODE -ne 0) {
            Write-Warning "resvg terminó con código $LASTEXITCODE; el SVG sí está disponible."
        } elseif (Test-Path -LiteralPath $pngPath -PathType Leaf) {
            Write-Output "PNG: $((Resolve-Path -LiteralPath $pngPath).Path)"
        } else {
            Write-Warning "resvg no creó la vista PNG; el SVG sí está disponible."
        }
    } else {
        Write-Warning "No se encontró resvg; instálalo con: cargo install resvg --locked"
    }
}
