from pathlib import Path

from flask import Blueprint, jsonify, request

from config import UPLOADS_DIR
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
    ruta.unlink(missing_ok=True)
    return jsonify({"message": "Archivo eliminado", "archivo": filename}), 200
