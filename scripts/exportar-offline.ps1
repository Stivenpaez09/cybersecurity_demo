param([string]$Destino = 'artifacts/planta-offline.tar')
$ErrorActionPreference = 'Stop'
docker compose build
if ($LASTEXITCODE -ne 0) { throw 'No se pudo construir la imagen.' }
$carpetaDemo = Split-Path -Parent $Destino
if ($carpetaDemo) { New-Item -ItemType Directory -Force -Path $carpetaDemo | Out-Null }
docker save -o $Destino codigo-valvula-demo:1.0.0
if ($LASTEXITCODE -ne 0) { throw 'No se pudo exportar la imagen.' }
$hashImagenDemo = (Get-FileHash -LiteralPath $Destino -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath ($Destino + '.sha256') -Encoding ascii -Value ($hashImagenDemo + '  ' + (Split-Path -Leaf $Destino))
Write-Host "Imagen exportada a $Destino. Copia tambien el repositorio. Importacion: docker load -i $Destino"
