"""Controladores delgados: delegan en modelo y política."""
from urllib.parse import urlsplit
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException


def crear_app(estado, politica, salud=None):
    aplicacion = Flask(__name__, template_folder="../views/templates", static_folder="../views/static")
    aplicacion.config["MAX_CONTENT_LENGTH"] = 4096

    @aplicacion.before_request
    def validar_origen():
        host = request.host.partition(":")[0].lower()
        if host not in ("localhost", "127.0.0.1"):
            return jsonify(error="Host local requerido"), 403
        if request.method == "POST":
            origen = request.headers.get("Origin")
            sitio = request.headers.get("Sec-Fetch-Site")
            if sitio == "cross-site":
                return jsonify(error="Origen no permitido"), 403
            if origen:
                partes = urlsplit(origen)
                if partes.scheme != "http" or partes.netloc != request.host:
                    return jsonify(error="Origen no permitido"), 403
            elif sitio:
                return jsonify(error="Origin requerido para el navegador"), 403
            if not request.is_json:
                return jsonify(error="Se requiere application/json"), 415

    @aplicacion.after_request
    def cabeceras(respuesta):
        respuesta.headers["Cache-Control"] = "no-store"
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'")
        return respuesta

    @aplicacion.errorhandler(HTTPException)
    def error_http(error):
        return jsonify(error=error.description), error.code

    @aplicacion.get("/")
    def tablero():
        return render_template("tablero.html", ponente=False)

    @aplicacion.get("/ponente")
    def ponente():
        return render_template("tablero.html", ponente=True)

    @aplicacion.get("/api/estado")
    def obtener_estado():
        return jsonify(estado.instantanea())

    @aplicacion.get("/api/salud")
    def obtener_salud():
        componentes = salud() if salud else {"web": True, "simulacion": False, "modbus": False}
        return jsonify(componentes), 200 if all(componentes.values()) else 503

    @aplicacion.post("/api/reiniciar")
    def reiniciar():
        estado.reiniciar()
        return jsonify(estado.instantanea())

    @aplicacion.post("/api/modo")
    def cambiar_modo():
        datos = request.get_json()
        try:
            if not isinstance(datos, dict) or set(datos) != {"modo"}:
                raise ValueError("Se requiere modo")
            estado.cambiar_modo(datos["modo"])
        except (ValueError, TypeError) as error:
            return jsonify(error=str(error)), 400
        return jsonify(estado.instantanea())

    @aplicacion.post("/api/control")
    def controlar():
        try:
            return jsonify(politica.autorizado(request.headers.get("Authorization", ""), request.get_json()))
        except PermissionError as error:
            return jsonify(error=str(error)), 401
        except (ValueError, TypeError) as error:
            return jsonify(error=str(error)), 400

    return aplicacion
