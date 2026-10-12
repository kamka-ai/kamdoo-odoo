# -*- coding: utf-8 -*-
"""What the Clefy app needs from this database.

* ``/clefy/info`` (public): who we are, before login — Odoo version and the
  company's name, colour and logo, so the app can brand its login screen.
  It reveals nothing the public login page does not already show.
* ``/clefy/qr`` (logged-in user): the page with the QR code that the app scans
  to add this company. The code carries the server address, the database and
  the user's login — never a password or a token.
"""
import json
from urllib.parse import quote, urlencode

from odoo import http, release
from odoo.http import request

QR_SCHEME = "clefy://ajouter"


class ClefyController(http.Controller):

    def _clefy_company(self):
        if request.env.uid:
            return request.env.user.company_id
        return request.env["res.company"].sudo().search([], limit=1, order="sequence, id")

    @http.route("/clefy/info", type="http", auth="public", methods=["GET"], readonly=True, sitemap=False)
    def clefy_info(self, **kwargs):
        company = self._clefy_company()
        module = request.env["ir.module.module"].sudo().search([("name", "=", "clefy_connect")], limit=1)
        payload = {
            "app": "clefy",
            "module_version": module.latest_version or "",
            "version_odoo": list(release.version_info[:2]),
            "version_odoo_texte": release.version,
            "db": request.db,
            "societe": {
                "nom": company.name,
                "couleur": company.primary_color or "",
                "logo": "/web/binary/company_logo?dbname=%s&company=%s" % (quote(request.db or ""), company.id),
            } if company else None,
        }
        return request.make_response(
            json.dumps(payload),
            headers=[("Content-Type", "application/json"), ("Cache-Control", "no-store")],
        )

    def _clefy_pairing_link(self):
        base_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url") or request.httprequest.host_url
        params = {"url": base_url.rstrip("/"), "db": request.db, "login": request.env.user.login}
        return "%s?%s" % (QR_SCHEME, urlencode(params))

    @http.route("/clefy/qr", type="http", auth="user", methods=["GET"], sitemap=False)
    def clefy_qr(self, **kwargs):
        link = self._clefy_pairing_link()
        return request.render("clefy_connect.page_qr", {
            "company": request.env.user.company_id,
            "link": link,
            "qr_src": "/report/barcode/?%s" % urlencode({
                "barcode_type": "QR", "value": link, "width": 360, "height": 360, "quiet": 1,
            }),
        })
