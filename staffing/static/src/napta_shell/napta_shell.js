/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { router } from "@web/core/browser/router";
import { NaptaSidebar } from "./napta_sidebar";
import { buildPageIndex } from "./menu_config";
import { PAGE_COMPONENTS } from "./pages/registry";

const DEFAULT_PAGE_KEY = "staffing.projects";

export class NaptaShell extends Component {
    static template = "staffing.NaptaShell";
    static props = { "*": true };
    static components = { NaptaSidebar };

    setup() {
        this.pageIndex = buildPageIndex();
        const fromUrl = router.current.napta_page;
        const initialKey = fromUrl && this.pageIndex[fromUrl] ? fromUrl : DEFAULT_PAGE_KEY;
        this.state = useState({ activeKey: initialKey });
        router.pushState({ napta_page: initialKey });
    }

    get activePage() {
        return this.pageIndex[this.state.activeKey];
    }

    // Composant dédié pixel-perfect de la page active. Chaque entrée de
    // menu_config.js DOIT avoir une entrée correspondante dans
    // pages/registry.js — il n'y a plus de squelette générique de repli :
    // toute nouvelle page de menu doit venir avec son propre composant.
    get activeComponent() {
        return PAGE_COMPONENTS[this.state.activeKey];
    }

    onSelect(key) {
        if (!this.pageIndex[key]) {
            return;
        }
        this.state.activeKey = key;
        router.pushState({ napta_page: key });
    }
}

registry.category("actions").add("staffing.napta_shell_action", NaptaShell);
