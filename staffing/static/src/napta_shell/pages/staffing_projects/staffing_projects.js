/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Données factices LOCALES à cette page (volontairement non partagées avec
 * mock/mock_data.js pour éviter tout conflit avec d'autres pages en cours
 * de développement en parallèle).
 *
 * Reproduit la page Napta "Staffing > Projets" (vues Cartes / Tableau) telle
 * que documentée dans modules-napta/staffing_page-projets-cartes-tableau.
 */
const COLUMNS = [
    { key: "a_staffer", title: "Projets à staffer" },
    { key: "staffings_valider", title: "Staffings à valider" },
    { key: "en_cours", title: "Projets en cours" },
    { key: "internes", title: "Projets internes" },
    { key: "formations", title: "Formations" },
];

let _id = 0;
function p(data) {
    _id++;
    return {
        id: _id,
        color: "violet",
        family: null, // null | "parent" | "child"
        demandes: 0,
        staffingsSimules: 0,
        likes: 0,
        liked: false,
        tags: [],
        category: "Stratégie",
        status: "Projet à démarrer",
        departments: "",
        ...data,
    };
}

const PROJECTS = [
    p({ column: "a_staffer", title: "Refonte du SI complet", client: "BNP Paribas", dateStart: "4 novembre 2024", dateEnd: "20 juin 2025", color: "violet", family: "parent", likes: 3, category: "Déploiement", status: "Opportunité en cours" }),
    p({ column: "a_staffer", title: "Audit interne", client: "Decathlon", dateStart: "23 décembre 2024", dateEnd: "25 juillet 2025", color: "vert", demandes: 1, demandesCount: 1, category: "Audit", status: "Projet à démarrer" }),
    p({ column: "a_staffer", title: "Refonte stratégie d'acquisition", client: "BackMarket", dateStart: "16 décembre 2024", dateEnd: "22 août 2025", color: "violet", demandes: 2, category: "Stratégie" }),
    p({ column: "a_staffer", title: "Audit data", client: "Aircall", dateStart: "16 décembre 2024", dateEnd: "15 août 2025", color: "vert", category: "Audit" }),
    p({ column: "a_staffer", title: "Optimisation fiscale", client: "PSG", dateStart: "3 février 2025", dateEnd: "24 octobre 2025", color: "violet", demandes: 1, staffingsSimules: 8, category: "Stratégie" }),

    p({ column: "staffings_valider", title: "Projet de transformation digitale", client: "SIEMENS", dateStart: "30 janvier 2025", dateEnd: "27 juin 2025", color: "rose", staffingsSimules: 2, category: "Déploiement" }),
    p({ column: "staffings_valider", title: "Accompagnement - Intrapreneuriat", client: "L'ORÉAL", dateStart: "30 août 2024", dateEnd: "22 août 2025", color: "violet", staffingsSimules: 1, likes: 1, category: "Stratégie" }),
    p({ column: "staffings_valider", title: "Déploiement stratégie data", client: "Kering", dateStart: "26 mars 2025", dateEnd: "26 septembre 2025", color: "rose", demandes: 2, staffingsSimules: 5, likes: 1, category: "Déploiement", departments: "Data & Analytics" }),
    p({ column: "staffings_valider", title: "Refonte de la stratégie RH", client: "Sony", dateStart: "", dateEnd: "", color: "violet", category: "Stratégie" }),

    p({ column: "en_cours", title: "Déploiement Salesforce", client: "BNP Paribas", dateStart: "9 décembre 2024", dateEnd: "25 juillet 2025", color: "rose", family: "child", demandes: 1, staffingsSimules: 2, likes: 6, tags: ["P1"], category: "Déploiement", status: "Projets en cours" }),
    p({ column: "en_cours", title: "Réorganisation de la DSI", client: "AIRBUS", dateStart: "6 septembre 2024", dateEnd: "16 mai 2025", color: "violet", demandes: 1, staffingsSimules: 1, category: "Déploiement" }),

    p({ column: "internes", title: "Amélioration de nos process...", client: "INTERNE", dateStart: "19 septembre 2024", dateEnd: "27 août 2025", color: "orange", family: "parent", demandes: 2, staffingsSimules: 1, likes: 1, tags: ["P1", "P2"], category: "Interne", status: "Projet interne" }),
    p({ column: "internes", title: "Amélioration de nos process R...", client: "INTERNE", dateStart: "19 septembre 2024", dateEnd: "19 septembre 2025", color: "violet", family: "child", likes: 1, category: "Interne" }),
    p({ column: "internes", title: "Amélioration des process de déploie...", client: "INTERNE", dateStart: "16 décembre 2024", dateEnd: "22 août 2025", color: "violet", staffingsSimules: 2, category: "Interne" }),

    p({ column: "formations", title: "Anglais", client: "Formation", dateStart: "27 janvier 2025", dateEnd: "30 avril 2025", color: "grisclaire", category: "Formation" }),
    p({ column: "formations", title: "Améliorer l'impact", client: "Formation", dateStart: "4 novembre 2024", dateEnd: "22 août 2025", color: "vert", staffingsSimules: 2, likes: 4, category: "Formation" }),
    p({ column: "formations", title: "Optimisation de la Marque", client: "Formation", dateStart: "13 mai 2025", dateEnd: "13 juin 2025", color: "grisclaire", demandes: 1, category: "Formation" }),
    p({ column: "formations", title: "Manager Niveau 2", client: "Formation", dateStart: "17 mars 2025", dateEnd: "14 avril 2025", color: "grisclaire", category: "Formation" }),
];

const TABLE_COLUMNS = [
    { key: "project", label: "Projet", sortable: true },
    { key: "client", label: "Client", sortable: true },
    { key: "status", label: "Statut de projet", sortable: true },
    { key: "category", label: "Catégorie", sortable: true },
    { key: "departments", label: "Départements (Projet)", sortable: false },
    { key: "demandes", label: "Demandes", sortable: true },
    { key: "staffingsSimules", label: "Staffings simulés", sortable: true },
];

const FILTER_SECTIONS = [
    { title: "Projet", items: ["Catégorie de projet", "Chefs de projet", "Client", "Colonne (vue cartes)", "Département (Projet)", "Étiquette", "Mode de facturation", "Projet", "Statut de projet"] },
    { title: "Utilisateur", items: ["Bureau", "Compétence", "Département (Utilisateur)", "Poste", "Responsable hiérarchique", "Utilisateur"] },
    { title: "Staffing", items: ["Statut de période de staffing", "Statut de staffing", "Type de staffing"] },
];

const CARD_MENU_ITEMS = [
    { key: "edit", icon: "fa-pencil", label: "Éditer" },
    { key: "duplicate", icon: "fa-clone", label: "Dupliquer le projet" },
    { key: "labels", icon: "fa-tag", label: "Étiquettes", chevron: true },
    { key: "add_staffing", icon: "fa-user-plus", label: "Ajouter un staffing" },
    { key: "remove_dashboard", icon: "fa-eye-slash", label: "Retirer du tableau de bord" },
    { key: "archive", icon: "fa-archive", label: "Archiver" },
    { key: "delete", icon: "fa-trash-o", label: "Supprimer", danger: true },
];

const DETAIL_TABS = [
    { key: "calendar", label: "Calendrier", icon: "fa-calendar" },
    { key: "requests", label: "Demandes / Staffings", icon: "fa-list-ul" },
    { key: "subprojects", label: "Sous-projets", icon: "fa-sitemap" },
    { key: "finance", label: "Suivi financier", icon: "fa-line-chart" },
];

/**
 * Données factices pour l'onglet « Suivi financier » d'un projet.
 * Reproduit fidèlement modules-napta/financier_suivi-financier-d-un-projet
 * (images 01, 02, 04, 06, 07, 09, 12, 14) : le mode de facturation d'un
 * projet (régie/forfait) est déduit de son id pour varier l'affichage, les
 * valeurs du tableau "Situation en cours" sont reprises telles quelles de
 * la capture image-12 (Consultant Senior), celles du graphique "Suivi de la
 * charge globale" de la capture image-06, et celles du tableau "Suivi de la
 * charge individuelle" de la capture image-07.
 */
const FINANCE_WEEKS = [
    { key: "s37", label: "S37", range: "Du 11-09-23 au 17-09-23" },
    { key: "s38", label: "S38", range: "Du 18-09-23 au 24-09-23" },
    { key: "s39", label: "S39", range: "Du 25-09-23 au 01-10-23" },
    { key: "s40", label: "S40", range: "Du 02-10-23 au 08-10-23" },
];

const FINANCE_ROWS = [
    {
        key: "advancement", label: "Taux d'avancement", unit: "%", forfaitOnly: true,
        totalToDate: { planned: 13.12, real: 12.18 }, totalAtEnd: { planned: 100, projected: 100 },
        weeks: [3.12, 3.13, 3.12, 3.13],
    },
    {
        key: "charge", label: "Charge (jours)", unit: "JH", expandable: true,
        totalToDate: { planned: 18.38, real: 17 }, totalAtEnd: { planned: 140, projected: 138.63 },
        weeks: [4.38, 4.38, 4.38, 4.38],
        subRows: [
            { name: "Consultant Senior", role: "Rôle sur le projet", totalToDate: { planned: 0, real: 0 }, totalAtEnd: { planned: 40, projected: 40 }, weeks: [0, 0, 0, 0] },
            { name: "BARTOLIE Aurore", role: "Consultant Senior", totalToDate: { planned: 0, real: 0 }, totalAtEnd: { planned: 30, projected: 30 }, weeks: [0, 0, 0, 0] },
            { name: "CONSTABE Etienne", role: "Partner", totalToDate: { planned: 10.5, real: 9.5 }, totalAtEnd: { planned: 40, projected: 39 }, weeks: [2.5, 2.5, 2.5, 2.5] },
            { name: "MEROT Isabelle", role: "Manager", totalToDate: { planned: 7.88, real: 7.5 }, totalAtEnd: { planned: 30, projected: 29.63 }, weeks: [1.88, 1.88, 1.88, 1.88] },
        ],
    },
    {
        key: "tjm", label: "TJM", unit: "€",
        totalToDate: { planned: 1428.57, real: 1432.71 }, totalAtEnd: { planned: 1428.57, projected: 1442.74 },
        weeks: [1428.57, 1429.33, 1428.57, 1429.33],
    },
    {
        key: "ca", label: "Chiffre d'affaires", unit: "€",
        totalToDate: { planned: 26250, real: 24356.06 }, totalAtEnd: { planned: 200000, projected: 200000 },
        weeks: [6250, 6253.33, 6250, 6253.33],
    },
    {
        key: "cost", label: "Coût", unit: "€",
        totalToDate: { planned: 13857.38, real: 12791.5 }, totalAtEnd: { planned: 101790, projected: 100724.13 },
        weeks: [3299.38, 3299.38, 3299.38, 3299.38],
    },
    {
        key: "fees", label: "Frais", unit: "€",
        totalToDate: { planned: null, real: null }, totalAtEnd: { planned: null, projected: null },
        weeks: [null, null, null, null],
    },
    {
        key: "margin", label: "Marge", unit: "€",
        totalToDate: { planned: 12392.62, real: 11564.56 }, totalAtEnd: { planned: 98210, projected: 99275.87 },
        weeks: [2950.62, 2953.96, 2950.62, 2953.96],
    },
    {
        key: "marginRate", label: "Taux de marge", unit: "%",
        totalToDate: { planned: 47.21, real: 47.48 }, totalAtEnd: { planned: 49.1, projected: 49.64 },
        weeks: [47.21, 47.24, 47.21, 47.24],
    },
];

const FINANCE_CHARGE_GLOBALE = {
    days: {
        months: ["avril", "mai", "juin", "juillet", "août", "septembre", "octobre"],
        budgetVendu: 390,
        planifie: [2, 28, 85, 168, 178, 222, 262],
        reel: [2, 27, 83, 165, null, null, null],
        projete: [null, null, null, null, 178, 222, 262],
    },
    turnover_eur: {
        months: ["avril", "mai", "juin", "juillet", "août", "septembre", "octobre"],
        budgetVendu: 225000,
        planifie: [1200, 16000, 49000, 97000, 103000, 128000, 151000],
        reel: [1200, 15500, 48000, 95000, null, null, null],
        projete: [null, null, null, null, 103000, 128000, 151000],
    },
};

const FINANCE_INDIVIDUAL_MONTHS = [
    { key: "sept23", label: "SEPTEMBRE 2023", range: "DU 11-09-23 AU 30-09-23" },
    { key: "oct23", label: "OCTOBRE 2023", range: "DU 01-10-23 AU 31-10-23" },
    { key: "nov23", label: "NOVEMBRE 2023", range: "DU 01-11-23 AU 30-11-23" },
    { key: "dec23", label: "DÉCEMBRE 2023", range: "DU 01-12-23 AU 29-12-23" },
];

const FINANCE_INDIVIDUAL_ROWS = [
    {
        name: "BARTOLIE Aurore", role: "Consultant Senior - Data & Analytics - Londres",
        months: [{ forecast: 0, real: 0 }, { forecast: 80, real: 0 }, { forecast: 80, real: 0 }, { forecast: 80, real: 0 }],
    },
    {
        name: "CONSTABE Etienne", role: "Partner - Management des organisations - Paris",
        months: [{ forecast: 60, real: 60 }, { forecast: 88, real: 16 }, { forecast: 88, real: 0 }, { forecast: 84, real: 0 }],
    },
    {
        name: "MEROT Isabelle", role: "Manager - Management des organisations - Londres",
        months: [{ forecast: 45, real: 45 }, { forecast: 66, real: 15 }, { forecast: 66, real: 0 }, { forecast: 63, real: 0 }],
    },
];

const FINANCE_COLUMN_GROUPS = [
    { title: "Colonnes à afficher", items: [{ key: "totalToDate", label: "Total à date" }, { key: "totalAtEnd", label: "Total à terme" }] },
    { title: "Colonnes détaillées", items: [{ key: "planned", label: "Prévisionnel" }, { key: "real", label: "Réel" }, { key: "projected", label: "Projeté" }] },
];

const FINANCE_ROWS_TO_DISPLAY = ["Charge (jours)", "TJM moyen", "Chiffre d'affaires", "Coût", "Frais", "Marge", "Taux de marge"];

/** Construit le jeu de données financières d'un projet (déterministe à partir de son id). */
function buildFinance(project) {
    const billingMode = project.id % 3 === 0 ? "regie" : "forfait";
    const scale = 0.7 + ((project.id * 37) % 10) * 0.12; // variété entre projets, sans casser la cohérence
    const round2 = (v) => Math.round(v * 100) / 100;
    return {
        billingMode,
        kpis: {
            soldBudget: round2(225000 * scale),
            manDaysSold: Math.round(180 * scale),
            advancementToDate: 41.7,
            turnoverToDate: round2(93814.24 * scale),
            targetMarginRate: 50,
            projectedMarginRateAtEnd: 41.91,
            driftToDate: 26.6,
            projectedDrift: -2.7,
        },
        rows: FINANCE_ROWS,
        weeks: FINANCE_WEEKS,
        chargeGlobale: FINANCE_CHARGE_GLOBALE,
        individualMonths: FINANCE_INDIVIDUAL_MONTHS,
        individualRows: FINANCE_INDIVIDUAL_ROWS,
    };
}

export class StaffingProjectsPage extends Component {
    static template = "staffing.StaffingProjectsPage";
    static props = { page: Object };

    setup() {
        this.columns = COLUMNS;
        this.tableColumns = TABLE_COLUMNS;
        this.filterSections = FILTER_SECTIONS;
        this.cardMenuItems = CARD_MENU_ITEMS;
        this.detailTabs = DETAIL_TABS;
        this.financeColumnGroups = FINANCE_COLUMN_GROUPS;
        this.financeRowsToDisplay = FINANCE_ROWS_TO_DISPLAY;

        this.state = useState({
            view: "cards", // "cards" | "table"
            projects: PROJECTS,
            selected: {}, // id -> true
            openMenuFor: null,
            showViews: false,
            showFilter: false,
            showColumns: false,
            sortKey: null,
            sortDir: "asc",
            detail: null, // project object ou null
            detailTab: "calendar",
            collapsedColumns: {},
            // ---- Onglet "Suivi financier" ----
            financeMenuOpen: null, // "situation" | "columns" | "display" | null
            financeSituation: "current", // "current" | id d'une situation sauvegardée
            financeExpandedRows: {}, // row.key -> bool
            financeSaveDrawerOpen: false,
            chargeGlobaleUnit: "days", // "days" | "turnover_eur"
            displaySettings: { unit: "day", groupBy: "week", currency: "EUR" },
        });

        this.exportTooltip = "Exporter les projets (.xlsx ou .csv)";
        this.financeInfoTooltip =
            "Le Détail du suivi financier, le Suivi de la charge globale et le rapport Suivi financier global " +
            "ignorent les staffings et feuilles de temps en dehors des dates de contrat.";
        this.financeSavedSituations = [
            { id: "sit1", label: "Fin du 1er mois", date: "09-10-23" },
        ];
    }

    // ---- Onglet "Suivi financier" ----
    get financeData() {
        return this.state.detail ? buildFinance(this.state.detail) : null;
    }

    toggleFinanceMenu(name, ev) {
        if (ev) ev.stopPropagation();
        this.state.financeMenuOpen = this.state.financeMenuOpen === name ? null : name;
    }

    closeFinanceMenus() {
        this.state.financeMenuOpen = null;
    }

    setFinanceSituation(id) {
        this.state.financeSituation = id;
        this.state.financeMenuOpen = null;
    }

    toggleFinanceRow(key) {
        this.state.financeExpandedRows[key] = !this.state.financeExpandedRows[key];
    }

    setChargeGlobaleUnit(unit, ev) {
        if (ev) ev.stopPropagation();
        this.state.chargeGlobaleUnit = unit;
        this.state.financeMenuOpen = null;
    }

    get chargeGlobaleData() {
        return this.financeData.chargeGlobale[this.state.chargeGlobaleUnit];
    }

    formatChargeGlobaleAxis(v) {
        if (this.state.chargeGlobaleUnit === "days") {
            return Math.round(v) + "D";
        }
        return Math.round(v).toLocaleString("fr-FR") + " €";
    }

    /** Calcule les coordonnées/chemins SVG du graphique "Suivi de la charge globale". */
    get chargeGlobaleChart() {
        const data = this.chargeGlobaleData;
        const width = 640;
        const height = 220;
        const padLeft = 54;
        const padRight = 10;
        const padTop = 10;
        const padBottom = 24;
        const plotW = width - padLeft - padRight;
        const plotH = height - padTop - padBottom;
        const maxValue = data.budgetVendu * 1.03;
        const n = data.months.length;
        const x = (i) => padLeft + (i / (n - 1)) * plotW;
        const y = (v) => padTop + plotH - (v / maxValue) * plotH;

        const toPath = (arr) => {
            let d = "";
            let started = false;
            arr.forEach((v, i) => {
                if (v === null || v === undefined) {
                    started = false;
                    return;
                }
                d += (started ? "L" : "M") + x(i).toFixed(1) + "," + y(v).toFixed(1) + " ";
                started = true;
            });
            return d.trim();
        };

        const reelIdx = data.reel.map((v, i) => (v !== null ? i : null)).filter((i) => i !== null);
        let reelAreaPath = "";
        if (reelIdx.length) {
            reelAreaPath = `M${x(reelIdx[0]).toFixed(1)},${y(0).toFixed(1)} `;
            for (const i of reelIdx) {
                reelAreaPath += `L${x(i).toFixed(1)},${y(data.reel[i]).toFixed(1)} `;
            }
            reelAreaPath += `L${x(reelIdx[reelIdx.length - 1]).toFixed(1)},${y(0).toFixed(1)} Z`;
        }

        return {
            width,
            height,
            budgetY: y(data.budgetVendu).toFixed(1),
            planifiePath: toPath(data.planifie),
            reelPath: toPath(data.reel),
            reelAreaPath,
            projetePath: toPath(data.projete),
            months: data.months.map((m, i) => ({ label: m, x: x(i).toFixed(1) })),
            gridY: [0, 0.25, 0.5, 0.75, 1].map((f) => ({
                key: f,
                y: y(maxValue * f).toFixed(1),
                label: this.formatChargeGlobaleAxis(maxValue * f),
            })),
        };
    }

    openFinanceSaveDrawer() {
        this.state.financeSaveDrawerOpen = true;
    }

    closeFinanceSaveDrawer() {
        this.state.financeSaveDrawerOpen = false;
    }

    setDisplaySetting(key, value) {
        this.state.displaySettings[key] = value;
    }

    // ---- Formatage ----
    formatFinanceValue(value, unit) {
        if (value === null || value === undefined) {
            return "-";
        }
        const formatted = value.toLocaleString("fr-FR", { minimumFractionDigits: unit === "JH" ? 2 : 2, maximumFractionDigits: 2 });
        if (unit === "%") return formatted + " %";
        if (unit === "JH") return formatted + " JH";
        return formatted + " €";
    }

    // ---- Vue Cartes / Tableau ----
    setView(view) {
        this.state.view = view;
        this.closeMenus();
    }

    cardsForColumn(key) {
        return this.state.projects.filter((c) => c.column === key);
    }

    toggleColumnCollapse(key) {
        this.state.collapsedColumns[key] = !this.state.collapsedColumns[key];
    }

    // ---- Sélection / actions de masse ----
    get selectedIds() {
        return Object.keys(this.state.selected).filter((k) => this.state.selected[k]);
    }

    get selectedCount() {
        return this.selectedIds.length;
    }

    toggleSelect(project, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        this.state.selected[project.id] = !this.state.selected[project.id];
    }

    isSelected(project) {
        return !!this.state.selected[project.id];
    }

    clearSelection() {
        this.state.selected = {};
    }

    // ---- Menu carte (...) ----
    toggleCardMenu(project, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        this.state.openMenuFor = this.state.openMenuFor === project.id ? null : project.id;
    }

    closeMenus() {
        this.state.openMenuFor = null;
        this.state.showViews = false;
        this.state.showFilter = false;
        this.state.showColumns = false;
        this.state.financeMenuOpen = null;
    }

    toggleViews(ev) {
        if (ev) ev.stopPropagation();
        this.state.showViews = !this.state.showViews;
        this.state.showFilter = false;
        this.state.showColumns = false;
    }

    toggleFilter(ev) {
        if (ev) ev.stopPropagation();
        this.state.showFilter = !this.state.showFilter;
        this.state.showViews = false;
        this.state.showColumns = false;
    }

    toggleColumnsMenu(ev) {
        if (ev) ev.stopPropagation();
        this.state.showColumns = !this.state.showColumns;
        this.state.showViews = false;
        this.state.showFilter = false;
    }

    // ---- Like ----
    toggleLike(project, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        project.liked = !project.liked;
        project.likes += project.liked ? 1 : -1;
    }

    // ---- Tri (vue Tableau) ----
    sortBy(col) {
        if (!col.sortable) {
            return;
        }
        if (this.state.sortKey === col.key) {
            this.state.sortDir = this.state.sortDir === "asc" ? "desc" : "asc";
        } else {
            this.state.sortKey = col.key;
            this.state.sortDir = "asc";
        }
    }

    get sortedProjects() {
        const list = this.state.projects.slice();
        const key = this.state.sortKey;
        if (!key) {
            return list;
        }
        const dir = this.state.sortDir === "asc" ? 1 : -1;
        return list.sort((a, b) => {
            const av = (a[key] ?? "").toString();
            const bv = (b[key] ?? "").toString();
            return av.localeCompare(bv, "fr", { numeric: true }) * dir;
        });
    }

    sortIcon(col) {
        if (this.state.sortKey !== col.key) {
            return "fa-sort";
        }
        return this.state.sortDir === "asc" ? "fa-sort-asc" : "fa-sort-desc";
    }

    // ---- Détail projet ----
    openDetail(project) {
        this.state.detail = project;
        this.state.detailTab = "calendar";
    }

    closeDetail() {
        this.state.detail = null;
    }

    setDetailTab(key) {
        this.state.detailTab = key;
    }
}
