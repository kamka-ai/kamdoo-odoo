# -*- coding: utf-8 -*-
{
    "name": "Kamdoo Mobile Connector",
    "summary": "Pair the Kamdoo mobile app with this database by QR code, and show your "
               "company's name, logo and colour in the app.",
    "description": """
Server side of Kamdoo, a free native mobile app for Odoo installed separately on
each phone. The app also works without this module, with the usual Odoo login.

This free module adds:

* "Connect my phone" in the user menu: a QR code that the app scans. It holds a
  one-time token valid five minutes, never a login or a password;
* your company's name, logo and colour shown in the app;
* screens adapted to touch when opened from the app;
* notifications on the phone (private messages, mentions, Inbox), end-to-end encrypted:
  Odoo 16 has no Web Push, this module adds it the way Odoo 17 does it.

External service: notifications. This module encrypts each notification
for the phone it is meant for and sends it to the Kamdoo relay (run by Kamka IT),
which forwards it to Apple or Google. The relay cannot read it and keeps nothing.
Nothing is sent unless a user paired a phone and allowed notifications on it.
Business data never goes through Kamka IT: the app talks directly to Odoo.
""",
    "version": "16.0.1.2.1",
    "author": "Kamka IT",
    "website": "https://kamka-it.com",
    "license": "LGPL-3",
    "category": "Productivity",
    "images": ["static/description/banner.png"],
    "depends": ["web", "base_setup", "mail"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/ir.model.access.csv",
        "views/templates.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "kamdoo_connect/static/src/kamdoo.scss",
            "kamdoo_connect/static/src/kamdoo_menu.js",
        ],
        "web.assets_frontend": [
            "kamdoo_connect/static/src/kamdoo_frontend.scss",
        ],
    },
    "installable": True,
    "application": False,
}
