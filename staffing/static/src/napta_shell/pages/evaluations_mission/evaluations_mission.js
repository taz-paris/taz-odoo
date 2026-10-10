/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Données factices LOCALES à cette page (non partagées avec mock/mock_data.js).
 *
 * Reproduit la page Napta "Évaluations > Évaluations de mission" telle que
 * documentée dans modules-napta/evaluations-et-templates_evaluations-de-mission.
 */

const COLUMNS = [
    { key: "status", label: "Statut" },
    { key: "person", label: "Évalué" },
    { key: "client", label: "Client" },
    { key: "project", label: "Projet" },
    { key: "assessors", label: "Évaluateurs" },
    { key: "period", label: "Période évaluée" },
    { key: "createdAt", label: "Date de création" },
    { key: "updatedAt", label: "Dernière mise à jour" },
];

function evaluation(data) {
    return {
        status: "ongoing",
        assessors: [],
        ...data,
    };
}

const EVALUATIONS = [
    evaluation({ person: "CONSTABE Etienne", role: "Directeur - Management des organisations - Paris", client: "Kering", project: "Schéma directeur", period: "24/07/23 › 25/08/23", createdAt: "30/01/24", updatedAt: "30/01/24", assessors: [{ name: "O. BRUN", done: true }] }),
    evaluation({ person: "PETIT Céline", role: "Consultant Senior - Management des organisations - Londres", client: "EDF", project: "Audit des processus Achats", period: "24/06/24 › 06/09/24", createdAt: "22/11/23", updatedAt: "22/11/23", assessors: [{ name: "T. BOLE", done: false }] }),
    evaluation({ person: "POUILLE Virginie", role: "Consultant Junior - Data & Analytics - Paris", client: "L'ORÉAL", project: "Accompagnement - Intrapreneuriat", period: "17/06/24 › 13/09/24", createdAt: "22/11/23", updatedAt: "22/11/23", assessors: [{ name: "C. BERGER", done: true }] }),
    evaluation({ person: "RENAUD Guillaume", role: "Consultant Senior - Data & Analytics - Paris", client: "AIRBUS", project: "Réorganisation de la DSI", period: "17/06/24 › 01/11/24", createdAt: "22/11/23", updatedAt: "22/11/23", assessors: [{ name: "N. BARTOLI", done: false }] }),
    evaluation({ person: "LAPLACE Delphine", role: "Consultant Junior - Management des organisations - Londres", client: "AIRBUS", project: "Réorganisation de la DSI", period: "19/08/24 › 13/09/24", createdAt: "21/11/23", updatedAt: "21/11/23" }),
    evaluation({ person: "ROUX Nicolas", role: "Consultant Senior - Data & Analytics - Paris", client: "EDF", project: "Audit des processus Achats", period: "10/06/24 › 13/09/24", createdAt: "21/11/23", updatedAt: "21/11/23", assessors: [{ name: "J. BARTOL", done: true }] }),
    evaluation({ person: "SIMON Frédéric", role: "Consultant Junior - Management des organisations - Paris", client: "EDF", project: "Audit des processus Achats", period: "13/05/24 › 23/08/24", createdAt: "21/11/23", updatedAt: "21/11/23", assessors: [{ name: "K. BERARDA", done: true }] }),
    evaluation({ person: "MORIN Florence", role: "Consultant Senior - Data & Analytics - Paris", client: "EDF", project: "Audit des processus Achats", period: "17/06/24 › 02/08/24", createdAt: "15/11/23", updatedAt: "15/11/23", assessors: [{ name: "T. BOLE", done: false }] }),
    evaluation({ person: "MOREL Elise", role: "Consultant Senior - Management des organisations - Paris", client: "EDF", project: "Audit des processus Achats", period: "27/05/24 › 13/09/24", createdAt: "15/11/23", updatedAt: "15/11/23" }),
    evaluation({ person: "AMERI Armand", role: "Consultant Senior - Data & Analytics - Paris", client: "BackMarket", project: "Refonte stratégie d'acquisition", period: "02/01/23 › 30/06/23", status: "finished", createdAt: "01/07/23", updatedAt: "12/07/23", assessors: [{ name: "O. BRUN", done: true }] }),
    evaluation({ person: "BOMPARD Jess", role: "Consultant Junior - Stratégie - Paris", client: "PSG", project: "Optimisation fiscale", period: "03/2024 › 06/2024", status: "finished", createdAt: "01/07/24", updatedAt: "20/07/24", assessors: [{ name: "C. BERGER", done: true }] }),
];

export class EvaluationsMissionPage extends Component {
    static template = "staffing.EvaluationsMissionPage";
    static props = { page: Object };

    setup() {
        this.columns = COLUMNS;
        this.state = useState({
            tab: "all", // "all" | "ongoing" | "finished"
            sortKey: "updatedAt",
        });
    }

    setTab(tab) {
        this.state.tab = tab;
    }

    get total() {
        return EVALUATIONS.length;
    }

    get ongoingCount() {
        return EVALUATIONS.filter((e) => e.status === "ongoing").length;
    }

    get filtered() {
        if (this.state.tab === "all") {
            return EVALUATIONS;
        }
        return EVALUATIONS.filter((e) => e.status === this.state.tab);
    }

    statusLabel(status) {
        return status === "ongoing" ? "En cours" : "Terminée";
    }

    initials(name) {
        return name
            .split(" ")
            .map((p) => p[0])
            .join("")
            .slice(0, 2)
            .toUpperCase();
    }
}
