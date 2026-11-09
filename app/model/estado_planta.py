"""Estado único; toda operación pública obtiene el mismo lock reentrante."""
from collections import deque
from datetime import datetime, timezone, timedelta
import random
import threading
import time
import uuid

from app.config import UMBRALES

INICIAL = dict(temperatura=38.0, presion=1.4, metano=62.0, sustrato=74.0,
               valvula=False, agitador=True)
REGISTROS = ("temperatura", "presion", "metano", "sustrato")
BOBINAS = ("valvula", "agitador")


class EstadoPlanta:
    def __init__(self, modo="inseguro"):
        if modo not in ("inseguro", "protegido"):
            raise ValueError("MODO debe ser inseguro o protegido")
        self.lock = threading.RLock()
        self.sesion = uuid.uuid4().hex
        self.modo = modo
        self.revision = 0
        self.generacion = 0
        self.reiniciar()

    def _evento(self, tipo, origen, resultado, descripcion):
        self.contador += 1
        self.eventos.appendleft(dict(id=self.contador,
            hora=datetime.now(timezone(timedelta(hours=-5))).isoformat(timespec="seconds"),
            tipo=tipo, origen=origen, resultado=resultado, descripcion=descripcion))
        self.revision += 1

    def registrar(self, tipo, origen, resultado, descripcion):
        with self.lock:
            self._evento(tipo, origen, resultado, descripcion)

    def reiniciar(self):
        with self.lock:
            self.valores = INICIAL.copy()
            self.azar = random.Random(2026)
            self.eventos = deque(maxlen=200)
            self.contador = self.ticks = 0
            self.generacion += 1
            self.ataque_hasta = 0.0
            self.valvula_indebida = False
            self.severidades = self._severidades()
            self._evento("sistema", "ponente", "aceptado", "Planta reiniciada: operación normal")

    def cambiar_modo(self, modo):
        if modo not in ("inseguro", "protegido"):
            raise ValueError("Modo inválido")
        with self.lock:
            self.modo = modo
            self._evento("modo", "ponente", "aceptado", f"MODO: {modo.upper()}")

    def _severidades(self):
        resultado = {}
        for campo, (minimo, bajo, alto, maximo) in UMBRALES.items():
            valor = self.valores[campo]
            resultado[campo] = ("alarma" if valor < minimo or valor > maximo else
                                "advertencia" if valor < bajo or valor > alto else "normal")
        resultado["metano"] = resultado["sustrato"] = "normal"
        resultado["valvula"] = "alarma" if self.valvula_indebida else "normal"
        resultado["agitador"] = "normal" if self.valores["agitador"] else "advertencia"
        return resultado

    def _evaluar(self):
        nuevas = self._severidades()
        for campo, severidad in nuevas.items():
            if self.severidades.get(campo) != severidad:
                self._evento("estado", "simulacion", severidad,
                             f"{campo.upper()}: {severidad.upper()}")
        self.severidades = nuevas

    def aplicar(self, cambios, origen):
        with self.lock:
            self.valores.update(cambios)
            if "valvula" in cambios:
                self.valvula_indebida = bool(cambios["valvula"] and origen == "modbus")
            if origen == "modbus":
                self.ataque_hasta = time.monotonic() + 8
            detalle = ", ".join(f"{campo}={valor}" for campo, valor in cambios.items())
            self._evento("control", origen, "aceptado", f"Escritura aceptada: {detalle}")
            self._evaluar()

    def avanzar(self):
        with self.lock:
            self.ticks += 1
            valores = self.valores
            objetivo_temp = 38 if valores["agitador"] else 42
            valores["temperatura"] += (objetivo_temp - valores["temperatura"]) * 0.002 + self.azar.uniform(-0.015, 0.015)
            objetivo_presion = 0.65 if valores["valvula"] else 1.4
            valores["presion"] += (objetivo_presion - valores["presion"]) * 0.012 + self.azar.uniform(-0.002, 0.002)
            if valores["presion"] > 2 and not valores["valvula"]:
                valores["presion"] += 0.02
            for campo, objetivo in (("metano", 62), ("sustrato", 74)):
                valores[campo] = max(0, min(100, valores[campo] +
                    (objetivo - valores[campo]) * 0.01 + self.azar.uniform(-0.025, 0.025)))
            valores["temperatura"] = max(0, min(6553.5, valores["temperatura"]))
            valores["presion"] = max(0, min(655.35, valores["presion"]))
            self.revision += 1
            self._evaluar()

    def instantanea(self):
        with self.lock:
            return dict(**{campo: round(valor, 3) if isinstance(valor, float) else valor
                          for campo, valor in self.valores.items()},
                modo=self.modo, revision=self.revision, generacion=self.generacion, sesion=self.sesion,
                ticks=self.ticks, severidades=self.severidades.copy(),
                alarmas=[campo for campo, nivel in self.severidades.items() if nivel == "alarma"],
                bajo_ataque=time.monotonic() < self.ataque_hasta,
                valvula_indebida=self.valvula_indebida,
                eventos=[evento.copy() for evento in self.eventos])
