# Plan de implementación por fases — Del código a la válvula

## 1. Objetivo y decisiones aprobadas

Implementar íntegramente el PRD mediante una demo de planta de biogás, ejecutable en Windows con Docker Compose, operativa sin internet y preparada para una ponencia presencial y virtual.

Fuentes: `Product Requirements Document.md`, `Architecture.md`, `Design.md` y `Agents.md`. Este documento conserva las decisiones aprobadas por el autor; `Verificacion.md` distingue implementación, evidencia ejecutada y validaciones pendientes.

- Backend Python y Flask, monolito MVC con separación model / control / web.
- Frontend con plantillas HTML, CSS y JavaScript local, sin framework adicional.
- Modbus TCP mediante pymodbus; estado único en memoria protegido por un lock.
- Sin base de datos, cuentas, persistencia duradera, servicios externos ni despliegue remoto.
- Código, comentarios y mensajes de demostración en español.
- Vista del ponente separada del tablero proyectado, cambio de modo en caliente y reinicio sin reconstrucción.
- Gateway HTTP con token de demostración para mostrar control autorizado.
- Consola de segunda terminal mediante Docker, script breve visible y mensajes reales del protocolo.
- La protección representa una política del simulador, no autenticación nativa de Modbus ni seguridad industrial de producción.

## 2. Arquitectura, conexiones e interfaces

Un servicio Compose `planta`, proyecto `codigo-valvula-demo`, sin nombres globales de contenedor, privilegios, red del host ni volúmenes persistentes. Red bridge propia; publicación explícita en loopback. La operación offline depende de recursos locales, sin llamadas externas; se evita internal porque el motor utilizado omite las publicaciones de puertos de esas redes.

| Componente | Dirección predeterminada | Función |
|---|---|---|
| Tablero | http://localhost:18473/ | Audiencia |
| Ponente | http://localhost:18473/ponente | Reinicio y modo |
| API y gateway | http://localhost:18473/api/… | Telemetría y control |
| Modbus TCP | 127.0.0.1:18524 | PLC simulado |
| Cliente dentro del contenedor | 127.0.0.1:18524 | Proceso independiente |

Publicaciones `127.0.0.1:18473:18473` y `127.0.0.1:18524:18524`. Variables `PUERTO_WEB_HOST` y `PUERTO_MODBUS_HOST` modifican los puertos externos; internos constantes. Valores predeterminados permiten arrancar sin `.env`. El comprobador PowerShell verifica Docker/Compose y puertos sin detener aplicaciones. La disponibilidad debe comprobarse en cada portátil.

Flujo: simulación y Modbus → política y modelo → snapshot JSON → polling del navegador. Gateway, web y PLC comparten estado y política.

| Método / ruta | Contrato |
|---|---|
| GET `/` | Tablero de audiencia |
| GET `/ponente` | Controles locales |
| GET `/api/estado` | Seis indicadores, modo, revisión, severidades, alarmas, eventos |
| POST `/api/reiniciar` | `{}`; restaura estado y semilla conservando modo |
| POST `/api/modo` | `{"modo":"inseguro"}` o `protegido`; cambio atómico |
| POST `/api/control` | `{"campo":"valvula","valor":true}`; requiere Bearer token |
| GET `/api/salud` | Disponibilidad de web, simulación y Modbus |

Unidades: °C, bar, porcentajes, booleanos de actuadores. Eventos: identificador, hora, tipo, origen, resultado y descripción. Gateway admite temperatura, presión, válvula y agitador. Token configurable local de demostración, transmitido en Authorization, nunca en URL ni eventos. Operaciones modificadoras con JSON, origen local previsto y sin CORS abierto. Sin cuentas de usuario.

| Dirección base cero, dispositivo 1 | Campo | Escala | Acceso |
|---|---|---|---|
| HR[0] | temperatura | °C ×10 | L/E |
| HR[1] | presión | bar ×100 | L/E |
| HR[2] | metano | % entero | L |
| HR[3] | sustrato | % entero | L |
| COIL[0] | válvula | 1 abierta | L/E |
| COIL[1] | agitador | 1 encendido | L/E |

Inseguro: sin autorización de escrituras, conservando validación del protocolo, direcciones y tipos. Protegido: escrituras Modbus directas rechazadas antes de mutar, con error y evento; lecturas disponibles y gateway con token como camino autorizado.

## 3. Fases de implementación

### Fase 0 — Trazabilidad y contratos

- Matriz de cada requisito, fase, entregable y prueba.
- Documentación de puertos, gateway, consola y vista del ponente.
- Contratos HTTP/JSON, mapa Modbus y semántica de modos definidos.
- Versiones fijadas de Python, Flask y pymodbus; comprobación del mecanismo real de rechazo de escrituras.
- pytest para pruebas y Waitress en un proceso con varios hilos; estructura MVC existente.

Aceptación: todos los requisitos asignados, sin decisiones abiertas sobre conexiones, estado o autorización.

### Fase 1 — Base del proyecto y Docker

- Estructura MVC, configuración central, dependencias fijadas, Dockerfile, Compose y `.dockerignore`.
- Exclusión de entorno virtual, cachés y archivos innecesarios del contexto de construcción.
- Proceso único con servidor web, simulación y Modbus; sin debugger, recargador o motores duplicados.
- Solo dos puertos locales publicados, healthcheck, logs, cierre ordenado y comprobación PowerShell.

Aceptación: `docker compose up` inicia el servicio y muestra direcciones; conflictos de puertos diagnosticables y configurables sin afectar otras apps.

### Fase 2 — Modelo y simulación determinista

- Estado único y snapshots atómicos: seis indicadores, modo, severidades, alarmas y últimos 200 eventos.
- Inicio: 38 °C, 1,4 bar, 62 % CH₄, 74 % sustrato, válvula cerrada, agitador ON.
- Paso 250 ms, semilla fija, variación pequeña y retorno gradual al equilibrio.
- Válvula abierta reduce presión; agitador influye en estabilidad; presión alta con válvula cerrada empeora.
- Temperatura normal 35–40 °C; alarma <30 o >45. Presión normal 1–1,6 bar; alarma <0,8 o >2. Umbrales configurables y advertencias intermedias.
- Metano y sustrato acotados a 0–100 % y variación lenta.
- Efectos visibles de escritura conservados; registro de transiciones sin inundar el log.
- Reinicio atómico de valores, semilla, contadores y eventos.

Aceptación: operación normal plausible, anomalías consistentes y trayectoria reproducible con iguales entradas/ticks.

### Fase 3 — Modbus y demostración insegura

- Lecturas/escrituras holdings y coils sobre el modelo; soporte simple y múltiple.
- Validación completa de escritura múltiple antes de mutar; HR[2–3] solo lectura.
- Cliente breve, claro, restringido al simulador local; escenarios abrir-valvula, temperatura-alta y presion-alta.
- Terminal muestra destino, registro, valor y resultado sin exploración de redes ni destinos arbitrarios.

Comando: `docker compose exec planta python cliente_control.py abrir-valvula`.

Aceptación: escritura válida afecta modelo y eventos; script proyectable sin instalar Python en Windows.

### Fase 4 — Política protegida y gateway autorizado

- Autorización y aplicación centralizadas en control; rutas sin negocio.
- Modo inicial configurable, inseguro predeterminado, cambio atómico y registrado.
- Rechazo de todas las peticiones Modbus de escritura soportadas en protegido, error explícito y evento sin cambios de estado.
- Gateway con token, validación y errores HTTP claros; cliente autorizado separado sin imprimir token.
- Eventos distinguen origen directo y autorizado.

Aceptación: mismo comando aceptado en inseguro y rechazado en protegido; token inválido sin efecto, válido con efecto visible.

### Fase 5 — API y frontend industrial

- Tablero y vista del ponente con plantillas Flask; polling cada 500 ms sin superposición y recuperación automática.
- Aviso de datos desactualizados tras dos segundos sin respuesta y diagnóstico de componentes caídos.
- Cuatro medidores con unidades, válvula y agitador, banner permanente y estados textuales e iconográficos.
- Paleta grafito/ámbar, fuentes empaquetadas, números ≥32 px, distribución 16:9 y contraste alto.
- Señal pulsante de escritura directa, apertura indebida identificada y rechazo verde en registro.
- Apertura autorizada diferenciada; eventos con hora, recientes arriba y scroll interno.
- Transiciones suaves sin retrasar estados críticos; reducción de movimiento respetada.
- Reinicio y selección de modo solo en `/ponente`, sincronizados con audiencia.

Aceptación: respuesta visible <2 s, indicadores legibles y audiencia sin controles operativos.

### Fase 6 — Integración, resiliencia y pruebas

- Pruebas de modelo, límites, escalas, políticas, HTTP y concurrencia.
- Todas las funciones de escritura soportadas respetan protección; funciones alternativas no abren bypass.
- Cambio de modo durante escrituras, reinicio con polling y múltiples navegadores.
- Reconexión tras caída/reinicio; salud falla si se detiene simulación o Modbus, con diagnóstico.
- Al menos 20 mediciones hasta representación visible, diez ciclos y ensayo real de 30 minutos.
- Revisiones a 1920×1080 y 1366×768, pantalla completa y proyección a unos tres metros.
- Verificación de ausencia de solicitudes externas y dependencias de internet en ejecución.

Aceptación: sin escrituras protegidas aplicadas, estados inconsistentes ni motores duplicados; ensayos <2 s y recuperación documentada.

### Fase 7 — Paquete offline y ponencia

- Construcción y prueba de imagen antes del evento; exportación/importación con docker save/load.
- Reutilización de imágenes locales sin descargas durante arranque de ponencia.
- Dependencias, fuentes, CSS, JS y recursos en imagen.
- Documentación de preparación, arranque, puertos alternativos, comandos y recuperación.
- Guion: normal → intento → efecto → reinicio → protegido → mismo intento rechazado → control autorizado.
- Checklist de Docker, imágenes, puertos, pantalla completa y terminal.
- Grabación y prueba del video local como tarea operativa fuera del código.
- README y arquitectura actualizados.

Aceptación: guion completo sin internet usando imágenes preparadas y `docker compose up`.

## 4. Matriz de cobertura del PRD

| Requisito | Fases | Entregable / prueba |
|---|---|---|
| §1–3: demo pedagógica, biogás, portátil y audiencia híbrida | 0,5,7 | Tablero y guion; ensayo proyectado |
| O1: planta creíble y autónoma | 2,5,6 | Motor y ensayo sostenido |
| O2: efecto visible <2 s | 3,5,6 | Cliente y 20 mediciones DOM |
| O3: rechazo registrado | 4–6 | Política y prueba mismo comando |
| O4: sin internet | 1,5,7 | Recursos locales; ensayo desconectado |
| O5: un comando, determinismo, reinicio | 1,2,5,7 | Compose y ciclos |
| §5.1: tablero web en vivo | 5 | Polling sin recargas |
| §5.1: temperatura, presión, metano, sustrato | 2,5 | Modelo y medidores con unidades |
| §5.1: válvula y agitador | 2,3,5 | Estados y pruebas de actuadores |
| §5.1: eventos con hora | 2–5 | Registro visible de cambios y alarmas |
| §5.1: banner permanente | 4,5 | Vista ambos modos |
| §5.1: normal, advertencia, alarma | 2,5,6 | Umbrales y representación accesible |
| §5.2: dinámica y alarmas | 2,6 | Pruebas normales y anomalías |
| §5.2: inicio determinista | 2,6 | Igualdad tras reinicio |
| §5.3: Modbus TCP local | 1,3 | Cliente/servidor real |
| §5.3: mapa documentado | 0,3,7 | Tabla y pruebas de escalas |
| §5.4: inseguro sin autorización | 3,6 | Escrituras aceptadas |
| §5.4: verificación, rechazo, registro | 4,6 | Rechazo y gateway |
| §5.4: modo inicial y en caliente | 1,4,5 | Env y vista ponente |
| §5.5: script corto y segunda terminal | 3,7 | cliente_control.py y guion |
| §5.5: mismo intento, dos resultados | 4,6,7 | Comparación inseguro/protegido |
| §5.6: reinicio rápido | 2,5,6 | Botón y endpoint |
| §6: Windows y Compose | 1,6,7 | Configuración y ensayo destino |
| §6: local sin servicios externos | 1,5,7 | Imagen y recursos autosuficientes |
| §6: proyector y fuentes grandes | 5,6 | Capturas y revisión a tres metros |
| §6: recuperación y video | 6,7 | Guía, checklist y video externo |
| §6: simplicidad, sin cuentas/BD pesada | 0–7 | Monolito en memoria |
| §7: sin equipos reales, escaneo ni terceros | 0,1,3,6 | Destinos fijos y loopback |
| §7: sin cuentas, persistencia o nube | 0–7 | Revisión de alcance |
| §8: repositorio, un comando, ambos modos | 6,7 | Ensayo final offline |

## 5. Supuestos y finalización

- Docker y las imágenes pueden requerir internet durante preparación, nunca durante la ponencia.
- Rangos y dinámica son pedagógicos; no son parámetros de una planta real.
- Arranque inseguro para guion; reinicio de planta conserva modo activo.
- El contenedor informa URLs; el navegador se abre manualmente.
- Terminal técnica con respuestas reales y alcance fijo al simulador.
- El código del video queda fuera de alcance; la proyección y grabación son tareas del ponente.
- Solo se declara verificación completa cuando cada fila tenga evidencia y el guion offline pase en el portátil objetivo. Las validaciones no ejecutadas permanecen explícitas en `Verificacion.md`.
