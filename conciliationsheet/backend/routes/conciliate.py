from flask import Blueprint, jsonify, request

from database.db import get_connection
from models.conciliacion import Conciliacion
from models.partida_conciliatoria import PartidaConciliatoria
from services.conciliador import ConciliadorBancario

conciliate_bp = Blueprint("conciliate", __name__)


@conciliate_bp.route("/api/conciliate", methods=["POST"])
def run_conciliation():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Se requieren datos JSON"}), 400

    metodo = data.get("metodo", "")
    if metodo != "desde_contabilidad":
        return jsonify({"error": "Metodo invalido. Unico metodo aceptado: desde_contabilidad"}), 400

    cuenta_id = data.get("cuenta_id")
    fecha_desde = data.get("fecha_desde")
    fecha_hasta = data.get("fecha_hasta")

    if not all([cuenta_id, fecha_desde, fecha_hasta]):
        return jsonify({"error": "Se requiere: cuenta_id, fecha_desde, fecha_hasta"}), 400

    try:
        conciliador = ConciliadorBancario()
        resultado = conciliador.conciliar_forma_1(cuenta_id, fecha_desde, fecha_hasta)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Error en conciliacion: {str(e)}"}), 500

    resultado["vision"] = "empresa"
    return jsonify(resultado), 200


@conciliate_bp.route("/api/conciliate/history", methods=["GET"])
def conciliation_history():
    cuenta_id = request.args.get("cuenta_id", type=int)
    if not cuenta_id:
        return jsonify({"error": "Se requiere cuenta_id"}), 400

    conciliaciones = Conciliacion.obtener_por_cuenta(cuenta_id)
    return jsonify({
        "total": len(conciliaciones),
        "data": [c.to_dict() for c in conciliaciones],
    }), 200


@conciliate_bp.route("/api/conciliate/<int:conciliacion_id>", methods=["GET"])
def get_conciliation(conciliacion_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM conciliaciones WHERE id=?", (conciliacion_id,)).fetchone()
        if not row:
            return jsonify({"error": "Conciliacion no encontrada"}), 404

        conc = Conciliacion.from_row(dict(row))
        result = conc.to_dict()

        partidas = conn.execute(
            """SELECT pc.* FROM partidas_conciliatorias pc
               WHERE pc.cuenta_id=?
               ORDER BY pc.fecha""",
            (conc.cuenta_id,),
        ).fetchall()
        result["partidas_conciliatorias"] = [dict(r) for r in partidas]

        return jsonify(result), 200
    finally:
        conn.close()


@conciliate_bp.route("/api/conciliate/<int:conciliacion_id>", methods=["DELETE"])
def delete_one_conciliation(conciliacion_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM conciliaciones WHERE id=?", (conciliacion_id,)).fetchone()
        if not row:
            return jsonify({"error": "Conciliacion no encontrada"}), 404

        cuenta_id = row["cuenta_id"]
        ultima = conn.execute(
            "SELECT id FROM conciliaciones WHERE cuenta_id=? ORDER BY id DESC LIMIT 1",
            (cuenta_id,),
        ).fetchone()

        if ultima and ultima["id"] == conciliacion_id:
            conn.execute("DELETE FROM partidas_conciliatorias WHERE cuenta_id=?", (cuenta_id,))

        conn.execute("DELETE FROM conciliaciones WHERE id=?", (conciliacion_id,))
        conn.commit()

        return jsonify({"message": "Conciliacion eliminada", "id": conciliacion_id}), 200
    finally:
        conn.close()


@conciliate_bp.route("/api/conciliate", methods=["DELETE"])
def clear_conciliation():
    conn = get_connection()
    try:
        conn.execute("DELETE FROM conciliaciones")
        conn.execute("DELETE FROM partidas_conciliatorias")
        conn.commit()
    finally:
        conn.close()

    return jsonify({"message": "Datos de conciliacion eliminados"}), 200
