/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Tiroir latéral mutualisé "Créer / Modifier une demande ou un staffing".
 *
 * Reproduit modules-napta/staffing_creation-de-staffing (tiroir de création)
 * et modules-napta/staffing_edition (tiroir d'édition, qui réutilise "la
 * même structure que celle du tiroir de création" avec des ajouts propres à
 * l'édition : bandeau de rappel de la mission, carte(s) utilisateur(s)
 * affecté(s) avec remplacement de contributeur, bascule Réel/Simulé pour un
 * staffing). Utilisé par Staffing > Demandes (création ET édition) et par
 * Staffing > Staffings (édition uniquement, cf. bouton "Ajouter un
 * staffing" resté désactivé).
 *
 * Toujours sans lien back-office : rien n'est persisté nulle part, les
 * boutons Enregistrer/Fermer se contentent de fermer le tiroir.
 */

const CRITERIA_FIELDS = [
    { key: "skills", label: "Compétences", options: ["Excel", "Anglais", "Python", "Salesforce", "Data analysis", "Communication", "Budget", "Design"] },
    { key: "businessUnits", label: "Unité commerciale", options: ["Conseil RH", "Audit", "Stratégie", "Transformation digitale", "Finance"] },
    { key: "positions", label: "Poste", options: ["Consultant", "Senior Consultant", "Manager", "Directeur de mission", "Analyste"] },
    { key: "offices", label: "Bureau", options: ["Paris", "Lyon", "Marseille", "Londres", "Bruxelles"] },
    { key: "contractTypes", label: "Type de contrat", options: ["CDI", "CDD", "Stage", "Alternance", "Freelance"] },
];

// L'unité de charge est commune à toutes les périodes (cf. doc : "L'unité
// est la même pour toutes les périodes"), d'où un seul sélecteur global.
const PERIOD_UNITS = ["Jours", "Heures", "% (congés exclus)"];
const PERIOD_PLANNING_MODES = ["Dates fixes", "À partir de"];
const HALF_DAY_OPTIONS = ["Matin", "Après-midi"];
const PERIOD_STATUS_OPTIONS = ["Non défini", "À valider", "Confirmée", "Annulée"];
const CURRENCY_OPTIONS = ["€", "$", "£"];

const USER_DIRECTORY = [
    "Oliver NGUYEN", "Isabelle MEROT", "Armand AMERI", "Benjamin LEFORT", "Fiona MAGGAL",
    "Christopher JOHNSON", "Nour BARTOLI", "Maria DAVOS", "Katharina BERARDA", "Jess BOMPARD",
    "Jérémie BARTOL", "Aurore BARTOLIE", "Sylvain BRIZARD", "Marie-Claire RODRIGUES", "Olivier BRUN",
].sort((a, b) => a.localeCompare(b, "fr"));

// Une demande ne staffe pas réellement : chaque utilisateur n'est que
// suggéré ou pré-réservé, selon les droits de son créateur (doc §Option de
// staffing). On simule ce choix par utilisateur sélectionné.
const USER_STAFFING_OPTIONS = ["Suggéré", "Pré-réservé"];
const REPLACE_SCOPE_OPTIONS = ["Pour l'ensemble de la mission", "Pour une partie de la mission", "À partir d'une date spécifique"];

const ASSIGNMENT_STATUS_OPTIONS = ["Suggestion", "Pré-réservation", "Staffing simulé", "Staffing confirmé"];
const PRIORITY_OPTIONS = ["Basse", "Normale", "Haute", "Urgente"];

const COMMENT_MAX_LENGTH = 200;

function computeInitials(name) {
    return (name || "")
        .split(" ")
        .filter(Boolean)
        .slice(0, 2)
        .map((w) => w[0].toUpperCase())
        .join("");
}

/** "DD/MM/YYYY" ou "DD/MM/YY" -> "YYYY-MM-DD" (pour <input type="date">). */
function toIsoDate(str) {
    if (!str) return "";
    const parts = str.trim().split("/");
    if (parts.length !== 3) return "";
    let [d, m, y] = parts;
    if (y.length === 2) y = "20" + y;
    return `${y}-${m.padStart(2, "0")}-${d.padStart(2, "0")}`;
}

export class AssignmentDrawer extends Component {
    static template = "staffing.AssignmentDrawer";
    static props = {
        kind: String, // "request" | "staffing"
        mode: String, // "create" | "edit"
        record: { type: [Object, { value: null }], optional: true },
        projectOptions: { type: Array, optional: true },
        onClose: Function,
    };

    setup() {
        this.criteriaFields = CRITERIA_FIELDS;
        this.periodUnits = PERIOD_UNITS;
        this.periodPlanningModes = PERIOD_PLANNING_MODES;
        this.halfDayOptions = HALF_DAY_OPTIONS;
        this.periodStatusOptions = PERIOD_STATUS_OPTIONS;
        this.currencyOptions = CURRENCY_OPTIONS;
        this.userStaffingOptions = USER_STAFFING_OPTIONS;
        this.replaceScopeOptions = REPLACE_SCOPE_OPTIONS;
        this.assignmentStatusOptions = ASSIGNMENT_STATUS_OPTIONS;
        this.priorityOptions = PRIORITY_OPTIONS;
        this.commentMaxLength = COMMENT_MAX_LENGTH;
        this._periodId = 0;

        const isEdit = this.props.mode === "edit";
        const record = this.props.record || null;

        this.state = useState({
            openSections: {},
            need: "",
            project: isEdit ? "" : "",
            criteria: { skills: [], businessUnits: [], positions: [], offices: [], contractTypes: [] },
            criteriaOpenField: null,
            periods: [],
            periodsConfig: { planningMode: "Dates fixes", unit: "Jours", ignoreLeaves: false, autoSplit: false },
            periodMenuOpenId: null,
            bulkEditOpen: false,
            bulkEdit: { amount: null, customFee: null, customFeeCurrency: "€", customCost: null, customCostCurrency: "€", status: "", description: "" },
            users: [],
            userOptions: {},
            userSearch: "",
            userSearchFocused: false,
            info: { status: "", daysSold: null, description: "", duration: "", priority: "" },
            comment: "",
            assignmentType: "real",
            replaceOpen: null,
            replaceScope: REPLACE_SCOPE_OPTIONS[0],
            replaceBy: "",
            replaceDate: "",
            replaceSearch: "",
            replaceSearchFocused: false,
        });

        if (isEdit && record) {
            this.seedFromRecord(record);
        }
    }

    // ---- Préremplissage en mode édition ----
    seedFromRecord(record) {
        if (this.props.kind === "staffing") {
            this.state.users = [{ name: record.employee.name, role: record.employee.role, initials: record.employee.initials }];
            this.state.userOptions = {};
            this.state.assignmentType = record.kind || "real";
            this.state.info.status = record.status || "";
            const [start, end] = (record.period || "").split("→").map((s) => s.trim());
            const amountMatch = /\(([\d.]+)/.exec(record.rate || "");
            this.addPeriod();
            Object.assign(this.state.periods[0], {
                start: toIsoDate(start),
                end: toIsoDate(end),
                amount: amountMatch ? Number(amountMatch[1]) : 0,
            });
        } else {
            this.state.users = (record.preBooked || [])
                .filter((n) => n && !n.startsWith("+") && !/\.$/.test(n))
                .map((name) => ({ name, role: "", initials: computeInitials(name) }));
            this.state.userOptions = Object.fromEntries(this.state.users.map((u) => [u.name, "Pré-réservé"]));
            this.state.info.status = record.status || "";
            this.state.info.daysSold = record.soldDays ?? null;
            if (record.startDate || record.endDate) {
                this.addPeriod();
                Object.assign(this.state.periods[0], {
                    start: toIsoDate(record.startDate),
                    end: toIsoDate(record.endDate),
                    amount: record.workloadDays ?? 0,
                });
            }
        }
    }

    // ---- Bandeau de rappel (mode édition uniquement) ----
    get banner() {
        const record = this.props.record;
        if (!record) return null;
        if (this.props.kind === "staffing") {
            return {
                title: record.project,
                subtitle: record.subproject,
                description: "",
                tags: [
                    { icon: "fa-suitcase", label: "Poste", value: record.position },
                    { icon: "fa-building-o", label: "Bureau", value: record.office },
                ],
            };
        }
        return {
            title: record.project,
            subtitle: record.client,
            description: "",
            tags: [
                { icon: "fa-star-o", label: "Compétences", value: (record.businessUnits || []).join(", ") || "—" },
                { icon: "fa-sitemap", label: "Jours vendus", value: record.soldDays != null ? record.soldDays + " j" : "—" },
            ],
        };
    }

    get title() {
        if (this.props.mode === "create") {
            return "Créer une demande";
        }
        return this.props.kind === "staffing" ? "Modifier le staffing" : "Modifier la demande";
    }

    close(ev) {
        if (ev) ev.stopPropagation();
        this.props.onClose();
    }

    closeDropdowns() {
        this.state.criteriaOpenField = null;
        this.state.userSearchFocused = false;
        this.state.periodMenuOpenId = null;
        this.state.replaceSearchFocused = false;
    }

    toggleSection(key) {
        // Ne stoppe pas la propagation : le clic doit atteindre le tiroir
        // pour que closeDropdowns() referme les menus Critères/Utilisateurs
        // d'une autre section restée ouverte.
        this.state.openSections[key] = !this.state.openSections[key];
    }

    isSectionOpen(key) {
        return !!this.state.openSections[key];
    }

    // ---- Section Critères (création uniquement) ----
    get criteriaCount() {
        const c = this.state.criteria;
        return c.skills.length + c.businessUnits.length + c.positions.length + c.offices.length + c.contractTypes.length;
    }

    toggleCriteriaDropdown(fieldKey, ev) {
        if (ev) ev.stopPropagation();
        const wasOpen = this.state.criteriaOpenField === fieldKey;
        this.state.criteriaOpenField = wasOpen ? null : fieldKey;
    }

    isCriteriaDropdownOpen(fieldKey) {
        return this.state.criteriaOpenField === fieldKey;
    }

    toggleCriteriaValue(fieldKey, option, ev) {
        if (ev) ev.stopPropagation();
        const list = this.state.criteria[fieldKey];
        const idx = list.indexOf(option);
        if (idx === -1) {
            list.push(option);
        } else {
            list.splice(idx, 1);
        }
    }

    isCriteriaValueSelected(fieldKey, option) {
        return this.state.criteria[fieldKey].includes(option);
    }

    criteriaFieldSummary(fieldKey) {
        const list = this.state.criteria[fieldKey];
        return list.length ? list.join(", ") : "Sélectionner…";
    }

    // ---- Section Périodes ----
    // Par défaut la demie-journée de début est le matin et celle de fin
    // l'après-midi (staffing à la journée pleine), cf. doc "Section détail
    // de la période".
    addPeriod(ev) {
        if (ev) ev.stopPropagation();
        this._periodId++;
        this.state.periods.push({
            id: this._periodId,
            start: "",
            end: "",
            amount: 0,
            expanded: false,
            selected: false,
            halfDayStart: "Matin",
            halfDayEnd: "Après-midi",
            customFee: null,
            customFeeCurrency: "€",
            customCost: null,
            customCostCurrency: "€",
            status: "",
            description: "",
        });
    }

    duplicatePeriod(period, ev) {
        if (ev) ev.stopPropagation();
        this._periodId++;
        const idx = this.state.periods.indexOf(period);
        this.state.periods.splice(idx + 1, 0, { ...period, id: this._periodId, selected: false });
        this.state.periodMenuOpenId = null;
    }

    removePeriod(period, ev) {
        if (ev) ev.stopPropagation();
        const idx = this.state.periods.indexOf(period);
        if (idx !== -1) {
            this.state.periods.splice(idx, 1);
        }
        this.state.periodMenuOpenId = null;
    }

    togglePeriodExpand(period, ev) {
        if (ev) ev.stopPropagation();
        period.expanded = !period.expanded;
    }

    get allPeriodsExpanded() {
        return this.state.periods.length > 0 && this.state.periods.every((p) => p.expanded);
    }

    toggleExpandAllPeriods(ev) {
        if (ev) ev.stopPropagation();
        const expand = !this.allPeriodsExpanded;
        for (const p of this.state.periods) {
            p.expanded = expand;
        }
    }

    togglePeriodSelected(period, ev) {
        if (ev) ev.stopPropagation();
        period.selected = !period.selected;
    }

    get selectedPeriods() {
        return this.state.periods.filter((p) => p.selected);
    }

    togglePeriodMenu(period, ev) {
        if (ev) ev.stopPropagation();
        this.state.periodMenuOpenId = this.state.periodMenuOpenId === period.id ? null : period.id;
    }

    isPeriodMenuOpen(period) {
        return this.state.periodMenuOpenId === period.id;
    }

    // Napta calcule automatiquement si le staffing entraînera un conflit
    // (cf. doc staffing_creation-de-staffing §Périodes) ; on simule ce
    // calcul par un simple recouvrement de dates entre périodes en mode
    // "Dates fixes".
    get hasPeriodConflict() {
        const periods = this.state.periods.filter((p) => p.start && p.end);
        for (let i = 0; i < periods.length; i++) {
            for (let j = i + 1; j < periods.length; j++) {
                if (periods[i].start <= periods[j].end && periods[j].start <= periods[i].end) {
                    return true;
                }
            }
        }
        return false;
    }

    // ---- Édition en masse des périodes sélectionnées ----
    openBulkEditPeriods(ev) {
        if (ev) ev.stopPropagation();
        if (!this.selectedPeriods.length) {
            return;
        }
        this.state.bulkEdit = { amount: null, customFee: null, customFeeCurrency: "€", customCost: null, customCostCurrency: "€", status: "", description: "" };
        this.state.bulkEditOpen = true;
    }

    closeBulkEditPeriods(ev) {
        if (ev) ev.stopPropagation();
        this.state.bulkEditOpen = false;
    }

    deleteSelectedPeriods(ev) {
        if (ev) ev.stopPropagation();
        this.state.periods = this.state.periods.filter((p) => !p.selected);
    }

    applyBulkEditPeriods(ev) {
        if (ev) ev.stopPropagation();
        const edit = this.state.bulkEdit;
        for (const period of this.selectedPeriods) {
            if (edit.amount !== null && edit.amount !== "") period.amount = edit.amount;
            if (edit.customFee !== null && edit.customFee !== "") { period.customFee = edit.customFee; period.customFeeCurrency = edit.customFeeCurrency; }
            if (edit.customCost !== null && edit.customCost !== "") { period.customCost = edit.customCost; period.customCostCurrency = edit.customCostCurrency; }
            if (edit.status) period.status = edit.status;
            if (edit.description) period.description = edit.description;
            period.selected = false;
        }
        this.state.bulkEditOpen = false;
    }

    // ---- Section Utilisateurs ----
    get userSuggestions() {
        const search = this.state.userSearch.trim().toLowerCase();
        const existing = this.state.users.map((u) => u.name);
        return USER_DIRECTORY
            .filter((name) => !existing.includes(name))
            .filter((name) => !search || name.toLowerCase().includes(search))
            .slice(0, 8);
    }

    addUser(name, ev) {
        if (ev) ev.stopPropagation();
        this.state.users.push({ name, role: "", initials: computeInitials(name) });
        this.state.userOptions[name] = "Suggéré";
        this.state.userSearch = "";
    }

    removeUser(user, ev) {
        if (ev) ev.stopPropagation();
        const idx = this.state.users.indexOf(user);
        if (idx !== -1) {
            this.state.users.splice(idx, 1);
        }
        delete this.state.userOptions[user.name];
    }

    setUserOption(name, option, ev) {
        if (ev) ev.stopPropagation();
        this.state.userOptions[name] = option;
    }

    focusUserSearch(ev) {
        if (ev) ev.stopPropagation();
        this.state.userSearchFocused = true;
    }

    // ---- Remplacement de contributeur (édition uniquement) ----
    openReplace(index, ev) {
        if (ev) ev.stopPropagation();
        this.state.replaceOpen = { index };
        this.state.replaceScope = REPLACE_SCOPE_OPTIONS[0];
        this.state.replaceBy = "";
        this.state.replaceDate = "";
        this.state.replaceSearch = "";
    }

    closeReplace(ev) {
        if (ev) ev.stopPropagation();
        this.state.replaceOpen = null;
    }

    get replaceSuggestions() {
        const search = this.state.replaceSearch.trim().toLowerCase();
        const existing = this.state.users.map((u) => u.name);
        return USER_DIRECTORY
            .filter((name) => !existing.includes(name))
            .filter((name) => !search || name.toLowerCase().includes(search))
            .slice(0, 8);
    }

    focusReplaceSearch(ev) {
        if (ev) ev.stopPropagation();
        this.state.replaceSearchFocused = true;
    }

    pickReplaceBy(name, ev) {
        if (ev) ev.stopPropagation();
        this.state.replaceBy = name;
        this.state.replaceSearch = name;
        this.state.replaceSearchFocused = false;
    }

    applyReplace(ev) {
        if (ev) ev.stopPropagation();
        if (!this.state.replaceOpen || !this.state.replaceBy) {
            return;
        }
        const user = this.state.users[this.state.replaceOpen.index];
        user.name = this.state.replaceBy;
        user.role = "";
        user.initials = computeInitials(this.state.replaceBy);
        delete this.state.userOptions[user.name];
        this.state.userOptions[this.state.replaceBy] = "Suggéré";
        this.state.replaceOpen = null;
    }

    setAssignmentType(type, ev) {
        if (ev) ev.stopPropagation();
        this.state.assignmentType = type;
    }

    // ---- Section Informations ----
    get informationCount() {
        const info = this.state.info;
        return ["status", "daysSold", "description", "duration", "priority"].filter((k) => info[k]).length;
    }

    // ---- Section Commentaire ----
    get commentCount() {
        return this.state.comment.trim() ? 1 : 0;
    }
}
