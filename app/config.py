"""Configuración local: los puertos internos permanecen constantes."""
import os
import math

PUERTO_WEB = 18473
PUERTO_MODBUS = 18524
MODO = os.getenv("MODO", "inseguro")
TOKEN = os.getenv("TOKEN_DEMO", "valvula-laboratorio-local")
INTERVALO = 0.25
DIRECCION_ESCUCHA = os.getenv("DIRECCION_ESCUCHA", "127.0.0.1")
if DIRECCION_ESCUCHA not in ("127.0.0.1", "0.0.0.0"):
    raise ValueError("Dirección de escucha inválida")
UMBRALES = {
    "temperatura": tuple(float(os.getenv(nombre, defecto)) for nombre, defecto in (
        ("TEMP_ALARMA_BAJA", "30"), ("TEMP_NORMAL_BAJA", "35"),
        ("TEMP_NORMAL_ALTA", "40"), ("TEMP_ALARMA_ALTA", "45"))),
    "presion": tuple(float(os.getenv(nombre, defecto)) for nombre, defecto in (
        ("PRESION_ALARMA_BAJA", "0.8"), ("PRESION_NORMAL_BAJA", "1"),
        ("PRESION_NORMAL_ALTA", "1.6"), ("PRESION_ALARMA_ALTA", "2"))),
}
for nombre, limites in UMBRALES.items():
    if not all(math.isfinite(valor) for valor in limites) or any(
            primero >= segundo for primero, segundo in zip(limites, limites[1:])):
        raise ValueError(f"Umbrales de {nombre} deben ser finitos y estar en orden creciente")
