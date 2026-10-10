/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Données factices pour le rapport "Suivi du consommé" (reporting/individual_timesheet
 * chez Napta) : comparaison entre la charge planifiée (affectations) et la charge
 * réellement saisie (feuilles de temps), par collaborateur et par période.
 */
const PERIODS = [
    { key: "s27", label: "S27", range: "DU 01/07 AU 06/07" },
    { key: "s28", label: "S28", range: "DU 07/07 AU 13/07" },
    { key: "s29", label: "S29", range: "DU 14/07 AU 20/07" },
    { key: "s30", label: "S30", range: "DU 21/07 AU 27/07" },
    { key: "s31", label: "S31", range: "DU 28/07 AU 03/08" },
];

const MOCK_ROWS = [
    {
        key: "ameri",
        name: "AMERI Armand",
        role: "Manager - Change Management - Paris",
        initials: "AA",
        values: {
            s27: { planned: "17.92h", actual: "32h" },
            s28: { planned: "27.38h", actual: "40h" },
            s29: { planned: "29.91h", actual: "48h" },
            s30: { planned: "4.21h", actual: "40h" },
            s31: { planned: "25.07h", actual: "25.07h" },
        },
        details: [],
    },
    {
        key: "bartol",
        name: "BARTOL Jeremy",
        role: "Director - Data & Analytics - Paris",
        initials: "JB",
        values: {
            s27: { planned: "24.71h", actual: "25.6h" },
            s28: { planned: "30.88h", actual: "32h" },
            s29: { planned: "36.71h", actual: "44h" },
            s30: { planned: "34.88h", actual: "36h" },
            s31: { planned: "34.88h", actual: "40h" },
        },
        details: [
            {
                label: "AIRCALL — Data Audit",
                values: {
                    s27: { planned: "24.71h", actual: "25.6h" },
                    s28: { planned: "30.88h", actual: "32h" },
                    s29: { planned: "24.71h", actual: "32h" },
                    s30: { planned: "30.88h", actual: "32h" },
                    s31: { planned: "30.88h", actual: "32h" },
                },
            },
            {
                label: "CISCO — Tax Optimization",
                values: {
                    s27: { planned: "", actual: "" },
                    s28: { planned: "", actual: "" },
                    s29: { planned: "", actual: "" },
                    s30: { planned: "", actual: "" },
                    s31: { planned: "", actual: "" },
                },
            },
            {
                label: "Congé utilisateur",
                values: {
                    s27: { planned: "", actual: "" },
                    s28: { planned: "", actual: "" },
                    s29: { planned: "8h", actual: "8h" },
                    s30: { planned: "", actual: "" },
                    s31: { planned: "", actual: "" },
                },
            },
        ],
    },
    {
        key: "bartoli",
        name: "BARTOLI Nour",
        role: "Senior - Data & Analytics - London",
        initials: "NB",
        values: {
            s27: { planned: "16h", actual: "16h" },
            s28: { planned: "20h", actual: "20h" },
            s29: { planned: "24h", actual: "24h" },
            s30: { planned: "24h", actual: "24h" },
            s31: { planned: "24h", actual: "24h" },
        },
        details: [],
    },
    {
        key: "berarda",
        name: "BERARDA Katharina",
        role: "Manager - Change Management - Paris",
        initials: "KB",
        values: {
            s27: { planned: "31.11h", actual: "25.6h" },
            s28: { planned: "32h", actual: "40h" },
            s29: { planned: "48h", actual: "48h" },
            s30: { planned: "34h", actual: "40h" },
            s31: { planned: "34h", actual: "40h" },
        },
        details: [],
    },
    {
        key: "berger",
        name: "BERGER Claire",
        role: "Senior - Data & Analytics - London",
        initials: "CB",
        values: {
            s27: { planned: "31.2h", actual: "32h" },
            s28: { planned: "39h", actual: "37.6h" },
            s29: { planned: "37h", actual: "40h" },
            s30: { planned: "39h", actual: "40h" },
            s31: { planned: "39h", actual: "40h" },
        },
        details: [],
    },
];

/** Compare la charge planifiée et la charge réelle pour déterminer le code couleur. */
function matchStatus(cell) {
    if (!cell || !cell.planned || !cell.actual) {
        return "";
    }
    const planned = parseFloat(cell.planned);
    const actual = parseFloat(cell.actual);
    if (Number.isNaN(planned) || Number.isNaN(actual)) {
        return "";
    }
    if (planned === actual) {
        return "o_napta_sc_match";
    }
    return planned > actual ? "o_napta_sc_over" : "o_napta_sc_under";
}

export class ReportsSuiviConsommePage extends Component {
    static template = "staffing.ReportsSuiviConsommePage";
    static props = {
        page: { type: Object, optional: true },
    };

    setup() {
        this.periods = PERIODS;
        this.state = useState({
            expanded: {},
            display: "hour",
            groupBy: "week",
            dateFrom: "01/07/25",
            dateTo: "31/10/25",
            page: 1,
        });
        this.legendTooltip =
            "Vert : la charge planifiée = la charge de la feuille de temps. " +
            "Orange : la charge planifiée > la charge de la feuille de temps. " +
            "Rouge : la charge planifiée < la charge de la feuille de temps.";
    }

    get rows() {
        return MOCK_ROWS;
    }

    toggleRow(key) {
        this.state.expanded[key] = !this.state.expanded[key];
    }

    isExpanded(key) {
        return !!this.state.expanded[key];
    }

    statusClass(cell) {
        return matchStatus(cell);
    }

    setDisplay(value) {
        this.state.display = value;
    }

    setGroupBy(value) {
        this.state.groupBy = value;
    }
}
