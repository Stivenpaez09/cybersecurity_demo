param(
    [int]$PuertoWeb = $(if ($env:PUERTO_WEB_HOST) { $env:PUERTO_WEB_HOST } else { 18473 }),
    [int]$PuertoModbus = $(if ($env:PUERTO_MODBUS_HOST) { $env:PUERTO_MODBUS_HOST } else { 18524 })
)
$ErrorActionPreference = 'Stop'
try {
    docker info --format '{{.ServerVersion}}'
    if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop no esta disponible. Inicialo y espera a que termine de arrancar.' }
    docker compose version
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose no esta disponible.' }
    if ($PuertoWeb -eq $PuertoModbus) { throw 'Los dos puertos deben ser diferentes.' }
    foreach ($puertoDemo in @($PuertoWeb, $PuertoModbus)) {
        if ($puertoDemo -lt 1024 -or $puertoDemo -gt 65535) { throw "Puerto invalido: $puertoDemo" }
        $escuchaDemo = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $puertoDemo)
        try {
            $escuchaDemo.Server.ExclusiveAddressUse = $true
            $escuchaDemo.Start()
            Write-Host "Puerto local $puertoDemo disponible."
        } catch {
            throw "Puerto $puertoDemo ocupado o reservado. Usa PUERTO_WEB_HOST o PUERTO_MODBUS_HOST con otro valor. No se detuvo ninguna aplicacion."
        } finally { $escuchaDemo.Stop() }
    }
    Write-Host "Listo. Tablero: http://localhost:$PuertoWeb/ | Ponente: http://localhost:$PuertoWeb/ponente"
    Write-Host 'La comprobacion no reserva los puertos. Si usas .env, pasa sus valores con -PuertoWeb y -PuertoModbus.'
} catch {
    Write-Error $_
    exit 1
}
