/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { AssignmentDrawer } from "../../components/assignment_drawer/assignment_drawer";

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

export class StaffingRequestsPage extends Component {
    static template = "staffing.StaffingRequestsPage";
    static props = { page: Object };
    static components = { AssignmentDrawer };

    setup() {
        this.tableColumns = TABLE_COLUMNS;
        this.tabs = TABS;
        this.filterSections = FILTER_SECTIONS;
        this.columnsMenu = COLUMNS_MENU;
        this.projectOptions = PROJECT_OPTIONS;

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
            // Tiroir mutualisé de création/édition (components/assignment_drawer) :
            // { mode: "create"|"edit", record: Object|null } ou null si fermé.
            assignmentDrawer: null,
            // Tiroir "Créer plusieurs demandes" : flux spécifique (upload PDF +
            // analyse IA groupée), distinct du tiroir mutualisé ci-dessus.
            bulkCreateOpen: false,
            bulkNeed: "",
            bulkProject: "",
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

    // ---- Tiroir mutualisé "Créer / Modifier une demande" ----
    // (components/assignment_drawer/assignment_drawer.js — partagé avec
    // Staffing > Staffings pour l'édition d'un staffing).
    openCreateRequestDrawer(ev) {
        if (ev) ev.stopPropagation();
        this.closeMenus();
        this.state.assignmentDrawer = { mode: "create", record: null };
    }

    openEditRequestDrawer(row, ev) {
        if (ev) ev.stopPropagation();
        this.state.assignmentDrawer = { mode: "edit", record: row };
    }

    closeAssignmentDrawer() {
        this.state.assignmentDrawer = null;
    }

    get assignmentDrawerKey() {
        const d = this.state.assignmentDrawer;
        return d ? d.mode + "-" + (d.record ? d.record.id : "new") : "";
    }

    // ---- Tiroir "Créer plusieurs demandes" (flux PDF + IA, non mutualisé) ----
    openBulkCreateDrawer(ev) {
        if (ev) ev.stopPropagation();
        this.closeMenus();
        this.state.bulkCreateOpen = true;
        this.state.bulkNeed = "";
        this.state.bulkProject = "";
    }

    closeBulkCreateDrawer() {
        this.state.bulkCreateOpen = false;
    }
}
