/** @odoo-module **/

// Registre central des composants de page dédiés (pixel-perfect), un par
// entrée de menu de menu_config.js. Toute nouvelle entrée de menu doit
// avoir son composant ajouté ici (il n'y a plus de page générique de repli).

import { StaffingProjectsPage } from "./staffing_projects/staffing_projects";
import { StaffingRequestsPage } from "./staffing_requests/staffing_requests";
import { StaffingModificationRequestsPage } from "./staffing_modification_requests/staffing_modification_requests";
import { StaffingStaffingsPage } from "./staffing_staffings/staffing_staffings";
import { StaffingGlobalCalendarPage } from "./staffing_global_calendar/staffing_global_calendar";
import { TimesheetsTimesheetPage } from "./timesheets_timesheet/timesheets_timesheet";
import { EvaluationsMissionPage } from "./evaluations_mission/evaluations_mission";
import { ReportsOccupationGlobalePage } from "./reports_occupation_globale/reports_occupation_globale";
import { ReportsPlanificationIndividuellePage } from "./reports_planification_individuelle/reports_planification_individuelle";
import { ReportsAvailabilityHubPage } from "./reports_availability_hub/reports_availability_hub";
import { ReportsSuiviChargePage } from "./reports_suivi_charge/reports_suivi_charge";
import { ReportsSuiviConsommePage } from "./reports_suivi_consomme/reports_suivi_consomme";
import { ReportsSuiviFinancierGlobalPage } from "./reports_suivi_financier_global/reports_suivi_financier_global";
import { ReportsCompetencesGlobalesPage } from "./reports_competences_globales/reports_competences_globales";
import { ReportsCompetencesIndividuellesPage } from "./reports_competences_individuelles/reports_competences_individuelles";

export const PAGE_COMPONENTS = {
    "staffing.projects": StaffingProjectsPage,
    "staffing.requests": StaffingRequestsPage,
    "staffing.modification_requests": StaffingModificationRequestsPage,
    "staffing.staffings": StaffingStaffingsPage,
    "staffing.global_calendar": StaffingGlobalCalendarPage,
    "timesheets.timesheet": TimesheetsTimesheetPage,
    "evaluations.mission": EvaluationsMissionPage,
    "reports.occupation_globale": ReportsOccupationGlobalePage,
    "reports.planification_individuelle": ReportsPlanificationIndividuellePage,
    "reports.availability_hub": ReportsAvailabilityHubPage,
    "reports.suivi_charge": ReportsSuiviChargePage,
    "reports.suivi_consomme": ReportsSuiviConsommePage,
    "reports.suivi_financier_global": ReportsSuiviFinancierGlobalPage,
    "reports.competences_globales": ReportsCompetencesGlobalesPage,
    "reports.competences_individuelles": ReportsCompetencesIndividuellesPage,
};
