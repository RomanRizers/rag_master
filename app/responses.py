from flask import jsonify


def error_response(code, message, details=None, status=400):
    payload = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return jsonify(payload), status
