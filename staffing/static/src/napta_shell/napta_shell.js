/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { router } from "@web/core/browser/router";
import { NaptaSidebar } from "./napta_sidebar";
import { PageSkeleton } from "./page_skeleton";
import { buildPageIndex } from "./menu_config";
import { PAGE_COMPONENTS } from "./pages/registry";

const DEFAULT_PAGE_KEY = "staffing.projects";

export class NaptaShell extends Component {
    static template = "staffing.NaptaShell";
    static props = { "*": true };
    static components = { NaptaSidebar, PageSkeleton };

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

    // Composant dédié pixel-perfect s'il existe pour cette page, sinon
    // repli sur le squelette générique (PageSkeleton).
    get activeComponent() {
        return PAGE_COMPONENTS[this.state.activeKey] || PageSkeleton;
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
