# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import AccessDenied


class ResUsers(models.Model):
    _inherit = "res.users"

    def _check_credentials(self, credential, env):
        """Kamdoo pairing: a one-time token from the QR code shown to this very user.

        The token was issued to a session already signed in (with its own second
        factor if any), so this sign-in skips the second factor.
        """
        if credential.get("type") != "kamdoo":
            return super()._check_credentials(credential, env)
        jeton = self.env["kamdoo.jeton"]._kamdoo_trouver(credential.get("jeton"))
        if not jeton or jeton.user_id != self.env.user:
            raise AccessDenied()
        jeton.sudo().utilise_le = fields.Datetime.now()
        return {"uid": self.env.user.id, "auth_method": "kamdoo", "mfa": "skip"}
