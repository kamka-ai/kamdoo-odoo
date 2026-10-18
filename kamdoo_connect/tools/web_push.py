# -*- coding: utf-8 -*-
"""Web Push (RFC 8291 + VAPID, RFC 8292) for Odoo versions without it (14, 15, 16).

Ported from Odoo 17's ``mail/tools/web_push.py`` and ``mail/tools/jwt.py`` (LGPL-3), runs on Python 3.7.
Uses the ``cryptography`` package when it is installed, otherwise the pure-Python fallback of
``crypto_pur`` (the official Odoo 14 image has no ``cryptography``). The phone created the key pair: only
it can decrypt the message; the Kamdoo relay that forwards it to Apple or Google cannot read it.
"""
import base64
import json
import logging
import os
import struct
import time
from urllib.parse import urlsplit

from . import crypto_pur

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    AVEC_CRYPTOGRAPHY = True
except ImportError:
    AVEC_CRYPTOGRAPHY = False

_logger = logging.getLogger(__name__)

MAX_PAYLOAD_SIZE = 4096


class DeviceUnreachableError(Exception):
    pass


def b64_decode(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def b64_encode(data):
    return base64.urlsafe_b64encode(data).decode("ascii").strip("=")


# --- Primitives : cryptography si présent, Python pur sinon ------------------------------------------
def _nouvelle_cle():
    """(private, uncompressed public bytes)."""
    if AVEC_CRYPTOGRAPHY:
        cle = ec.generate_private_key(ec.SECP256R1(), default_backend())
        return cle, cle.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    d, point = crypto_pur.nouvelle_cle()
    return d, crypto_pur.encoder(point)


def _ecdh(privee, publique_octets):
    if AVEC_CRYPTOGRAPHY:
        return privee.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), publique_octets))
    return crypto_pur.ecdh(privee, crypto_pur.decoder(publique_octets))


def _hkdf(longueur, sel, ikm, info):
    if AVEC_CRYPTOGRAPHY:
        return HKDF(algorithm=hashes.SHA256(), length=longueur, salt=sel, info=info, backend=default_backend()).derive(ikm)
    return crypto_pur.hkdf(longueur, sel, ikm, info)


def _aes_gcm(cle, nonce, clair):
    if AVEC_CRYPTOGRAPHY:
        return AESGCM(cle).encrypt(nonce, clair, None)
    return crypto_pur.aes_gcm_chiffrer(cle, nonce, clair)


def _signer_es256(privee_octets, message):
    d = int.from_bytes(privee_octets, "big")
    if AVEC_CRYPTOGRAPHY:
        cle = ec.derive_private_key(d, ec.SECP256R1(), default_backend())
        r, s = utils.decode_dss_signature(cle.sign(message, ec.ECDSA(hashes.SHA256())))
        return r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return crypto_pur.signer(d, message)


# --- Web Push ------------------------------------------------------------------------------------------
def generate_vapid_keys():
    """(private, public) VAPID keys, base64url without padding (P-256)."""
    if AVEC_CRYPTOGRAPHY:
        cle, publique = _nouvelle_cle()
        return b64_encode(cle.private_numbers().private_value.to_bytes(32, "big")), b64_encode(publique)
    d, point = crypto_pur.nouvelle_cle()
    return b64_encode(d.to_bytes(32, "big")), b64_encode(crypto_pur.encoder(point))


def _jwt_es256(claims, private_key):
    header = b64_encode(json.dumps({"typ": "JWT", "alg": "ES256"}).encode())
    payload = b64_encode(json.dumps(claims).encode())
    unsigned = "%s.%s" % (header, payload)
    return "%s.%s" % (unsigned, b64_encode(_signer_es256(b64_decode(private_key), unsigned.encode())))


def encrypt_payload(content, keys, record_size=MAX_PAYLOAD_SIZE):
    """aes128gcm body (RFC 8188) for the browser keys ``{"p256dh", "auth"}``."""
    p256dh = b64_decode(keys["p256dh"])
    auth = b64_decode(keys["auth"])
    privee, expediteur = _nouvelle_cle()
    salt = os.urandom(16)
    secret = _hkdf(32, auth, _ecdh(privee, p256dh), b"WebPush: info\x00" + p256dh + expediteur)
    key = _hkdf(16, salt, secret, b"Content-Encoding: aes128gcm\x00")
    nonce = _hkdf(12, salt, secret, b"Content-Encoding: nonce\x00")
    chunk_size = record_size - 1 - 16
    body = b""
    for i in range(0, len(content), chunk_size):
        padding = b"\x02" if (i + chunk_size) >= len(content) else b"\x01"
        body += _aes_gcm(key, nonce, content[i:i + chunk_size] + padding)
    return struct.pack("!16sLB", salt, record_size, len(expediteur)) + expediteur + body


def push_to_end_point(base_url, device, payload, vapid_private_key, vapid_public_key, session):
    """Sends ``payload`` (str) to ``device`` ({"endpoint", "keys": json}); raises DeviceUnreachableError on 404/410."""
    endpoint = device["endpoint"]
    url = urlsplit(endpoint)
    if url.netloc.endswith(".invalid"):
        raise DeviceUnreachableError("Device Unreachable")
    token = _jwt_es256({
        "aud": "%s://%s" % (url.scheme, url.netloc),
        "sub": base_url,
        "exp": int(time.time()) + 12 * 60 * 60,
    }, vapid_private_key)
    body = encrypt_payload(payload.encode(), json.loads(device["keys"]))
    response = session.post(endpoint, data=body, timeout=5, headers={
        "Authorization": "vapid t=%s, k=%s" % (token, vapid_public_key),
        "Content-Encoding": "aes128gcm",
        "TTL": "60",
    })
    if response.status_code == 201:
        return
    _logger.warning("Kamdoo push: %s answered %s", url.netloc, response.status_code)
    if response.status_code in (404, 410):
        raise DeviceUnreachableError("Device Unreachable")
