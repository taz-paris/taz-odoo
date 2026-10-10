/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

const PEOPLE = [
    "CONSTABE Etienne", "AMERI Armand", "BARBIER Gilles", "BARTOL Jérémie",
    "BARTOLIE Aurore", "BERARDA Katharina", "BERGER Claire", "BOLE Timothée",
    "BOMPARD Claire", "BRIZARD Sylvain", "BRUN Olivier",
];

const SORT_OPTIONS = [
    { key: "updated", label: "Date de mise à jour" },
    { key: "skill", label: "Compétence" },
    { key: "category", label: "Catégorie de compétence" },
];

/** Compétences factices évaluées pour le collaborateur sélectionné. */
const MOCK_SKILLS = [
    {
        skill: "A/B Testing",
        category: "Marketing / Acquisition",
        description: "Technique permettant de comparer deux versions d'une même page web pour en mesurer les performances.",
        note: 3,
        comment: "Bonne maîtrise de la compétence",
        evaluator: "MEROT Isabelle",
        daysAgo: 10,
        context: "Campagne d'évaluation",
        contextDetail: "Évaluations annuelles",
    },
    {
        skill: "Flask",
        category: "Software Engineering / Back-end",
        description: "Framework Python pour la création d'applications web.",
        note: 1,
        comment: "A fait les efforts nécessaires pour progresser",
        evaluator: "MEROT Isabelle",
        daysAgo: 10,
        context: "Campagne d'évaluation",
        contextDetail: "Évaluations annuelles",
    },
    {
        skill: "Microsoft Dynamics",
        category: "Sales / CRM",
        description: "Logiciel de gestion d'entreprise de Microsoft.",
        note: 4,
        comment: "Bonne maîtrise de la compétence",
        evaluator: "MEROT Isabelle",
        daysAgo: 18,
        context: "Campagne d'évaluation",
        contextDetail: "Évaluations annuelles",
    },
    {
        skill: "UI Design",
        category: "Design / Design - Global",
        description: "Processus de conception de l'interface utilisateur d'une application ou d'un site web.",
        note: 5,
        comment: "Belle progression sur la compétence",
        evaluator: "MEROT Isabelle",
        daysAgo: 18,
        context: "Campagne d'évaluation",
        contextDetail: "Évaluations annuelles",
    },
    {
        skill: "Computer vision",
        category: "Data / Machine Learning",
        description: "Domaine de l'informatique qui se concentre sur la compréhension et l'analyse des images et des vidéos.",
        note: 5,
        comment: "Montée en compétence encourageante",
        evaluator: "MEROT Isabelle",
        daysAgo: 24,
        context: "Campagne d'évaluation",
        contextDetail: "Évaluations annuelles",
    },
    {
        skill: "A/B Testing",
        category: "Marketing / Acquisition",
        description: "Technique permettant de comparer deux versions d'une même page web pour en mesurer les performances.",
        note: 3,
        comment: "",
        evaluator: "CONSTABE Etienne",
        daysAgo: 40,
        context: "Évaluation sur profil",
        contextDetail: "",
    },
    {
        skill: "Facebook Ads",
        category: "Marketing / Acquisition",
        description: "Plateforme publicitaire de Facebook qui permet aux annonceurs de créer et de diffuser des annonces en ligne.",
        note: 2,
        comment: "",
        evaluator: "CONSTABE Etienne",
        daysAgo: 40,
        context: "Évaluation sur profil",
        contextDetail: "",
    },
    {
        skill: "Google Ads",
        category: "Marketing / Acquisition",
        description: "Plateforme publicitaire de Google qui permet aux annonceurs de créer et de diffuser des annonces en ligne.",
        note: 1,
        comment: "",
        evaluator: "CONSTABE Etienne",
        daysAgo: 40,
        context: "Évaluation sur profil",
        contextDetail: "",
    },
];

const EXPORTS = [
    "Exporter l'historique des notes pour l'utilisateur actuel",
    "Exporter l'historique des notes pour tous les utilisateurs",
    "Exporter les notes pour l'utilisateur actuel",
    "Exporter les notes pour tous les utilisateurs",
];

function formatDate(date) {
    return String(date.getDate()).padStart(2, "0") + "/" +
        String(date.getMonth() + 1).padStart(2, "0") + "/" +
        String(date.getFullYear()).slice(2);
}

export class ReportsCompetencesIndividuellesPage extends Component {
    static template = "staffing.ReportsCompetencesIndividuellesPage";
    static props = {
        page: { type: Object, optional: true },
    };

    setup() {
        this.people = PEOPLE;
        this.sortOptions = SORT_OPTIONS;
        this.exports = EXPORTS;
        this.state = useState({
            user: PEOPLE[0],
            sortKey: "updated",
            sortMenuOpen: false,
            userMenuOpen: false,
            exportMenuOpen: false,
            userSearch: "",
            dateTo: new Date(2026, 0, 10),
        });
    }

    get filteredPeople() {
        const search = this.state.userSearch.toLowerCase();
        return this.people.filter((p) => p.toLowerCase().includes(search));
    }

    get currentSortLabel() {
        const opt = this.sortOptions.find((o) => o.key === this.state.sortKey);
        return opt ? opt.label : "";
    }

    get skills() {
        const sorted = [...MOCK_SKILLS];
        if (this.state.sortKey === "skill") {
            sorted.sort((a, b) => a.skill.localeCompare(b.skill));
        } else if (this.state.sortKey === "category") {
            sorted.sort((a, b) => a.category.localeCompare(b.category));
        } else {
            sorted.sort((a, b) => a.daysAgo - b.daysAgo);
        }
        return sorted.map((row) => ({
            ...row,
            updatedOn: this.updatedDate(row.daysAgo),
        }));
    }

    /** Date de mise à jour recalculée à partir de la borne de fin de la plage sélectionnée. */
    updatedDate(daysAgo) {
        const date = new Date(this.state.dateTo);
        date.setDate(date.getDate() - daysAgo);
        return formatDate(date);
    }

    get dateToLabel() {
        return formatDate(this.state.dateTo);
    }

    get dateFromLabel() {
        const date = new Date(this.state.dateTo);
        date.setMonth(date.getMonth() - 6);
        return formatDate(date);
    }

    shiftRange(months) {
        const date = new Date(this.state.dateTo);
        date.setMonth(date.getMonth() + months);
        this.state.dateTo = date;
    }

    toggleSortMenu() {
        this.state.sortMenuOpen = !this.state.sortMenuOpen;
        this.state.userMenuOpen = false;
        this.state.exportMenuOpen = false;
    }

    toggleUserMenu() {
        this.state.userMenuOpen = !this.state.userMenuOpen;
        this.state.sortMenuOpen = false;
        this.state.exportMenuOpen = false;
    }

    toggleExportMenu() {
        this.state.exportMenuOpen = !this.state.exportMenuOpen;
        this.state.sortMenuOpen = false;
        this.state.userMenuOpen = false;
    }

    setSortKey(key) {
        this.state.sortKey = key;
        this.state.sortMenuOpen = false;
    }

    setUser(user) {
        this.state.user = user;
        this.state.userMenuOpen = false;
        this.state.userSearch = "";
    }

    onUserSearchInput(ev) {
        this.state.userSearch = ev.target.value;
    }

    reset() {
        this.state.user = PEOPLE[0];
        this.state.sortKey = "updated";
        this.state.dateTo = new Date(2026, 0, 10);
    }

    stars(note) {
        return Array.from({ length: 5 }, (_, i) => i < note);
    }
}
