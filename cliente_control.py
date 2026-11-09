"""Cliente proyectable: exclusivamente el PLC simulado de este contenedor."""
import argparse
from pymodbus.client import ModbusTcpClient
from app.config import PUERTO_MODBUS


def main():
    escenarios = {"abrir-valvula": ("COIL", 0, True),
                  "temperatura-alta": ("HR", 0, 650), "presion-alta": ("HR", 1, 250)}
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("escenario", choices=escenarios, nargs="?", default="abrir-valvula")
    tipo, registro, valor = escenarios[argumentos.parse_args().escenario]
    print(f"[PLC LOCAL] 127.0.0.1:{PUERTO_MODBUS} | {tipo}[{registro}] <- {valor}")
    with ModbusTcpClient("127.0.0.1", port=PUERTO_MODBUS, timeout=2, retries=0) as cliente:
        if not cliente.connect():
            print("[SIN CONEXIÓN] Arranque la planta y revise /api/salud")
            return 1
        escribir = cliente.write_coil if tipo == "COIL" else cliente.write_register
        respuesta = escribir(registro, valor, slave=1)
        if respuesta.isError():
            print(f"[RECHAZADO] Error Modbus: {respuesta}. Revise el registro del tablero.")
            return 2
    print("[ACEPTADO] Escritura aplicada. Observe el tablero.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
