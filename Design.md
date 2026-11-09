# Design.md — Identidad visual de la demo

> Toda la parte visual del proyecto: paleta, tipografía, layout y estados. El objetivo es que se vea como un **panel de control industrial (SCADA/HMI)** real: serio, de alto contraste, intuitivo al instante. **Nada de la estética SaaS azul genérica.**

---

## 1. Principio de diseño

Un operador debe entender el estado de la planta en **menos de 2 segundos** y desde lejos (está proyectado). Prioridades, en orden: **claridad > legibilidad en proyector > carácter industrial > detalle estético**.

Referencia mental: tablero de una sala de control, HMI de un PLC, instrumentación de planta. Superficies oscuras tipo metal, acentos de color de seguridad (ámbar, naranja de peligro, verde de "en marcha"), datos en fuente monoespaciada como un instrumento digital.

---

## 2. Paleta de color

**Prohibido el azul de siempre.** La identidad es tierra/metal + colores de seguridad industrial.

### Base (superficies) — grafito cálido + óxido
| Rol | Color | Hex |
|-----|-------|-----|
| Fondo principal | Grafito cálido | `#15120F` |
| Lienzo del sinóptico | Grafito con retícula de puntos `#2A231C` | `#181410` |
| Paneles (registro, ponente) | Grafito tostado | `#1C1814` |
| Botones / placa neutra | Marrón metal | `#2A241E` |
| Tuberías / paredes | Óxido y cobre | `#3B2A1F` · `#8C4A2B` · `#6B4A34` |
| Texto principal | Hueso cálido | `#EDE6DA` |
| Texto secundario | Arena | `#A39888` |

### Acentos (seguridad industrial)
| Rol | Color | Hex | Uso |
|-----|-------|-----|-----|
| Primario / marca | **Ámbar de seguridad** | `#F2A900` | Encabezados, acento principal, foco |
| Normal / OK | **Verde musgo industrial** | `#6A994E` | Estado operativo normal, válvula correcta |
| Advertencia | **Mostaza/ocre** | `#C9821A` | Valores acercándose a límite |
| Alarma / peligro | **Naranja-rojo de peligro** | `#D64500` | Alarmas, estado bajo ataque, rechazo |
| Acento frío puntual | **Cian apagado** | `#2E8B8B` | Solo para datos neutros (metano/gas), con moderación |

> El cian apagado es el **único** azulado permitido y solo como dato secundario. El protagonismo es del ámbar y del grafito.

### Semántica de modo
- **MODO INSEGURO:** banner con borde/acento **naranja-rojo `#D64500`** (señal de riesgo).
- **MODO PROTEGIDO:** banner con acento **verde musgo `#6A994E`**.

---

## 3. Tipografía

- **Datos e instrumentos:** **DSEG7 Classic Bold** (display de 7 segmentos), con los segmentos apagados ("88.8") dibujados detrás de cada cifra a muy baja opacidad, como un instrumento real.
- **Títulos, etiquetas y registro:** **Big Shoulders** (sans condensada inspirada en señalética industrial), en mayúsculas y minúsculas normales; nada de rótulos diminutos en MAYÚSCULAS encima de cada título.
- **Tamaños pensados para proyector:** valores numéricos grandes (mínimo ~32px en los medidores principales); las lecturas escalan con el diagrama.
- Ambas fuentes tienen licencia OFL y están en `app/web/views/static/fonts/`.
- Usar fuentes **empaquetadas localmente** (no Google Fonts por CDN): la demo es offline.

---

## 4. Layout del tablero

```
┌──────────────────────────────────────────────────────────────────┐
│ Biodigestor 01  planta simulada        16:42:18  ▞▞ MODO INSEGURO │ ← cabecera
│                                                                    │
│  AT-103 62.0 %CH₄   PT-102 1.40 bar                │ Registro      │
│ ←═════════╗            ╔══════▷◁══════╗ atmósfera  │ 16:42:18 ▲ …  │
│           ╭─────(M)──────╮  XV-201 Cerrada         │ 16:42:01 ● …  │
│  38.0 °C ─│ ~ ~ ~ ~ ~ ~ ~│                         │               │
│  TT-101   │ sustrato ▓▓▓ │─ LT-104 74.0 %          │               │
│ ══════════╰──────┼───────╯                         │               │
│            M-202 · Agitador En marcha              │ simulados ·…  │
└──────────────────────────────────────────────────────────────────┘
```

- **Cabecera:** nombre de la planta a la izquierda; reloj, estado de conexión y **placa de modo** a la derecha (chapa con esquina cortada, franjas de peligro y candado abierto en inseguro; verde con candado cerrado en protegido).
- **Sinóptico (~70 %):** la planta dibujada como diagrama de proceso en SVG. Solo los equipos que existen en el modelo: biodigestor, XV-201 (símbolo de pajarita con actuador), M-202 (motor y aspas) y los cuatro instrumentos como burbujas ISA unidas al equipo, cada uno con su lectura al lado.
- **Registro de eventos:** columna derecha, con hora en 7 segmentos, icono por tipo y lo nuevo arriba.
- **Sin tarjetas repetidas ni líneas decorativas bajo los títulos.**
- **Animación ambiental sutil:** burbujas en el sustrato, flujo en las tuberías, agitador girando.

---

## 5. Estados visuales

Cada indicador tiene tres estados, **nunca comunicados solo por color** (añadir icono/texto por accesibilidad y daltonismo):

| Estado | Color | Señal extra |
|--------|-------|-------------|
| Normal | Verde musgo `#6A994E` | Texto "NORMAL", sin parpadeo |
| Advertencia | Ocre `#C9821A` | Icono ⚠, texto "ALTA/BAJA" |
| Alarma | Naranja-rojo `#D64500` | Icono, **parpadeo lento**, texto "ALARMA" |

- **Válvula abierta de forma indebida:** borde rojo + parpadeo + evento en el log.
- **Bajo ataque (modo inseguro):** viñeta naranja-roja pulsante en los bordes de la pantalla, placa de modo latiendo, franja de alerta bajo la cabecera, válvula parpadeando y gas saliendo animado por la línea de alivio.
- **Intento rechazado (modo protegido):** un *toast*/línea verde en el log: "Escritura rechazada: origen no autorizado".

---

## 6. Interacción y refresco

- El tablero se **actualiza solo** (polling cada ~1 s o websocket). El público no debe ver recargas bruscas.
- Transiciones suaves en los números (que "suban/bajen", no que salten).
- Un botón discreto de **REINICIAR PLANTA** (solo visible para el ponente).
- Diseño pensado para **16:9 de proyector**; debe verse bien a pantalla completa.

---

## 7. Accesibilidad / proyección

- Contraste alto (texto claro sobre grafito, cumple holgado).
- No depender solo del color: iconos + texto en cada estado.
- Fuentes grandes; evitar gris sobre gris para datos importantes.
- Probarlo a pantalla completa y mirándolo desde ~3 m antes de la ponencia.
