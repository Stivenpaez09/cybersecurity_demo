$ErrorActionPreference = 'Stop'
$nombrePruebaDemo = 'codigo-valvula-offline-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$codigoPruebaDemo = @'
import json
import subprocess
import time
from urllib.request import Request, urlopen
from urllib.error import URLError
from app.config import TOKEN

base = 'http://127.0.0.1:18473'
def consultar(ruta, datos=None, token=None):
    cabeceras = {'Content-Type': 'application/json'}
    if token:
        cabeceras['Authorization'] = 'Bearer ' + token
    solicitud = Request(base + ruta, data=None if datos is None else json.dumps(datos).encode(), headers=cabeceras)
    with urlopen(solicitud, timeout=2) as respuesta:
        return json.load(respuesta)

for intento in range(50):
    try:
        assert all(consultar('/api/salud').values())
        break
    except URLError:
        time.sleep(0.1)
else:
    raise RuntimeError('La planta sin red no arranco')

assert consultar('/api/estado')['modo'] == 'inseguro'
assert subprocess.run(['python', 'cliente_control.py', 'abrir-valvula']).returncode == 0
assert consultar('/api/estado')['valvula'] is True
consultar('/api/reiniciar', {})
consultar('/api/modo', {'modo': 'protegido'})
assert subprocess.run(['python', 'cliente_control.py', 'abrir-valvula']).returncode == 2
assert consultar('/api/estado')['valvula'] is False
consultar('/api/control', {'campo': 'valvula', 'valor': True}, TOKEN)
estado = consultar('/api/estado')
assert estado['valvula'] and not estado['valvula_indebida']
for ruta in ('/', '/static/tablero.css', '/static/tablero.js', '/static/fonts/BigShoulders.woff2', '/static/fonts/DSEG7Classic-Bold.woff2'):
    with urlopen(base + ruta, timeout=2) as respuesta:
        assert len(respuesta.read()) > 100
print('OFFLINE APROBADO: salud, web, assets, Modbus, rechazo y gateway sin interfaz externa de red.')
'@
try {
    docker run --detach --pull never --name $nombrePruebaDemo --network none --read-only --cap-drop ALL --security-opt no-new-privileges:true codigo-valvula-demo:1.0.0
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear la prueba offline. Construye o importa la imagen.' }
    docker exec $nombrePruebaDemo python -c $codigoPruebaDemo
    if ($LASTEXITCODE -ne 0) { throw 'Fallo de prueba offline.' }
} finally {
    docker rm --force $nombrePruebaDemo | Out-Null
}
