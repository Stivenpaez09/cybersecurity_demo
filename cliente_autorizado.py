"""Control por gateway local; el token nunca se imprime."""
import argparse
import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from app.config import TOKEN, PUERTO_WEB


def main():
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("escenario", choices=("abrir-valvula", "temperatura-alta", "presion-alta"),
                            nargs="?", default="abrir-valvula")
    ordenes = {"abrir-valvula": ("valvula", True), "temperatura-alta": ("temperatura", 65),
               "presion-alta": ("presion", 2.5)}
    campo, valor = ordenes[argumentos.parse_args().escenario]
    peticion = Request(f"http://127.0.0.1:{PUERTO_WEB}/api/control",
        data=json.dumps(dict(campo=campo, valor=valor)).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"})
    try:
        with urlopen(peticion, timeout=2) as respuesta:
            respuesta.read()
        print(f"[GATEWAY AUTORIZADO] {campo} <- {valor}. Observe el tablero.")
        return 0
    except HTTPError as error:
        print(f"[RECHAZADO] HTTP {error.code}. Revise el registro del tablero.")
    except URLError:
        print("[SIN CONEXIÓN] Revise el servicio planta.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
