# -*- coding: utf-8 -*-
"""API keys for the Kamdoo app (Odoo 19+).

With the JSON-2 API (``/json/2/<model>/<method>``) the app and the phone's
assistants (Siri, Gemini) reach the ERP with a key of their own instead of the
browser session. The key is handed to the phone when it pairs, is named after it
("Kamdoo · iPhone de Karim"), expires after the duration set in Settings (30 days
by default) and is renewed by the app before then. Users see and revoke it like any
other API key, in Preferences › Account Security.
"""
from datetime import timedelta

from odoo import api, fields, models

PREFIXE = "Kamdoo · "
PARAM_DUREE = "kamdoo_connect.duree_cle_jours"
DUREE_DEFAUT = 30


class ResUsersApikeys(models.Model):
    _inherit = "res.users.apikeys"

    @api.model
    def _kamdoo_duree(self):
        """Key lifetime in days, from Settings (1 to 365)."""
        brut = self.env["ir.config_parameter"].sudo().get_param(PARAM_DUREE, DUREE_DEFAUT)
        try:
            jours = int(brut)
        except (TypeError, ValueError):
            jours = DUREE_DEFAUT
        return max(1, min(jours, 365))

    @api.model
    def _kamdoo_nom(self, appareil):
        return (PREFIXE + ((appareil or "").strip() or "Phone"))[:100]

    @api.model
    def _kamdoo_revoquer(self, appareil):
        """Revokes the current user's Kamdoo keys for the phone ``appareil``."""
        self.sudo().search([("user_id", "=", self.env.uid), ("name", "=", self._kamdoo_nom(appareil))])._remove()

    @api.model
    def _kamdoo_generer(self, appareil):
        """A key for the current user's phone ``appareil``; that phone's older Kamdoo
        keys are revoked. Returns ``(key, expiry)``.

        The duration may exceed what the user's groups allow for keys made by hand
        (one day by default): it is the duration chosen for the app in Settings.
        """
        nom = self._kamdoo_nom(appareil)
        self._kamdoo_revoquer(appareil)
        expire = fields.Datetime.now() + timedelta(days=self._kamdoo_duree())
        cle = self.sudo()._generate("rpc", nom, expire)
        return cle, expire
