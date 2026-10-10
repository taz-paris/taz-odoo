/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Données factices : évolution hebdomadaire du taux d'occupation
 * (Staffing réel / simulé et Imputations), voir doc Napta
 * "Occupation globale".
 */
const WEEKS = [
    { label: "S26 2023", reel: null, simule: null, imputation: null },
    { label: "S27 2023", reel: 42, simule: 0, imputation: 44 },
    { label: "S28 2023", reel: 64, simule: 0, imputation: 67 },
    { label: "S29 2023", reel: 63, simule: 0, imputation: 66 },
    { label: "S30 2023", reel: 65, simule: 0, imputation: 64 },
    { label: "S31 2023", reel: 74, simule: 0, imputation: 73 },
    { label: "S32 2023", reel: 76, simule: 0, imputation: 30 },
    { label: "S33 2023", reel: 68, simule: 2, imputation: null },
    { label: "S34 2023", reel: 62, simule: 21, imputation: null },
    { label: "S35 2023", reel: 63, simule: 26, imputation: null },
    { label: "S36 2023", reel: 42, simule: 34, imputation: null },
    { label: "S37 2023", reel: 35, simule: 33, imputation: null },
    { label: "S38 2023", reel: 25, simule: 28, imputation: null },
    { label: "S39 2023", reel: 21, simule: 28, imputation: null },
];

const TABLE_ROWS = [
    { department: "Management des organisations", position: "Consultant Junior", color: "#9b87d6", values: [69, 63, 28, 34] },
    { department: "Data & Analytics", position: "Consultant Junior", color: "#e8b979", values: [102, 80, 39, 48] },
    { department: "Management des organisations", position: "Consultant Senior", color: "#9fb6e0", values: [49, 52, 29, 24] },
    { department: "Data & Analytics", position: "Consultant Senior", color: "#8fc7a8", values: [88, 79, 29, 14] },
];
const TABLE_MONTHS = ["Juillet 2023", "Août 2023", "Septembre 2023", "Octobre 2023"];

export class ReportsOccupationGlobalePage extends Component {
    static template = "staffing.ReportsOccupationGlobalePage";
    static props = { page: Object };

    setup() {
        this.weeks = WEEKS;
        this.tableRows = TABLE_ROWS;
        this.tableMonths = TABLE_MONTHS;
        this.state = useState({
            activeView: "Graphique",
            settingsOpen: false,
            showAverage: false,
        });

        this.infoTooltip =
            "Les taux affichés sur ce reporting sont des TACE (Taux d'activité congés exclus) = jours staffés / [jours ouvrés - congés].";
        this.cameraTooltip =
            "Prendre une photo du reporting affiché pour pouvoir le comparer à une autre période.";
    }

    setView(view) {
        this.state.activeView = view;
    }

    toggleSettings() {
        this.state.settingsOpen = !this.state.settingsOpen;
    }

    toggleAverage() {
        this.state.showAverage = !this.state.showAverage;
    }

    barHeight(value) {
        if (value === null || value === undefined) {
            return "0%";
        }
        return Math.min(100, value) + "%";
    }
}
