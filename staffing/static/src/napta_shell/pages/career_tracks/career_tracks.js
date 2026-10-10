/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Données factices : parcours de carrière, formés de plusieurs fiches
 * métiers ordonnées (voir doc Napta "Parcours professionnels").
 */
const CAREER_TRACKS = [
    {
        id: 1,
        title: "Conseil",
        mine: true,
        jobSheets: ["Consultant Junior", "Consultant Senior", "Manager", "Directeur"],
    },
    {
        id: 2,
        title: "Sales",
        mine: true,
        jobSheets: ["Sales Junior", "Sales Confirmé", "Sales Senior", "Head of Sales"],
    },
    {
        id: 3,
        title: "Développement IT",
        mine: false,
        jobSheets: [
            "Junior Software Engineer",
            "Senior Software Engineer",
            "Engineering Manager",
            "Engineering Director",
        ],
    },
    {
        id: 4,
        title: "Data & Analytics",
        mine: false,
        jobSheets: ["Data Analyst", "Data Scientist", "Lead Data Scientist", "Head of Data"],
    },
];

export class CareerTracksPage extends Component {
    static template = "staffing.CareerTracksPage";
    static props = { page: Object };

    setup() {
        this.tabs = ["Mes parcours", "Tous les parcours"];
        this.state = useState({
            activeTab: this.tabs[0],
            openMenuId: null,
        });
    }

    get tracks() {
        if (this.state.activeTab === "Mes parcours") {
            return CAREER_TRACKS.filter((t) => t.mine);
        }
        return CAREER_TRACKS;
    }

    setTab(tab) {
        this.state.activeTab = tab;
        this.state.openMenuId = null;
    }

    toggleMenu(trackId) {
        this.state.openMenuId = this.state.openMenuId === trackId ? null : trackId;
    }

    isMenuOpen(trackId) {
        return this.state.openMenuId === trackId;
    }
}
