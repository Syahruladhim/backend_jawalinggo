from datetime import datetime, timedelta, timezone
import secrets

from flask import Blueprint, current_app, jsonify, request
from google.auth.exceptions import GoogleAuthError
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import get_db
from app.services.auth_service import create_access_token, verify_google_id_token
from app.services.mail_service import (
    MailConfigurationError,
    MailDeliveryError,
    send_register_otp_email,
    send_reset_code_email,
)
from app.utils.responses import error_response
from app.utils.serializers import serialize_user

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    name = payload.get("name", "").strip()
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")

    if not name or not email or not password:
        return error_response("Nama, email, dan password wajib diisi.", 400)

    if len(password) < 6:
        return error_response("Password minimal 6 karakter.", 400)

    now = datetime.now(timezone.utc)
    user = {
        "name": name,
        "email": email,
        "password_hash": generate_password_hash(password),
        "auth_provider": "email",
        "created_at": now,
        "updated_at": now,
    }

    try:
        result = get_db().app_users.insert_one(user)
    except DuplicateKeyError:
        return error_response("Email sudah terdaftar.", 409)

    user["_id"] = result.inserted_id
    return jsonify(
        {
            "message": "Registrasi berhasil.",
            "access_token": create_access_token(user),
            "data": serialize_user(user),
        }
    ), 201


@auth_bp.post("/register/request-otp")
def request_register_otp():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")
    name = payload.get("name", "").strip() or email.split("@")[0]

    if not email or not password:
        return error_response("Email dan password wajib diisi.", 400)

    if len(password) < 6:
        return error_response("Password minimal 6 karakter.", 400)

    if get_db().app_users.find_one({"email": email}) is not None:
        return error_response("Email sudah terdaftar.", 409)

    code = f"{secrets.randbelow(10000):04d}"
    now = datetime.now(timezone.utc)
    pending_registration = {
        "name": name,
        "email": email,
        "password_hash": generate_password_hash(password),
        "otp_hash": generate_password_hash(code),
        "created_at": now,
        "updated_at": now,
        "expires_at": now + timedelta(minutes=10),
    }

    get_db().pending_registrations.update_one(
        {"email": email},
        {"$set": pending_registration},
        upsert=True,
    )

    try:
        send_register_otp_email(email, code)
    except MailConfigurationError as exc:
        get_db().pending_registrations.delete_one({"email": email})
        return error_response(str(exc), 500)
    except MailDeliveryError as exc:
        current_app.logger.exception("Gagal mengirim email OTP pendaftaran: %s", exc)
        get_db().pending_registrations.delete_one({"email": email})
        return error_response("Gagal mengirim email OTP pendaftaran.", 502)

    return jsonify({"message": "Kode OTP sudah dikirim ke email."})


@auth_bp.post("/register/verify-otp")
def verify_register_otp():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "").strip().lower()
    code = payload.get("otp", "").strip()

    if not email or not code:
        return error_response("Email dan OTP wajib diisi.", 400)

    now = datetime.now(timezone.utc)
    pending_registration = get_db().pending_registrations.find_one(
        {
            "email": email,
            "expires_at": {"$gt": now},
        }
    )

    if pending_registration is None:
        return error_response("OTP tidak ditemukan atau sudah kedaluwarsa.", 400)

    if not check_password_hash(pending_registration["otp_hash"], code):
        return error_response("OTP tidak valid.", 400)

    user = {
        "name": pending_registration["name"],
        "email": pending_registration["email"],
        "password_hash": pending_registration["password_hash"],
        "auth_provider": "email",
        "email_verified_at": now,
        "created_at": now,
        "updated_at": now,
    }

    try:
        result = get_db().app_users.insert_one(user)
    except DuplicateKeyError:
        get_db().pending_registrations.delete_one({"email": email})
        return error_response("Email sudah terdaftar.", 409)

    get_db().pending_registrations.delete_one({"email": email})
    user["_id"] = result.inserted_id

    return jsonify(
        {
            "message": "Verifikasi berhasil. Silakan login.",
            "data": serialize_user(user),
        }
    ), 201


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")

    if not email or not password:
        return error_response("Email dan password wajib diisi.", 400)

    user = get_db().app_users.find_one({"email": email})
    if user is None or not user.get("password_hash"):
        return error_response("Email atau password salah.", 401)

    if not check_password_hash(user["password_hash"], password):
        return error_response("Email atau password salah.", 401)

    return jsonify(
        {
            "message": "Login berhasil.",
            "access_token": create_access_token(user),
            "data": serialize_user(user),
        }
    )


@auth_bp.post("/google")
def google_login():
    payload = request.get_json(silent=True) or {}
    token = payload.get("id_token", "")

    if not token:
        return error_response("id_token Google wajib dikirim.", 400)

    try:
        google_user = verify_google_id_token(token)
    except (GoogleAuthError, ValueError, Exception) as exc:
        return error_response(str(exc), 401)

    email = google_user.get("email", "").lower()
    google_sub = google_user.get("uid") or google_user.get("sub")
    name = google_user.get("name", email.split("@")[0])
    picture = google_user.get("picture", "")

    if not email or not google_sub:
        return error_response("Token Google/Firebase tidak memiliki data email/uid yang valid.", 401)

    now = datetime.now(timezone.utc)
    update_data = {
        "$set": {
            "name": name,
            "email": email,
            "google_sub": google_sub,
            "avatar_url": picture,
            "auth_provider": "google",
            "updated_at": now,
        },
        "$setOnInsert": {"created_at": now},
    }

    get_db().app_users.update_one({"email": email}, update_data, upsert=True)
    user = get_db().app_users.find_one({"email": email})

    return jsonify(
        {
            "message": "Login Google berhasil.",
            "access_token": create_access_token(user),
            "data": serialize_user(user),
        }
    )


@auth_bp.post("/forgot-password")
def forgot_password():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "").strip().lower()

    if not email:
        return error_response("Email wajib diisi.", 400)

    user = get_db().app_users.find_one({"email": email})
    if user is None:
        return jsonify({"message": "Jika email terdaftar, kode reset akan dikirim."})

    code = f"{secrets.randbelow(1000000):06d}"
    now = datetime.now(timezone.utc)
    get_db().password_reset_codes.update_many(
        {"email": email, "used_at": None},
        {"$set": {"used_at": now}},
    )
    get_db().password_reset_codes.insert_one(
        {
            "email": email,
            "code": generate_password_hash(code),
            "used_at": None,
            "created_at": now,
            "expires_at": now + timedelta(minutes=10),
        }
    )

    try:
        send_reset_code_email(email, code)
    except MailConfigurationError as exc:
        return error_response(str(exc), 500)
    except MailDeliveryError as exc:
        current_app.logger.exception("Gagal mengirim email reset password: %s", exc)
        return error_response("Gagal mengirim email reset password.", 502)

    return jsonify({"message": "Jika email terdaftar, kode reset akan dikirim."})


@auth_bp.post("/reset-password")
def reset_password():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "").strip().lower()
    code = payload.get("code", "").strip()
    new_password = payload.get("new_password", "")

    if not email or not code or not new_password:
        return error_response("Email, kode, dan password baru wajib diisi.", 400)

    if len(new_password) < 6:
        return error_response("Password baru minimal 6 karakter.", 400)

    now = datetime.now(timezone.utc)
    reset_requests = get_db().password_reset_codes.find(
        {
            "email": email,
            "used_at": None,
            "expires_at": {"$gt": now},
        }
    ).sort("created_at", -1)

    reset_request = next(
        (item for item in reset_requests if check_password_hash(item["code"], code)),
        None,
    )

    if reset_request is None:
        return error_response("Kode reset tidak valid atau sudah kedaluwarsa.", 400)

    result = get_db().app_users.update_one(
        {"email": email},
        {
            "$set": {
                "password_hash": generate_password_hash(new_password),
                "updated_at": now,
            }
        },
    )

    if result.matched_count == 0:
        return error_response("User tidak ditemukan.", 404)

    get_db().password_reset_codes.update_one(
        {"_id": reset_request["_id"]},
        {"$set": {"used_at": now}},
    )

    return jsonify({"message": "Password berhasil direset."})


@auth_bp.post("/change-password")
def change_password():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "").strip().lower()
    old_password = payload.get("old_password", "")
    new_password = payload.get("new_password", "")

    if not email or not old_password or not new_password:
        return error_response("Email, sandi lama, dan sandi baru wajib diisi.", 400)

    if len(new_password) < 6:
        return error_response("Sandi baru minimal 6 karakter.", 400)

    user = get_db().app_users.find_one({"email": email})
    if user is None or not user.get("password_hash"):
        return error_response("User tidak valid atau tidak menggunakan login dengan email.", 400)

    if not check_password_hash(user["password_hash"], old_password):
        return error_response("Sandi lama tidak sesuai.", 401)

    now = datetime.now(timezone.utc)
    result = get_db().app_users.update_one(
        {"email": email},
        {
            "$set": {
                "password_hash": generate_password_hash(new_password),
                "updated_at": now,
            }
        },
    )

    if result.matched_count == 0:
        return error_response("Gagal memperbarui sandi.", 500)

    return jsonify({"message": "Sandi berhasil diubah."})
