from datetime import datetime, timezone

from bson import ObjectId
from flask import Blueprint, jsonify, request
from pymongo.errors import DuplicateKeyError

from app.db import get_db
from app.utils.responses import error_response
from app.utils.serializers import serialize_profile

profile_bp = Blueprint("profiles", __name__)

ALLOWED_FIELDS = {
    "user_id",
    "name",
    "email",
    "phone",
    "avatar_url",
    "bio",
    "level",
    "xp",
    "preferred_language",
}

REQUIRED_FIELDS = {"user_id", "name", "email"}


@profile_bp.post("")
def create_profile():
    payload = request.get_json(silent=True) or {}
    missing_fields = [field for field in REQUIRED_FIELDS if not payload.get(field)]

    if missing_fields:
        return error_response(
            "Data profil belum lengkap.",
            400,
            {"missing_fields": missing_fields},
        )

    now = datetime.now(timezone.utc)
    profile = _pick_allowed_fields(payload)
    profile.setdefault("phone", "")
    profile.setdefault("avatar_url", "")
    profile.setdefault("bio", "")
    profile.setdefault("level", 1)
    profile.setdefault("xp", 0)
    profile.setdefault("preferred_language", "jv")
    profile["created_at"] = now
    profile["updated_at"] = now

    try:
        result = get_db().user_profiles.insert_one(profile)
    except DuplicateKeyError:
        return error_response("User profile dengan user_id ini sudah ada.", 409)

    created_profile = get_db().user_profiles.find_one({"_id": result.inserted_id})
    return jsonify({"message": "Profil berhasil dibuat.", "data": serialize_profile(created_profile)}), 201


@profile_bp.get("")
def list_profiles():
    profiles = get_db().user_profiles.find().sort("created_at", -1)
    return jsonify({"data": [serialize_profile(profile) for profile in profiles]})


@profile_bp.get("/<profile_id>")
def get_profile(profile_id):
    object_id = _parse_object_id(profile_id)
    if object_id is None:
        return error_response("Format profile_id tidak valid.", 400)

    profile = get_db().user_profiles.find_one({"_id": object_id})
    if profile is None:
        return error_response("Profil tidak ditemukan.", 404)

    return jsonify({"data": serialize_profile(profile)})


@profile_bp.get("/by-user/<user_id>")
def get_profile_by_user(user_id):
    profile = get_db().user_profiles.find_one({"user_id": user_id})
    if profile is None:
        return error_response("Profil tidak ditemukan.", 404)

    return jsonify({"data": serialize_profile(profile)})


@profile_bp.patch("/<profile_id>")
def update_profile(profile_id):
    object_id = _parse_object_id(profile_id)
    if object_id is None:
        return error_response("Format profile_id tidak valid.", 400)

    payload = request.get_json(silent=True) or {}
    update_data = _pick_allowed_fields(payload)
    update_data.pop("user_id", None)

    if not update_data:
        return error_response("Tidak ada data profil yang bisa diupdate.", 400)

    update_data["updated_at"] = datetime.now(timezone.utc)
    result = get_db().user_profiles.update_one(
        {"_id": object_id},
        {"$set": update_data},
    )

    if result.matched_count == 0:
        return error_response("Profil tidak ditemukan.", 404)

    profile = get_db().user_profiles.find_one({"_id": object_id})
    return jsonify({"message": "Profil berhasil diupdate.", "data": serialize_profile(profile)})


@profile_bp.delete("/<profile_id>")
def delete_profile(profile_id):
    object_id = _parse_object_id(profile_id)
    if object_id is None:
        return error_response("Format profile_id tidak valid.", 400)

    result = get_db().user_profiles.delete_one({"_id": object_id})
    if result.deleted_count == 0:
        return error_response("Profil tidak ditemukan.", 404)

    return jsonify({"message": "Profil berhasil dihapus."})


def _pick_allowed_fields(payload):
    return {key: payload[key] for key in ALLOWED_FIELDS if key in payload}


def _parse_object_id(value):
    if not ObjectId.is_valid(value):
        return None

    return ObjectId(value)
