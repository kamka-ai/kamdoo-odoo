# -*- coding: utf-8 -*-
"""Phones that receive the Kamdoo notifications, for Odoo versions without Web Push (14, 15, 16).

The same API as ``mail.push.device`` in Odoo 17+, so the app registers the same way on every version:
``get_web_push_vapid_public_key``, ``register_devices``, ``unregister_devices``. The endpoint is the
Kamdoo relay address of one phone; ``keys`` are that phone's public keys (it alone can decrypt).
"""
import json

from odoo import api, fields, models
from odoo.exceptions import AccessDenied

from ..tools.web_push import generate_vapid_keys

PARAM_PUBLIQUE = "kamdoo_connect.web_push_vapid_public_key"
PARAM_PRIVEE = "kamdoo_connect.web_push_vapid_private_key"


class KamdooPushDevice(models.Model):
    _name = "kamdoo.push.device"
    _description = "Kamdoo notification device"

    partner_id = fields.Many2one("res.partner", required=True, index=True, ondelete="cascade",
                                 default=lambda self: self.env.user.partner_id)
    endpoint = fields.Char(required=True)
    keys = fields.Char(required=True)
    expiration_time = fields.Datetime()

    _sql_constraints = [("endpoint_unique", "unique(endpoint)", "The endpoint must be unique!")]

    @api.model
    def _kamdoo_vapid(self):
        """(private, public) keys of this database; created (and old devices dropped) the first time."""
        params = self.env["ir.config_parameter"].sudo()
        publique = params.get_param(PARAM_PUBLIQUE)
        if not publique:
            self.sudo().search([]).unlink()
            privee, publique = generate_vapid_keys()
            params.set_param(PARAM_PRIVEE, privee)
            params.set_param(PARAM_PUBLIQUE, publique)
        return params.get_param(PARAM_PRIVEE), publique

    @api.model
    def get_web_push_vapid_public_key(self):
        return self._kamdoo_vapid()[1]

    @api.model
    def register_devices(self, **kw):
        if self.env.user._is_public() or kw.get("vapid_public_key") != self._kamdoo_vapid()[1]:
            raise AccessDenied()
        endpoint, keys = kw.get("endpoint"), kw.get("keys")
        if not endpoint or not isinstance(keys, dict) or not keys.get("p256dh") or not keys.get("auth"):
            return
        valeurs = {
            "endpoint": endpoint,
            "keys": json.dumps({"p256dh": keys["p256dh"], "auth": keys["auth"]}),
            "expiration_time": kw.get("expirationTime") or False,
            "partner_id": self.env.user.partner_id.id,
        }
        appareil = self.sudo().search([("endpoint", "in", [kw.get("previousEndpoint") or endpoint, endpoint])], limit=1)
        if appareil:
            appareil.write(valeurs)
        else:
            self.sudo().create(valeurs)

    @api.model
    def unregister_devices(self, **kw):
        if kw.get("endpoint"):
            self.sudo().search([("endpoint", "=", kw["endpoint"]), ("partner_id", "=", self.env.user.partner_id.id)]).unlink()
