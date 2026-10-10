/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Données factices pour la page « Staffing > Calendrier global ».
 * Reproduit la structure de la capture image-01.png de
 * staffing_les-calendriers.md : une ligne par collaborateur, des colonnes
 * de semaines, des barres de staffing colorées (vert = réel, violet =
 * simulé, rouge = conflit, gris = absence / jour férié).
 *
 * Hypothèses :
 * - Les noms de projets/clients et pourcentages de charge sont inventés
 *   (inspirés du style des exemples visibles dans la doc : "LVMH - ...",
 *   "BackMarket - ...", "Orange - Audit Interne"...).
 * - La doc ne fige pas de palette violette officielle pour le "simulé" sur
 *   le calendrier global (elle y précise que la distinction réel/simulé
 *   est un style, pas une couleur dédiée) ; on reprend ici la consigne de
 *   la mission (vert = réel, violet/mauve = simulé) pour la lisibilité.
 */
const WEEKS = [
    { key: "w3", label: "S3 Janv. 2025", days: ["14", "15", "16", "17", "18"] },
    { key: "w4", label: "S4 Janv. 2025", days: ["20", "21", "22", "23", "24"] },
    { key: "w5", label: "S5 Janv./Fév. 2025", days: ["27", "28", "29", "30", "31"] },
    { key: "w6", label: "S6 Fév. 2025", days: ["3", "4", "5", "6", "7"] },
    { key: "w7", label: "S7 Fév. 2025", days: ["10", "11", "12", "13", "14"] },
    { key: "w8", label: "S8 Fév. 2025", days: ["17", "18", "19", "20", "21"] },
    { key: "w9", label: "S9 Fév./Mars 2025", days: ["24", "25", "26", "27", "28"] },
    { key: "w10", label: "S10 Mars 2025", days: ["3", "4", "5", "6", "7"] },
];

const PEOPLE = [
    {
        id: 1,
        name: "AMERI Armand",
        role: "Manager - Management des organisations - Paris",
        initials: "AA",
        bars: [
            { col: 1, span: 2, label: "LVMH - Amélioration", rate: "100%", type: "conflict" },
            { col: 6, span: 1, label: "INTERNE - Amélio...", rate: "15%", type: "conflict" },
            { col: 7, span: 1, label: "INTERNE - Amélio...", rate: "15%", type: "conflict" },
        ],
    },
    {
        id: 2,
        name: "BARBIER Gilles",
        role: "Consultant Junior - Data & Analytics - Paris",
        initials: "BG",
        bars: [
            { col: 1, span: 3, label: "BackMarket - Refonte", rate: "77%", type: "conflict" },
            { col: 4, span: 1, label: "BackMarket - Refonte", rate: "96%", type: "conflict" },
            { col: 5, span: 1, label: "Orange - Audit Interne", rate: "87%", type: "simulated" },
            { col: 6, span: 1, label: "Orange - Audit Interne", rate: "109%", type: "conflict" },
            { col: 7, span: 1, label: "Orange - Audit Interne", rate: "83%", type: "real" },
            { col: 8, span: 1, label: "Orange - Audit Interne", rate: "100%", type: "real" },
        ],
    },
    {
        id: 3,
        name: "BARTOL Jérémie",
        role: "Directeur - Data & Analytics - Paris",
        initials: "BJ",
        bars: [
            { col: 1, span: 3, label: "INTERNE - Amélioration", rate: "10%", type: "simulated" },
            { col: 4, span: 1, label: "Aircall - Audit data", rate: "75%", type: "real" },
            { col: 6, span: 2, label: "VEOLIA - Accompagnement", rate: "50%", type: "simulated" },
            { col: 8, span: 1, label: "VEOLIA - Accompagnement", rate: "50%", type: "real" },
        ],
    },
    {
        id: 4,
        name: "BARTOLIE Aurore",
        role: "Consultant Senior - Data & Analytics - Londres",
        initials: "BA",
        bars: [
            { col: 1, span: 1, label: "Aircall - Audit data", rate: "60%", type: "real" },
            { col: 2, span: 1, label: "Aircall - Audit data", rate: "60%", type: "real" },
            { col: 3, span: 1, label: "Aircall - Audit data", rate: "60%", type: "real" },
            { col: 4, span: 1, label: "Aircall - Audit data", rate: "60%", type: "real" },
            { col: 6, span: 1, label: "BNP Paribas - Dép.", rate: "48%", type: "simulated" },
            { col: 7, span: 1, label: "Aircall - Audit data", rate: "40%", type: "real" },
            { col: 8, span: 1, label: "PSG - Optimisation fiscale", rate: "100%", type: "conflict" },
        ],
    },
    {
        id: 5,
        name: "BOLE Timothée",
        role: "Consultant Senior - Data & Analytics - Paris",
        initials: "TB",
        bars: [
            { col: 1, span: 1, label: "Aircall - Audit data", rate: "40%", type: "real" },
            { col: 2, span: 1, label: "Jour férié", rate: "", type: "holiday" },
            { col: 3, span: 1, label: "Aircall - Audit data", rate: "40%", type: "real" },
            { col: 4, span: 1, label: "Aircall - Audit data", rate: "40%", type: "real" },
            { col: 5, span: 2, label: "Aircall - Audit data", rate: "33%", type: "conflict" },
        ],
    },
    {
        id: 6,
        name: "BERGER Claire",
        role: "Manager - Data & Analytics - Londres",
        initials: "CB",
        bars: [
            { col: 1, span: 2, label: "Absence", rate: "", type: "absence" },
            { col: 4, span: 1, label: "ManoMano - Audit Interne", rate: "80%", type: "real" },
            { col: 6, span: 1, label: "ManoMano - Audit Interne", rate: "80%", type: "simulated" },
            { col: 8, span: 1, label: "ManoMano - Audit Interne", rate: "80%", type: "real" },
        ],
    },
    {
        id: 7,
        name: "BOMPARD Jess",
        role: "Consultant Junior - Management des organisations - Paris",
        initials: "JB",
        bars: [
            { col: 2, span: 1, label: "Google - Audit Interne", rate: "50%", type: "simulated" },
            { col: 3, span: 1, label: "Google - Audit Interne", rate: "50%", type: "simulated" },
            { col: 5, span: 3, label: "Decathlon - Diffusion", rate: "25%", type: "real" },
        ],
    },
];

const LEGEND = [
    { type: "real", label: "Staffing réel" },
    { type: "simulated", label: "Staffing simulé" },
    { type: "conflict", label: "Conflit (charge > 100%)" },
    { type: "absence", label: "Absence / Jour férié" },
];

export class StaffingGlobalCalendarPage extends Component {
    static template = "staffing.StaffingGlobalCalendarPage";
    static props = { page: Object };

    setup() {
        this.weeks = WEEKS;
        this.people = PEOPLE;
        this.legend = LEGEND;
        this.state = useState({ sort: "user" });
        this.rightsTooltip =
            "L'utilisateur connecté ne peut voir que les utilisateurs et les projets que ses " +
            "droits lui permettent de voir. Les périodes en conflit (charge supérieure à 100% " +
            "d'occupation) sont affichées en rouge.";
        this.interactionTooltip =
            "Clic gauche sur une période : ouvre une pop-in d'informations et d'actions " +
            "(éditer, répéter, dupliquer, décaler, découper, rattacher à un autre projet, passer " +
            "en réel/simulé, supprimer). Double-clic : modification rapide de la période. " +
            "Glisser-déposer une période pour la décaler ou l'étendre (Échap pour annuler).";
    }
}
