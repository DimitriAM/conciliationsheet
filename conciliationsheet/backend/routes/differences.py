from flask import Blueprint, jsonify, request

from database.db import get_connection
from models.partida_conciliatoria import PartidaConciliatoria

differences_bp = Blueprint("differences", __name__)


@differences_bp.route("/api/partidas", methods=["GET"])
def get_partidas():
    cuenta_id = request.args.get("cuenta_id", type=int)
    tipo = request.args.get("tipo")
    estado = request.args.get("estado")
    origen = request.args.get("origen")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    per_page = min(per_page, 500)

    conn = get_connection()
    try:
        condiciones = []
        params = []

        if cuenta_id:
            condiciones.append("pc.cuenta_id = ?")
            params.append(cuenta_id)
        if tipo:
            condiciones.append("pc.tipo = ?")
            params.append(tipo)
        if estado:
            condiciones.append("pc.estado = ?")
            params.append(estado)
        if origen:
            condiciones.append("pc.origen = ?")
            params.append(origen)

        where = ""
        if condiciones:
            where = "WHERE " + " AND ".join(condiciones)

        count_row = conn.execute(
            f"SELECT COUNT(*) as total FROM partidas_conciliatorias pc {where}", params
        ).fetchone()
        total = count_row["total"]

        offset = (page - 1) * per_page
        rows = conn.execute(
            f"""SELECT pc.* FROM partidas_conciliatorias pc {where}
                ORDER BY pc.fecha DESC LIMIT ? OFFSET ?""",
            (*params, per_page, offset),
        ).fetchall()

        partidas = [PartidaConciliatoria.from_row(dict(r)).to_dict() for r in rows]

        resumen = conn.execute(
            f"""SELECT pc.tipo, COUNT(*) as cantidad,
                       COALESCE(SUM(pc.debe), 0) as total_debe,
                       COALESCE(SUM(pc.haber), 0) as total_haber
                FROM partidas_conciliatorias pc {where}
                GROUP BY pc.tipo""", params
        ).fetchall()

        return jsonify({
            "total": total,
            "page": page,
            "per_page": per_page,
            "data": partidas,
            "resumen": [dict(r) for r in resumen],
        }), 200
    finally:
        conn.close()


@differences_bp.route("/api/partidas/<int:partida_id>", methods=["GET"])
def get_partida(partida_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM partidas_conciliatorias WHERE id=?", (partida_id,)).fetchone()
        if not row:
            return jsonify({"error": "Partida no encontrada"}), 404
        return jsonify(PartidaConciliatoria.from_row(dict(row)).to_dict()), 200
    finally:
        conn.close()


@differences_bp.route("/api/partidas/<int:partida_id>", methods=["PATCH"])
def update_partida(partida_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se enviaron datos"}), 400

    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM partidas_conciliatorias WHERE id=?", (partida_id,)).fetchone()
        if not row:
            return jsonify({"error": "Partida no encontrada"}), 404

        campos = []
        params = []
        for campo in ("estado", "tipo", "origen", "observaciones", "fecha_resolucion"):
            if campo in data:
                campos.append(f"{campo} = ?")
                params.append(data[campo])

        if not campos:
            return jsonify({"error": "No hay campos validos para actualizar"}), 400

        params.append(partida_id)
        conn.execute(
            f"UPDATE partidas_conciliatorias SET {', '.join(campos)} WHERE id=?", params
        )
        conn.commit()

        row = conn.execute("SELECT * FROM partidas_conciliatorias WHERE id=?", (partida_id,)).fetchone()
        return jsonify(PartidaConciliatoria.from_row(dict(row)).to_dict()), 200
    finally:
        conn.close()
