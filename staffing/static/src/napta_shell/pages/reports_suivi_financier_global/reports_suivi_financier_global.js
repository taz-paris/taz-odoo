/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/** Clés d'entrée possibles pour le rapport, cf. documentation Napta. */
const ENTRY_KEYS = [
    "Projet",
    "Utilisateur",
    "Client",
    "Statut de projet",
    "Catégorie de projet",
    "Poste",
    "Département (Utilisateur)",
    "Bureau",
    "Type de contrat",
];

/** Données factices : chiffre d'affaires / coût / marge / charge par projet. */
const MOCK_ROWS = [
    {
        key: "accompagnement_commercial",
        label: "Accompagnement du service commercial",
        billing: "Forfait",
        budget: "210 000 €",
        caDate: { previsionnel: "496,91 €", reel: "569,99 €" },
        caTerme: { reel: "26 735,51 €", projete: "26 842,22 €" },
        coutDate: { previsionnel: "126,77 €", reel: "145,50 €" },
        coutTerme: "29 451,93 €",
        marge: "24 870 €",
        tauxMarge: "87,3 %",
        chargeDate: { reel: "11,2 JH", projete: "9,6 JH", unapproved: true },
        chargeTerme: { reel: "46,4 JH", projete: "44,8 JH", unapproved: false },
    },
    {
        key: "intrapreneuriat",
        label: "Accompagnement - Intrapreneuriat",
        billing: "Régie",
        budget: "245 000 €",
        caDate: { previsionnel: "81 958,76 €", reel: "80 429,20 €" },
        caTerme: { reel: "158 886,53 €", projete: "157 599,06 €" },
        coutDate: { previsionnel: "28 661,80 €", reel: "28 928,50 €" },
        coutTerme: "59 275,38 €",
        marge: "98 323,68 €",
        tauxMarge: "62,4 %",
        chargeDate: { reel: "25,2 JH", projete: "23,8 JH", unapproved: false },
        chargeTerme: { reel: "51,2 JH", projete: "48 JH", unapproved: true },
    },
    {
        key: "projets_internes",
        label: "Accompagnement - Projets internes",
        billing: "Régie",
        budget: "315 000 €",
        caDate: { previsionnel: "0 €", reel: "0 €" },
        caTerme: { reel: "1 194,44 €", projete: "1 194,44 €" },
        coutDate: { previsionnel: "0 €", reel: "0 €" },
        coutTerme: "5 522,61 €",
        marge: "-4 328,17 €",
        tauxMarge: "- %",
        chargeDate: { reel: "0 JH", projete: "0 JH", unapproved: false },
        chargeTerme: { reel: "14 JH", projete: "9,4 JH", unapproved: false },
    },
    {
        key: "audit_data",
        label: "Audit data",
        billing: "Forfait",
        budget: "250 000 €",
        caDate: { previsionnel: "47 558,83 €", reel: "50 736,68 €" },
        caTerme: { reel: "97 877,88 €", projete: "100 566,63 €" },
        coutDate: { previsionnel: "44 977,43 €", reel: "49 253,40 €" },
        coutTerme: "85 852,15 €",
        marge: "14 714,48 €",
        tauxMarge: "14,6 %",
        chargeDate: { reel: "39,2 JH", projete: "23,6 JH", unapproved: true },
        chargeTerme: { reel: "16,8 JH", projete: "5,6 JH", unapproved: false },
    },
    {
        key: "audit_processus_achats",
        label: "Audit des processus Achats",
        billing: "Régie",
        budget: "1 000 000 €",
        caDate: { previsionnel: "399 786 €", reel: "400 396 €" },
        caTerme: { reel: "597 123,07 €", projete: "597 323,07 €" },
        coutDate: { previsionnel: "142 646,60 €", reel: "142 864,66 €" },
        coutTerme: "219 314,28 €",
        marge: "378 008,79 €",
        tauxMarge: "63,3 %",
        chargeDate: { reel: "34 JH", projete: "34 JH", unapproved: false },
        chargeTerme: { reel: "0 JH", projete: "0 JH", unapproved: false },
    },
    {
        key: "deploiement_salesforce",
        label: "Déploiement Salesforce",
        billing: "Forfait",
        budget: "225 000 €",
        caDate: { previsionnel: "26 207,45 €", reel: "33 936,16 €" },
        caTerme: { reel: "95 168,17 €", projete: "91 365,81 €" },
        coutDate: { previsionnel: "17 399 €", reel: "21 457,50 €" },
        coutTerme: "50 527,50 €",
        marge: "40 838,31 €",
        tauxMarge: "44,7 %",
        chargeDate: { reel: "5,6 JH", projete: "4,8 JH", unapproved: false },
        chargeTerme: { reel: "17,6 JH", projete: "16,8 JH", unapproved: true },
    },
];

export class ReportsSuiviFinancierGlobalPage extends Component {
    static template = "staffing.ReportsSuiviFinancierGlobalPage";
    static props = {
        page: { type: Object, optional: true },
    };

    setup() {
        this.entryKeys = ENTRY_KEYS;
        this.state = useState({
            entryKey: "Projet",
            entryMenuOpen: false,
            dateFrom: "01/08/24",
            dateTo: "30/09/24",
        });
        this.legendPrevisionnelTooltip =
            "Donnée prévisionnelle : calculée à partir des affectations planifiées sur la période.";
        this.legendReelTooltip =
            "Donnée réelle : calculée à partir des temps saisis sur les périodes passées ou en cours.";
        this.legendProjeteTooltip =
            "Donnée projetée : combine le réel déjà saisi et le prévisionnel sur les périodes futures ou en cours.";
    }

    get rows() {
        return MOCK_ROWS;
    }

    get total() {
        return {
            caDate: { previsionnel: "760 540,81 €", reel: "773 019,59 €" },
            caTerme: { reel: "1 520 280,08 €", projete: "1 519 091,80 €" },
            coutDate: { previsionnel: "409 626,46 €", reel: "407 555,90 €" },
            coutTerme: "900 460,97 €",
            marge: "619 630,83 €",
        };
    }

    toggleEntryMenu() {
        this.state.entryMenuOpen = !this.state.entryMenuOpen;
    }

    setEntryKey(key) {
        this.state.entryKey = key;
        this.state.entryMenuOpen = false;
    }

    unapprovedTitle(flag) {
        return flag ? "Certaines imputations n'ont pas été approuvées" : "";
    }
}
