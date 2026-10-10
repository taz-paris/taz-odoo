/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Données factices : charge en ETP des demandes de staffing face à la
 * capacité totale de l'entreprise (voir doc Napta "Suivi de la charge").
 */
const WEEKS = [
    { label: "S04", date: "22-01-24", disponible: 21, conges: 0, staffe: 32, surstaffe: 4, demande: 0 },
    { label: "S05", date: "29-01-24", disponible: 25, conges: 6, staffe: 29, surstaffe: 4, demande: 0 },
    { label: "S06", date: "05-02-24", disponible: 17, conges: 7, staffe: 37, surstaffe: 6, demande: 5 },
    { label: "S07", date: "12-02-24", disponible: 19, conges: 8, staffe: 34, surstaffe: 7, demande: 5 },
    { label: "S08", date: "19-02-24", disponible: 20, conges: 9, staffe: 32, surstaffe: 7, demande: 5 },
    { label: "S09", date: "26-02-24", disponible: 23, conges: 7, staffe: 30, surstaffe: 4, demande: 5 },
    { label: "S10", date: "04-03-24", disponible: 28, conges: 6, staffe: 25, surstaffe: 3, demande: 5 },
    { label: "S11", date: "11-03-24", disponible: 30, conges: 6, staffe: 24, surstaffe: 3, demande: 5 },
    { label: "S12", date: "18-03-24", disponible: 30, conges: 10, staffe: 20, surstaffe: 4, demande: 5 },
    { label: "S13", date: "25-03-24", disponible: 34, conges: 9, staffe: 17, surstaffe: 3, demande: 5 },
    { label: "S14", date: "01-04-24", disponible: 34, conges: 10, staffe: 16, surstaffe: 0, demande: 0 },
];

const LEGEND = [
    { key: "disponible", label: "Disponible", tooltip: "Nombre d'ETP non staffé sur un projet ou en congé." },
    { key: "conges", label: "Congés", tooltip: "Nombre d'ETP en congé." },
    { key: "staffe", label: "Staffé", tooltip: "Nombre d'ETP staffé sur un projet." },
    { key: "surstaffe", label: "Sur-staffé", tooltip: "Nombre d'ETP dépassant 100% de staffing." },
    { key: "demande", label: "Demandes de staffing", tooltip: "Nombre d'ETP sur des demandes de staffing non pourvues." },
];

export class ReportsSuiviChargePage extends Component {
    static template = "staffing.ReportsSuiviChargePage";
    static props = { page: Object };

    setup() {
        this.weeks = WEEKS;
        this.legend = LEGEND;
        this.maxValue = 80;
        this.gridlines = [80, 60, 40, 20, 0];
        this.state = useState({ settingsOpen: false });
    }

    toggleSettings() {
        this.state.settingsOpen = !this.state.settingsOpen;
    }

    barHeight(value) {
        return Math.round((value / this.maxValue) * 100) + "%";
    }

    capacityTotal(week) {
        return week.disponible + week.conges + week.staffe + week.surstaffe;
    }
}
