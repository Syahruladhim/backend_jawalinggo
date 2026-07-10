from flask import current_app, g
from pymongo import MongoClient
from pymongo.errors import PyMongoError


def init_db(app):
    if not app.config["MONGO_URI"]:
        app.logger.warning("MONGO_URI belum diisi. Isi file .env sebelum menjalankan API.")
        return

    client = MongoClient(
        app.config["MONGO_URI"],
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )

    try:
        db = client[app.config["MONGO_DB_NAME"]]
        db.app_users.create_index("email", unique=True)
        db.app_users.create_index("google_sub", unique=True, sparse=True)
        db.pending_registrations.create_index("email", unique=True)
        db.pending_registrations.create_index("expires_at", expireAfterSeconds=0)
        db.password_reset_codes.create_index("email")
        db.password_reset_codes.create_index("expires_at", expireAfterSeconds=0)
        db.user_profiles.create_index("user_id", unique=True)
        db.user_profiles.create_index("email")
        db.user_progress.create_index("user_id", unique=True)
    except PyMongoError as exc:
        app.logger.error("Gagal terhubung ke MongoDB: %s", exc)
    else:
        app.extensions["mongo_client"] = client
        app.extensions["mongo_db"] = db


def get_db():
    if "mongo_db" not in current_app.extensions:
        raise RuntimeError("Database belum siap. Periksa MONGO_URI dan MONGO_DB_NAME.")

    if "db" not in g:
        g.db = current_app.extensions["mongo_db"]

    return g.db
