# -*- coding: utf-8 -*-
"""One-time pairing tokens for the Kamdoo app.

The QR code shown by ``/kamdoo/qr`` carries the server address, the database and
a random token — never a login or a password. The app exchanges the token once
for a session (``/kamdoo/jumelage``). Only a hash is stored; a token is valid
five minutes, works once, and showing a new QR code revokes the previous one.
Sessions opened this way are listed and revocable like any other in the user's
Preferences › Account Security › Devices.
"""
import hashlib
import secrets
from datetime import timedelta

from odoo import api, fields, models

DUREE = timedelta(minutes=5)


def empreinte(jeton):
    return hashlib.sha256(jeton.encode()).hexdigest()


class KamdooJeton(models.Model):
    _name = "kamdoo.jeton"
    _description = "Kamdoo pairing token"
    _log_access = False

    user_id = fields.Many2one("res.users", required=True, ondelete="cascade", index=True)
    empreinte = fields.Char(required=True, index=True)
    expire_le = fields.Datetime(required=True)
    utilise_le = fields.Datetime()

    @api.model
    def _kamdoo_creer(self, user):
        """A fresh token for ``user``; its pending ones (and every expired one) are dropped."""
        maintenant = fields.Datetime.now()
        self.sudo().search(["|", ("expire_le", "<", maintenant), "&", ("user_id", "=", user.id), ("utilise_le", "=", False)]).unlink()
        jeton = secrets.token_urlsafe(32)
        self.sudo().create({"user_id": user.id, "empreinte": empreinte(jeton), "expire_le": maintenant + DUREE})
        return jeton

    @api.model
    def _kamdoo_trouver(self, jeton):
        """The valid, unused token record for ``jeton`` (empty if none)."""
        if not jeton or not isinstance(jeton, str):
            return self.browse()
        return self.sudo().search([
            ("empreinte", "=", empreinte(jeton)),
            ("utilise_le", "=", False),
            ("expire_le", ">", fields.Datetime.now()),
        ], limit=1)
