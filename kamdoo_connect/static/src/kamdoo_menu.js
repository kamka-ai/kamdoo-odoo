odoo.define("kamdoo_connect.menu", function () {
    "use strict";
    /**
     * Kamdoo: the app-mode class when the page is opened from Kamdoo
     * (and no "Connect my phone" inside the app itself, see kamdoo.scss).
     */
    if (/\bKamdoo\/[\d.]+/.test(window.navigator.userAgent)) {
        document.documentElement.classList.add("o_kamdoo_app");
    }
});
