/** @odoo-module **/

/**
 * Arborescence du menu latéral façon Napta.
 *
 * Chaque entrée "inert" (inert: true) est affichée pour fidélité visuelle
 * mais n'est pas navigable : seules les entrées des groupes Staffing,
 * Feuilles de temps, Évaluations, Carrière et Rapports sont actives.
 *
 * Pour ajouter une page : ajouter une ligne dans "items" du bon groupe,
 * puis une entrée correspondante dans mock/mock_data.js si besoin.
 */
export const NAPTA_MENU = [
    { key: "search", label: "Rechercher", icon: "fa-search", inert: true },
    { key: "people", label: "Collaborateurs", icon: "fa-user-o", inert: true },

    {
        key: "staffing",
        label: "Staffing",
        icon: "fa-calendar",
        items: [
            {
                key: "staffing.projects",
                label: "Projets",
                layout: "cards",
                mock: "projects",
                subtitle: "Vue Cartes / Tableau de tous les projets de l'application.",
            },
            {
                key: "staffing.requests",
                label: "Demandes",
                layout: "table",
                mock: "requests",
                subtitle: "Cockpit central pour lister, filtrer, prioriser et traiter les demandes.",
                tabs: ["À attribuer", "Obsolètes", "Tous"],
            },
            {
                key: "staffing.modification_requests",
                label: "Demandes de modifications",
                layout: "table",
                mock: "modificationRequests",
                subtitle: "Demandes de modification d'un staffing déjà créé.",
                tabs: ["Toutes", "En attente", "Acceptées", "Rejetées"],
            },
            {
                key: "staffing.staffings",
                label: "Staffings",
                layout: "table",
                mock: "staffings",
                subtitle: "Liste des affectations réelles et simulées des collaborateurs.",
            },
            {
                key: "staffing.global_calendar",
                label: "Calendrier global",
                layout: "calendar",
                mock: "globalCalendar",
                subtitle: "Vue calendrier de l'ensemble des collaborateurs et de leurs staffings.",
            },
        ],
    },

    {
        key: "timesheets",
        label: "Feuilles de temps",
        icon: "fa-clock-o",
        page: {
            key: "timesheets.timesheet",
            label: "Feuilles de temps",
            layout: "calendar",
            mock: "timesheet",
            subtitle: "Saisie et suivi du temps passé sur les projets, vues Personnelle et Équipe.",
            tabs: ["Personnel", "Équipe"],
        },
    },

    {
        key: "evaluations",
        label: "Évaluations",
        icon: "fa-pencil",
        items: [
            {
                key: "evaluations.annual",
                label: "Évaluations annuelles",
                layout: "table",
                mock: "annualEvaluations",
                subtitle: "Campagnes d'évaluation annuelle des collaborateurs.",
                tabs: ["En cours", "Terminées"],
            },
            {
                key: "evaluations.mission",
                label: "Évaluations de mission",
                layout: "table",
                mock: "missionEvaluations",
                subtitle: "Évaluations réalisées à la fin ou pendant une mission.",
                tabs: ["Toutes", "En cours", "Terminées"],
            },
        ],
    },

    {
        key: "career",
        label: "Carrière",
        icon: "fa-graduation-cap",
        items: [
            {
                key: "career.career_tracks",
                label: "Parcours professionnels",
                layout: "cards",
                mock: "careerTracks",
                subtitle: "Parcours formés de plusieurs fiches métiers ordonnées.",
            },
            {
                key: "career.job_sheets",
                label: "Fiches de poste",
                layout: "table",
                mock: "jobSheets",
                subtitle: "Compétences et niveaux attendus pour chaque poste de l'entreprise.",
            },
        ],
    },

    {
        key: "reports",
        label: "Rapports",
        icon: "fa-bar-chart",
        items: [
            {
                key: "reports.occupation_globale",
                label: "Occupation globale",
                layout: "chart",
                mock: "occupationGlobale",
                subtitle: "Évolution du pourcentage d'occupation mensuel des collaborateurs.",
            },
            {
                key: "reports.planification_individuelle",
                label: "Planification individuelle",
                layout: "calendar",
                mock: "planificationIndividuelle",
                subtitle: "Planning détaillé jour par jour pour chaque collaborateur.",
            },
            {
                key: "reports.availability_hub",
                label: "Availability Hub",
                layout: "calendar",
                mock: "availabilityHub",
                subtitle: "Trouver rapidement les personnes disponibles et comprendre pourquoi.",
            },
            {
                key: "reports.suivi_charge",
                label: "Suivi de la charge",
                layout: "chart",
                mock: "suiviCharge",
                subtitle: "Charge en ETP des demandes face à la capacité totale de l'organisation.",
            },
            {
                key: "reports.suivi_consomme",
                label: "Suivi du consommé",
                layout: "table",
                mock: "suiviConsomme",
                subtitle: "Comparaison entre le temps planifié et le temps réellement saisi.",
            },
            {
                key: "reports.suivi_financier_global",
                label: "Suivi financier global",
                layout: "chart",
                mock: "suiviFinancierGlobal",
                subtitle: "Indicateurs financiers consolidés : CA, coût, marge, TJM.",
            },
            {
                key: "reports.competences_globales",
                label: "Compétences globales",
                layout: "chart",
                mock: "competencesGlobales",
                subtitle: "Répartition et tendances des compétences au niveau de l'organisation.",
            },
            {
                key: "reports.competences_individuelles",
                label: "Compétences individuelles",
                layout: "table",
                mock: "competencesIndividuelles",
                subtitle: "Détail des compétences évaluées pour chaque collaborateur.",
            },
        ],
    },

    { key: "dashboards", label: "Dashboards", icon: "fa-th-large", badge: "NEW", inert: true },
    { key: "notifications", label: "Notifications", icon: "fa-bell-o", inert: true },
    { key: "help", label: "Aide", icon: "fa-question-circle-o", inert: true },
    { key: "administration", label: "Administration", icon: "fa-cog", inert: true },
];

/** Index à plat {key: page} pour résoudre une page depuis son activeKey. */
export function buildPageIndex() {
    const index = {};
    for (const group of NAPTA_MENU) {
        if (group.items) {
            for (const page of group.items) {
                index[page.key] = { ...page, groupLabel: group.label };
            }
        } else if (group.page) {
            index[group.page.key] = { ...group.page, groupLabel: group.label };
        }
    }
    return index;
}
