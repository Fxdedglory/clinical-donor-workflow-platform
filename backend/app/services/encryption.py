from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

SENSITIVE_KEYS = {
    "address",
    "authorization",
    "blood_type",
    "clinical_notes",
    "consent",
    "dob",
    "donor_history",
    "donor_id",
    "donor_identifier",
    "donor_name",
    "email",
    "history",
    "medical",
    "name",
    "notes",
    "phone",
    "rejection_reason",
    "result_value",
    "review_notes",
    "source_organization",
}


def _key() -> bytes:
    configured = settings.encryption_key or settings.secret_key
    try:
        decoded = base64.urlsafe_b64decode(configured)
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass
    return hashlib.sha256(configured.encode("utf-8")).digest()


def encrypt_text(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    nonce = os.urandom(12)
    ciphertext = AESGCM(_key()).encrypt(nonce, value.encode("utf-8"), None)
    return "v1:" + base64.urlsafe_b64encode(nonce).decode() + ":" + base64.urlsafe_b64encode(ciphertext).decode()


def decrypt_text(value: str | None) -> str | None:
    if value is None or value == "" or not value.startswith("v1:"):
        return value
    try:
        _, nonce_text, ciphertext_text = value.split(":", 2)
        nonce = base64.urlsafe_b64decode(nonce_text.encode())
        ciphertext = base64.urlsafe_b64decode(ciphertext_text.encode())
        return AESGCM(_key()).decrypt(nonce, ciphertext, None).decode("utf-8")
    except Exception:
        return None


def encrypt_json(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return encrypt_text(json.dumps(value, default=str, sort_keys=True))


def decrypt_json(value: str | None) -> Any:
    decrypted = decrypt_text(value)
    if not decrypted:
        return None
    try:
        return json.loads(decrypted)
    except json.JSONDecodeError:
        return decrypted


def blind_index(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(f"{settings.secret_key}:{value.lower()}".encode()).hexdigest()


def mask_identifier(value: Any) -> Any:
    if value is None:
        return None
    text = str(value)
    if len(text) <= 4:
        return "*" * len(text)
    return f"{text[:2]}***{text[-2:]}"


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(token in lowered for token in SENSITIVE_KEYS)


def mask_sensitive_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: mask_identifier(item) if _is_sensitive_key(key) else mask_sensitive_payload(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [mask_sensitive_payload(item) for item in value]
    return value


def protect_donor_review(donor: Any) -> None:
    donor.donor_id_encrypted = encrypt_text(getattr(donor, "donor_id", None))
    donor.donor_id_hash = blind_index(getattr(donor, "donor_id", None))
    donor.donor_name_encrypted = encrypt_text(getattr(donor, "donor_name", None))
    donor.clinical_notes_encrypted = encrypt_text(getattr(donor, "clinical_notes", None))
    donor.rejection_reason_encrypted = encrypt_text(getattr(donor, "rejection_reason", None))


def protect_donor_master(donor: Any) -> None:
    donor.donor_identifier_encrypted = encrypt_text(getattr(donor, "donor_identifier", None))
    donor.donor_identifier_hash = blind_index(getattr(donor, "donor_identifier", None))
    donor.donor_name_encrypted = encrypt_text(getattr(donor, "donor_name", None))
    donor.source_organization_encrypted = encrypt_text(getattr(donor, "source_organization", None))
    donor.donor_history_encrypted = encrypt_json(getattr(donor, "donor_history", None))
