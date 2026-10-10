/** @odoo-module **/

/**
 * Données factices pour le squelette de pages. Aucune connexion au
 * backend n'est faite ici volontairement (étape ultérieure).
 */

const PEOPLE = [
    "Armand AMERI", "Jeremy BARTOL", "Nour BARTOLI", "Katharina BERARDA",
    "Claire BERGER", "Timothée BOLE", "Jess BOMPARD", "Olivier BRUN",
    "Thomas CAPER", "Marie-Claire CHARON",
];

export const MOCK_DATA = {
    projects: {
        columns: [
            { key: "a_staffer", title: "Projets à staffer" },
            { key: "en_cours", title: "En cours" },
            { key: "termines", title: "Terminés" },
        ],
        cards: [
            { column: "a_staffer", title: "Refonte stratégie d'acquisition", client: "BackMarket", dates: "16/12/2024 - 22/08/2025", tags: ["3"] },
            { column: "a_staffer", title: "Audit interne", client: "Decathlon", dates: "23/12/2024 - 15/07/2025", tags: ["1"] },
            { column: "en_cours", title: "Déploiement Salesforce", client: "BNP Paribas", dates: "10/07/2023 - 27/10/2023", tags: ["2"] },
            { column: "en_cours", title: "Accompagnement Intrapreneuriat", client: "L'ORÉAL", dates: "04/2024 - 22/2024", tags: [] },
            { column: "termines", title: "Optimisation fiscale", client: "PSG", dates: "01/2024 - 03/2024", tags: [] },
        ],
    },

    requests: {
        tabs: ["À attribuer", "Obsolètes", "Tous"],
        columns: [
            { key: "project", label: "Projet" },
            { key: "position", label: "Poste" },
            { key: "period", label: "Période" },
            { key: "status", label: "Statut" },
        ],
        rows: [
            { project: "HR Process Audit", position: "Consultant Senior", period: "07/10 → 30/10", status: "À staffer" },
            { project: "Internal Audit", position: "Manager", period: "14/10 → 20/12", status: "À staffer" },
            { project: "Acquisition Strategy Redesign", position: "Directeur", period: "21/10 → 05/01", status: "À staffer" },
            { project: "Tax Optimization", position: "Consultant Junior", period: "01/11 → 28/11", status: "À staffer" },
        ],
    },

    modificationRequests: {
        tabs: ["Toutes", "En attente", "Acceptées", "Rejetées"],
        columns: [
            { key: "requester", label: "Demandé par" },
            { key: "project", label: "Projet" },
            { key: "type", label: "Type" },
            { key: "status", label: "Statut" },
        ],
        rows: [
            { requester: "Sébastien AUBRY", project: "Cajoo - Diffusion", type: "Suppression de demande", status: "En attente" },
            { requester: "Olivier BRUN", project: "ManoMano - Audit Interne", type: "Changement de période", status: "En attente" },
            { requester: "Claire BERGER", project: "AREVA - Diffusion des innovations", type: "Remplacement", status: "Acceptée" },
        ],
    },

    staffings: {
        columns: [
            { key: "person", label: "Collaborateur" },
            { key: "project", label: "Projet" },
            { key: "type", label: "Type" },
            { key: "period", label: "Période" },
        ],
        rows: PEOPLE.slice(0, 6).map((p, i) => ({
            person: p,
            project: ["BNP Paribas — Déploiement Salesforce", "L'ORÉAL — Accompagnement", "AREVA — Diffusion"][i % 3],
            type: i % 2 === 0 ? "Réel" : "Simulé",
            period: "01/0" + ((i % 9) + 1) + " → 30/0" + ((i % 9) + 1),
        })),
    },

    globalCalendar: {
        people: PEOPLE,
        weeks: ["S27", "S28", "S29", "S30", "S31", "S32"],
    },

    timesheet: {
        tabs: ["Personnel", "Équipe"],
        projects: ["BNP Paribas — Déploiement Salesforce", "Leave", "Bank holiday"],
        days: ["Lun 4", "Mar 5", "Mer 6", "Jeu 7", "Ven 8", "Sam 9", "Dim 10"],
    },

    annualEvaluations: {
        tabs: ["En cours", "Terminées"],
        columns: [
            { key: "person", label: "Évalué" },
            { key: "campaign", label: "Campagne" },
            { key: "status", label: "Statut" },
        ],
        rows: PEOPLE.slice(0, 5).map((p) => ({ person: p, campaign: "Campagne annuelle 2026", status: "En cours" })),
    },

    missionEvaluations: {
        tabs: ["Toutes", "En cours", "Terminées"],
        columns: [
            { key: "person", label: "Évalué" },
            { key: "project", label: "Projet" },
            { key: "status", label: "Statut" },
        ],
        rows: PEOPLE.slice(0, 5).map((p, i) => ({ person: p, project: "Audit 2026", status: i % 2 ? "Terminée" : "En cours" })),
    },

    careerTracks: {
        columns: [
            { key: "tracks", title: "Parcours" },
        ],
        cards: [
            { column: "tracks", title: "Sales", client: "Consultant Junior → Consultant Senior → Manager → Directeur", dates: "", tags: [] },
            { column: "tracks", title: "Data & Analytics", client: "Consultant Junior → Consultant Senior → Manager → Directeur", dates: "", tags: [] },
        ],
    },

    jobSheets: {
        columns: [
            { key: "job", label: "Fiche de poste" },
            { key: "track", label: "Parcours" },
            { key: "skills", label: "Compétences attendues" },
        ],
        rows: [
            { job: "Consultant Senior", track: "Data & Analytics", skills: "12 compétences" },
            { job: "Manager", track: "Data & Analytics", skills: "18 compétences" },
            { job: "Directeur", track: "Sales", skills: "9 compétences" },
        ],
    },

    occupationGlobale: {
        unit: "%",
        points: [
            { label: "S26", value: 42 },
            { label: "S27", value: 44 },
            { label: "S28", value: 51 },
            { label: "S29", value: 58 },
            { label: "S30", value: 63 },
            { label: "S31", value: 57 },
        ],
    },

    suiviCharge: {
        unit: "ETP",
        points: [
            { label: "S04", value: 60 },
            { label: "S05", value: 65 },
            { label: "S06", value: 58 },
            { label: "S07", value: 70 },
        ],
    },

    suiviConsomme: {
        columns: [
            { key: "person", label: "Collaborateur" },
            { key: "planned", label: "Planifié" },
            { key: "actual", label: "Réel" },
            { key: "delta", label: "Écart" },
        ],
        rows: [
            { person: "Etienne CONSTABE", planned: "18,38 MD", actual: "14,32 MD", delta: "-4,06 MD" },
            { person: "Aurore BARTOLIE", planned: "10,50 MD", actual: "9,50 MD", delta: "-1,00 MD" },
        ],
    },

    suiviFinancierGlobal: {
        unit: "k€",
        points: [
            { label: "Jan", value: 120 },
            { label: "Fév", value: 148 },
            { label: "Mar", value: 132 },
            { label: "Avr", value: 165 },
        ],
    },

    competencesGlobales: {
        unit: "pts",
        horizontal: true,
        points: [
            { label: "Angular", value: 1400 },
            { label: "Business Analyst", value: 1250 },
            { label: "English", value: 1200 },
            { label: "Python", value: 980 },
            { label: "Scrum Master", value: 860 },
        ],
    },

    competencesIndividuelles: {
        columns: [
            { key: "skill", label: "Compétence" },
            { key: "category", label: "Catégorie" },
            { key: "level", label: "Niveau" },
        ],
        rows: [
            { skill: "JavaScript", category: "Développement Web", level: "4 / 5" },
            { skill: "Scrum Master", category: "Soft Skills", level: "3 / 5" },
            { skill: "Python", category: "Data & Analytics", level: "5 / 5" },
        ],
    },

    availabilityHub: {
        people: PEOPLE.slice(0, 8),
        weeks: ["W17", "W18", "W19", "W20", "W21"],
    },

    planificationIndividuelle: {
        people: PEOPLE.slice(0, 8),
        weeks: ["Lun", "Mar", "Mer", "Jeu", "Ven"],
    },
};
