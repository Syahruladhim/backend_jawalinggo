from flask import jsonify


def error_response(message, status_code=400, details=None):
    payload = {"message": message}
    if details is not None:
        payload["details"] = details

    return jsonify(payload), status_code
