# PRD — Simulador de Ciberseguridad Industrial "Del código a la válvula"

> Documento de requisitos de producto. Describe **qué** debe hacer la demo y **qué problema** resuelve. No describe implementación (eso va en `Architecture.md`) ni estética (eso va en `Design.md`).

---

## 1. Resumen

Aplicación de **demostración** para una ponencia de ciberseguridad. Simula una **planta de biogás** (biodigestor) con un tablero de control en tiempo real. Su propósito es mostrar, en vivo y ante un público, por qué el software que controla procesos físicos es un objetivo de seguridad distinto al software que solo maneja datos.

La demo ilustra un principio real y de manual: los protocolos de control industrial clásicos (como Modbus) se diseñaron **sin autenticación**. La app permite ver qué pasa cuando ese canal está desprotegido y cómo cambia la situación cuando se protege.

**Es un entorno de laboratorio cerrado.** Corre entera en un solo portátil, sin internet, y nunca se conecta a equipos o plantas reales. Todos los "equipos" son simulados.

---

## 2. Problema que resuelve

El público (profesionales de una especialización en seguridad) entiende la teoría: "Modbus no tiene autenticación". Pero rara vez lo *ven*. Una diapositiva no transmite el impacto de que, sin romper nada sofisticado, un valor escrito en el canal de control haga que una válvula cambie de estado en pantalla.

La demo convierte un concepto abstracto en un momento visible:

- **Antes:** el tablero muestra la planta operando normal.
- **Durante:** desde una segunda terminal se escribe un valor en el canal de control.
- **Después:** el tablero reacciona en vivo (la válvula se abre, la temperatura se dispara, salta una alarma).
- **Lección:** acto seguido se muestra el **modo protegido**, donde ese mismo intento es rechazado.

---

## 3. Público y contexto de uso

- **Usuario principal:** el ponente, que opera la demo desde su portátil y proyecta el tablero.
- **Audiencia:** presencial + virtual (ponencia híbrida). El tablero se proyecta y se comparte por pantalla en la transmisión.
- **Entorno:** un solo portátil con Windows + Docker. Puede no haber internet confiable en el sitio. La demo **no debe depender de la red del lugar**.

---

## 4. Objetivos

| # | Objetivo | Criterio de éxito |
|---|----------|-------------------|
| O1 | Mostrar una planta simulada creíble | El tablero muestra telemetría que cambia sola (temperatura, presión, metano, válvula) de forma realista |
| O2 | Demostrar el ataque en vivo | Con un comando corto desde otra terminal, el tablero reacciona visiblemente en < 2 s |
| O3 | Demostrar la defensa | En modo protegido, el mismo intento es rechazado y el tablero lo registra |
| O4 | Funcionar sin internet | Arranca y opera 100% local, sin servicios externos |
| O5 | Ser a prueba de nervios | Arranca con **un solo comando**; estado inicial reproducible; fácil de reiniciar |

---

## 5. Funcionalidades

### 5.1 Tablero de la planta (obligatorio)
- Vista web en tiempo real del biodigestor.
- Indicadores: **temperatura (°C), presión (bar/kPa), producción de metano (% CH₄), nivel de sustrato (%), estado de la válvula de alivio (ABIERTA/CERRADA), estado del agitador (ON/OFF)**.
- Un **registro de eventos** (log) visible que muestra cambios y alarmas con hora.
- Un **banner de modo** siempre visible: `MODO: INSEGURO` o `MODO: PROTEGIDO`.
- Estados visuales claros: **normal / advertencia / alarma**.

### 5.2 Motor de simulación (obligatorio)
- La planta evoluciona sola de forma plausible (rangos operativos normales con pequeña variación).
- Si un valor crítico se sale de rango (p. ej. presión alta con válvula cerrada), entra en **estado de alarma**.
- Estado inicial **determinista** para que cada demo arranque igual.

### 5.3 Canal de control estilo industrial (obligatorio)
- La planta expone su control por un canal tipo **Modbus TCP** (un "PLC" simulado) sobre localhost.
- Mapa de registros documentado (qué registro controla qué).

### 5.4 Modo inseguro vs. modo protegido (obligatorio)
- **Inseguro:** el canal de control acepta escrituras sin ninguna verificación.
- **Protegido:** las escrituras al canal de control requieren pasar por una verificación (gateway/autenticación/segmentación simulada); un intento directo es **rechazado y registrado**.
- El modo se puede fijar al arrancar (variable de entorno o parámetro). Idealmente también se puede alternar sin reiniciar toda la demo.

### 5.5 Consola de "intento de control" (obligatorio)
- Un script corto y legible que, desde una segunda terminal, escribe un valor en el canal de control (p. ej. "abrir válvula", "forzar temperatura").
- Debe ser **entendible al proyectarlo**: pocas líneas, nombres claros.
- En inseguro: tiene efecto. En protegido: es rechazado.

### 5.6 Reinicio rápido (obligatorio)
- Un comando o botón para volver la planta al estado inicial, por si hay que repetir la demo.

---

## 6. Requisitos no funcionales

- **Local y offline:** sin llamadas a internet ni dependencias de servicios externos.
- **Plataforma:** Windows + Docker (Docker Compose). Debe levantar con `docker compose up`.
- **Arranque de un comando** y estado inicial reproducible.
- **Legibilidad en proyector:** fuentes grandes, alto contraste (ver `Design.md`).
- **Robustez de demo:** si algo falla, debe ser obvio cómo reiniciar; se acompañará de un video de respaldo grabado (fuera del alcance del código).
- **Simplicidad:** es una demo; priorizar claridad sobre completitud. Nada de autenticación de usuarios real, base de datos pesada, ni despliegue en nube.

---

## 7. Fuera de alcance (NO construir)

- Cualquier conexión a equipos, PLCs o plantas reales.
- Descubrimiento/escaneo de dispositivos en redes reales.
- Técnicas de intrusión contra sistemas de terceros.
- Autenticación de usuarios, cuentas, persistencia a largo plazo.
- Despliegue en servidores remotos o VPS.

El valor de la demo es **pedagógico y defensivo**: mostrar el riesgo en un juguete propio para explicar cómo se mitiga.

---

## 8. Entregable

Un repositorio que arranca con `docker compose up` en Windows, abre el tablero en el navegador (localhost) y permite ejecutar el script de "intento de control" desde otra terminal, en ambos modos.
