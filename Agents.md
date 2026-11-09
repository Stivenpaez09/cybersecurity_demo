# Agents.md — Reglas del proyecto

> Guía para la IA al trabajar en este repositorio. **Léelo completo antes de escribir o modificar código.**

---

## 0. Qué es este proyecto

Demo **educativa y de laboratorio** para una ponencia de ciberseguridad: un simulador local de planta de biogás que muestra por qué el control industrial sin autenticación es riesgoso, con un **modo inseguro** y un **modo protegido**. Corre entera en un portátil (Windows + Docker), **offline** y **nunca contra sistemas reales**.

---

## 1. Archivos que SIEMPRE debes leer primero

Antes de cualquier tarea de código, lee y respeta estos tres documentos. Son la fuente de verdad:

1. **`Product Requirements Document.md`** — qué debe hacer y qué NO (alcance).
2. **`Design.md`** — identidad visual (paleta, tipografía, layout, estados).
3. **`Architecture.md`** — estructura, componentes, patrón MVC, mapa de registros.

Si algo que vas a hacer contradice uno de estos documentos, **detente y pregunta**.

---

## 2. Reglas de oro

1. **Respeta la arquitectura.** Monolito con MVC, con la separación **model / control / web** descrita en `Architecture.md`. No metas lógica de negocio en las vistas. No mezcles Modbus ni simulación dentro de los controladores web. No introduzcas microservicios ni capas nuevas.
2. **Pregunta, no asumas.** Ante cualquier duda, ambigüedad o decisión no cubierta por los documentos (nombre de un registro, un puerto, una librería, un cambio de estructura, usar Django en vez de Flask, etc.), **pregunta al autor antes de implementar**. Es preferible una pregunta de más que una suposición.
3. **No cambies el alcance por tu cuenta.** Nada de funcionalidades "extra" que nadie pidió. Si crees que algo falta, propónlo y espera confirmación.
4. **Mantén la estética definida.** No uses el azul SaaS genérico. Respeta la paleta industrial de `Design.md`. No cambies colores, fuentes ni layout sin consultar.
5. **Offline siempre.** Nada de CDNs, APIs externas, telemetría ni dependencias de red en tiempo de ejecución. Fuentes y assets empaquetados localmente.
6. **Ámbito ético/técnico fijo.** Esto es un sandbox cerrado. No agregues capacidades para descubrir, escanear o conectarse a dispositivos/redes reales. El "intento de control" solo apunta a la planta simulada en localhost.

---

## 3. Stack fijo (no cambiar sin consultar)

- **Lenguaje:** Python.
- **Web:** Flask, con estructura MVC (controllers / views).
- **Canal industrial:** Modbus TCP vía `pymodbus`.
- **Contenedores:** Docker + Docker Compose. Objetivo: `docker compose up` en Windows.
- **Estado:** en memoria, thread-safe (sin base de datos).

Si una tarea parece requerir algo fuera de este stack, **pregunta primero**.

---

## 4. Convenciones de código

- Nombres de variables, funciones y comentarios **en español** (el autor y el código del proyecto están en español).
- Código **claro y legible** por encima de "listo/ingenioso": partes de esto se proyectan ante un público.
- El `cliente_control.py` debe ser **corto y entendible a simple vista** (pocas líneas, nombres explícitos) porque se muestra en pantalla.
- Funciones pequeñas, responsabilidades separadas según la capa MVC.
- Comenta el **porqué**, no el qué obvio.
- No agregues dependencias nuevas a `requirements.txt` sin consultar.

---

## 5. Cómo se corre (objetivo)

- `docker compose up` levanta el servicio `planta` (web + Modbus + simulación).
- El tablero queda en `http://localhost:8080` (o el puerto definido en `config.py`).
- El "intento de control" se ejecuta desde otra terminal (script o `docker compose run atacante`), según lo definido en `Architecture.md`.
- El **modo** (inseguro/protegido) se fija por variable de entorno y, si es posible, se alterna en caliente.
- Debe existir una forma de **reiniciar la planta** al estado inicial.

---

## 6. Qué NO hacer

- ❌ Cambiar la arquitectura, el stack o la estructura de carpetas sin preguntar.
- ❌ Asumir decisiones ambiguas en lugar de consultarlas.
- ❌ Usar el azul genérico o salirte de la paleta de `Design.md`.
- ❌ Añadir dependencias de red/externas o romper el modo offline.
- ❌ Añadir cualquier capacidad que toque sistemas reales.
- ❌ Meter lógica de simulación o Modbus dentro de las vistas web.
- ❌ Ampliar el alcance con funciones no pedidas.

---

## 7. Flujo de trabajo esperado

1. Lee los tres documentos base.
2. Si la tarea está clara y encaja con ellos → impleméntala respetando MVC.
3. Si hay cualquier duda → **pregunta antes de codificar**.
4. Al terminar un cambio, explica brevemente qué tocaste y por qué, y confirma que no contradice los documentos.
