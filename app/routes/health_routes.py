from flask import Blueprint, current_app, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    database_connected = "mongo_db" in current_app.extensions

    return jsonify(
        {
            "status": "ok",
            "service": "jawalinggo-backend",
            "database_connected": database_connected,
        }
    )
