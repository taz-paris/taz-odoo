/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Données factices propres à cette page (aucune connexion au backend).
 * Reproduit la grille ISR "Planification individuelle" : Personne x
 * Semaines, avec panneaux Vues / Filtre / Colonnes / Paramètres
 * d'affichage et détail dépliable par personne.
 */
const WEEK_COLUMNS = [
    { key: "w30", label: "S30", date: "21 juil." },
    { key: "w31", label: "S31", date: "28 juil." },
    { key: "w32", label: "S32", date: "4 août" },
    { key: "w33", label: "S33", date: "11 août" },
    { key: "w34", label: "S34", date: "18 août" },
    { key: "w35", label: "S35", date: "25 août" },
];

const PEOPLE_ROWS = [
    { id: "ameri", name: "Armand AMERI", initials: "AA", notes: "Vérifier la sur-dotation", notesAlert: true, availability: "22/09/2025", weeks: [50, 102, 102, 122, 153, 153] },
    { id: "bartol", name: "Jeremy BARTOL", initials: "JB", notes: "", availability: "18/08/2025", weeks: [87, 87, 87, 95, 65, 96] },
    { id: "bartoli", name: "Nour BARTOLI", initials: "NB", notes: "", today: true, lastAssignment: "Dernière affectation il y a 6 jours", weeks: [60, 0, 120, 60, 0, 20] },
    { id: "berarda", name: "Katharina BERARDA", initials: "KB", notes: "", availability: "19/01/2026", weeks: [85, 85, 85, 100, 73, 143] },
    { id: "berger", name: "Claire BERGER", initials: "CB", notes: "", availability: "06/10/2025", weeks: [98, 98, 98, 60, 98, 98] },
    { id: "bompard", name: "Jess BOMPARD", initials: "JB", notes: "Demande de transfert", availability: "18/08/2025", weeks: [139, 139, 139, 131, 39, 39] },
    { id: "boyle", name: "Timothy BOYLE", initials: "TB", notes: "", today: true, lastAssignment: "Dernière affectation il y a 1 jour", weeks: [100, 10, 313, 173, 113, 159] },
    { id: "brun", name: "Olivier BRUN", initials: "OB", notes: "Équipe prioritaire Bruno", availability: "20/10/2025", weeks: [98, 100, 156, 96, 96, 96] },
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
        { client: "AIRCALL", project: "Audit data", simulated: false },
        { client: "INTERNE", project: "Amélioration des process de déploiement", simulated: false },
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
        project: "Audit interne",
        simulated: true,
        cells: person.weeks.map((w, i) => (i === person.weeks.length - 2 ? Math.round(w * 0.2) : null)),
    });
    rows.push({
        client: "APPLE",
        project: "Refonte stratégie d'acquisition",
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
