from flask import Blueprint, jsonify
from database.db import get_connection

reset_bp = Blueprint("reset", __name__)

@reset_bp.route("/api/reset", methods=["POST"])
def reset_database():
    conn = get_connection()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        tablas = [
            "partidas_conciliatorias",
            "conciliaciones",
            "movimientos_bancarios",
            "movimientos_contables",
            "diccionario_sinonimos",
        ]
        for t in tablas:
            conn.execute(f"DELETE FROM {t}")
        conn.execute("DELETE FROM sqlite_sequence")
        conn.execute("DELETE FROM cuentas_bancarias WHERE id <> 1")
        cur = conn.execute("SELECT COUNT(*) FROM cuentas_bancarias WHERE id=1")
        if cur.fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO cuentas_bancarias (id, nombre, banco) VALUES (1, 'Cuenta Principal', 'General')"
            )
        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        return jsonify({
            "message": "Base de datos reseteada correctamente",
            "tablas_limpiadas": tablas,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
