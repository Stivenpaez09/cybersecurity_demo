# Del código a la válvula

Simulador educativo de una planta de biogás. Python + Flask MVC + pymodbus, un servicio Docker, estado en memoria y recursos web locales. Todos los equipos son simulados.

## Preparación inicial en Windows

Requisitos: Docker Desktop iniciado con contenedores Linux y Docker Compose v2. La preparación inicial descarga dependencias; la ponencia funciona sin internet.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/comprobar.ps1
docker compose up
```

El arranque es **`docker compose up`**; si falta la imagen, Compose la construye usando el Dockerfile. La primera construcción necesita internet. Para una ponencia offline construye previamente con `docker compose build` o importa la imagen antes de arrancar. El comprobador PowerShell es una revisión opcional previa al evento.

- Tablero de audiencia: **http://localhost:18473/**
- Vista del ponente: **http://localhost:18473/ponente**
- Estado JSON: http://localhost:18473/api/estado
- Salud: http://localhost:18473/api/salud
- PLC Modbus: `127.0.0.1:18524`, dispositivo `1`, direcciones base cero.

Los puertos se publican solo en loopback. Compose crea una red bridge exclusiva del proyecto; la aplicación no realiza llamadas externas. No se necesitan Python ni Node en Windows para operar la demo.

## Guion de la demostración

1. Abre `/ponente` en una ventana privada del ponente y `/` en la ventana que proyectas. Selecciona **MODO INSEGURO** y **REINICIAR PLANTA**.
2. Muestra los seis indicadores y el banner. La planta evoluciona sola.
3. En una segunda terminal proyectada, muestra el script y ejecuta:

```powershell
Get-Content cliente_control.py
docker compose exec planta python cliente_control.py abrir-valvula
```

4. Observa válvula abierta, alarma, evento de escritura y caída gradual de presión. También puedes usar:

```powershell
docker compose exec planta python cliente_control.py temperatura-alta
docker compose exec planta python cliente_control.py presion-alta
```

5. Reinicia la planta desde `/ponente` y selecciona **MODO PROTEGIDO**.
6. Repite exactamente el primer comando: devuelve `[RECHAZADO]`, código de salida `2`, error Modbus `ILLEGAL_FUNCTION` y evento verde en el tablero. Las lecturas siguen disponibles.
7. Demuestra el camino autorizado:

```powershell
docker compose exec planta python cliente_autorizado.py abrir-valvula
```

La apertura autorizada no se marca como apertura directa indebida. La protección es una política del simulador: Modbus clásico no adquiere autenticación nativa. El gateway usa un token didáctico local, no cuentas de usuario ni seguridad de producción.

## Puertos alternativos y configuración

Los predeterminados `18473` y `18524` son configurables y deben comprobarse en el portátil. No se detienen otras apps.

```powershell
$env:PUERTO_WEB_HOST = '28473'
$env:PUERTO_MODBUS_HOST = '28524'
powershell -ExecutionPolicy Bypass -File scripts/comprobar.ps1 -PuertoWeb 28473 -PuertoModbus 28524
docker compose up
```

También puedes copiar `.env.example` a `.env`; Compose lo lee automáticamente. El comprobador PowerShell usa sus parámetros o las variables del proceso, no analiza `.env`. Si cambias puertos, abre `http://localhost:28473/`; los clientes dentro del contenedor siguen usando los puertos internos fijos. Después de cambiar configuración, `docker compose up --force-recreate` recrea solo esta demo.

Variables: `MODO=inseguro|protegido`, `TOKEN_DEMO` (predeterminado `valvula-laboratorio-local`) y los ocho umbrales de `app/config.py`. El token no se imprime ni se guarda en eventos. El arranque muestra las direcciones internas; usa el puerto host configurado para el navegador.

```powershell
$env:MODO = 'protegido'
docker compose up --force-recreate
```

## Reinicio y recuperación

- **REINICIAR PLANTA**: restaura valores, semilla y eventos conservando el modo activo; no reinicia el proceso.
- `docker compose restart planta`: recupera el proceso y vuelve al modo de la configuración inicial.
- `docker compose logs --tail 80 planta`: diagnóstico.
- `docker compose ps`: estado del healthcheck.
- `docker compose down`: detiene y elimina únicamente los recursos de este proyecto.

Si un puerto está ocupado, elige otro. Si Docker no responde, inicia Docker Desktop y comprueba que usa contenedores Linux. Si falta una imagen offline, impórtala. El banner **DATOS DESACTUALIZADOS** aparece tras dos segundos sin telemetría y se recupera automáticamente; **COMPONENTE DETENIDO** identifica fallos de simulación o Modbus. El healthcheck responde HTTP 503 ante degradación.

## Paquete offline

En el equipo de preparación, con internet:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/exportar-offline.ps1
```

Copia el repositorio y `artifacts/planta-offline.tar` al portátil. En el destino:

```powershell
docker load -i artifacts/planta-offline.tar
docker compose up --no-build
```

La imagen contiene dependencias, fuentes con licencia abierta y todos los recursos. No hay CDNs, APIs, telemetría ni almacenamiento persistente. `pull_policy: never` impide descargar la imagen de la aplicación durante el arranque. La exportación genera también un checksum SHA256. Para exportar una imagen ya construida sin reconstruir: `docker save -o artifacts/planta-offline.tar codigo-valvula-demo:1.0.0`.

Prueba reproducible sin interfaz externa de red, usando únicamente un contenedor temporal propio:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/probar-offline.ps1
```

Verifica salud, tablero, scripts, fuentes, Modbus inseguro, rechazo protegido y gateway. No modifica la conexión a internet del portátil ni otros contenedores.

## API local

| Método | Ruta | Entrada / resultado |
|---|---|---|
| GET | `/`, `/ponente` | Audiencia y controles del ponente |
| GET | `/api/estado` | Snapshot: seis indicadores, modo, revisión, generación, sesión, ticks, severidades, alarmas, eventos |
| POST | `/api/reiniciar` | `{}`; conserva modo |
| POST | `/api/modo` | `{"modo":"protegido"}` o `inseguro` |
| POST | `/api/control` | `{"campo":"valvula","valor":true}` y `Authorization: Bearer <TOKEN_DEMO>` |
| GET | `/api/salud` | `web`, `simulacion`, `modbus`; 200 o 503 |

Los POST requieren JSON. El navegador debe enviar el mismo origen local; no hay CORS abierto. Los clientes locales de terminal sin Origin están permitidos. Host limitado a `localhost` y `127.0.0.1`. `campo` admite `temperatura`, `presion`, `valvula`, `agitador`; actuadores requieren booleanos y registros valores numéricos finitos en su rango codificable. Respuestas: 400 dato inválido, 401 token inválido, 403 origen/host incorrecto, 415 contenido no JSON. Los eventos incluyen `id`, `hora` ISO-8601 UTC−05, `tipo`, `origen`, `resultado`, `descripcion`, en orden descendente y con máximo 200 entradas.

`sesion` identifica una instancia del modelo, `generacion` cada reinicio de planta y `revision` ordena sus cambios. El frontend descarta respuestas antiguas para evitar que un polling pendiente revierta visualmente una acción del ponente, y reconoce una nueva sesión al reiniciar el proceso.

## Registros y dinámica

| Dirección | Campo | Escala | Acceso |
|---|---|---|---|
| HR[0] | temperatura | °C × 10 | L/E |
| HR[1] | presión | bar × 100 | L/E |
| HR[2] | metano | % entero | L |
| HR[3] | sustrato | % entero | L |
| COIL[0] | válvula | 1 abierta | L/E |
| COIL[1] | agitador | 1 encendido | L/E |

Funciones admitidas: FC1, FC3 (lecturas), FC5, FC6, FC15 y FC16 (escrituras). FC22 y FC23 se rechazan explícitamente, también se registran en protegido; no hay ruta alternativa de escritura. Una escritura múltiple fuera del mapa no aplica cambios parciales. HR[2–3] son de solo lectura.

Inicio: 38 °C, 1,4 bar, 62 % CH₄, 74 % sustrato, válvula cerrada, agitador ON. Paso de 250 ms, semilla 2026. Temperatura normal 35–40 °C, alarma <30 o >45; presión normal 1–1,6 bar, alarma <0,8 o >2. Fuera de lo normal y antes de alarma: advertencia. Una presión excesiva con válvula cerrada crece; abrirla reduce presión. Apagar el agitador altera gradualmente el equilibrio térmico. Son parámetros didácticos. El reinicio reproduce la trayectoria con igual secuencia de ticks y órdenes; el reloj de eventos y la revisión siguen identificando cambios.

## Desarrollo y verificación

Runtime Docker: Python 3.13.12. Para ejecución nativa de desarrollo, usa Python 3.13 o compatible:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest -q -s
.venv/Scripts/python -m app.main
```

La ejecución nativa enlaza únicamente loopback. La imagen escucha dentro de su red de contenedor y Compose publica únicamente loopback del portátil. Los scripts de control no aceptan destinos arbitrarios.

Verificación de navegador opcional, con Node y planta iniciada:

```powershell
npm install
npx playwright install chromium
npm run test:e2e
npm run test:restart
```

`PYTHON_DEMO` permite cambiar el intérprete usado por la prueba. El navegador se prueba a 1366×768 y 1920×1080; se miden 20 escrituras de los tres escenarios hasta el cambio real en DOM, rechazo, gateway y reconexión, con capturas e informe en `artifacts/`. La prueba termina dejando el modo protegido. `test:restart` inicia y termina únicamente sus propios procesos de planta en puertos locales asignados por el sistema y comprueba la recuperación tras una caída real. Las pruebas backend incluyen 30 minutos **simulados**, no equivalentes al ensayo físico de 30 minutos. Para el ensayo real ejecuta `python scripts/ensayo.py` con la planta iniciada y consulta `Verificacion.md`.

Para ejecutar la prueba visual contra Docker en vez del proceso nativo: `$env:DOCKER_DEMO='1'`. Si publicas otro puerto, añade por ejemplo `$env:PUERTO_WEB_PRUEBA='28473'` antes de `npm run test:e2e`. La consola de esa prueba ejecuta los clientes con `docker compose exec -T`.

## Antes de la ponencia

- Comprobar Docker, imagen local y puertos libres.
- Desconectar internet y completar el guion con ambas terminales.
- Revisar pantalla completa, 16:9, transmisión y legibilidad a tres metros.
- Ejecutar 30 minutos reales y diez ciclos de demostración.
- Grabar un video de respaldo y comprobar reproducción local; esta tarea queda fuera del código.

Plan y trazabilidad: [Plan de implementacion.md](<Plan de implementacion.md>). Evidencias y pendientes: [Verificacion.md](Verificacion.md).
