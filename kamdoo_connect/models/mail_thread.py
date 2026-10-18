# -*- coding: utf-8 -*-
"""Kamdoo notifications on Odoo 14, 15 and 16 (Odoo 17+ sends them itself, by Web Push).

Hooked after Odoo's own notification: whoever Odoo has just notified in their Inbox (or by email, for a
comment) gets the message on their phones too; in Discuss, every member of a private conversation, and in
a channel the people mentioned — as Odoo 17+ does. Sent once the transaction is committed.
"""
import json
import logging

import requests

from odoo import SUPERUSER_ID, api, models
from odoo.tools import html2plaintext

from ..tools.web_push import DeviceUnreachableError, push_to_end_point

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        res = super()._notify_thread(message, msg_vals=msg_vals, **kwargs)
        try:
            self._kamdoo_notifier(message)
        except Exception:  # une notification ne doit jamais empêcher un message
            _logger.exception("Kamdoo push: preparation failed")
        return res

    def _kamdoo_destinataires(self, message):
        message = message.sudo()
        auteur = message.author_id
        if self._name == "mail.channel" and len(self) == 1:
            canal = self.sudo()
            membres = canal.channel_partner_ids
            partenaires = membres if canal.channel_type != "channel" else (message.partner_ids & membres)
        else:
            types = ("inbox", "email") if message.message_type == "comment" else ("inbox",)
            partenaires = message.notification_ids.filtered(lambda n: n.notification_type in types).mapped("res_partner_id")
        # Seulement les utilisateurs internes, jamais l'auteur.
        return (partenaires - auteur).filtered(lambda p: p.user_ids and not p.partner_share)

    def _kamdoo_contenu(self, message):
        message = message.sudo()
        auteur = message.author_id.name or ""
        titre = message.record_name or message.subject or ""
        if self._name == "mail.channel" and len(self) == 1:
            canal = self.sudo()
            if canal.channel_type == "chat":
                titre = auteur
            elif canal.channel_type == "channel":
                titre = "#%s - %s" % (canal.name, auteur)
            else:
                titre = "%s - %s" % (canal.name, auteur)
        elif auteur:
            titre = "%s: %s" % (auteur, titre) if titre else auteur
        corps = html2plaintext(message.body or "").strip()
        return {
            "title": titre[:200],
            "options": {
                "icon": "/web/image/res.partner/%d/avatar_128" % message.author_id.id if message.author_id else "",
                "body": corps[:1000],
                "data": {"model": message.model or "", "res_id": message.res_id or ""},
            },
        }

    def _kamdoo_notifier(self, message):
        if message.message_type not in ("comment", "notification", "user_notification"):
            return
        destinataires = self._kamdoo_destinataires(message)
        if not destinataires:
            return
        Appareil = self.env["kamdoo.push.device"].sudo()
        appareils = Appareil.search([("partner_id", "in", destinataires.ids)])
        if not appareils:
            return
        privee, publique = Appareil._kamdoo_vapid()
        envois = [{"id": a.id, "endpoint": a.endpoint, "keys": a.keys} for a in appareils]
        contenu = json.dumps(self._kamdoo_contenu(message))
        base_url = self.get_base_url()
        dbname = self.env.cr.dbname

        def envoyer():
            injoignables = []
            with requests.Session() as session:
                for appareil in envois:
                    try:
                        push_to_end_point(base_url, appareil, contenu, privee, publique, session)
                    except DeviceUnreachableError:
                        injoignables.append(appareil["id"])
                    except Exception as e:  # le relais ne répond pas : rien de bloquant
                        _logger.warning("Kamdoo push: %s", e)
            if injoignables:
                from odoo.modules.registry import Registry
                with Registry(dbname).cursor() as cr:
                    api.Environment(cr, SUPERUSER_ID, {})["kamdoo.push.device"].browse(injoignables).exists().unlink()

        postcommit = getattr(self.env.cr, "postcommit", None)
        if postcommit is not None:
            postcommit.add(envoyer)
        else:
            envoyer()
