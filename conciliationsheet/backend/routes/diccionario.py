from flask import Blueprint, jsonify, request

from models.diccionario import DiccionarioSinonimo

diccionario_bp = Blueprint("diccionario", __name__)


@diccionario_bp.route("/api/diccionario", methods=["GET"])
def listar_diccionario():
    fuente = request.args.get("fuente")
    tipo = request.args.get("tipo")
    entries = DiccionarioSinonimo.listar_por_fuente(fuente, tipo)
    return jsonify({
        "total": len(entries),
        "data": [e.to_dict() for e in entries],
    }), 200


@diccionario_bp.route("/api/diccionario", methods=["POST"])
def crear_entrada():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Se requieren datos JSON"}), 400

    fuente = data.get("fuente")
    patron = data.get("patron")
    tipo = data.get("tipo")

    if not all([fuente, patron, tipo]):
        return jsonify({"error": "Se requiere: fuente, patron, tipo"}), 400

    if fuente not in ("banco", "contabilidad"):
        return jsonify({"error": "fuente debe ser 'banco' o 'contabilidad'"}), 400

    entry_id = data.get("id")
    if entry_id:
        entry = DiccionarioSinonimo.obtener_por_id(entry_id)
        if not entry:
            return jsonify({"error": "Entrada no encontrada"}), 404
        entry.fuente = fuente
        entry.patron = patron
        entry.tipo = tipo
        entry.autogenerado = data.get("autogenerado", entry.autogenerado)
        entry.activo = data.get("activo", entry.activo)
        entry.guardar()
        return jsonify(entry.to_dict()), 200

    entry = DiccionarioSinonimo(
        fuente=fuente,
        patron=patron,
        tipo=tipo,
        autogenerado=data.get("autogenerado", False),
        activo=data.get("activo", True),
    )
    entry.guardar()
    return jsonify(entry.to_dict()), 201


@diccionario_bp.route("/api/diccionario/<int:entry_id>", methods=["DELETE"])
def eliminar_entrada(entry_id):
    entry = DiccionarioSinonimo.obtener_por_id(entry_id)
    if not entry:
        return jsonify({"error": "Entrada no encontrada"}), 404
    entry.eliminar()
    return jsonify({"message": "Entrada eliminada"}), 200
