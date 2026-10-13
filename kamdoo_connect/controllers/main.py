# -*- coding: utf-8 -*-
"""What the Kamdoo app needs from this database.

* ``/kamdoo/info`` (public): who we are, before login — Odoo version and the
  company's name, colour and logo, so the app can brand its login screen.
  It reveals nothing the public login page does not already show.
* ``/kamdoo/qr`` (logged-in user): the page with the QR code that the app scans
  to add this company. The code carries the server address, the database and a
  one-time token valid five minutes — never a login or a password.
* ``/kamdoo/jumelage`` (JSON): the app exchanges that token, once, for a session
  and, from Odoo 19, an API key of its own for the JSON-2 API.
* ``/kamdoo/cle`` (logged-in user): a key for a phone signed in through the login
  page; ``/kamdoo/cle/renouveler`` (that key): a fresh one before it expires;
  ``/kamdoo/cle/revoquer`` (that key): the company is removed from the phone.
"""
import json
from urllib.parse import quote, urlencode

from odoo import fields, http, release
from odoo.exceptions import AccessDenied
from odoo.http import request
from odoo.http.session import authenticate

QR_SCHEME = "kamdoo://ajouter"


class KamdooController(http.Controller):

    def _kamdoo_company(self):
        if request.env.uid:
            return request.env.user.company_id
        return request.env["res.company"].sudo().search([], limit=1, order="sequence, id")

    @http.route("/kamdoo/info", type="http", auth="public", methods=["GET"], readonly=True, sitemap=False)
    def kamdoo_info(self, **kwargs):
        company = self._kamdoo_company()
        module = request.env["ir.module.module"].sudo().search([("name", "=", "kamdoo_connect")], limit=1)
        payload = {
            "app": "kamdoo",
            "module_version": module.latest_version or "",
            "version_odoo": list(release.version_info[:2]),
            "version_odoo_texte": release.version,
            "db": request.db,
            # The phone gets its own API key at pairing (JSON-2 API, Odoo 19+).
            "cles": True,
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
        base_url = request.env["ir.config_parameter"].sudo().get_str("web.base.url") or request.httprequest.host_url
        jeton = request.env["kamdoo.jeton"]._kamdoo_creer(request.env.user)
        params = {"url": base_url.rstrip("/"), "db": request.db, "jeton": jeton}
        return "%s?%s" % (QR_SCHEME, urlencode(params))

    @http.route("/kamdoo/jumelage", type="jsonrpc", auth="public", methods=["POST"], csrf=False, sitemap=False)
    def kamdoo_jumelage(self, jeton=None, **kwargs):
        """Exchanges a QR token for a session of the user who displayed it."""
        trouve = request.env["kamdoo.jeton"]._kamdoo_trouver(jeton)
        if not trouve:
            raise AccessDenied()
        credential = {"type": "kamdoo", "login": trouve.user_id.sudo().login, "jeton": jeton}
        # Odoo 20 : authenticate est une fonction du module odoo.http.session.
        authenticate(request.session, request.env, credential)
        uid = request.session.uid
        return {"uid": uid, **self._kamdoo_cle(request.env(user=uid), kwargs.get("appareil"))}

    def _kamdoo_cle(self, env, appareil):
        cle, expire = env["res.users.apikeys"]._kamdoo_generer(appareil)
        return {"cle": cle, "expire": fields.Datetime.to_string(expire)}

    @http.route("/kamdoo/cle", type="jsonrpc", auth="user", methods=["POST"], sitemap=False)
    def kamdoo_cle(self, appareil=None, **kwargs):
        """A key for the phone of the signed-in user (paired through the login page)."""
        return self._kamdoo_cle(request.env, appareil)

    @http.route("/kamdoo/cle/renouveler", type="jsonrpc", auth="bearer", bearer_scope="rpc", methods=["POST"], sitemap=False)
    def kamdoo_cle_renouveler(self, appareil=None, **kwargs):
        """A fresh key for the phone calling with its current one, which is revoked."""
        return self._kamdoo_cle(request.env, appareil)

    @http.route("/kamdoo/cle/revoquer", type="jsonrpc", auth="bearer", bearer_scope="rpc", methods=["POST"], sitemap=False)
    def kamdoo_cle_revoquer(self, appareil=None, **kwargs):
        """The company is removed from the phone: its key goes."""
        request.env["res.users.apikeys"]._kamdoo_revoquer(appareil)
        return True

    @http.route("/kamdoo/qr", type="http", auth="user", methods=["GET"], sitemap=False)
    def kamdoo_qr(self, **kwargs):
        link = self._kamdoo_pairing_link()
        return request.render("kamdoo_connect.page_qr", {
            "company": request.env.user.company_id,
            "link": link,
            "qr_src": "/report/barcode/?%s" % urlencode({
                "barcode_type": "QR", "value": link, "width": 360, "height": 360, "quiet": 1,
            }),
        })
