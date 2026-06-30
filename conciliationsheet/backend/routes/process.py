from flask import Blueprint, jsonify, request

from config import UPLOADS_DIR
from database.db import get_connection
from models.cuenta_bancaria import CuentaBancaria
from models.diccionario import DiccionarioSinonimo
from services.file_processor import procesar_archivo_a_movimientos, _clasificar_tipo_movimiento

# ============================================================
# Los datos se guardan TAL CUAL vienen de cada fuente:
#   - fuente='banco'        → movimientos_bancarios  (VISION BANCO)
#     debe=cargo, haber=abono (tal cual del extracto)
#   - fuente='contabilidad' → movimientos_contables (VISION EMPRESA)
#     debe=ingreso, haber=egreso (tal cual de libros)
# NO se hace conversion aqui. La conversion logica se realiza
# en ConciliadorBancario (servicio de conciliacion).
# ============================================================

process_bp = Blueprint("process", __name__)


@process_bp.route("/api/process", methods=["POST"])
def process_file():
    """Procesa archivo y guarda movimientos TAL CUAL segun su fuente.
    Sin conversion de vision. Eso se delega al servicio de conciliacion."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Se requieren datos JSON"}), 400

    archivo = data.get("archivo")
    cuenta_id = data.get("cuenta_id")
    fuente = data.get("fuente")
    saldo_final = data.get("saldo_final")

    if not all([archivo, cuenta_id, fuente]):
        return jsonify({"error": "Se requiere: archivo, cuenta_id, fuente"}), 400

    if fuente not in ("banco", "contabilidad"):
        return jsonify({"error": "Fuente debe ser 'banco' o 'contabilidad'"}), 400

    cuenta = CuentaBancaria.obtener_por_id(cuenta_id)
    if not cuenta:
        return jsonify({"error": "Cuenta no encontrada"}), 404

    ruta = UPLOADS_DIR / archivo
    if not ruta.exists():
        return jsonify({"error": f"Archivo no encontrado: {archivo}"}), 404

    try:
        movimientos = procesar_archivo_a_movimientos(str(ruta), cuenta_id, fuente)
    except Exception as e:
        return jsonify({"error": f"Error al procesar archivo: {str(e)}"}), 500

    conn = get_connection()
    try:
        if fuente == "banco":
            conn.execute("DELETE FROM movimientos_bancarios WHERE cuenta_id=?", (cuenta_id,))
        else:
            conn.execute("DELETE FROM movimientos_contables WHERE cuenta_id=?", (cuenta_id,))

        insertados = 0
        for m in movimientos:
            if fuente == "banco":
                conn.execute(
                    """INSERT INTO movimientos_bancarios
                       (cuenta_id, fecha, descripcion, debe, haber, saldo, tipo, conciliado)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (m.cuenta_id, m.fecha, m.descripcion, m.debe, m.haber,
                     getattr(m, 'saldo', None), getattr(m, 'tipo', None), 0),
                )
            else:
                conn.execute(
                    """INSERT INTO movimientos_contables
                       (cuenta_id, fecha, descripcion, debe, haber, saldo, comprobante, conciliado)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (m.cuenta_id, m.fecha, m.descripcion, m.debe, m.haber,
                     getattr(m, 'saldo', None), getattr(m, 'comprobante', None), 0),
                )
            insertados += 1

        if saldo_final is not None and insertados > 0:
            tabla = "movimientos_bancarios" if fuente == "banco" else "movimientos_contables"
            conn.execute(
                f"""UPDATE {tabla} SET saldo=? WHERE id=(
                    SELECT id FROM {tabla} WHERE cuenta_id=? ORDER BY fecha DESC, id DESC LIMIT 1
                )""",
                (saldo_final, cuenta_id),
            )
        conn.commit()
    finally:
        conn.close()

    for m in movimientos:
        desc = m.descripcion.strip()
        if not desc:
            continue
        if fuente == "banco":
            tipo = getattr(m, 'tipo', None) or _clasificar_tipo_movimiento(desc)
        else:
            tipo = _clasificar_tipo_movimiento(desc)
        if tipo:
            DiccionarioSinonimo.aprender(fuente, desc, tipo)

    return jsonify({
        "message": "Archivo procesado correctamente",
        "cuenta_id": cuenta_id,
        "fuente": fuente,
        "registros_insertados": insertados,
    }), 200


@process_bp.route("/api/process/clear", methods=["DELETE"])
def clear_movimientos():
    data = request.get_json() or {}
    cuenta_id = data.get("cuenta_id")
    fuente = data.get("fuente")

    conn = get_connection()
    try:
        if cuenta_id and fuente == "banco":
            conn.execute("DELETE FROM movimientos_bancarios WHERE cuenta_id=?", (cuenta_id,))
        elif cuenta_id and fuente == "contabilidad":
            conn.execute("DELETE FROM movimientos_contables WHERE cuenta_id=?", (cuenta_id,))
        elif cuenta_id:
            conn.execute("DELETE FROM movimientos_bancarios WHERE cuenta_id=?", (cuenta_id,))
            conn.execute("DELETE FROM movimientos_contables WHERE cuenta_id=?", (cuenta_id,))
        else:
            conn.execute("DELETE FROM movimientos_bancarios")
            conn.execute("DELETE FROM movimientos_contables")
        conn.commit()
    finally:
        conn.close()

    return jsonify({"message": "Movimientos eliminados"}), 200
