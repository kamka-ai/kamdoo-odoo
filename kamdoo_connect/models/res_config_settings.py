# -*- coding: utf-8 -*-
from odoo import fields, models

from .res_users_apikeys import DUREE_DEFAUT, PARAM_DUREE


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    kamdoo_duree_cle = fields.Integer(
        string="Phone key duration (days)",
        config_parameter=PARAM_DUREE,
        default=DUREE_DEFAUT,
        help="How long the key given to a paired phone stays valid. The app renews it "
             "before it expires; revoking it in the user's preferences disconnects the phone.",
    )
