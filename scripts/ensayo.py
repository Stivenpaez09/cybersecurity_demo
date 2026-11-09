"""Ensayo real de estabilidad; no acelera el reloj ni modifica la planta."""
import argparse
import json
from pathlib import Path
import time
from urllib.request import urlopen


def main():
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--minutos", type=float, default=30)
    argumentos.add_argument("--puerto", type=int, default=18473)
    opciones = argumentos.parse_args()
    if opciones.minutos <= 0:
        argumentos.error("Los minutos deben ser positivos")
    inicio = time.monotonic()
    muestras = 0
    maximo = 0
    ultimo_tick = -1
    generacion = None
    while time.monotonic() - inicio < opciones.minutos * 60:
        consulta = time.monotonic()
        with urlopen(f"http://127.0.0.1:{opciones.puerto}/api/salud", timeout=2) as respuesta:
            assert all(json.load(respuesta).values()), "Componente detenido"
        with urlopen(f"http://127.0.0.1:{opciones.puerto}/api/estado", timeout=2) as respuesta:
            estado = json.load(respuesta)
        if generacion == estado["generacion"]:
            assert estado["ticks"] > ultimo_tick, "Simulacion sin progreso"
        generacion, ultimo_tick = estado["generacion"], estado["ticks"]
        assert len(estado["eventos"]) <= 200
        assert 0 <= estado["metano"] <= 100 and 0 <= estado["sustrato"] <= 100
        maximo = max(maximo, time.monotonic() - consulta)
        muestras += 1
        if muestras % 60 == 0:
            print(f"Ensayo activo: {muestras} muestras; {time.monotonic()-inicio:.0f} s", flush=True)
        time.sleep(1)
    informe = dict(segundos_reales=time.monotonic()-inicio, muestras=muestras,
                   maximo_consulta_ms=maximo*1000, resultado="aprobado")
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/ensayo.json").write_text(json.dumps(informe, indent=2), encoding="utf-8")
    print(json.dumps(informe), flush=True)


if __name__ == "__main__":
    main()
