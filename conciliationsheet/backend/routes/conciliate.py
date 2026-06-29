from flask import Blueprint, jsonify, request

from database.db import get_connection
from models.conciliacion import Conciliacion
from models.partida_conciliatoria import PartidaConciliatoria
from models.detalle_conciliacion import DetalleConciliacion
from services.conciliador import ConciliadorBancario

conciliate_bp = Blueprint("conciliate", __name__)


@conciliate_bp.route("/api/conciliate", methods=["POST"])
def run_conciliation():
    """Ejecuta conciliacion bancaria en VISION EMPRESA.
    ---
    Los datos se almacenan tal cual de cada fuente:
      - movimientos_bancarios: VISION BANCO (debe=cargo, haber=abono)
      - movimientos_contables: VISION EMPRESA (debe=ingreso, haber=egreso)
    La conversion se realiza en ConciliadorBancario.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Se requieren datos JSON"}), 400

    vision = data.get("vision", "empresa")
    if vision != "empresa":
        return jsonify({"error": "Esta aplicacion solo trabaja en vision empresa. Use vision='empresa'"}), 400

    cuenta_id = data.get("cuenta_id")
    fecha_desde = data.get("fecha_desde")
    fecha_hasta = data.get("fecha_hasta")
    metodo = data.get("metodo", "1")
    saldo_final_banco = data.get("saldo_final_banco")
    saldo_final_contable = data.get("saldo_final_contable")
    saldo_inicial_banco = data.get("saldo_inicial_banco")
    saldo_inicial_contable = data.get("saldo_inicial_contable")

    if not all([cuenta_id, fecha_desde, fecha_hasta]):
        return jsonify({"error": "Se requiere: cuenta_id, fecha_desde, fecha_hasta"}), 400

    try:
        conciliador = ConciliadorBancario(
            cuenta_id, fecha_desde, fecha_hasta,
            saldo_final_banco=saldo_final_banco,
            saldo_final_contable=saldo_final_contable,
            saldo_inicial_banco=saldo_inicial_banco,
            saldo_inicial_contable=saldo_inicial_contable,
        )
        if metodo in ("1", "forma_1"):
            resultado = conciliador.conciliar_forma_1()
        elif metodo in ("2", "forma_2"):
            resultado = conciliador.conciliar_forma_2()
        elif metodo in ("cuadrada", "forma_3"):
            resultado = conciliador.conciliar_cuadrada()
        else:
            return jsonify({"error": "Metodo invalido. Use: 1, 2, cuadrada"}), 400
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
        result["detalles"] = [d.to_dict() for d in conc.obtener_detalles()]

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


@conciliate_bp.route("/api/conciliate", methods=["DELETE"])
def clear_conciliation():
    conn = get_connection()
    try:
        conn.execute("DELETE FROM detalles_conciliacion")
        conn.execute("DELETE FROM conciliaciones")
        conn.execute("DELETE FROM partidas_conciliatorias")
        conn.commit()
    finally:
        conn.close()

    return jsonify({"message": "Datos de conciliacion eliminados"}), 200
