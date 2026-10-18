# -*- coding: utf-8 -*-
"""What the Kamdoo app needs from this database.

* ``/kamdoo/info`` (public): who we are, before login — Odoo version and the
  company's name, colour and logo, so the app can brand its login screen.
  It reveals nothing the public login page does not already show.
* ``/kamdoo/qr`` (logged-in user): the page with the QR code that the app scans
  to add this company. The code carries the server address, the database and a
  one-time token valid five minutes — never a login or a password.
* ``/kamdoo/jumelage`` (JSON): the app exchanges that token, once, for a session.
"""
import json
from urllib.parse import quote, urlencode

from odoo import http, release
from odoo.exceptions import AccessDenied
from odoo.http import request

QR_SCHEME = "kamdoo://ajouter"


class KamdooController(http.Controller):

    def _kamdoo_company(self):
        if request.env.uid:
            return request.env.user.company_id
        return request.env["res.company"].sudo().search([], limit=1, order="sequence, id")

    @http.route("/kamdoo/info", type="http", auth="public", methods=["GET"], sitemap=False)
    def kamdoo_info(self, **kwargs):
        company = self._kamdoo_company()
        module = request.env["ir.module.module"].sudo().search([("name", "=", "kamdoo_connect")], limit=1)
        payload = {
            "app": "kamdoo",
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

    def _kamdoo_pairing_link(self):
        base_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url") or request.httprequest.host_url
        jeton = request.env["kamdoo.jeton"]._kamdoo_creer(request.env.user)
        params = {"url": base_url.rstrip("/"), "db": request.db, "jeton": jeton}
        return "%s?%s" % (QR_SCHEME, urlencode(params))

    @http.route("/kamdoo/jumelage", type="json", auth="public", methods=["POST"], csrf=False, sitemap=False)
    def kamdoo_jumelage(self, jeton=None, **kwargs):
        """Exchanges a QR token for a session of the user who displayed it."""
        trouve = request.env["kamdoo.jeton"]._kamdoo_trouver(jeton)
        if not trouve:
            raise AccessDenied()
        from ..models.res_users import PREFIXE
        session = request.session
        session.authenticate(request.db, trouve.user_id.sudo().login, PREFIXE + jeton)
        # Le jeton vient d'une session déjà authentifiée (second facteur compris) : pas de
        # second facteur ici (Odoo 15 n'a pas le « mfa: skip » des versions suivantes).
        if not session.uid and session.pre_uid:
            session.finalize()
        return {"uid": session.uid}

    @http.route("/kamdoo/qr", type="http", auth="user", methods=["GET"], sitemap=False)
    def kamdoo_qr(self, **kwargs):
        link = self._kamdoo_pairing_link()
        return request.render("kamdoo_connect.page_qr", {
            "company": request.env.user.company_id,
            "link": link,
            "qr_src": "/report/barcode/?%s" % urlencode({
                "type": "QR", "value": link, "width": 360, "height": 360, "quiet": 1,
            }),
        })
