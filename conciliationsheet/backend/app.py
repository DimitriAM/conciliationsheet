import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flask import Flask, jsonify, request
from flask_cors import CORS
from config import MAX_CONTENT_LENGTH, DATABASE_PATH
from database.db import init_database
from models.cuenta_bancaria import CuentaBancaria
from routes.upload import upload_bp
from routes.process import process_bp
from routes.conciliate import conciliate_bp
from routes.differences import differences_bp
from routes.reports import reports_bp
from routes.diccionario import diccionario_bp
from routes.reset import reset_bp

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
CORS(app)

init_database()


@app.before_request
def ensure_database():
    if not DATABASE_PATH.exists():
        init_database()


app.register_blueprint(upload_bp)
app.register_blueprint(process_bp)
app.register_blueprint(conciliate_bp)
app.register_blueprint(differences_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(diccionario_bp)
app.register_blueprint(reset_bp)


@app.route("/api/health", methods=["GET"])
def health():
    cuentas = len(CuentaBancaria.listar_todas())
    return jsonify({"status": "ok", "cuentas": cuentas})


@app.route("/api/cuenta/default", methods=["GET"])
def obtener_cuenta_default():
    from database.db import get_connection
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM cuentas_bancarias ORDER BY id LIMIT 1").fetchone()
        if row:
            cuenta = CuentaBancaria.from_row(dict(row))
        else:
            cuenta = CuentaBancaria(nombre="Cuenta Principal", banco="General")
            cuenta.guardar()
        return jsonify(cuenta.to_dict()), 200
    finally:
        conn.close()


@app.route("/api/cuentas", methods=["GET"])
def list_cuentas():
    cuentas = CuentaBancaria.listar_todas()
    return jsonify([c.to_dict() for c in cuentas]), 200


@app.route("/api/cuentas/<int:cuenta_id>", methods=["DELETE"])
def eliminar_cuenta(cuenta_id):
    cuenta = CuentaBancaria.obtener_por_id(cuenta_id)
    if not cuenta:
        return jsonify({"error": "Cuenta no encontrada"}), 404
    cuenta.eliminar()
    return jsonify({"message": "Cuenta eliminada", "id": cuenta_id}), 200


@app.route("/api/cuentas", methods=["POST"])
def crear_cuenta():
    data = request.get_json()
    if not data or not data.get("nombre") or not data.get("banco"):
        return jsonify({"error": "Se requiere: nombre, banco"}), 400
    cuenta_id = data.get("id")
    if cuenta_id:
        cuenta = CuentaBancaria.obtener_por_id(cuenta_id)
        if not cuenta:
            return jsonify({"error": "Cuenta no encontrada"}), 404
        cuenta.nombre = data["nombre"]
        cuenta.cbu = data.get("cbu")
        cuenta.banco = data["banco"]
        cuenta.saldo_inicial = data.get("saldo_inicial", 0)
        cuenta.fecha_apertura = data.get("fecha_apertura")
        cuenta.guardar()
        return jsonify(cuenta.to_dict()), 200
    else:
        cuenta = CuentaBancaria(
            nombre=data["nombre"],
            cbu=data.get("cbu"),
            banco=data["banco"],
            saldo_inicial=data.get("saldo_inicial", 0),
            fecha_apertura=data.get("fecha_apertura"),
        )
        cuenta.guardar()
        return jsonify(cuenta.to_dict()), 201


if __name__ == "__main__":
    init_database()
    app.run(host="0.0.0.0", port=5000, debug=True)
