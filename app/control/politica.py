"""Autorización y validación compartidas por ambos canales."""
import hmac
import math


class Politica:
    def __init__(self, estado, token):
        if not token:
            raise ValueError("TOKEN_DEMO no puede estar vacío")
        self.estado, self.token = estado, token

    def permitir_directo(self):
        # El llamador mantiene el lock hasta terminar la petición completa.
        if self.estado.modo == "protegido":
            self.estado.registrar("control", "modbus", "rechazado",
                                  "Escritura rechazada: origen no autorizado")
            return False
        return True

    def autorizado(self, autorizacion, orden):
        with self.estado.lock:
            if not hmac.compare_digest(autorizacion.encode(), f"Bearer {self.token}".encode()):
                self.estado.registrar("control", "gateway", "rechazado", "Gateway: token inválido")
                raise PermissionError("Token inválido")
            if not isinstance(orden, dict) or set(orden) != {"campo", "valor"}:
                raise ValueError("Se requieren campo y valor")
            campo, valor = orden["campo"], orden["valor"]
            if campo in ("valvula", "agitador"):
                if type(valor) is not bool:
                    raise ValueError("El actuador requiere true o false")
            elif campo in ("temperatura", "presion"):
                limite = 6553.5 if campo == "temperatura" else 655.35
                if type(valor) not in (int, float) or not math.isfinite(valor) or not 0 <= valor <= limite:
                    raise ValueError("Valor fuera del rango del registro")
            else:
                raise ValueError("Campo de control inválido")
            self.estado.aplicar({campo: valor}, "gateway")
            return self.estado.instantanea()
