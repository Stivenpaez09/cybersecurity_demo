"""Adaptador base cero; rechazo en PDU para evitar respuestas de éxito falsas."""
import asyncio
import logging
import threading
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.pdu import ExceptionResponse
from pymodbus.pdu.bit_message import WriteSingleCoilRequest, WriteMultipleCoilsRequest
from pymodbus.pdu.register_message import (WriteSingleRegisterRequest,
    WriteMultipleRegistersRequest, MaskWriteRegisterRequest, ReadWriteMultipleRegistersRequest)
from pymodbus.server import ModbusTcpServer
from app.config import PUERTO_MODBUS
from app.model.estado_planta import REGISTROS, BOBINAS


class ContextoPlanta(ModbusSlaveContext):
    def __init__(self, politica):
        super().__init__()
        self.politica = politica
        self.estado = politica.estado

    def validate(self, codigo, direccion, cantidad=1):
        limite = {1: 2, 3: 4, 5: 2, 6: 2, 15: 2, 16: 2}.get(codigo, 0)
        return cantidad > 0 and direccion >= 0 and direccion + cantidad <= limite

    def getValues(self, codigo, direccion, cantidad=1):
        with self.estado.lock:
            valores = self.estado.valores
            datos = ([valores[campo] for campo in BOBINAS] if codigo in (1, 5, 15) else
                [round(valores["temperatura"] * 10), round(valores["presion"] * 100),
                 round(valores["metano"]), round(valores["sustrato"])])
            return datos[direccion:direccion + cantidad]

    def setValues(self, codigo, direccion, valores):
        with self.estado.lock:
            if not self.validate(codigo, direccion, len(valores)):
                raise ValueError("Dirección inválida")
            campos = BOBINAS if codigo in (5, 15) else REGISTROS
            cambios = {campos[direccion + indice]: bool(valor) if codigo in (5, 15)
                       else valor / (10 if direccion + indice == 0 else 100)
                       for indice, valor in enumerate(valores)}
            self.estado.aplicar(cambios, "modbus")


def peticion_protegida(clase):
    async def update_datastore(self, contexto):
        # No hay suspensión efectiva en el datastore: el mismo lock serializa modo y escritura.
        with contexto.estado.lock:
            if not contexto.politica.permitir_directo():
                return ExceptionResponse(self.function_code, ExceptionResponse.ILLEGAL_FUNCTION)
            if self.function_code in (22, 23):
                return ExceptionResponse(self.function_code, ExceptionResponse.ILLEGAL_FUNCTION)
            return await clase.update_datastore(self, contexto)
    return type(f"PeticionProtegida{clase.__name__}", (clase,), {"update_datastore": update_datastore})


PETICIONES = [peticion_protegida(clase) for clase in (WriteSingleCoilRequest,
    WriteMultipleCoilsRequest, WriteSingleRegisterRequest, WriteMultipleRegistersRequest,
    MaskWriteRegisterRequest, ReadWriteMultipleRegistersRequest)]


class ServidorModbus(threading.Thread):
    def __init__(self, politica, host="0.0.0.0", puerto=PUERTO_MODBUS):
        super().__init__(name="modbus", daemon=True)
        self.contexto = ContextoPlanta(politica)
        self.host, self.puerto = host, puerto
        self.listo = threading.Event()
        self.bucle = self.servidor = None

    def saludable(self):
        return self.is_alive() and self.listo.is_set()

    async def _servir(self):
        self.bucle = asyncio.get_running_loop()
        self.servidor = ModbusTcpServer(ModbusServerContext(slaves={1: self.contexto}, single=False),
            address=(self.host, self.puerto), custom_pdu=PETICIONES)
        await self.servidor.serve_forever(background=True)
        if not self.servidor.transport:
            raise OSError("Puerto Modbus no disponible")
        self.listo.set()
        await self.servidor.serving

    def run(self):
        try:
            asyncio.run(self._servir())
        except Exception:
            logging.exception("Fallo Modbus: revise el puerto y reinicie planta")
        finally:
            self.listo.clear()

    def detener(self):
        if self.bucle and self.servidor and self.is_alive():
            futuro = asyncio.run_coroutine_threadsafe(self.servidor.shutdown(), self.bucle)
            futuro.result(timeout=5)
