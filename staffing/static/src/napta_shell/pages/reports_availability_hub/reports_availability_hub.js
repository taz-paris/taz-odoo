/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Données factices propres à cette page (aucune connexion au backend).
 * Reproduit l'Availability Hub : seuil cible de disponibilité, plage de
 * dates glissante, paramètres d'affichage et tableau Personnes x Semaines
 * avec panneau de détails et suggestions "Scenario Architect".
 */
const WEEK_COLUMNS = [
    { key: "w17", label: "W17", date: "24 Apr", current: true },
    { key: "w18", label: "W18", date: "27 Apr" },
    { key: "w19", label: "W19", date: "4 May" },
    { key: "w20", label: "W20", date: "11 May" },
    { key: "w21", label: "W21", date: "18 May" },
    { key: "w22", label: "W22", date: "25 May" },
    { key: "w23", label: "W23", date: "1 Jun" },
];

const PEOPLE_ROWS = [
    { id: "hernandez", name: "Leah HERNANDEZ", initials: "LH", lastStaffing: "0 days ago", firstAvailability: "Today", weeks: [75, 50, 70, 100, 100, 71, 77] },
    {
        id: "zyvel", name: "Luca ZYVEL", initials: "LZ", lastStaffing: "-", firstAvailability: "Today", weeks: [100, 80, 80, 80, 100, 80, 100],
        hasDetail: true,
        suggestions: [
            { label: "AIRBUS — ISD Reorganization", weekIndex: 5, value: 40 },
            { label: "INTERNAL — Open a new Agency", weekIndex: 5, value: 100 },
        ],
    },
    { id: "zamora", name: "Sofia ZAMORA", initials: "SZ", lastStaffing: "-", firstAvailability: "Today", weeks: [100, 100, 80, 100, 100, 100, 100] },
    { id: "dev_virtual", name: "Dev Virtual", initials: "DV", virtual: true, lastStaffing: "-", firstAvailability: "Today", weeks: [100, 100, 100, 100, 100, 100, 100] },
    { id: "data_analyst_virtual", name: "Data Analyst Virtual", initials: "DA", virtual: true, lastStaffing: "-", firstAvailability: "Today", weeks: [100, 100, 100, 100, 100, 100, 100] },
    { id: "scott", name: "James SCOTT", initials: "JS", lastStaffing: "-", firstAvailability: "29/04/2026", weeks: [0, 60, 20, 100, 100, 100, 100] },
    { id: "ferris", name: "Thomas FERRIS", initials: "TF", lastStaffing: "-", firstAvailability: "05/05/2026", weeks: [0, 0, 50, 68, 68, 68, 68] },
    { id: "vincent", name: "Anthony VINCENT", initials: "AV", lastStaffing: "-", firstAvailability: "05/05/2026", weeks: [0, 0, 20, 100, 100, 100, 100] },
    { id: "teixeira", name: "Julia TEIXEIRA", initials: "JT", lastStaffing: "-", firstAvailability: "06/05/2026", weeks: [0, 0, 65, 100, 100, 100, 100] },
    { id: "leclerc", name: "Nathalie LECLERC", initials: "NL", lastStaffing: "-", firstAvailability: "06/05/2026", weeks: [0, 0, 65, 100, 100, 100, 85] },
    {
        id: "rossi", name: "Serena ROSSI", initials: "SR", lastStaffing: "-", firstAvailability: "12/05/2026", weeks: [0, 0, 0, 80, 95, 95, 95],
        profile: {
            jobPosition: "Senior",
            businessUnit: "Change Management",
            office: "London",
            dailyCost: "€357",
            contractType: "Internal",
            certifications: ["IFRS", "CloudFormation", "US GAAP"],
            skills: [
                { label: "Model optimisation", rating: 5 },
                { label: "Google Ads", rating: 5 },
                { label: "Agile CRM", rating: 5 },
                { label: "PowerPoint", rating: 5 },
                { label: "Reporting", rating: 4 },
            ],
            summary: "Autonomous, rigorous, and possessing excellent interpersonal skills, Serena has strong Audit and Analysis skills, mostly in the banking sector, allowing work with multidisciplinary teams.",
            lastExperience: "Senior Consultant",
        },
    },
];

const DEFAULT_PROFILE = {
    jobPosition: "Consultant",
    businessUnit: "Operations",
    office: "Paris",
    dailyCost: "€—",
    contractType: "Internal",
    certifications: [],
    skills: [],
    summary: "Aucun résumé professionnel renseigné pour ce profil.",
    lastExperience: "—",
};

/** Classe de couleur par seuil de disponibilité (même légende que le ISR). */
function availabilityClass(value) {
    if (value <= 0) {
        return "o_ah_cell_zero";
    } else if (value <= 50) {
        return "o_ah_cell_mid";
    }
    return "o_ah_cell_high";
}

export class ReportsAvailabilityHubPage extends Component {
    static template = "staffing.ReportsAvailabilityHubPage";
    static props = { page: Object };

    setup() {
        this.weekColumns = WEEK_COLUMNS;
        this.people = PEOPLE_ROWS;

        this.state = useState({
            openMenu: null, // 'views' | 'filter' | 'availability' | 'columns' | 'display' | 'horizon'
            legendOpen: false,
            expanded: { zyvel: true },
            selectedPersonId: "rossi",
            threshold: 50,
            horizonValue: 6,
            horizonUnit: "Weeks",
        });

        this.currentWeekTooltip = "Semaine en cours.";
    }

    get availablePeopleCount() {
        return this.people.filter((p) => p.weeks.some((w) => w >= this.state.threshold)).length;
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

    selectPerson(personId) {
        this.state.selectedPersonId = this.state.selectedPersonId === personId ? null : personId;
    }

    closeDetails() {
        this.state.selectedPersonId = null;
    }

    get selectedPerson() {
        return this.people.find((p) => p.id === this.state.selectedPersonId) || null;
    }

    get selectedProfile() {
        const person = this.selectedPerson;
        return (person && person.profile) || DEFAULT_PROFILE;
    }

    selectAdjacent(offset) {
        const ids = this.people.map((p) => p.id);
        const idx = ids.indexOf(this.state.selectedPersonId);
        if (idx === -1) {
            return;
        }
        const nextIdx = Math.min(Math.max(idx + offset, 0), ids.length - 1);
        this.state.selectedPersonId = ids[nextIdx];
    }

    cellClass(value) {
        return availabilityClass(value);
    }
}
