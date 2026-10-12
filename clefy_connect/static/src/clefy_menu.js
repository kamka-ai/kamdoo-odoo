/** @odoo-module **/
/**
 * Clefy: "Connect my phone" in the user menu (hidden inside the app itself),
 * and the app-mode class when the page is opened from Clefy.
 */
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

const inClefy = /\bClefy\/[\d.]+/.test(browser.navigator.userAgent);
if (inClefy) {
    document.documentElement.classList.add("o_clefy_app");
}

function connectPhoneItem() {
    return {
        type: "item",
        id: "clefy_connect_phone",
        description: _t("Connect my phone"),
        href: "/clefy/qr",
        callback: () => browser.open("/clefy/qr", "_blank"),
        show: () => !inClefy,
        sequence: 45,
    };
}

registry.category("user_menuitems").add("clefy_connect_phone", connectPhoneItem);
