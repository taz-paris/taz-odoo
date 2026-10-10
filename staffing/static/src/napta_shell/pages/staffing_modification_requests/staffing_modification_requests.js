/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Données factices pour la page « Demandes de modifications ».
 * Reproduit la structure observée dans la documentation Napta :
 * staffing_demande-de-modification-de-staffing.md (images 01, 03, 10, 11, 12).
 *
 * Hypothèses prises faute de détail exhaustif dans la doc :
 * - Les initiales d'avatar et couleurs associées sont inventées (pas de vraies photos).
 * - Les libellés de catégorie de projet ("Formation", "Audit", ...) sont des exemples
 *   plausibles, la doc ne fige pas de liste de valeurs.
 */
const MODIFICATION_REQUESTS = [
    {
        id: "M-01",
        client: "Véolia",
        project: "Coaching - Intrapreneuriat",
        category: "Accompagnement",
        employee: { name: "Arnaud LEROY", role: "Consultant Junior - Management des organisations", initials: "AL" },
        status: "accepted",
        type: "deletion",
        startDate: "09-10-23",
        endDate: "13-10-23",
        createdDate: "18-10-23",
        requestedBy: "Sébastien AUDIBERT",
        resolvedBy: "Timothée BOLE",
        resolvedOn: "19-10-23",
        comments: 2,
    },
    {
        id: "M-02",
        client: "Véolia",
        project: "Coaching - Intrapreneuriat",
        category: "Accompagnement",
        employee: { name: "Arnaud LEROY", role: "Consultant Junior - Management des organisations", initials: "AL" },
        status: "pending",
        type: "addition",
        startDate: "15-01-24",
        endDate: "19-01-24",
        createdDate: "18-10-23",
        requestedBy: "Sébastien AUDIBERT",
        resolvedBy: "-",
        resolvedOn: "-",
        comments: 2,
    },
    {
        id: "M-03",
        client: "Soft skills",
        project: "Améliorer l'impact de ses présentations",
        category: "Formation",
        employee: { name: "Arnaud LEROY", role: "Consultant Junior - Management des organisations", initials: "AL" },
        status: "pending",
        type: "addition",
        startDate: "08-01-24",
        endDate: "12-01-24",
        createdDate: "18-10-23",
        requestedBy: "Claire BERGER",
        resolvedBy: "-",
        resolvedOn: "-",
        comments: 0,
    },
    {
        id: "M-04",
        client: "Soft skills",
        project: "Améliorer l'impact de ses présentations",
        category: "Formation",
        employee: { name: "Arnaud LEROY", role: "Consultant Junior - Management des organisations", initials: "AL" },
        status: "pending",
        type: "deletion",
        startDate: "16-10-23",
        endDate: "20-10-23",
        createdDate: "18-10-23",
        requestedBy: "Claire BERGER",
        resolvedBy: "-",
        resolvedOn: "-",
        comments: 1,
    },
    {
        id: "M-05",
        client: "INTERNE",
        project: "Amélioration de nos process RH",
        category: "Projet interne",
        employee: { name: "Timothée BOLE", role: "Consultant Senior - Data & Analytics", initials: "TB" },
        status: "pending",
        type: "deletion",
        startDate: "06-11-23",
        endDate: "10-11-23",
        createdDate: "18-10-23",
        requestedBy: "Olivier BRUN",
        resolvedBy: "-",
        resolvedOn: "-",
        comments: 0,
    },
    {
        id: "M-06",
        client: "BackMarket",
        project: "Refonte stratégie d'acquisition",
        category: "Audit",
        employee: { name: "Marie-Claire CHARON", role: "Consultant Senior - Data & Analytics", initials: "MC" },
        status: "rejected",
        type: "addition",
        startDate: "11-12-23",
        endDate: "15-12-23",
        createdDate: "18-10-23",
        requestedBy: "Jess BOMPARD",
        resolvedBy: "Timothée BOLE",
        resolvedOn: "20-10-23",
        comments: 3,
    },
    {
        id: "M-07",
        client: "ManoMano",
        project: "Audit interne",
        category: "Audit",
        employee: { name: "Olivier BRUN", role: "Consultant Junior - Management des organisations", initials: "OB" },
        status: "accepted",
        type: "deletion",
        startDate: "02-10-23",
        endDate: "03-11-23",
        createdDate: "17-10-23",
        requestedBy: "Nour BARTOLI",
        resolvedBy: "Timothée BOLE",
        resolvedOn: "18-10-23",
        comments: 0,
    },
    {
        id: "M-08",
        client: "AREVA",
        project: "Diffusion des innovations",
        category: "Accompagnement",
        employee: { name: "Claire BERGER", role: "Manager - Data & Analytics", initials: "CB" },
        status: "pending",
        type: "addition",
        startDate: "18-12-23",
        endDate: "22-12-23",
        createdDate: "18-10-23",
        requestedBy: "Armand AMERI",
        resolvedBy: "-",
        resolvedOn: "-",
        comments: 0,
    },
];

const STATUS_LABELS = {
    pending: "En attente",
    accepted: "Acceptée",
    rejected: "Rejetée",
};

const TYPE_LABELS = {
    addition: "Ajout",
    deletion: "Suppression",
};

const TABS = [
    { key: "all", label: "Toutes" },
    { key: "pending", label: "En attente" },
    { key: "accepted", label: "Acceptées" },
    { key: "rejected", label: "Rejetées" },
];

const COLUMNS = [
    { key: "client", label: "Client" },
    { key: "project", label: "Projet" },
    { key: "category", label: "Catégorie de projet" },
    { key: "employee", label: "Collaborateur impacté" },
    { key: "status", label: "Statut" },
    { key: "type", label: "Type de modification" },
    { key: "dates", label: "Date de début / fin" },
    { key: "createdDate", label: "Date de création" },
    { key: "requestedBy", label: "Demandé par" },
    { key: "comments", label: "Commentaire" },
    { key: "actions", label: "" },
];

export class StaffingModificationRequestsPage extends Component {
    static template = "staffing.StaffingModificationRequestsPage";
    static props = { page: Object };

    setup() {
        this.columns = COLUMNS;
        this.TABS = TABS;
        this.state = useState({ activeTab: "all" });
        this.infoTooltip =
            "Cette fonctionnalité permet de répondre à certaines configurations où les groupes " +
            "d'utilisateurs n'ont pas le droit de modifier les staffings. Ces groupes effectuaient " +
            "auparavant leurs demandes de modification en dehors du produit ; ils peuvent désormais " +
            "les faire directement depuis Napta. Les groupes ayant des droits de modification " +
            "peuvent voir les demandes et les accepter ou les rejeter.";
    }

    get pendingCount() {
        return MODIFICATION_REQUESTS.filter((r) => r.status === "pending").length;
    }

    get rows() {
        if (this.state.activeTab === "all") {
            return MODIFICATION_REQUESTS;
        }
        return MODIFICATION_REQUESTS.filter((r) => r.status === this.state.activeTab);
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    statusLabel(status) {
        return STATUS_LABELS[status];
    }

    typeLabel(type) {
        return TYPE_LABELS[type];
    }
}
