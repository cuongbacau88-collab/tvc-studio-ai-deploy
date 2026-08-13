"""Server-to-server bearer authentication and owner context validation."""

from __future__ import annotations

import hmac

from .errors import APIError


def headers(scope: dict) -> dict[str, str]:
    return {key.decode("latin1").lower(): value.decode("latin1") for key, value in scope.get("headers", [])}


def authenticate(scope: dict, expected_token: str) -> str:
    values = headers(scope)
    authorization = values.get("authorization", "")
    scheme, separator, supplied = authorization.partition(" ")
    if not expected_token or not separator or scheme.lower() != "bearer" or not hmac.compare_digest(supplied, expected_token):
        raise APIError("unauthorized", "Authentication required", 401)
    owner_id = values.get("x-owner-id", "").strip()
    if not owner_id:
        raise APIError("owner_required", "X-Owner-ID is required", 400)
    return owner_id
