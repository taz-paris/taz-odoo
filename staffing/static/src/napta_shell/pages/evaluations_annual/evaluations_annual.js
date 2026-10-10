/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Données factices LOCALES à cette page (non partagées avec mock/mock_data.js).
 *
 * Reproduit la page Napta "Évaluations > Évaluations annuelles" telle que
 * documentée dans modules-napta/evaluations-et-templates_evaluations-annuelles
 * et la section "Évaluations annuelles" de
 * modules-napta/evaluations-et-templates_evaluations-et-templates.
 */

const COLUMNS = [
    { key: "status", label: "Statut" },
    { key: "person", label: "Évalué" },
    { key: "campaign", label: "Nom de la campagne" },
    { key: "assessors", label: "Évaluateurs" },
    { key: "period", label: "Période évaluée" },
    { key: "createdAt", label: "Créée le" },
    { key: "updatedAt", label: "Mise à jour le" },
];

function evaluation(data) {
    return {
        status: "Ongoing",
        assessors: [],
        ...data,
    };
}

const EVALUATIONS = [
    evaluation({ person: "RENAUD Guillaume", role: "Senior - Data & Analytics - Paris", campaign: "Campagne annuelle 2026", period: "27/10/22 › 27/10/23", createdAt: "22/11/23", updatedAt: "27/02/24" }),
    evaluation({ person: "PECH Olivier", role: "Junior - Data & Analytics - Londres", campaign: "Campagne annuelle 2026", period: "27/10/22 › 27/10/23", createdAt: "27/10/23", updatedAt: "15/11/23", assessors: [{ name: "C. BERGER", done: true }] }),
    evaluation({ person: "MORIN Florence", role: "Senior - Data & Analytics - Paris", campaign: "Campagne annuelle 2026", period: "27/10/22 › 27/10/23", createdAt: "15/11/23", updatedAt: "15/11/23", assessors: [{ name: "T. BOLE", done: true }] }),
    evaluation({ person: "MOREL Elise", role: "Senior - Change Management - Paris", campaign: "Campagne annuelle 2026", period: "27/10/22 › 27/10/23", createdAt: "15/11/23", updatedAt: "15/11/23" }),
    evaluation({ person: "TEIXEIRA Julia", role: "Junior - Data & Analytics - Londres", campaign: "Campagne annuelle 2026", period: "27/10/22 › 27/10/23", createdAt: "15/11/23", updatedAt: "15/11/23" }),
    evaluation({ person: "MASON Robert", role: "Junior - Data & Analytics - Paris", campaign: "Campagne annuelle 2026", period: "27/10/22 › 27/10/23", createdAt: "27/10/23", updatedAt: "15/11/23", assessors: [{ name: "O. BRUN", done: true }, { name: "N. BARTOLI", done: false }] }),
    evaluation({ person: "MARTIN Pierre", role: "Director - Change Management - Paris", campaign: "Campagne annuelle 2026", period: "27/10/22 › 27/10/23", createdAt: "08/11/23", updatedAt: "15/11/23" }),
    evaluation({ person: "MARCHAND Laurence", role: "Junior - Data & Analytics - Londres", campaign: "Campagne annuelle 2026", period: "27/10/22 › 27/10/23", createdAt: "08/11/23", updatedAt: "15/11/23" }),
    evaluation({ person: "LEROY Paul", role: "Senior - Change Management - Paris", campaign: "Campagne annuelle 2026", period: "27/10/22 › 27/10/23", createdAt: "08/11/23", updatedAt: "15/11/23" }),
    evaluation({ person: "VINCENT Anthony", role: "Junior - Data & Analytics - Londres", campaign: "Campagne annuelle 2026", period: "27/10/22 › 27/10/23", createdAt: "03/11/23", updatedAt: "03/11/23", assessors: [{ name: "K. BERARDA", done: true }] }),
    evaluation({ person: "BERGER Claire", role: "Manager - Data & Analytics - Paris", campaign: "Campagne annuelle 2025", period: "27/10/21 › 27/10/22", status: "Finished", createdAt: "10/11/22", updatedAt: "02/12/22" }),
    evaluation({ person: "BRUN Olivier", role: "Senior - Stratégie - Paris", campaign: "Campagne annuelle 2025", period: "27/10/21 › 27/10/22", status: "Finished", createdAt: "08/11/22", updatedAt: "29/11/22" }),
];

export class EvaluationsAnnualPage extends Component {
    static template = "staffing.EvaluationsAnnualPage";
    static props = { page: Object };

    setup() {
        this.columns = COLUMNS;
        this.state = useState({
            tab: "ongoing", // "ongoing" | "finished"
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
        return EVALUATIONS.filter((e) => e.status === "Ongoing").length;
    }

    get filtered() {
        const status = this.state.tab === "ongoing" ? "Ongoing" : "Finished";
        return EVALUATIONS.filter((e) => e.status === status);
    }

    statusLabel(status) {
        return status === "Ongoing" ? "En cours" : "Clôturée";
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
