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

// Filtres disponibles en vue Équipe (voir "Filtrer" dans feuilles-de-temps_vue-equipe).
const TEAM_FILTER_ITEMS = [
    "Unité d'Affaires (Utilisateur)",
    "Employé",
    "Bureau",
    "Poste",
    "Projet",
    "Responsables de projet",
    "Statut",
];

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

/**
 * Intervalle de saisie Jour (voir "Paramètres de saisie (intervalle,
 * unité)") : c'est dans ce mode que les commentaires par jour sont
 * disponibles (voir "Commentaires" dans la doc, image-04.gif) — en vue
 * Personnelle comme en vue Équipe.
 */
const PERSONAL_DAYS = [
    { key: "mon", label: "LUN", date: "04/03" },
    { key: "tue", label: "MAR", date: "05/03" },
    { key: "wed", label: "MER", date: "06/03" },
    { key: "thu", label: "JEU", date: "07/03" },
    { key: "fri", label: "VEN", date: "08/03" },
    { key: "sat", label: "SAM", date: "09/03" },
    { key: "sun", label: "DIM", date: "10/03" },
];

function buildPersonalDayRows() {
    return [
        {
            key: "bnp_day",
            project: "BNP Paribas — Déploiement Salesforce",
            cells: [
                { value: "1", status: "approved", comment: "" },
                { value: "1", status: "approved", comment: "Télétravail" },
                { value: "1", status: "saved", comment: "" },
                { value: "0.5", status: "saved", comment: "RDV client l'après-midi, parti plus tôt" },
                { value: "0", status: "to_complete", comment: "" },
                { value: "0", status: "to_complete", comment: "" },
                { value: "0", status: "to_complete", comment: "" },
            ],
        },
    ];
}

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

/**
 * Vue Équipe en intervalle Mois (colonnes Semaine) — c'est la configuration
 * illustrée par l'article "Vue Équipe" de la doc (image-01, image-02) :
 * déplier/replier, sélectionner une ou plusieurs lignes puis Approuver /
 * Rouvrir en masse, et des actions "Validated / Approve / Save" propres à
 * chaque semaine de la ligne sélectionnée.
 */
const TEAM_MONTH_WEEKS = [
    { key: "w27", label: "S27", range: "22/06 → 28/06" },
    { key: "w28", label: "S28", range: "29/06 → 05/07" },
    { key: "w29", label: "S29", range: "06/07 → 12/07" },
    { key: "w30", label: "S30", range: "13/07 → 19/07" },
    { key: "w31", label: "S31", range: "20/07 → 26/07" },
];

const TEAM_PEOPLE = [
    {
        id: 1,
        name: "AMERI Armand",
        totalByDay: ["1d", "1d", "1d", "1d", "1d", "0d", "0d"],
        total: "5d",
        monthCells: [
            { value: "0.63", status: "approved", movement: "up", movementValue: "1d" },
            { value: "3.13", status: "approved", movement: "down", movementValue: "0d" },
            { value: "3.51", status: "pending", movement: "down", movementValue: "1d" },
            { value: "3.13", status: "saved", movement: null },
            { value: "0", status: "to_complete", movement: null },
        ],
        projects: [
            {
                name: "AIRCALL — Data Audit",
                gauge: gauge(26, 39.51, 26, "blue"),
                values: ["0.4d", "0.4d", "0.4d", "0.4d", "0.4d", "0d", "0d"],
                total: "2d",
                monthValues: [0.25, 1.25, 1.4, 1.25, 0],
            },
            {
                name: "APPLE — Acquisition Strategy Redesign",
                gauge: gauge(2, 0, 0, "orange"),
                gaugeNote: "Aucune affectation",
                values: ["0.4d", "0.4d", "0.4d", "0.4d", "0.4d", "0d", "0d"],
                total: "2d",
                monthValues: [0.25, 1.25, 1.4, 1.25, 0],
            },
            {
                name: "INTERNAL — Deployment Process Improvement",
                gauge: gauge(5.85, 16.4, 5.85, "blue"),
                values: ["0.2d", "0.2d", "0.2d", "0.2d", "0.2d", "0d", "0d"],
                total: "1d",
                monthValues: [0.13, 0.63, 0.71, 0.63, 0],
            },
        ],
        availability: ["0d", "0d", "0d", "0d", "0d", "0d", "0d"],
        availabilityTotal: "0d",
        monthAvailability: ["0d", "0d", "0d", "0d", "0d"],
        monthAvailabilityTotal: "0d",
    },
    {
        id: 2,
        name: "BARTOL Jeremy",
        totalByDay: ["1d", "1d", "1d", "1d", "1d", "0d", "0d"],
        total: "5d",
        monthCells: [
            { value: "0.87", status: "approved", movement: "up", movementValue: "1d" },
            { value: "4.36", status: "approved", movement: "down", movementValue: "0d" },
            { value: "4.75", status: "pending", movement: "down", movementValue: "1d" },
            { value: "0", status: "to_complete", movement: null },
            { value: "0", status: "to_complete", movement: null },
        ],
        projects: [
            {
                name: "AIRCALL — Data Audit",
                gauge: gauge(40, 45.75, 40, "blue"),
                values: ["0.8d", "0.8d", "0.8d", "0.8d", "0.8d", "0d", "0d"],
                total: "4d",
                monthValues: [0.7, 3.49, 3.8, 0, 0],
            },
            {
                name: "INTERNAL — Deployment Process Improvement",
                gauge: gauge(2, 2, 2, "green"),
                values: ["0.2d", "0.2d", "0.2d", "0.2d", "0.2d", "0d", "0d"],
                total: "1d",
                monthValues: [0.17, 0.87, 0.95, 0, 0],
            },
        ],
        availability: ["0d", "0d", "0d", "0d", "0d", "0d", "0d"],
        availabilityTotal: "0d",
        monthAvailability: ["0d", "0d", "0d", "0d", "0d"],
        monthAvailabilityTotal: "0d",
    },
    {
        id: 3,
        name: "CHEN John",
        totalByDay: ["1d", "1d", "1d", "1d", "1d", "0d", "0d"],
        total: "5d",
        monthCells: [
            { value: "0.65", status: "approved", movement: null },
            { value: "3.25", status: "saved", movement: null },
            { value: "0", status: "to_complete", movement: null },
            { value: "0", status: "to_complete", movement: null },
            { value: "0", status: "to_complete", movement: null },
        ],
        projects: [
            {
                name: "INTERNAL — HR Process Improvement",
                gauge: gauge(11, 8.92, 11, "red"),
                values: ["0.4d", "0.4d", "0.4d", "0.4d", "0.4d", "0d", "0d"],
                total: "2d",
                monthValues: [0.26, 1.3, 0, 0, 0],
            },
            {
                name: "AIRCALL — Data Audit",
                gauge: gauge(8, 27.2, 8, "blue"),
                values: ["0.6d", "0.6d", "0.6d", "0.6d", "0.6d", "0d", "0d"],
                total: "3d",
                monthValues: [0.39, 1.95, 0, 0, 0],
            },
        ],
        availability: ["0d", "0d", "0d", "0d", "0d", "0d", "0d"],
        availabilityTotal: "0d",
        monthAvailability: ["0d", "0d", "0d", "0d", "0d"],
        monthAvailabilityTotal: "0d",
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
        this.personalDays = PERSONAL_DAYS;

        this.teamDays = TEAM_DAYS;
        this.teamMonthWeeks = TEAM_MONTH_WEEKS;
        this.teamFilterItems = TEAM_FILTER_ITEMS;

        this.state = useState({
            tab: "personal", // "personal" | "team"
            expanded: { 1: true, 2: true, 3: true },
            allExpanded: true,
            selected: {},
            team: TEAM_PEOPLE,
            personalRows: buildPersonalRows(),
            personalDayRows: buildPersonalDayRows(),
            personalPeriodMode: "week", // "week" (colonnes Semaine) | "day" (colonnes Jour, avec commentaires)
            commentOpenFor: null, // "<rowKey>_<cellIndex>" | null
            teamPeriodMode: "month", // "month" (colonnes Semaine) | "week" (colonnes Jour)
            teamMenuOpen: null, // "filter" | null
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

    /** Formatte la valeur brute d'une cellule (ex. monthCells) en "Xd". */
    cellDays(cell) {
        return this.formatDays(parseFloat(cell.value) || 0);
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

    /**
     * Statut "canonique" d'une semaine (pris sur la 1ère ligne de projet,
     * la validation d'une semaine s'applique au niveau utilisateur, pas
     * ligne par ligne) — permet de proposer Enregistrer/Soumettre sur
     * TOUTE semaine non validée, pas seulement une semaine figée en dur.
     */
    weekStatus(index) {
        return this.state.personalRows[0]?.cells[index]?.status || "to_complete";
    }

    saveWeek(index) {
        for (const row of this.state.personalRows) {
            const cell = row.cells[index];
            if (cell && cell.status === "to_complete") {
                cell.status = "saved";
            }
        }
    }

    submitWeek(index) {
        for (const row of this.state.personalRows) {
            const cell = row.cells[index];
            if (cell && cell.status === "saved") {
                cell.status = "pending";
            }
        }
    }

    // ---- Intervalle de saisie Jour (vue Personnelle) + commentaires ----
    setPersonalPeriodMode(mode) {
        this.state.personalPeriodMode = mode;
    }

    onDayCellInput(cell, ev) {
        cell.value = ev.target.value;
        if (cell.status === "to_complete" && parseFloat(cell.value) > 0) {
            cell.status = "saved";
        }
    }

    dayRowTotal(row) {
        return this.rowTotal(row);
    }

    commentKey(row, index) {
        return row.key + "_" + index;
    }

    isCommentOpen(row, index) {
        return this.state.commentOpenFor === this.commentKey(row, index);
    }

    toggleComment(row, index, ev) {
        if (ev) ev.stopPropagation();
        const key = this.commentKey(row, index);
        this.state.commentOpenFor = this.state.commentOpenFor === key ? null : key;
    }

    closeComment() {
        this.state.commentOpenFor = null;
    }

    onCommentInput(cell, ev) {
        cell.comment = ev.target.value;
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

    get selectedPeople() {
        return this.state.team.filter((p) => this.isSelected(p));
    }

    setTeamPeriodMode(mode) {
        this.state.teamPeriodMode = mode;
    }

    toggleTeamMenu(name, ev) {
        if (ev) ev.stopPropagation();
        this.state.teamMenuOpen = this.state.teamMenuOpen === name ? null : name;
    }

    closeTeamMenus() {
        this.state.teamMenuOpen = null;
    }

    /**
     * Détermine quelle action proposer sous une semaine, pour la ligne
     * sélectionnée : « Validated » (verrouillé) si déjà approuvée,
     * « Approve » si une saisie attend l'approbation, « Save » sinon —
     * reproduit les trois états visibles dans image-02/image-03 de la doc.
     */
    weekActionKind(cell) {
        if (cell.status === "approved") {
            return "locked";
        }
        if (cell.status === "saved" || cell.status === "pending") {
            return "approve";
        }
        return "save";
    }

    approveCell(cell) {
        cell.status = "approved";
    }

    saveCell(cell) {
        if (parseFloat(cell.value) > 0) {
            cell.status = "saved";
        }
    }

    /** Bandeau de masse : « ✓ Approve » valide toutes les semaines saisies des lignes sélectionnées. */
    bulkApprove() {
        for (const person of this.selectedPeople) {
            for (const cell of person.monthCells) {
                if (cell.status === "saved" || cell.status === "pending") {
                    cell.status = "approved";
                }
            }
        }
    }

    /** Bandeau de masse : « 🔒 Re-open » rouvre les semaines déjà approuvées (repassent en attente). */
    bulkReopen() {
        for (const person of this.selectedPeople) {
            for (const cell of person.monthCells) {
                if (cell.status === "approved") {
                    cell.status = "pending";
                }
            }
        }
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
