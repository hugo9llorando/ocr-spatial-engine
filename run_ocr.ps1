param(
    [string]$Path = "",
    [switch]$Watch,
    [switch]$Verbose,
    [string]$Mode = "columns",
    [switch]$NoColumns,
    [string]$Export = "",
    [switch]$Gemini,
    [switch]$Help
)

$VENV_PYTHON = "C:\Users\elcha\ocr_env312\Scripts\python.exe"
$MAIN_SCRIPT = "C:\Users\elcha\ocr_spatial_engine\main.py"

# Cargar API key del registro de Windows si no está en el entorno
if (-not $env:GEMINI_API_KEY) {
    $regKey = [Environment]::GetEnvironmentVariable("GEMINI_API_KEY", "User")
    if ($regKey) { $env:GEMINI_API_KEY = $regKey }
}

if ($Help -or ($Path -eq "" -and -not $Watch)) {
    Write-Host @"
OCR Spatial Engine - CLI Wrapper
=================================
Uso:
  .\run_ocr.ps1 -Path <imagen> [-Verbose] [-Mode columns|rows] [-NoColumns] [-Gemini] [-Export txt|json|csv|all|none]
  .\run_ocr.ps1 -Watch [-Verbose]

Ejemplos:
  .\run_ocr.ps1 -Path "C:\Users\elcha\Desktop\captura.png" -Verbose -Gemini
  .\run_ocr.ps1 -Path "C:\Users\elcha\Desktop\documento.jpg" -Export json
  .\run_ocr.ps1 -Watch
"@
    exit 0
}

$argsList = @($MAIN_SCRIPT)

if ($Watch) {
    $argsList += "--watch"
} elseif ($Path -ne "") {
    $argsList += "`"$Path`""
} else {
    Write-Host "[ERROR] Debes especificar -Path <imagen> o -Watch" -ForegroundColor Red
    exit 1
}

if ($Verbose) { $argsList += "-v" }
if ($Mode -ne "columns") { $argsList += "-m"; $argsList += $Mode }
if ($NoColumns) { $argsList += "--no-columns" }
if ($Gemini) { $argsList += "--gemini" }
if ($Export -ne "") { $argsList += "-e"; $argsList += $Export }

Write-Host "[OCR] Ejecutando..." -ForegroundColor Cyan
Write-Host "[OCR] $VENV_PYTHON $argsList" -ForegroundColor Gray

& $VENV_PYTHON $argsList

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OCR] Completado" -ForegroundColor Green
} else {
    Write-Host "[OCR] Error (código: $LASTEXITCODE)" -ForegroundColor Red
}
