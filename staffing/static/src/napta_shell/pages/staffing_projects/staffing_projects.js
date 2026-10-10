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

export class StaffingProjectsPage extends Component {
    static template = "staffing.StaffingProjectsPage";
    static props = { page: Object };

    setup() {
        this.columns = COLUMNS;
        this.tableColumns = TABLE_COLUMNS;
        this.filterSections = FILTER_SECTIONS;
        this.cardMenuItems = CARD_MENU_ITEMS;
        this.detailTabs = DETAIL_TABS;

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
        });

        this.exportTooltip = "Exporter les projets (.xlsx ou .csv)";
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
