# Kamdoo Connect

Free, open-source Odoo module for **[Kamdoo](https://kamdoo.kamka-it.com)**, the native app that opens your company's Odoo on iPhone, iPad and Android.

Kamdoo works without it: people sign in with their usual Odoo login. Installing this module on your database adds pairing by QR code, your company's identity in the app and, on Odoo 14 to 16, notifications.

*[Version française plus bas.](#français)*

## What it adds

- **"Connect my phone"** in the user menu: a QR code the app scans. It holds a one-time token valid for five minutes, never a login or a password.
- **Your company in the app**: its name, logo and colour, read by the app before sign-in from `/kamdoo/info`. This public route returns the Odoo and module versions, the database name and the company's name, colour and logo: what the public login page already shows, nothing more.
- **Touch-friendly screens** when an Odoo page is opened from the app.
- **Odoo 14, 15 and 16: phone notifications** for private messages, mentions and the Inbox, end-to-end encrypted. These versions have no Web Push; the module adds it the way Odoo 17 does (RFC 8291 encryption, RFC 8292 VAPID signature). If the `cryptography` package is missing, as in the official Odoo 14 image, a pure-Python implementation of the same algorithms is used.
- **Odoo 19 and 20: a key for each phone.** The app talks to the JSON-2 API with an API key of its own instead of a browser session. The key is named after the phone ("Kamdoo · Karim's iPhone"), expires after the duration set in Settings (30 days by default), is renewed by the app before then, and can be revoked like any API key in Preferences › Account Security.

## One branch per Odoo version

| Branch | Odoo | Notifications | Phone API key |
|---|---|---|---|
| `14.0`, `15.0`, `16.0` | 14 to 16 | added by this module | no |
| `17.0`, `18.0` | 17 and 18 | native in Odoo | no |
| `19.0`, `20.0` | 19 and 20 | native in Odoo | yes |

## Install

1. Take the branch matching your Odoo version and copy the `kamdoo_connect` folder into your addons path.
2. Update the Apps list, then install **Kamdoo – Mobile app for your company**.
3. In the app, users open the user menu › **Connect my phone** and scan the QR code.

Odoo 14 to 16 need the Python `requests` package, present in the official images.

## Privacy

The app talks directly to your Odoo; Kamka IT receives none of your data. Notifications are the only exception: your Odoo encrypts each one for the phone it is meant for, then sends it through the Kamdoo relay to Apple or Google. The relay cannot read them and keeps none of them. Its code is public: **[kamka-ai/kamdoo-relais](https://github.com/kamka-ai/kamdoo-relais)**. Full details: [privacy policy](https://kamdoo.kamka-it.com/privacy.html).

## Tests

```
odoo -d <database> -i kamdoo_connect --test-enable --stop-after-init
```

## License

[LGPL-3](LICENSE). Published by [Kamka IT](https://kamka-it.com) · contact@kamka-it.com

---

## Français

Module Odoo gratuit et libre pour **[Kamdoo](https://kamdoo.kamka-it.com)**, l'app native qui ouvre l'Odoo de votre société sur iPhone, iPad et Android.

Kamdoo fonctionne sans lui : on se connecte avec ses identifiants Odoo habituels. Installé sur votre base, ce module ajoute le jumelage par QR code, l'identité de votre société dans l'app et, sur Odoo 14 à 16, les notifications.

### Ce qu'il ajoute

- **« Connecter mon téléphone »** dans le menu de l'utilisateur : un QR code que l'app scanne. Il contient un jeton à usage unique, valable cinq minutes, jamais un identifiant ni un mot de passe.
- **Votre société dans l'app** : son nom, son logo et sa couleur, lus par l'app avant la connexion sur `/kamdoo/info`. Cette route publique renvoie les versions d'Odoo et du module, le nom de la base, et le nom, la couleur et le logo de la société : ce que montre déjà la page de connexion publique, rien de plus.
- **Des écrans adaptés au toucher** quand une page d'Odoo est ouverte depuis l'app.
- **Odoo 14, 15 et 16 : les notifications sur le téléphone** pour les messages privés, les mentions et la boîte de réception, chiffrées de bout en bout. Ces versions n'ont pas de Web Push : le module l'ajoute comme le fait Odoo 17 (chiffrement RFC 8291, signature VAPID RFC 8292). Si le paquet `cryptography` manque, comme dans l'image officielle d'Odoo 14, une version en Python pur des mêmes algorithmes prend le relais.
- **Odoo 19 et 20 : une clé par téléphone.** L'app parle à l'API JSON-2 avec une clé d'API à elle, plutôt qu'avec une session de navigateur. La clé porte le nom du téléphone (« Kamdoo · iPhone de Karim »), expire après la durée choisie dans les Paramètres (30 jours par défaut), est renouvelée par l'app avant l'échéance, et se révoque comme toute clé d'API dans Préférences › Sécurité du compte.

### Une branche par version d'Odoo

| Branche | Odoo | Notifications | Clé d'API du téléphone |
|---|---|---|---|
| `14.0`, `15.0`, `16.0` | 14 à 16 | ajoutées par ce module | non |
| `17.0`, `18.0` | 17 et 18 | natives dans Odoo | non |
| `19.0`, `20.0` | 19 et 20 | natives dans Odoo | oui |

### Installation

1. Prenez la branche de votre version d'Odoo et copiez le dossier `kamdoo_connect` dans votre chemin d'addons.
2. Mettez à jour la liste des Applications, puis installez **Kamdoo – Mobile app for your company**.
3. Dans l'app, chacun ouvre le menu de l'utilisateur › **Connecter mon téléphone** et scanne le QR code.

Odoo 14 à 16 ont besoin du paquet Python `requests`, présent dans les images officielles.

### Confidentialité

L'app parle directement à votre Odoo : Kamka IT ne reçoit aucune de vos données. Seule exception, les notifications : votre Odoo chiffre chacune pour le téléphone à qui elle est destinée, puis l'envoie par le relais de Kamdoo à Apple ou Google. Le relais ne peut pas les lire et n'en garde rien. Son code est public : **[kamka-ai/kamdoo-relais](https://github.com/kamka-ai/kamdoo-relais)**. Tout le détail : [politique de confidentialité](https://kamdoo.kamka-it.com/confidentialite.html).

### Licence

[LGPL-3](LICENSE). Édité par [Kamka IT](https://kamka-it.com) · contact@kamka-it.com
