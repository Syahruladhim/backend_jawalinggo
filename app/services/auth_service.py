from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app
from google.auth.transport import requests
from google.oauth2 import id_token


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
    client_id = current_app.config["GOOGLE_CLIENT_ID"]
    if not client_id:
        raise ValueError("GOOGLE_CLIENT_ID belum diisi di .env.")

    return id_token.verify_oauth2_token(token, requests.Request(), client_id)
