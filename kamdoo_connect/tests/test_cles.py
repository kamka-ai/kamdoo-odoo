# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged

from ..models.res_users_apikeys import PARAM_DUREE


@tagged("post_install", "-at_install")
class TestCles(TransactionCase):
    """The paired phone gets an API key of its own (JSON-2 API), named after it,
    with the duration set in Settings, one per phone, revocable like any key."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create({
            "name": "Kamdoo Cles", "login": "kamdoo_cles", "password": "kamdoo_cles_mdp",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.Cles = cls.env["res.users.apikeys"].with_user(cls.user)

    def _uid_de(self, cle):
        return self.env["res.users.apikeys"]._check_credentials(scope="rpc", key=cle)

    def test_cle_ouvre_l_api_pour_son_utilisateur(self):
        cle, _expire = self.Cles._kamdoo_generer("iPhone de Test")
        self.assertEqual(self._uid_de(cle), self.user.id)

    def test_cle_nommee_d_apres_le_telephone(self):
        self.Cles._kamdoo_generer("iPhone de Test")
        noms = self.env["res.users.apikeys"].sudo().search([("user_id", "=", self.user.id)]).mapped("name")
        self.assertEqual(noms, ["Kamdoo · iPhone de Test"])

    def test_duree_des_reglages_au_dela_de_la_limite_des_groupes(self):
        self.env["ir.config_parameter"].sudo().set_int(PARAM_DUREE, 45)
        _cle, expire = self.Cles._kamdoo_generer("iPhone de Test")
        ecart = expire - fields.Datetime.now()
        self.assertGreater(ecart, timedelta(days=44))
        self.assertLessEqual(ecart, timedelta(days=45))

    def test_duree_bornee(self):
        self.env["ir.config_parameter"].sudo().set_int(PARAM_DUREE, 9999)
        self.assertEqual(self.Cles._kamdoo_duree(), 365)
        self.env["ir.config_parameter"].sudo().set_str(PARAM_DUREE, "abc")
        self.assertEqual(self.Cles._kamdoo_duree(), 30)

    def test_une_cle_par_telephone(self):
        ancienne, _ = self.Cles._kamdoo_generer("iPhone de Test")
        nouvelle, _ = self.Cles._kamdoo_generer("iPhone de Test")
        self.assertFalse(self._uid_de(ancienne))
        self.assertEqual(self._uid_de(nouvelle), self.user.id)

    def test_deux_telephones_deux_cles(self):
        iphone, _ = self.Cles._kamdoo_generer("iPhone de Test")
        android, _ = self.Cles._kamdoo_generer("Pixel de Test")
        self.assertEqual(self._uid_de(iphone), self.user.id)
        self.assertEqual(self._uid_de(android), self.user.id)

    def test_retirer_la_societe_revoque_la_cle_du_telephone(self):
        iphone, _ = self.Cles._kamdoo_generer("iPhone de Test")
        android, _ = self.Cles._kamdoo_generer("Pixel de Test")
        self.Cles._kamdoo_revoquer("iPhone de Test")
        self.assertFalse(self._uid_de(iphone))
        self.assertEqual(self._uid_de(android), self.user.id)

    def test_cle_revoquee_ne_marche_plus(self):
        cle, _ = self.Cles._kamdoo_generer("iPhone de Test")
        self.env["res.users.apikeys"].sudo().search([("user_id", "=", self.user.id)])._remove()
        self.assertFalse(self._uid_de(cle))
