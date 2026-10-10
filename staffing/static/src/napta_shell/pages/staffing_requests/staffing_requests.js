/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Données factices LOCALES à cette page.
 *
 * Reproduit la page Napta "Staffing > Demandes" telle que documentée dans
 * modules-napta/staffing_la-page-des-demandes.
 */
let _id = 0;
function r(data) {
    _id++;
    const today = new Date();
    const end = data.endDate ? new Date(data.endDate.split("/").reverse().join("-")) : null;
    return {
        id: _id,
        obsolete: end ? end < today : false,
        preBooked: [],
        status: "",
        businessUnits: [],
        ...data,
    };
}

const REQUESTS = [
    r({ project: "HR Process Audit", client: "Microsoft", startDate: "01/02/2027", endDate: "23/04/2027", soldDays: 70, workloadDays: 15, workloadPct: 25, preBooked: ["Oliver NGUYEN", "John S.", "+1"], businessUnits: [] }),
    r({ project: "Internal Audit", client: "Orange", startDate: "22/07/2026", endDate: "22/01/2027", soldDays: 65, workloadDays: 67, workloadPct: 50, preBooked: ["Isabelle MEROT", "Olivier B.", "+1"] }),
    r({ project: "Acquisition Strategy Redesign", client: "APPLE", startDate: "25/05/2027", endDate: "22/06/2028", soldDays: 25, workloadDays: 70.75, workloadPct: 25, preBooked: ["Armand AMERI", "Jess B."] }),
    r({ project: "Innovation Dissemination", client: "STELLANTIS", startDate: "06/07/2026", endDate: "18/12/2026", soldDays: 120, workloadDays: 120, workloadPct: 50, preBooked: ["Benjamin LEFORT", "T."], businessUnits: ["Excel", "Anglais"] }),
    r({ project: "Commercial Service Support", client: "ETAM", startDate: "12/07/2027", endDate: "17/12/2027", soldDays: 60, workloadDays: 57.5, workloadPct: 50, preBooked: ["Fiona MAGGAL", "Sop."], businessUnits: ["Excel", "Anglais"] }),
    r({ project: "HR Strategy Redesign", client: "Sony", startDate: "22/07/2026", endDate: "22/01/2027", soldDays: 70, workloadDays: 67, workloadPct: 50, preBooked: ["Oliver NGUYEN", "Joh."] }),
    r({ project: "Internal Audit", client: "Orange", startDate: "09/08/2027", endDate: "22/11/2027", soldDays: 70, workloadDays: 38, workloadPct: 50, preBooked: ["Christopher JOHNSON"] }),
    r({ project: "Tax Optimization", client: "CISCO", startDate: "01/03/2027", endDate: "23/04/2027", soldDays: 135, workloadDays: 8, workloadPct: 20, preBooked: ["Christopher JOHNSON"] }),
    r({ project: "Ops Process Improvement", client: "LVMH", startDate: "30/06/2026", endDate: "03/07/2026", soldDays: 0, workloadDays: 4, workloadPct: 100, preBooked: ["Nour BARTOLI"], businessUnits: ["English", "Communication"] }),
    r({ project: "Complete IS Redesign", client: "BNP Paribas", startDate: "27/07/2026", endDate: "25/12/2026", soldDays: 0, workloadDays: 110, workloadPct: 100, preBooked: ["Maria DAVOS"], businessUnits: ["Data analysis"] }),
    r({ project: "ISD Reorganization", client: "AIRBUS", startDate: "27/07/2026", endDate: "04/09/2026", soldDays: 140, workloadDays: 12, workloadPct: 40, preBooked: ["Katharina BERARDA"], status: "En attente", businessUnits: ["Excel", "Anglais"] }),
    r({ project: "Salesforce Deployment", client: "BNP Paribas", startDate: "06/07/2026", endDate: "14/08/2026", soldDays: 320, workloadDays: 27.07, workloadPct: 90, preBooked: ["Jess BOMPARD"], status: "En attente", businessUnits: ["Salesforce"] }),
    r({ project: "Coaching - Digital Transformation", client: "JP MORGAN", startDate: "20/07/2026", endDate: "11/09/2026", soldDays: 0, workloadDays: 10, workloadPct: 25, status: "En attente", businessUnits: ["Anglais", "Budget"] }),
    r({ project: "Ops Process Improvement", client: "LVMH", startDate: "23/12/2026", endDate: "22/02/2027", soldDays: 320, workloadDays: 11, workloadPct: 25, businessUnits: ["Anglais", "Design"] }),
    r({ project: "HR Process Improvement", client: "INTERNAL", startDate: "25/03/2027", endDate: "23/07/2027", soldDays: 0, workloadDays: 21.75, workloadPct: 25, status: "En attente", businessUnits: ["Anglais"] }),
    r({ project: "Enhancing the Impact of Presentations", client: "TRAINING", startDate: "23/11/2026", endDate: "22/12/2026", soldDays: 0, workloadDays: 4.4, workloadPct: 20, businessUnits: ["Anglais"] }),
    r({ project: "Audit 2026", client: "COCA-COLA", startDate: "17/08/2026", endDate: "20/11/2026", soldDays: 0, workloadDays: 26, workloadPct: 37 }),
    r({ project: "Data Strategy Deployment", client: "Kering", startDate: "27/07/2026", endDate: "23/10/2026", soldDays: 60, workloadDays: 60, workloadPct: 46, businessUnits: ["Python"] }),
    // Demandes obsolètes (période entièrement passée)
    r({ project: "Audit process RH 2023", client: "Microsoft", startDate: "01/02/2023", endDate: "23/04/2023", soldDays: 40, workloadDays: 12, workloadPct: 30 }),
    r({ project: "Optimisation fiscale 2022", client: "PSG", startDate: "01/01/2022", endDate: "20/03/2022", soldDays: 15, workloadDays: 5, workloadPct: 20 }),
];

const TABLE_COLUMNS = [
    { key: "project", label: "Projet", sortable: true },
    { key: "client", label: "Client", sortable: false },
    { key: "startDate", label: "Date de début", sortable: true },
    { key: "endDate", label: "Date de fin", sortable: true },
    { key: "soldDays", label: "Jours vendus", sortable: false },
    { key: "workloadDays", label: "Charge (Jours)", sortable: false },
    { key: "workloadPct", label: "Charge (%)", sortable: false },
    { key: "preBooked", label: "Utilisateur pré-réservé", sortable: true },
    { key: "status", label: "Statut", sortable: true },
    { key: "businessUnits", label: "Unité commerciale (Projet)", sortable: false },
];

const TABS = [
    { key: "to_assign", label: "À attribuer" },
    { key: "deprecated", label: "Obsolètes" },
    { key: "all", label: "Tous" },
];

const FILTER_SECTIONS = [
    { title: "Projet", items: ["Projet", "Catégorie de projet", "Chef de projet", "Type de projet"] },
    { title: "Critères", items: ["Unité commerciale (Projet)", "Type de contrat", "Poste", "Bureau", "Compétence"] },
    { title: "Demande", items: ["Créée depuis", "Date de fin prévue", "Utilisateur pré-réservé", "Pré-réservation", "Statut", "Utilisateur suggéré", "Type"] },
];

const COLUMNS_MENU = TABLE_COLUMNS.map((c) => c.label).concat(["Compétences", "Postes", "Partenaires", "Dernier commentaire"]);

const PROJECT_OPTIONS = [...new Set(REQUESTS.map((r) => r.project))].sort((a, b) => a.localeCompare(b, "fr"));

/**
 * Champs du tiroir "Créer une demande", conformes à
 * modules-napta/staffing_creation-de-staffing (sections Critères, Périodes,
 * Utilisateurs, Informations, Commentaire).
 */
const CRITERIA_FIELDS = [
    { key: "skills", label: "Compétences", options: ["Excel", "Anglais", "Python", "Salesforce", "Data analysis", "Communication", "Budget", "Design"] },
    { key: "businessUnits", label: "Unité commerciale", options: ["Conseil RH", "Audit", "Stratégie", "Transformation digitale", "Finance"] },
    { key: "positions", label: "Poste", options: ["Consultant", "Senior Consultant", "Manager", "Directeur de mission", "Analyste"] },
    { key: "offices", label: "Bureau", options: ["Paris", "Lyon", "Marseille", "Londres", "Bruxelles"] },
    { key: "contractTypes", label: "Type de contrat", options: ["CDI", "CDD", "Stage", "Alternance", "Freelance"] },
];

// L'unité de charge est commune à toutes les périodes (cf. doc : "L'unité
// est la même pour toutes les périodes"), d'où un seul sélecteur global.
const PERIOD_UNITS = ["Jours", "Heures", "% (congés exclus)"];
const PERIOD_PLANNING_MODES = ["Dates fixes", "À partir de"];
const HALF_DAY_OPTIONS = ["Matin", "Après-midi"];
const PERIOD_STATUS_OPTIONS = ["Non défini", "À valider", "Confirmée", "Annulée"];
const CURRENCY_OPTIONS = ["€", "$", "£"];

const USER_DIRECTORY = [...new Set(REQUESTS.flatMap((r) => r.preBooked).filter((n) => n && !n.startsWith("+") && !/\.$/.test(n)))].concat([
    "Jérémie BARTOL", "Aurore BARTOLIE", "Sylvain BRIZARD", "Marie-Claire RODRIGUES",
]).sort((a, b) => a.localeCompare(b, "fr"));

// Une demande ne staffe pas réellement : chaque utilisateur n'est que
// suggéré ou pré-réservé, selon les droits de son créateur (doc §Option de
// staffing). On simule ce choix par utilisateur sélectionné.
const USER_STAFFING_OPTIONS = ["Suggéré", "Pré-réservé"];

const ASSIGNMENT_STATUS_OPTIONS = ["Suggestion", "Pré-réservation", "Staffing simulé", "Staffing confirmé"];
const PRIORITY_OPTIONS = ["Basse", "Normale", "Haute", "Urgente"];

const COMMENT_MAX_LENGTH = 200;

export class StaffingRequestsPage extends Component {
    static template = "staffing.StaffingRequestsPage";
    static props = { page: Object };

    setup() {
        this.tableColumns = TABLE_COLUMNS;
        this.tabs = TABS;
        this.filterSections = FILTER_SECTIONS;
        this.columnsMenu = COLUMNS_MENU;
        this.projectOptions = PROJECT_OPTIONS;
        this.criteriaFields = CRITERIA_FIELDS;
        this.periodUnits = PERIOD_UNITS;
        this.periodPlanningModes = PERIOD_PLANNING_MODES;
        this.halfDayOptions = HALF_DAY_OPTIONS;
        this.periodStatusOptions = PERIOD_STATUS_OPTIONS;
        this.currencyOptions = CURRENCY_OPTIONS;
        this.userStaffingOptions = USER_STAFFING_OPTIONS;
        this.assignmentStatusOptions = ASSIGNMENT_STATUS_OPTIONS;
        this.priorityOptions = PRIORITY_OPTIONS;
        this.commentMaxLength = COMMENT_MAX_LENGTH;
        this._periodId = 0;

        this.state = useState({
            requests: REQUESTS,
            activeTab: "to_assign",
            selected: {},
            showViews: false,
            showFilter: false,
            showColumns: false,
            showCreateMenu: false,
            showExportMenu: false,
            sortKey: null,
            sortDir: "asc",
            createDrawer: null,
            createNeed: "",
            createProject: "",
            createOpenSections: {},
            createCriteria: { skills: [], businessUnits: [], positions: [], offices: [], contractTypes: [] },
            createCriteriaOpenField: null,
            createPeriods: [],
            createPeriodsConfig: { planningMode: "Dates fixes", unit: "Jours", ignoreLeaves: false, autoSplit: false },
            createPeriodMenuOpenId: null,
            createBulkEditOpen: false,
            createBulkEdit: { amount: null, customFee: null, customFeeCurrency: "€", customCost: null, customCostCurrency: "€", status: "", description: "" },
            createUsers: [],
            createUserOptions: {},
            createUserSearch: "",
            createUserSearchFocused: false,
            createInfo: { status: "", daysSold: null, description: "", duration: "", priority: "" },
            createComment: "",
        });

        this.scenarioTooltip = "Résoudre automatiquement les demandes grâce à l'IA (fonctionnalité en version bêta)";
    }

    // ---- Onglets ----
    setTab(key) {
        this.state.activeTab = key;
        this.state.selected = {};
    }

    get filteredRequests() {
        if (this.state.activeTab === "deprecated") {
            return this.state.requests.filter((r) => r.obsolete);
        }
        if (this.state.activeTab === "to_assign") {
            return this.state.requests.filter((r) => !r.obsolete);
        }
        return this.state.requests;
    }

    get sortedRequests() {
        const list = this.filteredRequests.slice();
        const key = this.state.sortKey;
        if (!key) {
            return list;
        }
        const dir = this.state.sortDir === "asc" ? 1 : -1;
        return list.sort((a, b) => {
            const av = (Array.isArray(a[key]) ? a[key].join(",") : a[key] ?? "").toString();
            const bv = (Array.isArray(b[key]) ? b[key].join(",") : b[key] ?? "").toString();
            return av.localeCompare(bv, "fr", { numeric: true }) * dir;
        });
    }

    get totalCount() {
        return this.state.requests.length;
    }

    get noOwnerCount() {
        return this.state.requests.filter((r) => !r.preBooked.length).length;
    }

    // ---- Tri ----
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

    sortIcon(col) {
        if (this.state.sortKey !== col.key) {
            return "fa-sort";
        }
        return this.state.sortDir === "asc" ? "fa-sort-asc" : "fa-sort-desc";
    }

    // ---- Sélection ----
    toggleSelect(row, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        this.state.selected[row.id] = !this.state.selected[row.id];
    }

    isSelected(row) {
        return !!this.state.selected[row.id];
    }

    get selectedCount() {
        return Object.values(this.state.selected).filter(Boolean).length;
    }

    // ---- Dropdowns ----
    closeMenus() {
        this.state.showViews = false;
        this.state.showFilter = false;
        this.state.showColumns = false;
        this.state.showCreateMenu = false;
        this.state.showExportMenu = false;
    }

    toggleDropdown(name, ev) {
        if (ev) ev.stopPropagation();
        const wasOpen = this.state[name];
        this.closeMenus();
        this.state[name] = !wasOpen;
    }

    // ---- Tiroir de création de demande(s) ----
    openCreateDrawer(mode, ev) {
        if (ev) ev.stopPropagation();
        this.closeMenus();
        this.state.createDrawer = mode;
        this.state.createNeed = "";
        this.state.createProject = "";
        this.state.createOpenSections = {};
        this.state.createCriteria = { skills: [], businessUnits: [], positions: [], offices: [], contractTypes: [] };
        this.state.createCriteriaOpenField = null;
        this.state.createPeriods = [];
        this.state.createPeriodsConfig = { planningMode: "Dates fixes", unit: "Jours", ignoreLeaves: false, autoSplit: false };
        this.state.createPeriodMenuOpenId = null;
        this.state.createBulkEditOpen = false;
        this.state.createBulkEdit = { amount: null, customFee: null, customFeeCurrency: "€", customCost: null, customCostCurrency: "€", status: "", description: "" };
        this.state.createUsers = [];
        this.state.createUserOptions = {};
        this.state.createUserSearch = "";
        this.state.createUserSearchFocused = false;
        this.state.createInfo = { status: "", daysSold: null, description: "", duration: "", priority: "" };
        this.state.createComment = "";
    }

    closeCreateDrawer() {
        this.state.createDrawer = null;
    }

    closeCreateDropdowns() {
        this.state.createCriteriaOpenField = null;
        this.state.createUserSearchFocused = false;
        this.state.createPeriodMenuOpenId = null;
    }

    toggleCreateSection(key) {
        // Ne stoppe pas la propagation : le clic doit atteindre le tiroir
        // pour que closeCreateDropdowns() referme les menus Critères/Utilisateurs
        // d'une autre section restée ouverte.
        this.state.createOpenSections[key] = !this.state.createOpenSections[key];
    }

    isCreateSectionOpen(key) {
        return !!this.state.createOpenSections[key];
    }

    // ---- Section Critères ----
    get criteriaCount() {
        const c = this.state.createCriteria;
        return c.skills.length + c.businessUnits.length + c.positions.length + c.offices.length + c.contractTypes.length;
    }

    toggleCriteriaDropdown(fieldKey, ev) {
        if (ev) ev.stopPropagation();
        const wasOpen = this.state.createCriteriaOpenField === fieldKey;
        this.state.createCriteriaOpenField = wasOpen ? null : fieldKey;
    }

    isCriteriaDropdownOpen(fieldKey) {
        return this.state.createCriteriaOpenField === fieldKey;
    }

    toggleCriteriaValue(fieldKey, option, ev) {
        if (ev) ev.stopPropagation();
        const list = this.state.createCriteria[fieldKey];
        const idx = list.indexOf(option);
        if (idx === -1) {
            list.push(option);
        } else {
            list.splice(idx, 1);
        }
    }

    isCriteriaValueSelected(fieldKey, option) {
        return this.state.createCriteria[fieldKey].includes(option);
    }

    criteriaFieldSummary(fieldKey) {
        const list = this.state.createCriteria[fieldKey];
        if (!list.length) {
            return "Sélectionner…";
        }
        return list.join(", ");
    }

    // ---- Section Périodes ----
    // Par défaut la demie-journée de début est le matin et celle de fin
    // l'après-midi (staffing à la journée pleine), cf. doc "Section détail
    // de la période".
    addCreatePeriod(ev) {
        if (ev) ev.stopPropagation();
        this._periodId++;
        this.state.createPeriods.push({
            id: this._periodId,
            start: "",
            end: "",
            amount: 0,
            expanded: false,
            selected: false,
            halfDayStart: "Matin",
            halfDayEnd: "Après-midi",
            customFee: null,
            customFeeCurrency: "€",
            customCost: null,
            customCostCurrency: "€",
            status: "",
            description: "",
        });
    }

    duplicateCreatePeriod(period, ev) {
        if (ev) ev.stopPropagation();
        this._periodId++;
        const idx = this.state.createPeriods.indexOf(period);
        this.state.createPeriods.splice(idx + 1, 0, { ...period, id: this._periodId, selected: false });
        this.state.createPeriodMenuOpenId = null;
    }

    removeCreatePeriod(period, ev) {
        if (ev) ev.stopPropagation();
        const idx = this.state.createPeriods.indexOf(period);
        if (idx !== -1) {
            this.state.createPeriods.splice(idx, 1);
        }
        this.state.createPeriodMenuOpenId = null;
    }

    togglePeriodExpand(period, ev) {
        if (ev) ev.stopPropagation();
        period.expanded = !period.expanded;
    }

    get allPeriodsExpanded() {
        return this.state.createPeriods.length > 0 && this.state.createPeriods.every((p) => p.expanded);
    }

    toggleExpandAllPeriods(ev) {
        if (ev) ev.stopPropagation();
        const expand = !this.allPeriodsExpanded;
        for (const p of this.state.createPeriods) {
            p.expanded = expand;
        }
    }

    togglePeriodSelected(period, ev) {
        if (ev) ev.stopPropagation();
        period.selected = !period.selected;
    }

    get selectedPeriods() {
        return this.state.createPeriods.filter((p) => p.selected);
    }

    togglePeriodMenu(period, ev) {
        if (ev) ev.stopPropagation();
        this.state.createPeriodMenuOpenId = this.state.createPeriodMenuOpenId === period.id ? null : period.id;
    }

    isPeriodMenuOpen(period) {
        return this.state.createPeriodMenuOpenId === period.id;
    }

    // ---- Édition en masse des périodes sélectionnées ----
    openBulkEditPeriods(ev) {
        if (ev) ev.stopPropagation();
        if (!this.selectedPeriods.length) {
            return;
        }
        this.state.createBulkEdit = { amount: null, customFee: null, customFeeCurrency: "€", customCost: null, customCostCurrency: "€", status: "", description: "" };
        this.state.createBulkEditOpen = true;
    }

    closeBulkEditPeriods(ev) {
        if (ev) ev.stopPropagation();
        this.state.createBulkEditOpen = false;
    }

    deleteSelectedPeriods(ev) {
        if (ev) ev.stopPropagation();
        this.state.createPeriods = this.state.createPeriods.filter((p) => !p.selected);
    }

    applyBulkEditPeriods(ev) {
        if (ev) ev.stopPropagation();
        const edit = this.state.createBulkEdit;
        for (const period of this.selectedPeriods) {
            if (edit.amount !== null && edit.amount !== "") period.amount = edit.amount;
            if (edit.customFee !== null && edit.customFee !== "") { period.customFee = edit.customFee; period.customFeeCurrency = edit.customFeeCurrency; }
            if (edit.customCost !== null && edit.customCost !== "") { period.customCost = edit.customCost; period.customCostCurrency = edit.customCostCurrency; }
            if (edit.status) period.status = edit.status;
            if (edit.description) period.description = edit.description;
            period.selected = false;
        }
        this.state.createBulkEditOpen = false;
    }

    // ---- Section Utilisateurs ----
    get createUserSuggestions() {
        const search = this.state.createUserSearch.trim().toLowerCase();
        return USER_DIRECTORY
            .filter((name) => !this.state.createUsers.includes(name))
            .filter((name) => !search || name.toLowerCase().includes(search))
            .slice(0, 8);
    }

    addCreateUser(name, ev) {
        if (ev) ev.stopPropagation();
        this.state.createUsers.push(name);
        this.state.createUserOptions[name] = "Suggéré";
        this.state.createUserSearch = "";
    }

    removeCreateUser(name, ev) {
        if (ev) ev.stopPropagation();
        const idx = this.state.createUsers.indexOf(name);
        if (idx !== -1) {
            this.state.createUsers.splice(idx, 1);
        }
        delete this.state.createUserOptions[name];
    }

    setUserOption(name, option, ev) {
        if (ev) ev.stopPropagation();
        this.state.createUserOptions[name] = option;
    }

    focusCreateUserSearch(ev) {
        if (ev) ev.stopPropagation();
        this.state.createUserSearchFocused = true;
    }

    // ---- Section Informations ----
    get informationCount() {
        const info = this.state.createInfo;
        return ["status", "daysSold", "description", "duration", "priority"].filter((k) => info[k]).length;
    }

    // ---- Section Commentaire ----
    get commentCount() {
        return this.state.createComment.trim() ? 1 : 0;
    }
}
