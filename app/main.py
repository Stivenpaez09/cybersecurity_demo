"""Un proceso, un modelo, sin recargador ni workers adicionales."""
import logging
import signal
import threading
from waitress import create_server
from app.config import MODO, TOKEN, PUERTO_WEB, DIRECCION_ESCUCHA
from app.model.estado_planta import EstadoPlanta
from app.model.simulacion import Simulacion
from app.control.politica import Politica
from app.control.servidor_modbus import ServidorModbus
from app.web.controllers.rutas import crear_app


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    estado = EstadoPlanta(MODO)
    politica = Politica(estado, TOKEN)
    simulacion = Simulacion(estado)
    modbus = ServidorModbus(politica, host=DIRECCION_ESCUCHA)
    web = None
    detener = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: detener.set())
    signal.signal(signal.SIGINT, lambda *_: detener.set())
    try:
        simulacion.start()
        modbus.start()
        if not modbus.listo.wait(5):
            raise RuntimeError("Modbus no arrancó: revise el puerto 18524")
        aplicacion = crear_app(estado, politica, lambda: dict(web=True,
            simulacion=simulacion.saludable(), modbus=modbus.saludable()))
        web = create_server(aplicacion, host=DIRECCION_ESCUCHA, port=PUERTO_WEB, threads=4)
        hilo_web = threading.Thread(target=web.run, name="web", daemon=True)
        hilo_web.start()
        logging.info("Tablero http://localhost:%s/ | Ponente /ponente | MODO: %s", PUERTO_WEB, MODO.upper())
        logging.info("Puertos del host configurables en Compose. Reinicio: vista /ponente o docker compose restart planta")
        while not detener.wait(0.5):
            if not hilo_web.is_alive():
                raise RuntimeError("El servidor web se detuvo")
    finally:
        if web:
            web.close()
        simulacion.detener.set()
        simulacion.join(timeout=3)
        modbus.detener()
        modbus.join(timeout=3)
        logging.info("Planta detenida")


if __name__ == "__main__":
    main()
