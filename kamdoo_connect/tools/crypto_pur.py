# -*- coding: utf-8 -*-
"""Pure-Python fallback for Web Push when the ``cryptography`` package is missing (the official Odoo 14
Docker image does not ship it).

Only what Web Push needs: P-256 (key generation, ECDH, ECDSA-SHA256 signature), HKDF-SHA256 and
AES-128-GCM, with the standard library alone. Used only if ``cryptography`` cannot be imported; it is
checked against ``cryptography`` by the module's tests. One message costs a few scalar multiplications:
fine for notifications, not meant for bulk use.
"""
import hashlib
import hmac
import secrets

# --- P-256 (SEC 2, secp256r1) -----------------------------------------------------------------------
P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
A = P - 3
B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
G = (0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
     0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5)


def _inverse(x, m):
    return pow(x, m - 2, m)  # m premier (Python 3.7 n'a pas pow(x, -1, m))


def _double(pt):
    x, y, z = pt
    if not y or not z:
        return (0, 1, 0)
    # a = -3 : formules dbl-2001-b
    delta = z * z % P
    gamma = y * y % P
    beta = x * gamma % P
    alpha = 3 * (x - delta) * (x + delta) % P
    x3 = (alpha * alpha - 8 * beta) % P
    z3 = ((y + z) * (y + z) - gamma - delta) % P
    y3 = (alpha * (4 * beta - x3) - 8 * gamma * gamma) % P
    return (x3, y3, z3)


def _ajouter(p1, p2):
    if not p1[2]:
        return p2
    if not p2[2]:
        return p1
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    z1z1, z2z2 = z1 * z1 % P, z2 * z2 % P
    u1, u2 = x1 * z2z2 % P, x2 * z1z1 % P
    s1, s2 = y1 * z2 * z2z2 % P, y2 * z1 * z1z1 % P
    if u1 == u2:
        return _double(p1) if s1 == s2 else (0, 1, 0)
    h = (u2 - u1) % P
    r = (s2 - s1) % P
    h2 = h * h % P
    h3 = h * h2 % P
    u1h2 = u1 * h2 % P
    x3 = (r * r - h3 - 2 * u1h2) % P
    y3 = (r * (u1h2 - x3) - s1 * h3) % P
    z3 = h * z1 * z2 % P
    return (x3, y3, z3)


def _affine(pt):
    x, y, z = pt
    if not z:
        raise ValueError("point at infinity")
    zi = _inverse(z, P)
    zi2 = zi * zi % P
    return (x * zi2 % P, y * zi2 * zi % P)


def multiplier(k, point):
    """k · point (affine coordinates), Montgomery ladder."""
    r0, r1 = (0, 1, 0), (point[0], point[1], 1)
    for i in reversed(range(256)):
        if (k >> i) & 1:
            r0, r1 = _ajouter(r0, r1), _double(r1)
        else:
            r1, r0 = _ajouter(r0, r1), _double(r0)
    return _affine(r0)


def sur_la_courbe(point):
    x, y = point
    return 0 <= x < P and 0 <= y < P and (y * y - (x * x * x + A * x + B)) % P == 0


def encoder(point):
    """Uncompressed SEC 1 encoding: 0x04 ‖ X ‖ Y."""
    return b"\x04" + point[0].to_bytes(32, "big") + point[1].to_bytes(32, "big")


def decoder(data):
    if len(data) != 65 or data[0] != 4:
        raise ValueError("invalid P-256 public key")
    point = (int.from_bytes(data[1:33], "big"), int.from_bytes(data[33:], "big"))
    if not sur_la_courbe(point):
        raise ValueError("point not on P-256")
    return point


def nouvelle_cle():
    """(private int, public affine point)."""
    d = secrets.randbelow(N - 1) + 1
    return d, multiplier(d, G)


def ecdh(d, publique):
    """Shared secret: X coordinate of d · publique (32 bytes)."""
    return multiplier(d, publique)[0].to_bytes(32, "big")


def signer(d, message):
    """ECDSA-SHA256 signature as raw r ‖ s (64 bytes), as JWT ES256 expects."""
    e = int.from_bytes(hashlib.sha256(message).digest(), "big")
    while True:
        k = secrets.randbelow(N - 1) + 1
        r = multiplier(k, G)[0] % N
        if not r:
            continue
        s = _inverse(k, N) * (e + r * d) % N
        if s:
            return r.to_bytes(32, "big") + s.to_bytes(32, "big")


# --- HKDF-SHA256 (RFC 5869) -------------------------------------------------------------------------
def hkdf(longueur, sel, ikm, info):
    prk = hmac.new(sel, ikm, hashlib.sha256).digest()
    sortie, bloc = b"", b""
    for i in range(1, -(-longueur // 32) + 1):
        bloc = hmac.new(prk, bloc + info + bytes([i]), hashlib.sha256).digest()
        sortie += bloc
    return sortie[:longueur]


# --- AES-128 (FIPS 197) et GCM (SP 800-38D) ---------------------------------------------------------
def _sbox():
    sbox = [0] * 256
    p = q = 1
    while True:
        p = p ^ ((p << 1) & 0xFF) ^ (0x1B if p & 0x80 else 0)
        q ^= q << 1
        q ^= q << 2
        q ^= q << 4
        q &= 0xFF
        if q & 0x80:
            q ^= 0x09
        x = q ^ ((q << 1) | (q >> 7)) ^ ((q << 2) | (q >> 6)) ^ ((q << 3) | (q >> 5)) ^ ((q << 4) | (q >> 4))
        sbox[p] = (x ^ 0x63) & 0xFF
        if p == 1:
            break
    sbox[0] = 0x63
    return sbox


SBOX = _sbox()


def _xtime(a):
    return ((a << 1) ^ 0x1B) & 0xFF if a & 0x80 else a << 1


def _cles_de_tours(cle):
    mots = [list(cle[i:i + 4]) for i in range(0, 16, 4)]
    rcon = 1
    for i in range(4, 44):
        t = list(mots[i - 1])
        if i % 4 == 0:
            t = [SBOX[t[1]] ^ rcon, SBOX[t[2]], SBOX[t[3]], SBOX[t[0]]]
            rcon = _xtime(rcon)
        mots.append([a ^ b for a, b in zip(mots[i - 4], t)])
    return [sum(mots[4 * r:4 * r + 4], []) for r in range(11)]


def _chiffrer_bloc(tours, bloc):
    s = [b ^ k for b, k in zip(bloc, tours[0])]
    for r in range(1, 11):
        s = [SBOX[b] for b in s]
        # ShiftRows (état rangé par colonnes)
        s = [s[(i + 4 * (i % 4)) % 16] for i in range(16)]
        if r != 10:
            m = []
            for c in range(4):
                a = s[4 * c:4 * c + 4]
                t = a[0] ^ a[1] ^ a[2] ^ a[3]
                m += [a[i] ^ t ^ _xtime(a[i] ^ a[(i + 1) % 4]) for i in range(4)]
            s = m
        s = [b ^ k for b, k in zip(s, tours[r])]
    return bytes(s)


def _gf_mult(x, y):
    r = 0
    for i in range(127, -1, -1):
        if (y >> i) & 1:
            r ^= x
        x = (x >> 1) ^ (0xE1 << 120) if x & 1 else x >> 1
    return r


def aes_gcm_chiffrer(cle, nonce, clair):
    """AES-128-GCM with a 12-byte nonce, no associated data: ciphertext ‖ tag (16 bytes)."""
    tours = _cles_de_tours(cle)
    h = int.from_bytes(_chiffrer_bloc(tours, b"\x00" * 16), "big")
    j0 = nonce + b"\x00\x00\x00\x01"
    chiffre = bytearray()
    compteur = 2
    for i in range(0, len(clair), 16):
        flux = _chiffrer_bloc(tours, nonce + compteur.to_bytes(4, "big"))
        chiffre += bytes(a ^ b for a, b in zip(clair[i:i + 16], flux))
        compteur += 1
    g = 0
    for i in range(0, len(chiffre), 16):
        bloc = bytes(chiffre[i:i + 16]).ljust(16, b"\x00")
        g = _gf_mult(g ^ int.from_bytes(bloc, "big"), h)
    longueurs = (0).to_bytes(8, "big") + (len(chiffre) * 8).to_bytes(8, "big")
    g = _gf_mult(g ^ int.from_bytes(longueurs, "big"), h)
    tag = bytes(a ^ b for a, b in zip(g.to_bytes(16, "big"), _chiffrer_bloc(tours, j0)))
    return bytes(chiffre) + tag
