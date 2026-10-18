# -*- coding: utf-8 -*-
"""Web Push (RFC 8291 + VAPID, RFC 8292) for Odoo versions without it (14, 15, 16).

Ported from Odoo 17's ``mail/tools/web_push.py`` and ``mail/tools/jwt.py`` (LGPL-3), without the newer
Python syntax so that it runs on Python 3.7. The phone created the key pair: only it can decrypt the
message; the Kamdoo relay that forwards it to Apple or Google cannot read it.
"""
import base64
import binascii
import json
import logging
import os
import struct
import time
from urllib.parse import urlsplit

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

_logger = logging.getLogger(__name__)

MAX_PAYLOAD_SIZE = 4096


class DeviceUnreachableError(Exception):
    pass


def b64_decode(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def b64_encode(data):
    return base64.urlsafe_b64encode(data).decode("ascii").strip("=")


def generate_vapid_keys():
    """(private, public) VAPID keys, base64url without padding (P-256)."""
    private_object = ec.generate_private_key(ec.SECP256R1(), default_backend())
    private_bytes = private_object.private_numbers().private_value.to_bytes(32, "big")
    public_bytes = private_object.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return b64_encode(private_bytes), b64_encode(public_bytes)


def _jwt_es256(claims, private_key):
    header = b64_encode(json.dumps({"typ": "JWT", "alg": "ES256"}).encode())
    payload = b64_encode(json.dumps(claims).encode())
    unsigned = "%s.%s" % (header, payload)
    key = ec.derive_private_key(int(binascii.hexlify(b64_decode(private_key)), 16), ec.SECP256R1(), default_backend())
    r, s = utils.decode_dss_signature(key.sign(unsigned.encode(), ec.ECDSA(hashes.SHA256())))
    return "%s.%s" % (unsigned, b64_encode(r.to_bytes(32, "big") + s.to_bytes(32, "big")))


def _derive_key(salt, private_key, keys):
    p256dh = b64_decode(keys["p256dh"])
    auth = b64_decode(keys["auth"])
    pub_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), p256dh)
    sender_pub_key = private_key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    context = b"WebPush: info\x00" + p256dh + sender_pub_key

    def hkdf(length, hkdf_salt, info):
        return HKDF(algorithm=hashes.SHA256(), length=length, salt=hkdf_salt, info=info, backend=default_backend())

    secret = hkdf(32, auth, context).derive(private_key.exchange(ec.ECDH(), pub_key))
    return (hkdf(16, salt, b"Content-Encoding: aes128gcm\x00").derive(secret),
            hkdf(12, salt, b"Content-Encoding: nonce\x00").derive(secret))


def encrypt_payload(content, keys, record_size=MAX_PAYLOAD_SIZE):
    """aes128gcm body (RFC 8188) for the browser keys ``{"p256dh", "auth"}``."""
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    salt = os.urandom(16)
    key, nonce = _derive_key(salt, private_key, keys)
    chunk_size = record_size - 1 - 16
    aesgcm = AESGCM(key)
    body = b""
    for i in range(0, len(content), chunk_size):
        padding = b"\x02" if (i + chunk_size) >= len(content) else b"\x01"
        body += aesgcm.encrypt(nonce, content[i:i + chunk_size] + padding, None)
    sender_public_key = private_key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return struct.pack("!16sLB", salt, record_size, len(sender_public_key)) + sender_public_key + body


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
