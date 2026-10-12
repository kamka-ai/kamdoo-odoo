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

* "Connect my phone" in the user menu: a QR code that the app scans;
* your company's name, logo and colour shown in the app;
* screens adapted to touch when opened from the app.
""",
    "version": "18.0.1.0.1",
    "author": "Kamka IT",
    "website": "https://kamka-it.com",
    "license": "LGPL-3",
    "category": "Productivity",
    "depends": ["web", "base_setup"],
    "data": [
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
