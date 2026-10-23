"""ASK-Protokoll v1; kompatibel mit Lizenzgenerator 0.1.0. Nur öffentliche Prüfung."""
import base64
import hashlib
import json
import re
import uuid
from datetime import datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

PRODUCT = "knx-alarmserver"
DOMAIN = b"ASK-LICENSE-v1\x00"
REQUEST_FIELDS = {"v", "product", "email", "device"}
LICENSE_FIELDS = REQUEST_FIELDS | {"plan", "license_id", "issued_at", "key_id", "request_hash"}


class LicenseError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def unb64(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise LicenseError("Ungültige Code-Kodierung.")
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except ValueError as exc:
        raise LicenseError("Ungültige Code-Kodierung.") from exc
    if b64(raw) != value:
        raise LicenseError("Nicht kanonische Code-Kodierung.")
    return raw


def normalize_email(email):
    if not isinstance(email, str) or len(email) > 254:
        raise LicenseError("Ungültige Lizenz-E-Mail-Adresse.")
    parts = email.strip().lower().split("@")
    if len(parts) != 2:
        raise LicenseError("Ungültige Lizenz-E-Mail-Adresse.")
    local, domain = parts
    try:
        domain = domain.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise LicenseError("Ungültige E-Mail-Domain.") from exc
    labels = domain.split(".")
    if (not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}", local)
            or local.startswith(".") or local.endswith(".") or ".." in local
            or len(labels) < 2 or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", x)
                                    for x in labels)):
        raise LicenseError("Ungültige Lizenz-E-Mail-Adresse.")
    result = local + "@" + domain
    if len(result) > 254:
        raise LicenseError("Lizenz-E-Mail-Adresse ist zu lang.")
    return result


def identity(email, device):
    email = normalize_email(email)
    if not isinstance(device, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", device):
        raise LicenseError("Gerätefingerabdruck muss sha256: und 64 Hex-Zeichen enthalten.")
    return {"v": 1, "product": PRODUCT, "email": email, "device": device}


def validate_identity(data):
    if not isinstance(data, dict) or not REQUEST_FIELDS <= data.keys():
        raise LicenseError("Anfragefelder fehlen.")
    if type(data["v"]) is not int or data["v"] != 1 or data["product"] != PRODUCT:
        raise LicenseError("Unbekanntes Produkt oder Format.")
    expected = identity(data["email"], data["device"])
    if any(data[k] != expected[k] for k in REQUEST_FIELDS):
        raise LicenseError("Nicht normalisierte Anfrage.")
    return expected


def _pairs(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise LicenseError("Doppeltes JSON-Feld.")
        result[k] = v
    return result


def _parse(raw):
    try:
        data = json.loads(raw, object_pairs_hook=_pairs)
        if canonical(data) != raw:
            raise LicenseError("Nicht kanonische JSON-Daten.")
        return data
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise LicenseError("Beschädigte oder nicht kanonische Daten.") from exc


def _parts(code, prefix, count):
    if not isinstance(code, str) or len(code) > 8192:
        raise LicenseError("Code fehlt oder ist zu lang.")
    parts = code.strip().split(".")
    if len(parts) != count or parts[0] != prefix:
        raise LicenseError("Unbekanntes Codeformat.")
    return parts


def make_request(email, device):
    return "ASKREQ1." + b64(canonical(identity(email, device)))


def read_request(code):
    data = _parse(unb64(_parts(code, "ASKREQ1", 2)[1]))
    if not isinstance(data, dict) or set(data) != REQUEST_FIELDS:
        raise LicenseError("Unbekannte Anfragefelder.")
    return validate_identity(data)


def request_hash(request):
    return hashlib.sha256(canonical(request)).hexdigest()


def key_id(key):
    raw = key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()[:32]


def public_document(key):
    return {"format": "ASK-PUBLIC-KEY-1", "algorithm": "Ed25519", "key_id": key_id(key),
            "public_key": b64(key.public_bytes(Encoding.Raw, PublicFormat.Raw))}


def read_public(document):
    try:
        if (not isinstance(document, dict)
                or set(document) != {"format", "algorithm", "key_id", "public_key"}
                or document["format"] != "ASK-PUBLIC-KEY-1" or document["algorithm"] != "Ed25519"):
            raise LicenseError("Unbekanntes Schlüsselformat.")
        key = Ed25519PublicKey.from_public_bytes(unb64(document["public_key"]))
        if key_id(key) != document["key_id"]:
            raise LicenseError("Schlüsselkennung stimmt nicht überein.")
        return key
    except (ValueError, TypeError) as exc:
        raise LicenseError("Ungültiger öffentlicher Schlüssel.") from exc


def verify_license(code, trusted_keys, *, email=None, device=None):
    parts = _parts(code, "ASKLIC1", 3)
    raw, signature = unb64(parts[1]), unb64(parts[2])
    data = _parse(raw)
    if not isinstance(data, dict) or set(data) != LICENSE_FIELDS:
        raise LicenseError("Ungültige Lizenzfelder.")
    request = validate_identity(data)
    if data["plan"] != "lifetime" or data["request_hash"] != request_hash(request):
        raise LicenseError("Ungültige Lizenzdaten.")
    try:
        if str(uuid.UUID(data["license_id"])) != data["license_id"]:
            raise ValueError()
        stamp = datetime.strptime(data["issued_at"], "%Y-%m-%dT%H:%M:%SZ")
        if stamp.strftime("%Y-%m-%dT%H:%M:%SZ") != data["issued_at"]:
            raise ValueError()
        if not isinstance(data["key_id"], str):
            raise ValueError()
        key = trusted_keys.get(data["key_id"])
        if key is None or key_id(key) != data["key_id"] or len(signature) != 64:
            raise ValueError()
        key.verify(signature, DOMAIN + raw)
    except (ValueError, TypeError, AttributeError, InvalidSignature) as exc:
        raise LicenseError("Lizenz ist ungültig oder der Prüfschlüssel ist unbekannt.") from exc
    if email is not None and normalize_email(email) != data["email"]:
        raise LicenseError("Lizenz gehört zu einer anderen E-Mail-Adresse.")
    if device is not None and device != data["device"]:
        raise LicenseError("Lizenz gehört zu einem anderen Server.")
    return data
