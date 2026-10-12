# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessDenied
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestJumelage(TransactionCase):
    """The QR code holds a one-time token, never a login; the token opens a session once.

    The HTTP exchange (/kamdoo/qr, /kamdoo/jumelage) is checked end to end against a running server.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create({
            "name": "Kamdoo Testeur", "login": "kamdoo_testeur", "password": "kamdoo_testeur_mdp",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.autre = cls.env["res.users"].create({
            "name": "Autre", "login": "kamdoo_autre", "password": "kamdoo_autre_mdp",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.Jeton = cls.env["kamdoo.jeton"]

    def _verifier(self, user, jeton):
        return self.env["res.users"].with_user(user)._check_credentials({"type": "kamdoo", "jeton": jeton}, {})

    def test_jeton_usage_unique(self):
        jeton = self.Jeton._kamdoo_creer(self.user)
        info = self._verifier(self.user, jeton)
        self.assertEqual(info, {"uid": self.user.id, "auth_method": "kamdoo", "mfa": "skip"})
        with self.assertRaises(AccessDenied):
            self._verifier(self.user, jeton)

    def test_jeton_d_un_autre(self):
        jeton = self.Jeton._kamdoo_creer(self.user)
        with self.assertRaises(AccessDenied):
            self._verifier(self.autre, jeton)

    def test_jeton_expire(self):
        jeton = self.Jeton._kamdoo_creer(self.user)
        self.Jeton.search([("user_id", "=", self.user.id)]).expire_le = fields.Datetime.now() - timedelta(seconds=1)
        with self.assertRaises(AccessDenied):
            self._verifier(self.user, jeton)

    def test_nouveau_qr_revoque_l_ancien(self):
        ancien = self.Jeton._kamdoo_creer(self.user)
        self.Jeton._kamdoo_creer(self.user)
        with self.assertRaises(AccessDenied):
            self._verifier(self.user, ancien)

    def test_seule_l_empreinte_est_gardee(self):
        jeton = self.Jeton._kamdoo_creer(self.user)
        self.assertFalse(self.Jeton.search([("empreinte", "=", jeton)]))
        self.assertEqual(len(self.Jeton.search([("user_id", "=", self.user.id)])), 1)

    def test_mot_de_passe_inchange(self):
        info = self.env["res.users"].with_user(self.user)._check_credentials(
            {"type": "password", "password": "kamdoo_testeur_mdp"}, {})
        self.assertEqual(info["auth_method"], "password")
