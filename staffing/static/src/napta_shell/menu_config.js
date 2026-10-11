/** @odoo-module **/

/**
 * Métadonnées des pages Napta, indexées par clé.
 *
 * La navigation elle-même est portée par de vrais menus Odoo (voir
 * views/napta_shell_menus.xml) : chaque entrée de menu déclenche une action
 * cliente ir.actions.client distincte (tag "staffing.napta_shell_action")
 * dont les params contiennent {'napta_page': '<clé>'}. NaptaShell lit cette
 * clé et résout le composant correspondant via pages/registry.js.
 *
 * Ce fichier ne sert donc plus qu'à fournir au composant de page le "page"
 * prop (subtitle/tabs/layout/mock) — les labels/groupes affichés dans le
 * menu sont définis directement dans le XML.
 *
 * Pour ajouter une page : ajouter une entrée ici, construire son composant
 * dans pages/ et l'enregistrer dans pages/registry.js, puis déclarer son
 * action + menuitem dans napta_shell_menus.xml.
 */
export const NAPTA_PAGES = {
    "staffing.projects": {
        label: "Projets",
        layout: "cards",
        mock: "projects",
        subtitle: "Vue Cartes / Tableau de tous les projets de l'application.",
    },
    "staffing.requests": {
        label: "Demandes",
        layout: "table",
        mock: "requests",
        subtitle: "Cockpit central pour lister, filtrer, prioriser et traiter les demandes.",
        tabs: ["À attribuer", "Obsolètes", "Tous"],
    },
    "staffing.modification_requests": {
        label: "Demandes de modifications",
        layout: "table",
        mock: "modificationRequests",
        subtitle: "Demandes de modification d'un staffing déjà créé.",
        tabs: ["Toutes", "En attente", "Acceptées", "Rejetées"],
    },
    "staffing.staffings": {
        label: "Staffings",
        layout: "table",
        mock: "staffings",
        subtitle: "Liste des affectations réelles et simulées des collaborateurs.",
    },
    "staffing.global_calendar": {
        label: "Calendrier global",
        layout: "calendar",
        mock: "globalCalendar",
        subtitle: "Vue calendrier de l'ensemble des collaborateurs et de leurs staffings.",
    },
    "timesheets.timesheet": {
        label: "Feuilles de temps",
        layout: "calendar",
        mock: "timesheet",
        subtitle: "Saisie et suivi du temps passé sur les projets, vues Personnelle et Équipe.",
        tabs: ["Personnel", "Équipe"],
    },
    "evaluations.mission": {
        label: "Évaluations de mission",
        layout: "table",
        mock: "missionEvaluations",
        subtitle: "Évaluations réalisées à la fin ou pendant une mission.",
        tabs: ["Toutes", "En cours", "Terminées"],
    },
    "reports.occupation_globale": {
        label: "Occupation globale",
        layout: "chart",
        mock: "occupationGlobale",
        subtitle: "Évolution du pourcentage d'occupation mensuel des collaborateurs.",
    },
    "reports.planification_individuelle": {
        label: "Planification individuelle",
        layout: "calendar",
        mock: "planificationIndividuelle",
        subtitle: "Planning détaillé jour par jour pour chaque collaborateur.",
    },
    "reports.availability_hub": {
        label: "Availability Hub",
        layout: "calendar",
        mock: "availabilityHub",
        subtitle: "Trouver rapidement les personnes disponibles et comprendre pourquoi.",
    },
    "reports.suivi_charge": {
        label: "Suivi de la charge",
        layout: "chart",
        mock: "suiviCharge",
        subtitle: "Charge en ETP des demandes face à la capacité totale de l'organisation.",
    },
    "reports.suivi_consomme": {
        label: "Suivi du consommé",
        layout: "table",
        mock: "suiviConsomme",
        subtitle: "Comparaison entre le temps planifié et le temps réellement saisi.",
    },
    "reports.suivi_financier_global": {
        label: "Suivi financier global",
        layout: "chart",
        mock: "suiviFinancierGlobal",
        subtitle: "Indicateurs financiers consolidés : CA, coût, marge, TJM.",
    },
    "reports.competences_globales": {
        label: "Compétences globales",
        layout: "chart",
        mock: "competencesGlobales",
        subtitle: "Répartition et tendances des compétences au niveau de l'organisation.",
    },
    "reports.competences_individuelles": {
        label: "Compétences individuelles",
        layout: "table",
        mock: "competencesIndividuelles",
        subtitle: "Détail des compétences évaluées pour chaque collaborateur.",
    },
};

/** Résout la page active ({key: page}) à partir de sa clé ; conservé pour la forme de l'ancien buildPageIndex(). */
export function buildPageIndex() {
    return NAPTA_PAGES;
}
