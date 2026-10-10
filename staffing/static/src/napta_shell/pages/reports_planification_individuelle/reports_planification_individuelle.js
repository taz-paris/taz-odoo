/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Données factices propres à cette page (aucune connexion au backend).
 * Reproduit la grille ISR "Planification individuelle" : Personne x
 * Semaines, avec panneaux Vues / Filtre / Colonnes / Paramètres
 * d'affichage et détail dépliable par personne.
 */
const WEEK_COLUMNS = [
    { key: "w30", label: "W30", date: "Jul 21" },
    { key: "w31", label: "W31", date: "Jul 28" },
    { key: "w32", label: "W32", date: "Aug 4" },
    { key: "w33", label: "W33", date: "Aug 11" },
    { key: "w34", label: "W34", date: "Aug 18" },
    { key: "w35", label: "W35", date: "Aug 25" },
];

const PEOPLE_ROWS = [
    { id: "ameri", name: "Armand AMERI", initials: "AA", notes: "Check for overstaffing", notesAlert: true, availability: "22/09/2025", weeks: [50, 102, 102, 122, 153, 153] },
    { id: "bartol", name: "Jeremy BARTOL", initials: "JB", notes: "", availability: "18/08/2025", weeks: [87, 87, 87, 95, 65, 96] },
    { id: "bartoli", name: "Nour BARTOLI", initials: "NB", notes: "", today: true, lastAssignment: "Last assignment 6 days ago", weeks: [60, 0, 120, 60, 0, 20] },
    { id: "berarda", name: "Katharina BERARDA", initials: "KB", notes: "", availability: "19/01/2026", weeks: [85, 85, 85, 100, 73, 143] },
    { id: "berger", name: "Claire BERGER", initials: "CB", notes: "", availability: "06/10/2025", weeks: [98, 98, 98, 60, 98, 98] },
    { id: "bompard", name: "Jess BOMPARD", initials: "JB", notes: "Transfer request", availability: "18/08/2025", weeks: [139, 139, 139, 131, 39, 39] },
    { id: "boyle", name: "Timothy BOYLE", initials: "TB", notes: "", today: true, lastAssignment: "Last assignment 1 day ago", weeks: [100, 10, 313, 173, 113, 159] },
    { id: "brun", name: "Olivier BRUN", initials: "OB", notes: "Priority team Bruno", availability: "20/10/2025", weeks: [98, 100, 156, 96, 96, 96] },
];

/** Classe de couleur par seuil, identique à la légende du rapport. */
function thresholdClass(value) {
    if (value >= 101) {
        return "o_pi_cell_red";
    } else if (value >= 90) {
        return "o_pi_cell_green";
    } else if (value >= 50) {
        return "o_pi_cell_amber";
    }
    return "o_pi_cell_purple";
}

/** Génère un détail de calendrier déplié, dérivé des valeurs de la ligne. */
function buildDetailRows(person) {
    const clients = [
        { client: "AIRCALL", project: "Data Audit", simulated: false },
        { client: "INTERNAL", project: "Deployment Process Improvement", simulated: false },
    ];
    const rows = clients.map((c, idx) => ({
        ...c,
        cells: person.weeks.map((w, i) => {
            if (i === 0 && idx === 1) {
                return null;
            }
            const share = idx === 0 ? 0.65 : 0.35;
            return Math.round(w * share) || null;
        }),
    }));
    rows.push({
        client: "Decathlon",
        project: "Internal Audit",
        simulated: true,
        cells: person.weeks.map((w, i) => (i === person.weeks.length - 2 ? Math.round(w * 0.2) : null)),
    });
    rows.push({
        client: "APPLE",
        project: "Acquisition Strategy Redesign",
        simulated: false,
        highlight: true,
        cells: person.weeks.map((w) => Math.round(w * 0.3) || null),
    });
    return rows;
}

export class ReportsPlanificationIndividuellePage extends Component {
    static template = "staffing.ReportsPlanificationIndividuellePage";
    static props = { page: Object };

    setup() {
        this.weekColumns = WEEK_COLUMNS;
        this.people = PEOPLE_ROWS;

        this.state = useState({
            activeTab: "users",
            openMenu: null, // 'views' | 'filter' | 'columns' | 'display' | 'date' | null
            legendOpen: false,
            expanded: {},
        });

        this.notesTooltip =
            "Les utilisateurs autorisés peuvent voir et modifier le champ Notes directement depuis le rapport ou depuis le profil utilisateur.";
        this.downloadTooltip = "Exporter les données (.xlsx ou .csv)";
        this.dailyCostTooltip =
            "Coût journalier de l'utilisateur. Dans l'export avancé, une moyenne pondérée par le nombre de jours travaillés est calculée si le taux change sur la période.";
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    toggleMenu(menu) {
        this.state.openMenu = this.state.openMenu === menu ? null : menu;
        this.state.legendOpen = false;
    }

    toggleLegend() {
        this.state.legendOpen = !this.state.legendOpen;
        this.state.openMenu = null;
    }

    toggleRow(personId) {
        this.state.expanded[personId] = !this.state.expanded[personId];
    }

    isExpanded(personId) {
        return !!this.state.expanded[personId];
    }

    cellClass(value) {
        return thresholdClass(value);
    }

    detailRows(person) {
        return buildDetailRows(person);
    }
}
