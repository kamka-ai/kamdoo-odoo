# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import AccessDenied

# Odoo 17 : les identifiants sont un mot de passe (texte) ; le jeton du QR y voyage préfixé.
PREFIXE = "kamdoo-jeton:"


class ResUsers(models.Model):
    _inherit = "res.users"

    def _check_credentials(self, password, env):
        """Kamdoo pairing: a one-time token from the QR code shown to this very user."""
        if not (isinstance(password, str) and password.startswith(PREFIXE)):
            return super()._check_credentials(password, env)
        jeton = self.env["kamdoo.jeton"]._kamdoo_trouver(password[len(PREFIXE):])
        if not jeton or jeton.user_id != self.env.user:
            raise AccessDenied()
        jeton.sudo().utilise_le = fields.Datetime.now()
