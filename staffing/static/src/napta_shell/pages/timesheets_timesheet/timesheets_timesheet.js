/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Données factices LOCALES à cette page (volontairement non partagées avec
 * mock/mock_data.js pour éviter tout conflit avec d'autres pages en cours
 * de développement en parallèle).
 *
 * Reproduit la page Napta "Feuilles de temps" (vues Personnelle / Équipe)
 * telle que documentée dans :
 *  - modules-napta/feuilles-de-temps_feuilles-de-temps
 *  - modules-napta/feuilles-de-temps_vue-personnelle
 *  - modules-napta/feuilles-de-temps_vue-equipe
 */

// Statuts de validation d'une semaine (voir "Flux de validation" dans la doc).
const STATUS_LEGEND = [
    { key: "forecast", label: "Prévisionnel", tooltip: "Donnée prévisionnelle issue du staffing, non encore saisie par l'employé." },
    { key: "to_complete", label: "À compléter", tooltip: "Semaine non encore créée / saisie par l'employé. N'apparaît pas dans les rapports." },
    { key: "saved", label: "Sauvegardé", tooltip: "Semaine enregistrée par l'employé mais pas encore soumise pour approbation." },
    { key: "pending", label: "En attente d'approbation", tooltip: "Semaine soumise par l'employé, en attente de validation par un manager." },
    { key: "approved", label: "Approuvé", tooltip: "Semaine validée. L'employé ne peut plus la modifier depuis la vue Personnelle." },
];
const MOVEMENT_TOOLTIP = "La valeur saisie diffère de la donnée prévisionnelle issue du staffing.";

const PERSONAL_WEEKS = [
    { key: "W05", label: "W05", range: "DU 1 AU 4 FÉV", info: "Semaine tronquée : elle chevauche janvier et février, seule la partie de février est affichée." },
    { key: "W06", label: "W06", range: "DU 5 AU 11 FÉV" },
    { key: "W07", label: "W07", range: "DU 12 AU 18 FÉV" },
    { key: "W08", label: "W08", range: "DU 19 AU 25 FÉV", info: "Semaine tronquée : elle chevauche février et mars, seule la partie de février est affichée." },
    { key: "W09", label: "W09", range: "DU 26 AU 29 FÉV" },
];

/**
 * Valeurs numériques brutes (sans suffixe "d") : la vue Personnelle est
 * rendue éditable (voir onCellInput) et recalcule le total de la ligne en
 * direct. Seules les cellules au statut "approved" restent en lecture
 * seule, conformément à la doc : « Une fois la semaine approuvée, il n'est
 * plus possible pour l'employé de modifier la saisie depuis la vue
 * Personnelle. » Rien n'est persisté : l'état ne vit que dans le composant.
 */
function buildPersonalRows() {
    return [
        {
            key: "bnp",
            project: "BNP Paribas — Déploiement Salesforce",
            removable: false,
            cells: [
                { value: "1.33", status: "approved", movement: "down", movementValue: "1d" },
                { value: "1.67", status: "approved", movement: "up", movementValue: "3d" },
                { value: "4", status: "pending", movement: "down", movementValue: "2.5d" },
                { value: "2.5", status: "saved", movement: null },
                { value: "3.33", status: "to_complete", movement: null },
            ],
        },
        {
            key: "backmarket",
            project: "BackMarket — Refonte stratégie d'acquisition",
            removable: true,
            cells: [
                { value: "0", status: "approved", movement: null },
                { value: "0", status: "approved", movement: null },
                { value: "0", status: "pending", movement: null },
                { value: "0", status: "saved", movement: null },
                { value: "0", status: "to_complete", movement: null },
            ],
        },
    ];
}

const PERSONAL_AVAILABILITY = ["1d", "2d", "2.5d", "2.5d", "0.67d"];
const PERSONAL_AVAILABILITY_TOTAL = "8.67d";

const PERSONAL_WEEK_STATUS = [
    { label: "Validée", icon: "fa-lock", locked: true },
    { label: "Validée", icon: "fa-lock", locked: true },
    { label: "En attente", icon: "fa-hourglass-half", locked: false },
    { label: null, icon: null, locked: false },
    { label: null, icon: null, locked: false },
];

// --- Vue Équipe --------------------------------------------------------

function gauge(real, planned, sold, color) {
    const ratio = planned > 0 ? Math.min(1, real / planned) : 0;
    return {
        real,
        planned,
        sold,
        percent: Math.round(ratio * 100),
        color, // "blue" | "orange" | "green" | "red"
        tooltip: `Réel : ${real}d\nPlanifié : ${planned}d\nVendu : ${sold}d`,
    };
}

const TEAM_DAYS = [
    { key: "mon", label: "LUNDI", date: "01/06/26" },
    { key: "tue", label: "MARDI", date: "02/06/26" },
    { key: "wed", label: "MERCREDI", date: "03/06/26" },
    { key: "thu", label: "JEUDI", date: "04/06/26" },
    { key: "fri", label: "VENDREDI", date: "05/06/26" },
    { key: "sat", label: "SAMEDI", date: "06/06/26" },
    { key: "sun", label: "DIMANCHE", date: "07/06/26" },
];

const TEAM_PEOPLE = [
    {
        id: 1,
        name: "AMERI Armand",
        totalByDay: ["1d", "1d", "1d", "1d", "1d", "0d", "0d"],
        total: "5d",
        projects: [
            {
                name: "AIRCALL — Data Audit",
                gauge: gauge(26, 39.51, 26, "blue"),
                values: ["0.4d", "0.4d", "0.4d", "0.4d", "0.4d", "0d", "0d"],
                total: "2d",
            },
            {
                name: "APPLE — Acquisition Strategy Redesign",
                gauge: gauge(2, 0, 0, "orange"),
                gaugeNote: "Aucune affectation",
                values: ["0.4d", "0.4d", "0.4d", "0.4d", "0.4d", "0d", "0d"],
                total: "2d",
            },
            {
                name: "INTERNAL — Deployment Process Improvement",
                gauge: gauge(5.85, 16.4, 5.85, "blue"),
                values: ["0.2d", "0.2d", "0.2d", "0.2d", "0.2d", "0d", "0d"],
                total: "1d",
            },
        ],
        availability: ["0d", "0d", "0d", "0d", "0d", "0d", "0d"],
        availabilityTotal: "0d",
    },
    {
        id: 2,
        name: "BARTOL Jeremy",
        totalByDay: ["1d", "1d", "1d", "1d", "1d", "0d", "0d"],
        total: "5d",
        projects: [
            {
                name: "AIRCALL — Data Audit",
                gauge: gauge(40, 45.75, 40, "blue"),
                values: ["0.8d", "0.8d", "0.8d", "0.8d", "0.8d", "0d", "0d"],
                total: "4d",
            },
            {
                name: "INTERNAL — Deployment Process Improvement",
                gauge: gauge(2, 2, 2, "green"),
                values: ["0.2d", "0.2d", "0.2d", "0.2d", "0.2d", "0d", "0d"],
                total: "1d",
            },
        ],
        availability: ["0d", "0d", "0d", "0d", "0d", "0d", "0d"],
        availabilityTotal: "0d",
    },
    {
        id: 3,
        name: "CHEN John",
        totalByDay: ["1d", "1d", "1d", "1d", "1d", "0d", "0d"],
        total: "5d",
        projects: [
            {
                name: "INTERNAL — HR Process Improvement",
                gauge: gauge(11, 8.92, 11, "red"),
                values: ["0.4d", "0.4d", "0.4d", "0.4d", "0.4d", "0d", "0d"],
                total: "2d",
            },
            {
                name: "AIRCALL — Data Audit",
                gauge: gauge(8, 27.2, 8, "blue"),
                values: ["0.6d", "0.6d", "0.6d", "0.6d", "0.6d", "0d", "0d"],
                total: "3d",
            },
        ],
        availability: ["0d", "0d", "0d", "0d", "0d", "0d", "0d"],
        availabilityTotal: "0d",
    },
];

export class TimesheetsTimesheetPage extends Component {
    static template = "staffing.TimesheetsTimesheetPage";
    static props = { page: Object };

    setup() {
        this.statusLegend = STATUS_LEGEND;
        this.movementTooltip = MOVEMENT_TOOLTIP;

        this.personalWeeks = PERSONAL_WEEKS;
        this.personalAvailability = PERSONAL_AVAILABILITY;
        this.personalAvailabilityTotal = PERSONAL_AVAILABILITY_TOTAL;
        this.personalWeekStatus = PERSONAL_WEEK_STATUS;

        this.teamDays = TEAM_DAYS;

        this.state = useState({
            tab: "personal", // "personal" | "team"
            expanded: { 1: true, 2: true, 3: true },
            allExpanded: true,
            selected: {},
            team: TEAM_PEOPLE,
            personalRows: buildPersonalRows(),
        });

        this.availabilityTooltip =
            "Disponibilité = Heures/Jours travaillés - Jours fériés - Congés - Charge imputée. " +
            "Ne peut pas être négative.";
    }

    setTab(tab) {
        this.state.tab = tab;
    }

    // ---- Vue Personnelle (éditable, rien n'est persisté) ----
    cellClass(cell) {
        return "o_napta_ts_cell o_napta_ts_status_" + cell.status;
    }

    /** Une cellule n'est plus modifiable une fois la semaine approuvée. */
    isCellLocked(cell) {
        return cell.status === "approved";
    }

    onCellInput(cell, ev) {
        cell.value = ev.target.value;
        // Saisir une valeur dans une semaine "à compléter" la fait vivre
        // visuellement : elle passe à "Sauvegardé", comme le ferait un
        // clic sur "Enregistrer" dans Napta.
        if (cell.status === "to_complete" && parseFloat(cell.value) > 0) {
            cell.status = "saved";
        }
    }

    rowTotal(row) {
        const sum = row.cells.reduce((acc, c) => acc + (parseFloat(c.value) || 0), 0);
        return this.formatDays(sum);
    }

    formatDays(n) {
        const rounded = Math.round(n * 100) / 100;
        return (Number.isInteger(rounded) ? String(rounded) : String(rounded)) + "d";
    }

    /** « L'icône de suppression est affichée uniquement sur les lignes de projet ne contenant aucune saisie de temps. » */
    isRowEmpty(row) {
        return row.cells.every((c) => !(parseFloat(c.value) > 0));
    }

    removeProjectRow(row, ev) {
        if (ev) ev.stopPropagation();
        if (!this.isRowEmpty(row)) {
            return;
        }
        this.state.personalRows = this.state.personalRows.filter((r) => r.key !== row.key);
    }

    // ---- Vue Équipe ----
    toggleExpand(person) {
        this.state.expanded[person.id] = !this.state.expanded[person.id];
    }

    isExpanded(person) {
        return !!this.state.expanded[person.id];
    }

    toggleExpandAll() {
        this.state.allExpanded = !this.state.allExpanded;
        for (const person of this.state.team) {
            this.state.expanded[person.id] = this.state.allExpanded;
        }
    }

    toggleSelect(person, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        this.state.selected[person.id] = !this.state.selected[person.id];
    }

    isSelected(person) {
        return !!this.state.selected[person.id];
    }

    get selectedCount() {
        return Object.values(this.state.selected).filter(Boolean).length;
    }

    initials(name) {
        return name
            .split(" ")
            .map((p) => p[0])
            .join("")
            .slice(0, 2)
            .toUpperCase();
    }
}
