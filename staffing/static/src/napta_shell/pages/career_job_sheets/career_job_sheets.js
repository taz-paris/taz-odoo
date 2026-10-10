/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Données factices : fiches de poste avec compétences attendues,
 * groupées par catégorie (voir doc Napta "Fiches de poste").
 */
const JOB_SHEETS = [
    {
        id: 1,
        name: "Senior Consultant",
        mine: true,
        description: [
            "Working alone or as part of a team, senior management consultants provide their expertise in organisation and management to client companies.",
            "They work on assignments in which they propose solutions aimed at improving the client's performance and, where necessary, supervise their implementation.",
        ],
        tracks: ["Conseil"],
        yourScore: { met: 6, total: 6 },
        categories: [
            {
                name: "Languages",
                skills: [
                    { name: "English", requiredGrade: 3, requiredLevel: "Fluent", gradeDescription: "Fluent", yourScore: 4 },
                ],
            },
            {
                name: "Consulting / Mission type",
                skills: [
                    { name: "Process optimisation", requiredGrade: 2, requiredLevel: "Intermediate", gradeDescription: "I have used my knowledge on the subject, at least partially", yourScore: 5 },
                    { name: "AMOA", requiredGrade: 2, requiredLevel: "Intermediate", gradeDescription: "I have used my knowledge on the subject, at least partially", yourScore: 3 },
                ],
            },
            {
                name: "Soft skills",
                skills: [
                    { name: "Presentation", requiredGrade: 3, requiredLevel: "Skillful", gradeDescription: "I acquired more than 2/3 years of experience in the activity in question or carried out several missions related to the expertise", yourScore: 5 },
                    { name: "Team work", requiredGrade: 3, requiredLevel: "Skillful", gradeDescription: "I acquired more than 2/3 years of experience in the activity in question or carried out several missions related to the expertise", yourScore: 4 },
                ],
            },
        ],
    },
    {
        id: 2,
        name: "Director",
        mine: true,
        description: [
            "Responsibility for sales development in a sector/trade.",
            "Responsible for a skills centre (telecoms, purchasing, etc.).",
            "Legal responsibility for the project and project profitability.",
            "KPIs: staffing rate, turnover, margins.",
            "Coordination of the global network.",
        ],
        tracks: ["Conseil"],
        yourScore: { met: 4, total: 7 },
        categories: [
            {
                name: "Sales / Lead closing",
                skills: [
                    { name: "Reporting", requiredGrade: 5, requiredLevel: "Expert", gradeDescription: "I have more than 10 years of experience on the subject. I am known as a referent in the company, or even the network.", yourScore: 2 },
                ],
            },
            {
                name: "Languages",
                skills: [
                    { name: "English", requiredGrade: 4, requiredLevel: "Bilingual", gradeDescription: "Bilingual", yourScore: 4 },
                ],
            },
            {
                name: "Consulting / Mission type",
                skills: [
                    { name: "Process optimisation", requiredGrade: 5, requiredLevel: "Expert", gradeDescription: "I have more than 10 years of experience on the subject. I am known as a referent in the company, or even the network.", yourScore: 5 },
                    { name: "Planning management", requiredGrade: 4, requiredLevel: "Advanced", gradeDescription: "I have acquired between 3 and 8 years of experience on the subject. I lead missions for different clients on the subject", yourScore: 5 },
                ],
            },
            {
                name: "Consulting / Project management",
                skills: [
                    { name: "Budget a project", requiredGrade: 5, requiredLevel: "Expert", gradeDescription: "I have more than 10 years of experience on the subject. I am known as a referent in the company, or even the network.", yourScore: 4 },
                ],
            },
        ],
    },
    {
        id: 3,
        name: "Engineering Director",
        mine: false,
        description: [
            "Define and implement a strategy to maximise customer satisfaction within the scope of your teams.",
            "Define and implement a strategy for growing your teams.",
            "Define and implement a strategy to improve the practices of your teams.",
            "Define and implement a strategy for transforming the technical environment of your teams.",
        ],
        tracks: ["Développement IT"],
        yourScore: { met: 1, total: 5 },
        categories: [
            {
                name: "Développement",
                skills: [
                    { name: "Data analysis", requiredGrade: 5, requiredLevel: "Expert", gradeDescription: "Référent sur le sujet au niveau de l'entreprise.", yourScore: null },
                    { name: "JavaScript", requiredGrade: 5, requiredLevel: "Expert", gradeDescription: "Référent sur le sujet au niveau de l'entreprise.", yourScore: null },
                    { name: "Python", requiredGrade: 5, requiredLevel: "Expert", gradeDescription: "Référent sur le sujet au niveau de l'entreprise.", yourScore: 5 },
                ],
            },
            {
                name: "Soft skills",
                skills: [
                    { name: "Team management", requiredGrade: 5, requiredLevel: "Expert", gradeDescription: "Référent sur le sujet au niveau de l'entreprise.", yourScore: null },
                    { name: "Natural Language Processing", requiredGrade: 4, requiredLevel: "Advanced", gradeDescription: "Expérience confirmée sur le sujet.", yourScore: null },
                ],
            },
        ],
    },
];

export class CareerJobSheetsPage extends Component {
    static template = "staffing.CareerJobSheetsPage";
    static props = { page: Object };

    setup() {
        this.tabs = ["Mes fiches de poste", "Toutes les fiches de poste"];
        this.state = useState({
            activeTab: this.tabs[0],
            expandedId: JOB_SHEETS[0].id,
        });
    }

    get jobSheets() {
        if (this.state.activeTab === "Mes fiches de poste") {
            return JOB_SHEETS.filter((j) => j.mine);
        }
        return JOB_SHEETS;
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    toggleExpand(id) {
        this.state.expandedId = this.state.expandedId === id ? null : id;
    }

    isExpanded(id) {
        return this.state.expandedId === id;
    }

    categoryMet(category) {
        return category.skills.every((s) => s.yourScore !== null && s.yourScore >= s.requiredGrade);
    }

    categoryCount(category) {
        const met = category.skills.filter((s) => s.yourScore !== null && s.yourScore >= s.requiredGrade).length;
        return met + "/" + category.skills.length;
    }

    skillMet(skill) {
        return skill.yourScore !== null && skill.yourScore >= skill.requiredGrade;
    }

    scorePercent(job) {
        return Math.round((job.yourScore.met / job.yourScore.total) * 100) + "%";
    }
}
