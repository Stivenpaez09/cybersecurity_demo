# Verificación de implementación

Fecha: 7 de noviembre de 2026, America/Bogota.

## Implementación entregada

Las fases 0–7 tienen código, configuración, pruebas o instrucciones operativas según corresponde. El plan y su matriz completa están en `Plan de implementacion.md`. Las validaciones físicas y de infraestructura se distinguen de las pruebas automatizadas.

| Área | Evidencia |
|---|---|
| MVC y proceso único | app/model, app/control, app/web; entrada app.main sin reloader |
| Modelo, simulación, reinicio y eventos | tests/test_planta.py: determinismo, dinámica, límites y concurrencia |
| Modbus real y política | Cliente TCP contra listener real; FC5/6/15/16 y rechazo explícito de FC22/23 |
| Atomicidad | Escritura múltiple cruzando registro de solo lectura sin mutación parcial; cambios de modo concurrentes con escrituras reales |
| Gateway | Token válido/inválido, actuadores booleanos, rangos y ausencia de token en eventos |
| API y origen local | Contratos, errores, Host, Origin, Sec-Fetch-Site y Content-Type |
| Salud | Detección de motor detenido y listener Modbus real detenido |
| Frontend | Navegador Chromium real, dos resoluciones, consola JS y tráfico externo |
| Fuentes offline | Big Shoulders y DSEG7 con licencias OFL en static/fonts |
| Docker | Imagen construida, contenedor healthy, usuario 10001, filesystem de solo lectura y publicaciones loopback comprobadas |
| Operación | README, scripts PowerShell, exportación/importación y guion |

## Pruebas ejecutadas

- `python -m pytest -q -s`: **10 pruebas aprobadas**. Incluye 7.200 pasos equivalentes a 30 minutos de tiempo **simulado**, diez ciclos y 20 mediciones de escritura TCP hasta instantánea. No se confunde esa medición con render del navegador.
- `python -m pip check`: dependencias compatibles, sin requisitos rotos.
- `python -m compileall`: compilación de módulos correcta.
- Análisis de sintaxis PowerShell: los cuatro scripts correctos.
- `docker compose config --quiet`: configuración válida.
- `docker manifest inspect python:3.13.12-slim`: imagen base disponible con manifiesto Linux amd64.
- `node tests/navegador.cjs`: prueba del navegador con 20 escrituras visibles, modos, gateway, reconexión y sin llamadas externas. Métricas y capturas en `artifacts/navegador.json`, `tablero-1366.png`, `tablero-1920.png`, `tablero-protegido.png`.
- Medición nativa: **20 escrituras repartidas entre los tres escenarios, máximo 534,6 ms**. Medición final contra **Docker: máximo 1,051 s**, sin errores JavaScript ni peticiones externas; ambas resoluciones muestran el tablero completo sin desplazamiento horizontal ni pie fuera de pantalla.
- Respuesta de polling retrasada deliberadamente: se descarta y no revierte un cambio de modo ya confirmado. Sesión identifica cada proceso, generación cada reinicio de planta y revisión ordena cambios.
- `node tests/reinicio.cjs`: caída real de un proceso propio, aviso de datos desactualizados y recuperación automática en el mismo navegador tras iniciar una nueva instancia; estado inicial y modo de arranque recuperados.
- `python scripts/ensayo.py`: **ensayo nativo aprobado de 1.800,771 segundos reales**, 1.772 muestras y consulta máxima de 42,822 ms. Salud de los tres componentes, progreso de simulación, rangos y límite de eventos comprobados durante 30 minutos. Evidencia: `artifacts/ensayo.json`. Es independiente de los 30 minutos simulados de la prueba unitaria.
- `docker compose build` y `docker compose up -d --wait --no-build`: imagen Python 3.13.12 construida y servicio healthy. Prueba inicial en puertos host 28473/28524 para no interrumpir el ensayo nativo en 18473/18524.
- Arranque con etiqueta de imagen inicialmente inexistente: `compose up` construyó la imagen y llegó a healthy en un proyecto temporal sin puertos publicados; dicho proyecto se eliminó al terminar. Confirma el flujo de un solo comando además del arranque con imagen preparada.
- `docker inspect`: usuario 10001, filesystem de solo lectura y publicaciones explícitas en 127.0.0.1.
- Arranque por entorno en modo protegido y `docker compose restart planta`: modo inicial recuperado, valores reiniciados y cierre ordenado registrado como "Planta detenida".
- Exportación a `artifacts/planta-offline.tar` e importación con `docker load`: aprobadas.
- `scripts/probar-offline.ps1`: aprobado dentro de un contenedor `--network none`, sin interfaz externa. Comprueba HTTP, fuentes y recursos locales, escritura Modbus, rechazo protegido y gateway. El contenedor temporal fue eliminado al terminar.
- Estado de entrega: proceso nativo de prueba cerrado; contenedor final healthy en `127.0.0.1:18473` y `127.0.0.1:18524`, modo inseguro, válvula cerrada y agitador encendido. Tablero y vista del ponente responden HTTP 200.

Entorno automatizado utilizado: Windows, Python 3.14 del entorno virtual existente, Flask 3.1.3, pymodbus 3.8.6, Waitress 3.0.2, pytest 8.3.5 y Playwright 1.61.1. También se verificó el runtime Docker Linux amd64 con Python 3.13.12 y Docker Engine 29.6.1.

Se resolvió el arranque inicial de Docker Desktop. La red internal omitía publicaciones de puertos en este motor; se sustituyó por una red bridge propia con exposición únicamente loopback. La prueba --network none verifica independientemente que la aplicación no depende de internet.

## Validaciones pendientes de infraestructura o del ponente

1. Revisar proyección real a unos tres metros y compartir pantalla en la transmisión.
2. Grabar y reproducir el video local de respaldo, fuera del alcance del código.
3. Repetir el checklist en el portátil y sala definitivos si se trasladan los artefactos a otro equipo.

## Referencias técnicas consultadas

- [Internos de pymodbus 3.8.6](https://pymodbus.readthedocs.io/en/v3.8.6/source/internals.html), contrastados con el código instalado: las PDU se interceptan antes de aplicar escrituras para garantizar respuesta de error.
- [Servicios y política de descarga de Docker Compose](https://docs.docker.com/reference/compose-file/services/#pull_policy): se prepara/importa la imagen antes del arranque offline con pull_policy never.
