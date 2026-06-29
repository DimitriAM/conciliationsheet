from datetime import datetime

from flask import Blueprint, jsonify, request, send_file

from services.report_generator import generar_excel_partidas, generar_pdf_partidas
from database.db import get_connection

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/api/reports/summary", methods=["GET"])
def report_summary():
    cuenta_id = request.args.get("cuenta_id", type=int)
    tipo = request.args.get("tipo")
    estado = request.args.get("estado")
    fecha_desde = request.args.get("fecha_desde")
    fecha_hasta = request.args.get("fecha_hasta")

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
        if fecha_desde:
            condiciones.append("pc.fecha >= ?")
            params.append(fecha_desde)
        if fecha_hasta:
            condiciones.append("pc.fecha <= ?")
            params.append(fecha_hasta)

        where = "WHERE " + " AND ".join(condiciones) if condiciones else ""

        resumen = conn.execute(
            f"""SELECT pc.tipo, COUNT(*) as cantidad,
                       COALESCE(SUM(pc.debe), 0) as total_debe,
                       COALESCE(SUM(pc.haber), 0) as total_haber
                FROM partidas_conciliatorias pc {where}
                GROUP BY pc.tipo""", params
        ).fetchall()

        total_filas = conn.execute(
            f"SELECT COUNT(*) as total FROM partidas_conciliatorias pc {where}", params
        ).fetchone()

        monto_total = conn.execute(
            f"""SELECT COALESCE(SUM(pc.debe + pc.haber), 0) as monto
                FROM partidas_conciliatorias pc {where}""", params
        ).fetchone()

        # Ultima conciliacion si hay cuenta_id
        ultima = None
        if cuenta_id:
            row = conn.execute(
                "SELECT * FROM conciliaciones WHERE cuenta_id=? ORDER BY fecha_cierre DESC LIMIT 1",
                (cuenta_id,),
            ).fetchone()
            if row:
                ultima = dict(row)

        return jsonify({
            "total": total_filas["total"],
            "monto_total": round(monto_total["monto"], 2),
            "resumen": [dict(r) for r in resumen],
            "ultima_conciliacion": ultima,
        }), 200
    finally:
        conn.close()


@reports_bp.route("/api/reports/export", methods=["GET"])
def export_report():
    formato = request.args.get("formato", "excel")
    cuenta_id = request.args.get("cuenta_id", type=int)
    tipo = request.args.get("tipo")
    estado = request.args.get("estado")
    fecha_desde = request.args.get("fecha_desde")
    fecha_hasta = request.args.get("fecha_hasta")

    if formato == "pdf":
        output = generar_pdf_partidas(cuenta_id, tipo, estado, fecha_desde, fecha_hasta)
        filename = f"reporte_partidas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        mimetype = "application/pdf"
    else:
        output = generar_excel_partidas(cuenta_id, tipo, estado, fecha_desde, fecha_hasta)
        filename = f"reporte_partidas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return send_file(output, mimetype=mimetype, as_attachment=True, download_name=filename)
