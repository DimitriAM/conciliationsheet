import openpyxl
from pathlib import Path

from flask import Blueprint, jsonify, request

from config import UPLOADS_DIR
from database.db import get_connection
from utils.validators import validar_extension
from utils.helpers import generar_nombre_unico

# ============================================================
# VISION DE ALMACENAMIENTO:
#   - Extracto bancario  → movimientos_bancarios  (VISION BANCO)
#     debe=cargo, haber=abono (tal cual del extracto)
#   - Movimientos contab. → movimientos_contables (VISION EMPRESA)
#     debe=ingreso, haber=egreso (tal cual de libros)
# La conversion logica se realiza en el servicio de conciliacion.
# ============================================================

upload_bp = Blueprint("upload", __name__)


@upload_bp.route("/api/upload", methods=["GET"])
def list_archivos():
    archivos = []
    for f in Path(UPLOADS_DIR).iterdir():
        if f.is_file():
            archivos.append({
                "nombre": f.name,
                "ruta": str(f),
                "tamano": f.stat().st_size,
            })
    return jsonify(archivos), 200


@upload_bp.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No se envio ningun archivo"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nombre de archivo vacio"}), 400

    if not validar_extension(file.filename):
        return jsonify({"error": "Formato no permitido. Use .xlsx, .xls o .csv"}), 400

    nombre_unico = generar_nombre_unico(file.filename)
    ruta = UPLOADS_DIR / nombre_unico
    file.save(str(ruta))

    return jsonify({
        "message": "Archivo subido correctamente",
        "archivo": {
            "nombre_original": file.filename,
            "nombre_archivo": nombre_unico,
            "ruta": str(ruta),
        }
    }), 201


@upload_bp.route("/api/upload/<filename>", methods=["DELETE"])
def delete_archivo(filename):
    ruta = UPLOADS_DIR / filename
    if not ruta.exists():
        return jsonify({"error": "Archivo no encontrado"}), 404

    fuente = _detectar_fuente(str(ruta))

    ruta.unlink(missing_ok=True)

    if fuente:
        conn = get_connection()
        try:
            tabla = "movimientos_bancarios" if fuente == "banco" else "movimientos_contables"
            conn.execute(f"DELETE FROM {tabla} WHERE cuenta_id=1")
            conn.execute("DELETE FROM sqlite_sequence WHERE name=?", (tabla,))
            conn.commit()
            return jsonify({
                "message": f"Archivo eliminado y movimientos de {fuente} removidos",
                "archivo": filename,
                "fuente": fuente,
            }), 200
        finally:
            conn.close()
    else:
        return jsonify({"message": "Archivo eliminado (no se pudo determinar fuente)", "archivo": filename}), 200


def _detectar_fuente(ruta: str) -> str | None:
    try:
        wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(min_row=1, max_row=5, values_only=True))
        wb.close()
        texto = " ".join(str(c or "") for row in rows for c in row).lower()
        if "contabilidad" in texto:
            return "contabilidad"
        if "banco" in texto or "extracto" in texto and "bancario" in texto:
            return "banco"
        return None
    except Exception:
        return None
