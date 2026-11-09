import concurrent.futures
import socket
import threading
import time
import pytest
from pymodbus.client import ModbusTcpClient
from app.model.estado_planta import EstadoPlanta
from app.model.simulacion import Simulacion
from app.control.politica import Politica
from app.control.servidor_modbus import ServidorModbus
from app.web.controllers.rutas import crear_app


@pytest.fixture
def sistema():
    estado = EstadoPlanta()
    politica = Politica(estado, "prueba")
    return estado, politica, crear_app(estado, politica).test_client()


def test_reinicio_determinista_y_eventos(sistema):
    estado, _, _ = sistema
    for _ in range(100):
        estado.avanzar()
    primero = estado.instantanea()
    estado.cambiar_modo("protegido")
    estado.reiniciar()
    for _ in range(100):
        estado.avanzar()
    segundo = estado.instantanea()
    assert primero["sesion"] == segundo["sesion"]
    assert segundo["revision"] > primero["revision"]
    assert EstadoPlanta().instantanea()["sesion"] != segundo["sesion"]
    for campo in ("temperatura", "presion", "metano", "sustrato", "ticks"):
        assert primero[campo] == segundo[campo]
    assert segundo["modo"] == "protegido"
    for _ in range(250):
        estado.registrar("prueba", "local", "aceptado", "Evento")
    assert len(estado.instantanea()["eventos"]) == 200


def test_dinamica_30_minutos_simulados(sistema):
    estado, _, _ = sistema
    for _ in range(7200):
        estado.avanzar()
        assert not estado.instantanea()["alarmas"]
    estado.aplicar({"presion": 2.5}, "modbus")
    assert "presion" in estado.instantanea()["alarmas"]
    estado.avanzar()
    assert estado.instantanea()["presion"] > 2.5
    estado.reiniciar()
    estado.aplicar({"valvula": True}, "modbus")
    for _ in range(100):
        estado.avanzar()
    assert estado.instantanea()["presion"] < 1.4
    assert estado.instantanea()["valvula_indebida"]


def test_api_gateway_y_origen(sistema):
    estado, _, web = sistema
    assert web.get("/").status_code == 200
    assert b'data-modo=' not in web.get("/").data
    assert b'data-modo=' in web.get("/ponente").data
    assert web.get("/api/salud").status_code == 503
    assert web.post("/api/modo", json={"modo": "protegido"}).status_code == 200
    orden = {"campo": "valvula", "valor": True}
    assert web.post("/api/control", json=orden).status_code == 401
    assert not estado.instantanea()["valvula"]
    assert web.post("/api/control", json=orden, headers={"Authorization": "Bearer prueba"}).status_code == 200
    assert estado.instantanea()["valvula"] and not estado.instantanea()["valvula_indebida"]
    assert web.post("/api/reiniciar", json={}, headers={"Origin": "https://tercero.invalid"}).status_code == 403
    assert web.post("/api/reiniciar", json={}, headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert web.post("/api/reiniciar", data="{}").status_code == 415
    assert web.get("/api/estado", headers={"Host": "tercero.invalid"}).status_code == 403
    assert web.post("/api/modo", json={"modo": "otro"}).status_code == 400
    assert web.post("/api/reiniciar", json={}).json["modo"] == "protegido"
    for orden in ([], {"campo": "metano", "valor": 1}, {"campo": "valvula", "valor": 1},
                  {"campo": "temperatura", "valor": -1}, {"campo": [], "valor": True}):
        assert web.post("/api/control", json=orden, headers={"Authorization": "Bearer prueba"}).status_code == 400
    assert "prueba" not in str(estado.instantanea()["eventos"])


@pytest.fixture
def plc(sistema):
    estado, politica, _ = sistema
    with socket.socket() as puerto:
        puerto.bind(("127.0.0.1", 0))
        numero = puerto.getsockname()[1]
    servidor = ServidorModbus(politica, "127.0.0.1", numero)
    servidor.start()
    assert servidor.listo.wait(5)
    cliente = ModbusTcpClient("127.0.0.1", port=numero, timeout=2, retries=0)
    assert cliente.connect()
    try:
        yield estado, cliente, servidor
    finally:
        cliente.close()
        servidor.detener()
        servidor.join(5)
        assert not servidor.is_alive()


def test_modbus_real_lecturas_escrituras_y_atomicidad(plc):
    estado, cliente, _ = plc
    assert cliente.read_holding_registers(0, count=4, slave=1).registers == [380, 140, 62, 74]
    assert not cliente.write_registers(0, [650, 250], slave=1).isError()
    assert estado.instantanea()["temperatura"] == 65
    assert estado.instantanea()["presion"] == 2.5
    assert cliente.write_registers(1, [200, 99], slave=1).isError()
    assert estado.instantanea()["presion"] == 2.5
    assert not cliente.write_coils(0, [True, False], slave=1).isError()
    assert cliente.read_coils(0, count=2, slave=1).bits[:2] == [True, False]
    estado.cambiar_modo("protegido")
    antes = estado.instantanea()
    operaciones = [lambda: cliente.write_coil(0, False, slave=1),
        lambda: cliente.write_coils(0, [False, True], slave=1),
        lambda: cliente.write_register(0, 400, slave=1),
        lambda: cliente.write_registers(0, [400, 100], slave=1),
        lambda: cliente.mask_write_register(address=0, and_mask=0, or_mask=400, slave=1),
        lambda: cliente.readwrite_registers(read_address=0, read_count=1, write_address=0,
                                          values=[400], slave=1)]
    for operacion in operaciones:
        respuesta = operacion()
        assert respuesta.isError() and respuesta.exception_code == 1
        for campo in ("temperatura", "presion", "valvula", "agitador"):
            assert estado.instantanea()[campo] == antes[campo]
    assert sum(evento["resultado"] == "rechazado" for evento in estado.instantanea()["eventos"]) == 6
    assert not cliente.read_holding_registers(0, count=4, slave=1).isError()


def test_concurrencia_reinicio_modo_y_gateway(sistema):
    estado, politica, _ = sistema
    def operar(indice):
        for _ in range(100):
            if indice == 0:
                estado.reiniciar()
            elif indice == 1:
                estado.avanzar()
            elif indice == 2:
                estado.cambiar_modo("protegido")
            else:
                politica.autorizado("Bearer prueba", {"campo": "valvula", "valor": True})
            instantanea = estado.instantanea()
            assert all(campo in instantanea for campo in ("temperatura", "presion", "modo", "eventos"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as grupo:
        list(grupo.map(operar, range(4)))


def test_diez_ciclos_y_20_mediciones(plc):
    estado, cliente, _ = plc
    latencias = []
    for _ in range(10):
        estado.cambiar_modo("inseguro")
        estado.reiniciar()
        for escenario in ("valvula", "temperatura"):
            inicio = time.perf_counter()
            respuesta = (cliente.write_coil(0, True, slave=1) if escenario == "valvula" else
                         cliente.write_register(0, 650, slave=1))
            assert not respuesta.isError()
            assert estado.instantanea()[escenario] == (True if escenario == "valvula" else 65)
            latencias.append(time.perf_counter() - inicio)
        estado.cambiar_modo("protegido")
        assert cliente.write_coil(0, False, slave=1).isError()
    assert len(latencias) == 20 and max(latencias) < 1
    print(f"\n20 escrituras Modbus -> instantanea: máximo {max(latencias)*1000:.1f} ms (no mide render del navegador)")


def test_salud_motor(sistema):
    estado, _, _ = sistema
    motor = Simulacion(estado)
    assert not motor.saludable()
    motor.start()
    time.sleep(0.05)
    assert motor.saludable()
    motor.detener.set()
    motor.join(2)
    assert not motor.saludable()


def test_salud_degradada_y_peticion_mismo_origen(sistema):
    estado, politica, _ = sistema
    salud = {"web": True, "simulacion": True, "modbus": True}
    web = crear_app(estado, politica, lambda: salud.copy()).test_client()
    assert web.get("/api/salud").status_code == 200
    salud["modbus"] = False
    assert web.get("/api/salud").status_code == 503
    assert web.get("/api/salud").json["modbus"] is False
    assert web.post("/api/modo", json={"modo": "protegido"},
        headers={"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}).status_code == 200
    assert web.post("/api/control", json={"campo": "temperatura", "valor": 65},
        headers={"Authorization": "Bearer prueba", "Origin": "null"}).status_code == 403


def test_cambio_modo_durante_escrituras_reales(plc):
    estado, cliente, _ = plc
    aplicar_original = estado.aplicar
    violaciones = []
    def aplicar_observado(cambios, origen):
        with estado.lock:
            if origen == "modbus" and estado.modo != "inseguro":
                violaciones.append(estado.modo)
            aplicar_original(cambios, origen)
    estado.aplicar = aplicar_observado
    def alternar():
        for indice in range(150):
            estado.cambiar_modo("protegido" if indice % 2 else "inseguro")
            if indice % 10 == 0:
                estado.reiniciar()
            time.sleep(0.001)
    hilo = threading.Thread(target=alternar)
    hilo.start()
    try:
        for indice in range(150):
            respuesta = cliente.write_register(0, 380 + indice % 10, slave=1)
            assert not respuesta.isError() or respuesta.exception_code == 1
    finally:
        hilo.join(3)
    assert not hilo.is_alive() and not violaciones


def test_salud_listener_real(plc):
    estado, _, servidor = plc
    politica = Politica(estado, "prueba")
    motor = Simulacion(estado)
    motor.start()
    try:
        time.sleep(0.03)
        web = crear_app(estado, politica, lambda: dict(web=True,
            simulacion=motor.saludable(), modbus=servidor.saludable())).test_client()
        assert web.get("/api/salud").status_code == 200
        servidor.detener()
        servidor.join(3)
        assert web.get("/api/salud").status_code == 503
        assert web.get("/api/salud").json["modbus"] is False
    finally:
        motor.detener.set()
        motor.join(2)
