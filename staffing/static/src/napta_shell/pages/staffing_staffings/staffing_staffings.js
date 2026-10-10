/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { AssignmentDrawer } from "../../components/assignment_drawer/assignment_drawer";

/**
 * Données factices pour la page « Staffing > Staffings ».
 * Reproduit la liste observée dans staffing_staffings.md (image-18) :
 * Projet / Collaborateur staffé / Statut de staffing / Période / Indicateurs
 * clés / Poste / Département / Bureau / Type de contrat.
 *
 * Hypothèses :
 * - "Statut facturable" (demandé explicitement par la mission) n'apparaît pas
 *   tel quel dans la doc staffing_staffings.md mais correspond au badge
 *   "Facturé" visible au niveau des tiroirs d'édition de période
 *   (staffing_les-calendriers.md, image-03 : "📑 Facturé"). On l'ajoute donc
 *   comme colonne dédiée.
 * - Les valeurs des indicateurs clés (charge vendue, reste à planifier,
 *   dérive de date) sont inventées mais plausibles.
 */
const STAFFINGS = [
    {
        id: 1,
        project: "Aircall", subproject: "Audit data",
        employee: { name: "Arnaude BRUN", role: "Consultant Junior - Data & Analytics - Londres", initials: "AB" },
        kind: "real",
        status: "en_cours",
        period: "15/01/24 → 08/03/24",
        rate: "40% (16 jours)",
        indicators: { sold: "0 JH", remaining: "-16 JH", drift: "0 JH" },
        position: "Consultant Junior",
        department: "Data & Analytics",
        office: "Londres",
        contract: "CDI",
        billable: true,
    },
    {
        id: 2,
        project: "PSG", subproject: "Refonte des process commerciaux",
        employee: { name: "Arnaude BRUN", role: "Consultant Junior - Data & Analytics - Londres", initials: "AB" },
        kind: "simulated",
        status: "futur",
        period: "15/01/24 → 29/03/24",
        rate: "41% (21.6 jours)",
        indicators: { sold: "0 JH", remaining: "-21.6 JH", drift: "0 JH" },
        position: "Consultant Junior",
        department: "Data & Analytics",
        office: "Londres",
        contract: "CDI",
        billable: false,
    },
    {
        id: 3,
        project: "INTERNE", subproject: "Amélioration des process de déploiement",
        employee: { name: "Pauline BRUN", role: "Directeur - Data & Analytics - Paris", initials: "PB" },
        kind: "real",
        status: "en_cours",
        period: "04/12/23 → 29/12/23",
        rate: "11% (2 jours)",
        indicators: { sold: "0 JH", remaining: "-0.43 JH", drift: "-1.36 JH" },
        position: "Directeur",
        department: "Data & Analytics",
        office: "Paris",
        contract: "CDI",
        billable: false,
    },
    {
        id: 4,
        project: "Google", subproject: "Audit Interne",
        employee: { name: "Xavier BERNIER", role: "Manager - Management des organisations - Paris", initials: "XB" },
        kind: "real",
        status: "passe",
        period: "04/12/23 → 05/01/24",
        rate: "50% (11.5 jours)",
        indicators: { sold: "0 JH", remaining: "-4.71 JH", drift: "-6.79 JH" },
        position: "Manager",
        department: "Management des organisations",
        office: "Paris",
        contract: "CDI",
        billable: true,
    },
    {
        id: 5,
        project: "Google", subproject: "Audit Interne",
        employee: { name: "Zacharie MULLER", role: "Consultant Senior - Data & Analytics - Paris", initials: "ZM" },
        kind: "real",
        status: "passe",
        period: "04/12/23 → 05/01/24",
        rate: "39% (9 jours)",
        indicators: { sold: "0 JH", remaining: "-2.71 JH", drift: "-5.43 JH" },
        position: "Consultant Senior",
        department: "Data & Analytics",
        office: "Paris",
        contract: "CDI",
        billable: true,
    },
    {
        id: 6,
        project: "BackMarket", subproject: "Refonte stratégie d'acquisition",
        employee: { name: "Michelle MUNOZ", role: "Consultant Junior - Data & Analytics - Paris", initials: "MM" },
        kind: "simulated",
        status: "futur",
        period: "04/12/23 → 29/12/23",
        rate: "21% (4 jours)",
        indicators: { sold: "0 JH", remaining: "-1.29 JH", drift: "-2.71 JH" },
        position: "Consultant Junior",
        department: "Data & Analytics",
        office: "Paris",
        contract: "Alternant",
        billable: false,
    },
    {
        id: 7,
        project: "BackMarket", subproject: "Refonte stratégie d'acquisition",
        employee: { name: "André COLLET", role: "Consultant Junior - Management des organisations - Paris", initials: "AC" },
        kind: "real",
        status: "en_cours",
        period: "04/12/23 → 05/01/24",
        rate: "47% (8 jours)",
        indicators: { sold: "0 JH", remaining: "-3 JH", drift: "-5 JH" },
        position: "Consultant Junior",
        department: "Management des organisations",
        office: "Paris",
        contract: "CDI",
        billable: true,
    },
    {
        id: 8,
        project: "EDF", subproject: "Audit des processus Achats",
        employee: { name: "Frédérique GRONDIN", role: "Consultant Senior - Data & Analytics - Paris", initials: "FG" },
        kind: "real",
        status: "en_cours",
        period: "02/10/23 → 29/12/23",
        rate: "74% (41.5 jours)",
        indicators: { sold: "0 JH", remaining: "-0.5 JH", drift: "-40.8 JH" },
        position: "Consultant Senior",
        department: "Data & Analytics",
        office: "Paris",
        contract: "CDI",
        billable: true,
    },
    {
        id: 9,
        project: "L'ORÉAL", subproject: "Accompagnement - Intrapreneuriat",
        employee: { name: "David VALLET", role: "Consultant Junior - Management des organisations - Paris", initials: "DV" },
        kind: "simulated",
        status: "futur",
        period: "02/10/23 → 05/01/24",
        rate: "88% (52.5 jours)",
        indicators: { sold: "0 JH", remaining: "-6.5 JH", drift: "-46 JH" },
        position: "Consultant Junior",
        department: "Management des organisations",
        office: "Paris",
        contract: "CDI",
        billable: false,
    },
    {
        id: 10,
        project: "Decathlon", subproject: "Diffusion des innovations",
        employee: { name: "Margaux LACROIX", role: "Consultant Junior - Management des organisations - Paris", initials: "ML" },
        kind: "real",
        status: "passe",
        period: "18/12/23 → 05/01/24",
        rate: "26% (7 jours)",
        indicators: { sold: "7 JH", remaining: "0 JH", drift: "-9.2 JH" },
        position: "Consultant Junior",
        department: "Management des organisations",
        office: "Paris",
        contract: "CDI",
        billable: true,
    },
];

const TABS = [
    { key: "all", label: "Tous" },
    { key: "passe", label: "Passés" },
    { key: "en_cours", label: "En cours" },
    { key: "futur", label: "Futurs" },
    { key: "simulated", label: "Simulés" },
];

export class StaffingStaffingsPage extends Component {
    static template = "staffing.StaffingStaffingsPage";
    static props = { page: Object };
    static components = { AssignmentDrawer };

    setup() {
        this.TABS = TABS;
        this.state = useState({ activeTab: "all", openRowId: null });
        this.infoTooltip =
            "Un staffing réel correspond à un collaborateur confirmé sur le projet. Un staffing " +
            "simulé indique qu'une ressource est réservée mais pas encore officiellement confirmée " +
            "(contrat, décision finale...). Les deux apparaissent toujours avec un style visuel " +
            "différent pour être distingués l'un de l'autre.";
    }

    get rows() {
        if (this.state.activeTab === "all") {
            return STAFFINGS;
        }
        if (this.state.activeTab === "simulated") {
            return STAFFINGS.filter((r) => r.kind === "simulated");
        }
        return STAFFINGS.filter((r) => r.status === this.state.activeTab);
    }

    get simulatedCount() {
        return STAFFINGS.filter((r) => r.kind === "simulated").length;
    }

    get totalCount() {
        return STAFFINGS.length;
    }

    get openRow() {
        return STAFFINGS.find((r) => r.id === this.state.openRowId) || null;
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    openDrawer(rowId) {
        this.state.openRowId = rowId;
    }

    closeDrawer() {
        this.state.openRowId = null;
    }
}
