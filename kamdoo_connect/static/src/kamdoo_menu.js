/** @odoo-module **/
/**
 * Kamdoo: "Connect my phone" in the user menu (hidden inside the app itself),
 * and the app-mode class when the page is opened from Kamdoo.
 */
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

const inKamdoo = /\bKamdoo\/[\d.]+/.test(browser.navigator.userAgent);
if (inKamdoo) {
    document.documentElement.classList.add("o_kamdoo_app");
}

function connectPhoneItem() {
    return {
        type: "item",
        id: "kamdoo_connect_phone",
        description: _t("Connect my phone"),
        href: "/kamdoo/qr",
        callback: () => browser.open("/kamdoo/qr", "_blank"),
        show: () => !inKamdoo,
        sequence: 45,
    };
}

registry.category("user_menuitems").add("kamdoo_connect_phone", connectPhoneItem);
