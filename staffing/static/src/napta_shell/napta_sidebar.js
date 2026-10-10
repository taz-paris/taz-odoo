/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { NAPTA_MENU } from "./menu_config";

export class NaptaSidebar extends Component {
    static template = "staffing.NaptaSidebar";
    static props = {
        activeKey: String,
        onSelect: Function,
    };

    setup() {
        this.menu = NAPTA_MENU;
        // Groupe contenant la page active déplié par défaut.
        const initialOpen = {};
        for (const group of this.menu) {
            if (group.items && group.items.some((it) => it.key === this.props.activeKey)) {
                initialOpen[group.key] = true;
            }
        }
        this.state = useState({ open: initialOpen });
    }

    toggleGroup(group) {
        this.state.open[group.key] = !this.state.open[group.key];
    }

    isGroupOpen(group) {
        return !!this.state.open[group.key];
    }

    isGroupActive(group) {
        if (group.page) {
            return group.page.key === this.props.activeKey;
        }
        if (group.items) {
            return group.items.some((it) => it.key === this.props.activeKey);
        }
        return false;
    }

    onClickGroup(group) {
        if (group.inert) {
            return;
        }
        if (group.page) {
            this.props.onSelect(group.page.key);
        } else if (group.items) {
            this.toggleGroup(group);
        }
    }

    onClickItem(item) {
        this.props.onSelect(item.key);
    }
}
