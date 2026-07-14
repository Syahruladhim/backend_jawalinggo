from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app
import firebase_admin.auth


def create_access_token(user):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["_id"]),
        "email": user["email"],
        "name": user.get("name", ""),
        "iat": now,
        "exp": now + timedelta(days=7),
    }

    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def verify_google_id_token(token):
    try:
        decoded_token = firebase_admin.auth.verify_id_token(token)
        return decoded_token
    except Exception as exc:
        raise ValueError(f"Invalid Firebase ID token: {exc}")
