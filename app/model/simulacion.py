import logging
import threading
import time
from app.config import INTERVALO


class Simulacion(threading.Thread):
    def __init__(self, estado):
        super().__init__(name="simulacion", daemon=True)
        self.estado = estado
        self.detener = threading.Event()
        self.ultimo_tick = 0.0

    def saludable(self):
        return self.is_alive() and time.monotonic() - self.ultimo_tick < 2

    def run(self):
        try:
            while not self.detener.is_set():
                self.estado.avanzar()
                self.ultimo_tick = time.monotonic()
                self.detener.wait(INTERVALO)
        except Exception:
            logging.exception("Fallo del motor: reinicie el servicio planta")
