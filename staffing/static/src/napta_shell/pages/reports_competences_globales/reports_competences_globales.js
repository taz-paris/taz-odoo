/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/** Données factices : répartition des compétences au niveau de l'organisation. */
const MOCK_SKILLS = [
    { label: "Angular", category: "Développement Web", parentCategory: "Software Engineering", aspirations: 8, peopleWithSkill: 32, avgGrade: 2.9 },
    { label: "Business Analyst", category: "Conseil", parentCategory: "Métier", aspirations: 4, peopleWithSkill: 29, avgGrade: 3.2 },
    { label: "English", category: "Langues", parentCategory: "Soft Skills", aspirations: 6, peopleWithSkill: 28, avgGrade: 2.3 },
    { label: "Python", category: "Data & Analytics", parentCategory: "Software Engineering", aspirations: 7, peopleWithSkill: 27, avgGrade: 2.6 },
    { label: "Scrum Master", category: "Gestion de projet", parentCategory: "Soft Skills", aspirations: 7, peopleWithSkill: 27, avgGrade: 3.0 },
    { label: "Team work", category: "Collaboration", parentCategory: "Soft Skills", aspirations: 7, peopleWithSkill: 21, avgGrade: 3.0 },
    { label: "UI Design", category: "Design - Global", parentCategory: "Design", aspirations: 5, peopleWithSkill: 26, avgGrade: 2.9 },
    { label: "Figma", category: "Design - Global", parentCategory: "Design", aspirations: 3, peopleWithSkill: 24, avgGrade: 2.7 },
    { label: "Time management", category: "Organisation", parentCategory: "Soft Skills", aspirations: 4, peopleWithSkill: 22, avgGrade: 3.6 },
    { label: "Laravel", category: "Développement Web", parentCategory: "Software Engineering", aspirations: 11, peopleWithSkill: 12, avgGrade: 2.0 },
];

const SORT_OPTIONS = [
    { key: "people_desc", label: "# de personnes avec la compétence", field: "peopleWithSkill", dir: -1 },
    { key: "people_asc", label: "# de personnes avec la compétence (croissant)", field: "peopleWithSkill", dir: 1 },
    { key: "aspirations_desc", label: "# d'aspirations", field: "aspirations", dir: -1 },
    { key: "aspirations_asc", label: "# d'aspirations (croissant)", field: "aspirations", dir: 1 },
    { key: "grade_desc", label: "Note moyenne", field: "avgGrade", dir: -1 },
    { key: "grade_asc", label: "Note moyenne (croissant)", field: "avgGrade", dir: 1 },
];

const RESULT_COUNTS = [10, 25, 50, "Tous"];

export class ReportsCompetencesGlobalesPage extends Component {
    static template = "staffing.ReportsCompetencesGlobalesPage";
    static props = {
        page: { type: Object, optional: true },
    };

    setup() {
        this.resultCounts = RESULT_COUNTS;
        this.sortOptions = SORT_OPTIONS;
        this.state = useState({
            view: "graph",
            resultsCount: 10,
            sortKey: "people_desc",
            resultsMenuOpen: false,
            sortMenuOpen: false,
        });
    }

    get currentSort() {
        return this.sortOptions.find((o) => o.key === this.state.sortKey) || this.sortOptions[0];
    }

    get skills() {
        const sort = this.currentSort;
        const sorted = [...MOCK_SKILLS].sort((a, b) => (a[sort.field] - b[sort.field]) * sort.dir);
        const count = this.state.resultsCount === "Tous" ? sorted.length : this.state.resultsCount;
        return sorted.slice(0, count);
    }

    get maxValue() {
        return Math.max(1, ...this.skills.map((s) => s.aspirations + s.peopleWithSkill));
    }

    aspirationsWidth(skill) {
        return Math.round((skill.aspirations / this.maxValue) * 100) + "%";
    }

    peopleWidth(skill) {
        return Math.round((skill.peopleWithSkill / this.maxValue) * 100) + "%";
    }

    dotPosition(skill) {
        return Math.round(((skill.aspirations + skill.peopleWithSkill) / this.maxValue) * 100) + "%";
    }

    skillTitle(skill) {
        return (
            skill.label + "\n" +
            "# d'aspirations : " + skill.aspirations + "\n" +
            "# de personnes avec la compétence : " + skill.peopleWithSkill + "\n" +
            "Note moyenne : " + skill.avgGrade
        );
    }

    setView(view) {
        this.state.view = view;
    }

    toggleResultsMenu() {
        this.state.resultsMenuOpen = !this.state.resultsMenuOpen;
        this.state.sortMenuOpen = false;
    }

    toggleSortMenu() {
        this.state.sortMenuOpen = !this.state.sortMenuOpen;
        this.state.resultsMenuOpen = false;
    }

    setResultsCount(count) {
        this.state.resultsCount = count;
        this.state.resultsMenuOpen = false;
    }

    setSortKey(key) {
        this.state.sortKey = key;
        this.state.sortMenuOpen = false;
    }
}
