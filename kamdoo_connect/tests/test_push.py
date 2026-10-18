# -*- coding: utf-8 -*-
import json

from odoo.tests import tagged
from odoo.tests import SavepointCase

from ..tools import crypto_pur
from ..tools.web_push import encrypt_payload, generate_vapid_keys, b64_decode, b64_encode


@tagged("post_install", "-at_install")
class TestPush(SavepointCase):
    """Web Push without the cryptography package: reference vectors, and the device API."""

    def test_aes_gcm_nist(self):
        # NIST GCM, cas de test 2 (clé, nonce et texte nuls).
        sortie = crypto_pur.aes_gcm_chiffrer(bytes(16), bytes(12), bytes(16))
        self.assertEqual(sortie.hex(), "0388dace60b6a392f328c2b971b2fe78" "ab6e47d42cec13bdf53a67b21257bddf")

    def test_hkdf_rfc5869(self):
        # RFC 5869, cas de test 1.
        okm = crypto_pur.hkdf(42, bytes.fromhex("000102030405060708090a0b0c"), bytes.fromhex("0b" * 22),
                              bytes.fromhex("f0f1f2f3f4f5f6f7f8f9"))
        self.assertEqual(okm.hex(), "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865")

    def test_ecdh_et_signature(self):
        d1, q1 = crypto_pur.nouvelle_cle()
        d2, q2 = crypto_pur.nouvelle_cle()
        self.assertEqual(crypto_pur.ecdh(d1, q2), crypto_pur.ecdh(d2, q1))
        self.assertEqual(crypto_pur.decoder(crypto_pur.encoder(q1)), q1)
        signature = crypto_pur.signer(d1, b"kamdoo")
        self.assertEqual(len(signature), 64)
        with self.assertRaises(ValueError):
            crypto_pur.decoder(b"\x04" + b"\x01" * 64)

    def test_chiffrement_format(self):
        _d, q = crypto_pur.nouvelle_cle()
        corps = encrypt_payload(b'{"title": "x"}', {"p256dh": b64_encode(crypto_pur.encoder(q)), "auth": b64_encode(bytes(16))})
        # sel (16) | taille d'enregistrement (4) | longueur de clé (1) | clé (65) | message + délimiteur + tag
        self.assertEqual(corps[20], 65)
        self.assertEqual(len(corps), 16 + 4 + 1 + 65 + len(b'{"title": "x"}') + 1 + 16)

    def test_appareils(self):
        Appareil = self.env["kamdoo.push.device"]
        vapid = Appareil.get_web_push_vapid_public_key()
        self.assertEqual(len(b64_decode(vapid)), 65)
        _d, q = crypto_pur.nouvelle_cle()
        cles = {"p256dh": b64_encode(crypto_pur.encoder(q)), "auth": b64_encode(bytes(16))}
        Appareil.register_devices(vapid_public_key=vapid, endpoint="https://relais.invalid/v1/e/a", keys=cles)
        Appareil.register_devices(vapid_public_key=vapid, endpoint="https://relais.invalid/v1/e/b", keys=cles,
                                  previousEndpoint="https://relais.invalid/v1/e/a")
        appareils = Appareil.search([("partner_id", "=", self.env.user.partner_id.id)])
        self.assertEqual(appareils.mapped("endpoint"), ["https://relais.invalid/v1/e/b"])
        self.assertEqual(json.loads(appareils.keys)["auth"], cles["auth"])
        Appareil.unregister_devices(endpoint="https://relais.invalid/v1/e/b")
        self.assertFalse(Appareil.search([("partner_id", "=", self.env.user.partner_id.id)]))
        self.assertEqual(len(generate_vapid_keys()), 2)
