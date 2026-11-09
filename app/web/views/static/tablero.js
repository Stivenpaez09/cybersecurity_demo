"use strict";
const elemento = id => document.getElementById(id);
const campos = ["temperatura", "presion", "metano", "sustrato"];
const etiquetas = {normal: "● Normal", advertencia: "⚠︎ Advertencia", alarma: "▲ Alarma"};
const modos = {
  inseguro: {titulo: "Modo inseguro", detalle: "Acepta escrituras Modbus sin autenticar"},
  protegido: {titulo: "Modo protegido", detalle: "Solo acepta órdenes de orígenes autorizados"}
};
let ultimaRespuesta = 0, ultimaSalud = 0, revisionEventos = "", animacion = 0;
let valoresActuales = {}, generacion = null, ultimoEvento = null, finRechazo = 0;
let sesionActual = null, revisionActual = -1;
const sesionesAnteriores = new Set();
const reducirMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)");

// El nivel del sustrato y la tinta del gas siguen al valor animado, no al dato crudo.
function pintarTanque(valores) {
  const nivel = Math.max(0, Math.min(100, valores.sustrato));
  elemento("nivel-sustrato").setAttribute("transform", `translate(334 ${580 - 3 * nivel})`);
  elemento("espacio-gas").style.opacity = (0.05 + Math.max(0, Math.min(100, valores.metano)) / 100 * 0.14).toFixed(3);
}

function pintarNumeros(datos) {
  cancelAnimationFrame(animacion);
  const origen = {...valoresActuales};
  const inicio = performance.now();
  const inmediata = reducirMovimiento.matches || generacion !== datos.generacion || datos.alarmas.length > 0;
  generacion = datos.generacion;
  function paso(ahora) {
    const progreso = inmediata ? 1 : Math.min((ahora - inicio) / 280, 1);
    campos.forEach(campo => {
      const valor = (origen[campo] ?? datos[campo]) + (datos[campo] - (origen[campo] ?? datos[campo])) * progreso;
      valoresActuales[campo] = valor;
      elemento(campo).textContent = valor.toFixed(campo === "presion" ? 2 : 1);
    });
    pintarTanque(valoresActuales);
    if (progreso < 1) animacion = requestAnimationFrame(paso);
  }
  animacion = requestAnimationFrame(paso);
}

function pintarModo(datos) {
  const placa = elemento("modo");
  placa.className = `placa ${datos.modo}`;
  // El latido marca el momento exacto del ataque; el destello verde, un rechazo.
  if (datos.bajo_ataque && datos.modo === "inseguro") placa.classList.add("latido");
  else if (performance.now() < finRechazo) placa.classList.add("rechazo");
  elemento("modo-titulo").textContent = modos[datos.modo].titulo;
  elemento("modo-detalle").textContent = modos[datos.modo].detalle;
  document.querySelectorAll("[data-modo]").forEach(boton =>
    boton.setAttribute("aria-pressed", String(boton.dataset.modo === datos.modo)));
}

function claseEvento(evento) {
  if (evento.resultado === "rechazado") return "ev-ok";
  if (evento.resultado === "alarma" || (evento.origen === "modbus" && evento.resultado === "aceptado")) return "ev-alarma";
  if (evento.resultado === "advertencia") return "ev-adv";
  if (evento.resultado === "normal") return "ev-ok";
  return "ev-sis";
}
const iconos = {"ev-ok": "✓", "ev-alarma": "▲", "ev-adv": "!", "ev-sis": "◆"};

function pintarEventos(datos) {
  const clave = `${datos.generacion}:${datos.eventos[0]?.id}:${datos.eventos[0]?.hora}`;
  if (clave === revisionEventos) return;
  const primero = datos.eventos[0];
  const marcaPrimero = primero && `${datos.generacion}:${primero.id}`;
  if (primero && ultimoEvento && marcaPrimero !== ultimoEvento && primero.resultado === "rechazado") finRechazo = performance.now() + 2400;
  const fragmento = document.createDocumentFragment();
  datos.eventos.forEach(evento => {
    const fila = document.createElement("li");
    fila.dataset.evento = `${datos.generacion}:${evento.id}`;
    fila.className = claseEvento(evento);
    if (ultimoEvento && evento === primero && marcaPrimero !== ultimoEvento) fila.classList.add("evento-nuevo");
    const icono = document.createElement("span");
    icono.className = "ev-icono";
    icono.setAttribute("aria-hidden", "true");
    icono.textContent = iconos[fila.classList[0]];
    const hora = document.createElement("time");
    hora.className = "digitos";
    hora.dateTime = evento.hora;
    hora.textContent = evento.hora.slice(11, 19);
    const texto = document.createElement("span");
    texto.className = "ev-texto";
    texto.textContent = evento.descripcion;
    fila.append(icono, hora, document.createElement("span"), texto);
    fragmento.append(fila);
  });
  elemento("eventos").replaceChildren(fragmento);
  elemento("eventos").scrollTop = 0;
  revisionEventos = clave;
  ultimoEvento = marcaPrimero;
}

function mostrar(datos) {
  if (sesionesAnteriores.has(datos.sesion)) return;
  if (sesionActual !== datos.sesion) {
    if (sesionActual) sesionesAnteriores.add(sesionActual);
    if (sesionesAnteriores.size > 8) sesionesAnteriores.delete(sesionesAnteriores.values().next().value);
    sesionActual = datos.sesion;
    revisionActual = -1;
    generacion = null;
    revisionEventos = "";
    ultimoEvento = null;
  }
  // Una consulta iniciada antes de un control no puede deshacerlo visualmente.
  if (datos.revision < revisionActual) return;
  revisionActual = datos.revision;
  pintarNumeros(datos);
  document.body.dataset.generacion = datos.generacion;
  pintarModo(datos);
  [...campos, "valvula", "agitador"].forEach(campo => {
    elemento(`tarjeta-${campo}`).classList.remove("normal", "advertencia", "alarma");
    elemento(`tarjeta-${campo}`).classList.add(datos.severidades[campo]);
    elemento(`estado-${campo}`).textContent = etiquetas[datos.severidades[campo]];
    elemento(`instrumento-${campo}`)?.setAttribute("class", `instrumento ${datos.severidades[campo]}`);
  });
  elemento("valvula").textContent = datos.valvula ? "Abierta" : "Cerrada";
  elemento("agitador").textContent = datos.agitador ? "En marcha" : "Detenido";
  if (!datos.agitador) elemento("estado-agitador").textContent = "⚠︎ Sin agitación";
  if (datos.valvula_indebida) elemento("estado-valvula").textContent = "▲ Apertura directa indebida";
  document.body.classList.toggle("valvula-abierta", datos.valvula);
  document.body.classList.toggle("agitador-detenido", !datos.agitador);
  document.body.classList.toggle("alarma-global", datos.alarmas.length > 0 || datos.bajo_ataque);
  elemento("alerta-ataque").hidden = !datos.valvula_indebida;
  const resumen = elemento("resumen");
  resumen.textContent = datos.alarmas.length
    ? `▲ ${datos.alarmas.length} ${datos.alarmas.length === 1 ? "alarma activa" : "alarmas activas"}` : "● Sin alarmas";
  resumen.className = datos.alarmas.length ? "con-alarmas" : "sin-alarmas";
  elemento("revision").textContent = `PLC local · ciclo ${datos.ticks}`;
  pintarEventos(datos);
}

async function consultar() {
  try {
    const respuesta = await fetch("/api/estado", {signal: AbortSignal.timeout(1600), cache: "no-store"});
    if (!respuesta.ok) throw new Error("Telemetría no disponible");
    mostrar(await respuesta.json());
    ultimaRespuesta = performance.now();
    if (performance.now() - ultimaSalud > 3000) {
      const salud = await fetch("/api/salud", {signal: AbortSignal.timeout(1200), cache: "no-store"});
      ultimaSalud = performance.now();
      if (!salud.ok) {
        const componentes = await salud.json();
        elemento("aviso").textContent = `⚠ COMPONENTE DETENIDO: ${Object.keys(componentes).filter(clave => !componentes[clave]).join(", ")} · Reinicie planta`;
        elemento("aviso").hidden = false;
        elemento("conexion").textContent = "⚠ Servicio degradado";
      } else {
        elemento("aviso").hidden = true;
        elemento("conexion").textContent = "● Conexión local activa";
      }
    }
  } catch (_) {
    // El vigilante marca la desconexión incluso si una petición queda pendiente.
  } finally { setTimeout(consultar, 500); }
}

setInterval(() => {
  const atrasado = !ultimaRespuesta || performance.now() - ultimaRespuesta > 2000;
  document.body.classList.toggle("desconectado", atrasado);
  if (atrasado) {
    elemento("aviso").hidden = false;
    elemento("aviso").textContent = "⚠ DATOS DESACTUALIZADOS · Revise la planta o ejecute docker compose restart planta";
    elemento("conexion").textContent = "○ Sin telemetría";
    ultimaSalud = 0;
  }
}, 200);

const pintarReloj = () => elemento("reloj").textContent = new Date().toTimeString().slice(0, 8);
pintarReloj();
setInterval(pintarReloj, 1000);

async function controlar(ruta, datos) {
  const botones = document.querySelectorAll("button");
  botones.forEach(boton => boton.disabled = true);
  try {
    const respuesta = await fetch(ruta, {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(datos), signal: AbortSignal.timeout(2000)});
    const resultado = await respuesta.json();
    if (!respuesta.ok) throw new Error(resultado.error);
    mostrar(resultado);
    elemento("resultado-control").textContent = "✓ Operación aplicada";
  } catch (error) { elemento("resultado-control").textContent = `⚠ ${error.message}`; }
  finally { botones.forEach(boton => boton.disabled = false); }
}
document.querySelectorAll("[data-modo]").forEach(boton => boton.addEventListener("click", () => controlar("/api/modo", {modo: boton.dataset.modo})));
elemento("reiniciar")?.addEventListener("click", () => controlar("/api/reiniciar", {}));
consultar();
