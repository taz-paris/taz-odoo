/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { MOCK_DATA } from "./mock/mock_data";

/**
 * Rendu générique d'une page de contenu à partir d'une entrée de
 * menu_config.js. Le "layout" choisit le gabarit visuel :
 * - table    : tableau de lignes (+ onglets optionnels)
 * - cards    : colonnes de cartes façon kanban
 * - chart    : graphique en barres (vertical ou horizontal)
 * - calendar : liste de personnes x grille de colonnes temporelles
 */
export class PageSkeleton extends Component {
    static template = "staffing.PageSkeleton";
    static props = {
        page: Object,
    };

    setup() {
        this.state = useState({ activeTab: this.props.page.tabs ? this.props.page.tabs[0] : null });
    }

    // Getter (et non une valeur figée dans setup()) : reste correct même si
    // ce composant venait à être réutilisé sans être démonté entre deux pages.
    get data() {
        return MOCK_DATA[this.props.page.mock] || {};
    }

    get maxValue() {
        const points = this.data.points || [];
        return Math.max(1, ...points.map((p) => p.value));
    }

    barHeight(value) {
        return Math.round((value / this.maxValue) * 100) + "%";
    }

    barWidth(value) {
        return Math.round((value / this.maxValue) * 100) + "%";
    }

    cardsForColumn(columnKey) {
        return (this.data.cards || []).filter((c) => c.column === columnKey);
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }
}
