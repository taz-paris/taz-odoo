/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { buildPageIndex } from "./menu_config";
import { PAGE_COMPONENTS } from "./pages/registry";

const DEFAULT_PAGE_KEY = "staffing.projects";

// Monte directement la page ciblée par l'action cliente qui a déclenché ce
// composant : chaque entrée du menu Odoo "Napta UI" (voir
// views/napta_shell_menus.xml) est une ir.actions.client distincte dont les
// params contiennent {'napta_page': '<clé>'}. Il n'y a plus de sidebar
// maison ni de routage interne : la navigation entre pages est assurée par
// les vrais menus Odoo, un clic = une nouvelle action = une nouvelle
// instance de ce composant.
export class NaptaShell extends Component {
    static template = "staffing.NaptaShell";
    static props = { "*": true };

    setup() {
        const pageIndex = buildPageIndex();
        const key = this.props.action?.params?.napta_page || DEFAULT_PAGE_KEY;
        this.activePage = pageIndex[key];
        this.ActiveComponent = PAGE_COMPONENTS[key];
    }
}

registry.category("actions").add("staffing.napta_shell_action", NaptaShell);
