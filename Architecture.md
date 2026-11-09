# Architecture.md — Arquitectura de la demo

> Define cómo está construido el sistema y cómo encajan sus partes. **Arquitectura elegida: monolito con patrón MVC.** Es una demo; se busca lo más simple que cumpla el PRD, no un sistema de producción. Cualquier cambio arquitectónico debe consultarse antes (ver `Claude.md`).

---

## 1. Visión general

Un único proceso/servicio (monolito) que corre dentro de Docker y contiene tres piezas que comparten un mismo **estado de la planta** en memoria:

```
                        ┌──────────────────────────────────────┐
                        │        CONTENEDOR "planta"            │
                        │                                        │
  Navegador  ◀── HTTP ──┤  [Web MVC: Flask]                      │
  (tablero)             │      ├─ Controllers (rutas)            │
                        │      ├─ Views (plantillas/JSON)        │
                        │      └─ lee ──┐                        │
                        │               ▼                        │
                        │        [Model: EstadoPlanta]           │
                        │          (en memoria, thread-safe)     │
                        │               ▲                        │
                        │      ┌────────┴─────────┐              │
                        │  [Motor de simulación]  [Servidor      │
                        │   (hilo, actualiza       Modbus TCP]   │
                        │    el estado)            (el "PLC")    │
                        └───────────────────────────┬────────────┘
                                                     │ Modbus TCP (localhost)
                                                     ▼
                        [Script "intento de control"] ◀── segunda terminal
```

El **script de intento de control** es un programa aparte (no parte del monolito): un cliente Modbus corto que el ponente ejecuta desde otra terminal.

---

## 2. Componentes

### 2.1 Model — `EstadoPlanta`
- Clase que guarda el estado actual: temperatura, presión, % CH₄, sustrato, válvula, agitador, modo, alarmas.
- **Única fuente de verdad.** Todos leen y escriben aquí.
- Debe ser **thread-safe** (lock), porque la tocan dos hilos (simulación y servidor Modbus) y la lee la web.
- Expone un **mapa de registros** que relaciona cada registro Modbus con un campo del estado (documentado en §5).

### 2.2 Motor de simulación
- Hilo en segundo plano que cada X ms actualiza `EstadoPlanta` con dinámica plausible (variación normal + reglas: si presión sube y válvula cerrada → sube más → alarma).
- Define los **rangos normales** y cuándo se dispara una alarma.
- Arranca siempre desde un **estado inicial determinista**.

### 2.3 Servidor Modbus TCP (el "PLC")
- Expone el control de la planta como un servidor Modbus TCP en localhost (usar `pymodbus`).
- Su banco de registros está **sincronizado** con `EstadoPlanta`: escribir un registro cambia el estado; el estado se refleja en los registros.
- **Aquí vive la diferencia entre modos:**
  - **Inseguro:** acepta cualquier escritura entrante y la aplica.
  - **Protegido:** las escrituras pasan por una verificación (p. ej. token/origen permitido simulado, o el canal queda aislado y solo un "gateway" interno puede escribir). Un intento directo se **rechaza** y se registra en el log.

### 2.4 Web MVC (Flask)
- **Controllers:** rutas HTTP (`/` tablero, `/api/estado` para el polling, `/api/reiniciar`, `/api/modo`).
- **Views:** plantilla del tablero + respuestas JSON para el refresco.
- **No contiene lógica de negocio:** solo lee del Model y presenta. Nada de simulación ni de Modbus dentro de las vistas.

### 2.5 Script "intento de control" (cliente, separado)
- Programa corto e independiente (`cliente_control.py` o servicio `atacante` en compose).
- Abre un cliente Modbus a la planta y escribe uno o dos registros (p. ej. válvula=abierta, temperatura=valor alto).
- Pensado para **leerse en pantalla**: pocas líneas, variables con nombres claros.

---

## 3. Estructura de carpetas (propuesta)

```
/app
  /model
    estado_planta.py        # EstadoPlanta + mapa de registros
    simulacion.py           # motor de simulación (hilo)
  /control
    servidor_modbus.py      # servidor Modbus TCP + lógica de modo
    politica.py             # verificación inseguro/protegido
  /web
    /controllers
      rutas.py              # endpoints Flask
    /views
      /templates
        tablero.html
      /static               # css, fuentes locales, js de polling
  config.py                 # modo por defecto, puertos, rangos
  main.py                   # arranca hilos (sim + modbus) y la web
cliente_control.py          # script de "intento de control"
docker-compose.yml
Dockerfile
requirements.txt
README.md
```

> Si Claude Code propone una estructura distinta, debe **preguntar antes** (ver `Claude.md`). La separación model / control / web es obligatoria.

---

## 4. Concurrencia

Dentro del monolito corren a la vez:
1. El **hilo de simulación** (actualiza el estado).
2. El **servidor Modbus** (atiende escrituras/lecturas).
3. El **servidor web** (atiende al navegador).

Todos acceden a `EstadoPlanta`, así que **todo acceso al estado va protegido por un lock**. Mantenerlo simple: un solo lock para el estado es suficiente para una demo.

---

## 5. Mapa de registros Modbus (documentar y mantener)

Ejemplo (ajustar al implementar, pero dejarlo documentado aquí y en código):

| Registro | Tipo | Campo | Notas |
|----------|------|-------|-------|
| HR[0] | holding | temperatura (×10) | lectura/escritura |
| HR[1] | holding | presión (×100) | lectura/escritura |
| HR[2] | holding | % CH₄ | lectura |
| HR[3] | holding | sustrato % | lectura |
| COIL[0] | coil | válvula alivio (0/1) | 1 = abierta |
| COIL[1] | coil | agitador (0/1) | |

El "intento de control" escribe, por ejemplo, `COIL[0]=1` (abrir válvula) o `HR[0]` a un valor alto.

---

## 6. Docker

- `docker-compose.yml` con el servicio **`planta`** (monolito: web + modbus + simulación), proyecto `codigo-valvula-demo`, puertos web `18473` y Modbus `18524` publicados únicamente en `127.0.0.1`. Variables `PUERTO_WEB_HOST` y `PUERTO_MODBUS_HOST` cambian puertos externos.
- El intento se ejecuta como proceso independiente dentro del mismo contenedor: `docker compose exec planta python cliente_control.py abrir-valvula`. Destino fijo `127.0.0.1:18524`; no requiere Python en el host.
- Sin volúmenes de datos ni dependencias externas. Todo offline.
- El **modo** (inseguro/protegido) se fija por variable de entorno en el compose y, si se puede, se alterna en caliente por `/api/modo`.

---

## 7. Decisiones y límites (trade-offs)

- **Monolito MVC**, no microservicios: es una demo; un proceso es más fácil de arrancar y explicar.
- **Estado en memoria**, no base de datos: no hace falta persistencia; se reinicia limpio.
- **Flask**, no DRF/Django: el ponente usa DRF a diario, pero aquí se prioriza un monolito mínimo con vistas MVC; menos peso para una demo. (Si el ponente prefiere Django por comodidad, **consultar** antes de cambiar.)
- **Seguridad "protegida" simulada:** el modo protegido ilustra el concepto (verificación de origen/segmentación). No pretende ser una implementación de seguridad industrial de producción.

## 8. Decisiones aprobadas e implementación

- Python 3.13.12 en Docker; Flask 3.1.3, pymodbus 3.8.6, Waitress 3.0.2. Dependencias fijadas en requirements. Un proceso, cuatro hilos web y los componentes de simulación/Modbus, sin reloader.
- `GET /ponente` contiene reinicio y cambio de modo; `/` solo audiencia. Frontend sin framework, fuentes abiertas empaquetadas, polling secuencial cada 500 ms.
- `POST /api/control` es un gateway HTTP en la capa control (no otro servicio). Bearer token local configurable; cliente `cliente_autorizado.py`. JSON y contratos detallados en README.
- En protegido, las PDU de escritura se rechazan con excepción Modbus ILLEGAL_FUNCTION antes de tocar el estado. Se mantiene el mismo RLock durante autorización y ejecución. FC5/6/15/16 soportadas; FC22/23 explícitamente denegadas, sin ruta alternativa. FC1/3 permiten lectura en ambos modos. Direcciones base cero, dispositivo 1.
- El datastore adapta directamente el modelo: no existen copias independientes del banco de registros. La validación múltiple precede la escritura completa.
- Inicio determinista y motor cada 250 ms; reset conserva modo, restaura semilla/valores/eventos y aumenta generación. El reloj de eventos no es parte de la trayectoria determinista.
- La API incluye sesión de proceso y revisión monotónica: el frontend descarta respuestas antiguas y reconoce reinicios del proceso, evitando regresiones visuales entre polling y controles del ponente.
- Salud comprueba hilos y progreso del motor; Modbus mantiene indicador de listener activo. Fallos se muestran en frontend y healthcheck.
- Red bridge propia del proyecto y puertos publicados solo en loopback; imagen sin privilegios y filesystem de solo lectura, sin volúmenes. No se usa red internal porque este motor omite sus publicaciones de puertos. Preparación online y operación offline con imagen previamente construida/importada; ninguna dependencia de red durante ejecución.
- Este documento conserva MVC model/control/web. Plan aprobado: `Plan de implementacion.md`; ejecución de pruebas y pendientes: `Verificacion.md`.
