# -*- coding: utf-8 -*-
{
    "name": "Kamdoo – Mobile app for your company",
    "summary": "Connect the Kamdoo iOS and Android app to this database: QR code "
               "pairing, your company's name, logo and colours in the app, and "
               "screens adapted to touch.",
    "description": """
Kamdoo opens your company's ERP on iPhone, iPad and Android: native tab bar,
your day's activities, all your apps (custom modules included), quick
creation, search, and the Discuss messages.

This free module adds:

* "Connect my phone" in the user menu: a QR code that the app scans. It holds a
  one-time token valid five minutes, never a login or a password;
* your company's name, logo and colour shown in the app;
* screens adapted to touch when opened from the app;
* notifications on the phone (private messages, mentions, Inbox), end-to-end encrypted: Odoo 14 has no
  Web Push, this module adds it the way Odoo 17 does it.
""",
    "version": "14.0.1.2.0",
    "author": "Kamka IT",
    "website": "https://kamka-it.com",
    "license": "LGPL-3",
    "category": "Productivity",
    "depends": ["web", "base_setup", "mail"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/ir.model.access.csv",
        "views/templates.xml",
        "views/res_config_settings_views.xml",
        "views/assets.xml",
    ],
    "qweb": ["static/src/xml/kamdoo_menu.xml"],
    "installable": True,
    "application": False,
}
