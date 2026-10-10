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
// suggéré ou pré-positionné (= pré-booké), selon les droits de son créateur
// (doc staffing_pre-booking : Suggérée/Pré-booking sont liées à une DEMANDE,
// Simulée/Réelle sont liées à une AFFECTATION — les 4 niveaux sont proposés
// dans le même sélecteur par utilisateur, cf. capture produit).
const USER_STAFFING_OPTIONS = ["Suggérer", "Pré-positionner", "Simulé", "Réel"];
const USER_STAFFING_OPTION_SLUGS = { "Suggérer": "suggest", "Pré-positionner": "prebook", "Simulé": "simulated", "Réel": "real" };
const REPLACE_SCOPE_OPTIONS = ["Pour l'ensemble de la mission", "Pour une partie de la mission", "À partir d'une date spécifique"];

const ASSIGNMENT_STATUS_OPTIONS = ["Suggestion", "Pré-positionnement", "Staffing simulé", "Staffing confirmé"];
const PRIORITY_OPTIONS = ["Basse", "Normale", "Haute", "Urgente"];

const COMMENT_MAX_LENGTH = 200;

// ---- Profile Finder : volet de recherche de profils ouvert depuis l'icône
// loupe de la section Utilisateurs (ressemble au rapport "Planification
// individuelle", avec sélection multiple + bascule de statut par ligne). ----
const FINDER_WEEK_COLUMNS = [
    { key: "w46", label: "S46", date: "9 nov." },
    { key: "w47", label: "S47", date: "16 nov." },
    { key: "w48", label: "S48", date: "23 nov." },
    { key: "w49", label: "S49", date: "30 nov." },
    { key: "w50", label: "S50", date: "7 déc." },
    { key: "w51", label: "S51", date: "14 déc." },
];

const FINDER_PROJECT_POOL = [
    { client: "Tasmane", project: "Interne - K4M", internal: true },
    { client: "ARQUUS", project: "Arquus - audit architecture SI" },
    { client: "GRDF", project: "Orga et Change projet Biométhane DR nord" },
    { client: "CARVEN FRANCE", project: "MDM scoping and solution benchmark" },
];

const FINDER_ROLES = ["Consultant", "Consultant Senior", "Manager", "Directeur de mission", "Analyste"];
const FINDER_OFFICES = ["Paris", "Lyon", "Londres"];

/** Classe de couleur par seuil de charge, mêmes teintes que le rapport Planification individuelle. */
function finderCellClass(value) {
    if (value >= 101) return "o_napta_adw_finder_cell_red";
    if (value >= 90) return "o_napta_adw_finder_cell_green";
    if (value >= 50) return "o_napta_adw_finder_cell_amber";
    return "o_napta_adw_finder_cell_purple";
}

/** Liste factice de profils, générée de façon déterministe (pas de lien back-office). */
function buildFinderPeople() {
    return USER_DIRECTORY.map((name, i) => {
        const seed = i * 17 + name.length;
        const weeks = FINDER_WEEK_COLUMNS.map((_, wi) => (seed * (wi + 3) * 7) % 140);
        const projectCount = 1 + (seed % 2);
        const projects = Array.from({ length: projectCount }, (_, pi) => {
            const pool = FINDER_PROJECT_POOL[(seed + pi) % FINDER_PROJECT_POOL.length];
            return {
                ...pool,
                weeks: FINDER_WEEK_COLUMNS.map((_, wi) => (wi === 0 && pi === 1 ? null : Math.round(weeks[wi] * (pi === 0 ? 0.6 : 0.3)) || null)),
            };
        });
        return {
            id: "finder-" + i,
            name,
            initials: computeInitials(name),
            role: FINDER_ROLES[seed % FINDER_ROLES.length],
            office: FINDER_OFFICES[seed % FINDER_OFFICES.length],
            weeks,
            projects,
        };
    });
}

const FINDER_PEOPLE = buildFinderPeople();

// ---- Aperçu : volet plein-largeur ouvert depuis le bouton "Aperçu" du
// pied du tiroir, montre jour par jour la charge des utilisateurs déjà
// ajoutés à la demande/au staffing (réutilise finderCellClass pour les
// mêmes seuils de couleur que le Profile Finder). ----
const PREVIEW_WEEK_COUNT = 3;
const PREVIEW_MONTH_ABBR = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];

function buildPreviewDayColumns() {
    const start = new Date(2026, 10, 2);
    const columns = [];
    for (let i = 0; i < PREVIEW_WEEK_COUNT * 7; i++) {
        const d = new Date(start);
        d.setDate(start.getDate() + i);
        columns.push({
            key: "d" + i,
            label: d.getDate() + " " + PREVIEW_MONTH_ABBR[d.getMonth()],
            weekend: i % 7 === 5 || i % 7 === 6,
        });
    }
    return columns;
}

const PREVIEW_DAY_COLUMNS = buildPreviewDayColumns();

const PREVIEW_WEEK_BLOCKS = Array.from({ length: PREVIEW_WEEK_COUNT }, (_, wi) => ({
    key: "pw" + wi,
    weekdayStart: wi * 7,
}));

/** Ligne d'aperçu factice pour un utilisateur déjà ajouté à la demande. */
function buildPreviewRow(user, index) {
    const seed = index * 13 + user.name.length;
    const conflictStart = 10 + (seed % 3);
    const conflictEnd = conflictStart + 2;
    const totals = PREVIEW_DAY_COLUMNS.map((day, i) => {
        if (day.weekend) return (seed * (i + 1)) % 10;
        const base = 2 + ((seed * (i + 3)) % 64);
        return i >= conflictStart && i <= conflictEnd && index % 2 === 1 ? base + 90 : base;
    });
    const hasConflict = totals.some((v) => v >= 101);
    const projected = hasConflict
        ? PREVIEW_DAY_COLUMNS.map((_, i) => (i >= conflictStart && i <= conflictEnd ? Math.round(totals[i] * 0.55) : null))
        : null;
    const projectCount = 1 + (seed % 2);
    const projects = Array.from({ length: projectCount }, (_, pi) => {
        const pool = FINDER_PROJECT_POOL[(seed + pi) % FINDER_PROJECT_POOL.length];
        return {
            key: user.name + "-pprev-" + pi,
            client: pool.client,
            project: pool.project,
            internal: !!pool.internal,
            weeklyValues: Array.from({ length: PREVIEW_WEEK_COUNT }, (_, wi) => ((seed * (wi + pi + 2) * 3) % 60) || 2),
        };
    });
    const holidayIndex = (seed * 7) % PREVIEW_DAY_COLUMNS.length;
    return {
        id: "preview-" + index,
        name: user.name,
        initials: user.initials || computeInitials(user.name),
        totals,
        projected,
        projects,
        conges: PREVIEW_DAY_COLUMNS.map((day) => day.weekend),
        holidays: PREVIEW_DAY_COLUMNS.map((day, i) => i === holidayIndex && !day.weekend),
    };
}

const PREVIEW_GROUP_OPTIONS = ["Demi-journée", "Jour", "Semaine", "Mois", "Trimestre", "Année", "Aucun groupement"];

// Jours fériés fixes (mock, dates françaises) utilisés pour simuler la
// détection de conflit "congés ou jours fériés" (doc staffing_les-calendriers
// §Découper le staffing / notion de congé).
const MOCK_HOLIDAYS_MMDD = ["01-01", "05-01", "05-08", "07-14", "08-15", "11-01", "11-11", "12-25"];

// Toujours dériver la chaîne ISO des composantes LOCALES de la date (pas
// de toISOString(), qui convertit en UTC et décale la date d'un jour dès
// que le fuseau local est en avance/retard sur UTC à minuit).
function toIsoLocal(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
}

function isoDatesInRange(startIso, endIso) {
    const dates = [];
    if (!startIso || !endIso) return dates;
    let cur = new Date(startIso + "T00:00:00");
    const end = new Date(endIso + "T00:00:00");
    if (isNaN(cur) || isNaN(end)) return dates;
    while (cur <= end) {
        dates.push(toIsoLocal(cur));
        cur.setDate(cur.getDate() + 1);
    }
    return dates;
}

function holidaysInRange(startIso, endIso) {
    return isoDatesInRange(startIso, endIso).filter((iso) => MOCK_HOLIDAYS_MMDD.includes(iso.slice(5)));
}

/** Lundi (ISO) de la semaine contenant la date donnée. */
function weekStartIso(iso) {
    const date = new Date(iso + "T00:00:00");
    const day = date.getDay();
    const diff = (day === 0 ? -6 : 1) - day;
    date.setDate(date.getDate() + diff);
    return toIsoLocal(date);
}

/** Regroupe une liste de dates ISO triées par clé (jour/semaine/mois). */
function chunkDatesByKey(days, keyFn) {
    const chunks = [];
    let currentKey = null;
    let current = null;
    for (const d of days) {
        const key = keyFn(d);
        if (key !== currentKey) {
            current = [];
            chunks.push(current);
            currentKey = key;
        }
        current.push(d);
    }
    return chunks;
}

/**
 * Granularités de découpage disponibles pour une période, conformes à
 * doc staffing_les-calendriers §Découper le staffing : "Seules les options
 * possibles sont proposées" (ex. une période de 3 jours sur une même
 * semaine ne propose ni le découpage semaine ni le découpage mois).
 */
function splitGranularityOptions(period) {
    const days = isoDatesInRange(period.start, period.end);
    if (days.length <= 1) return [];
    const options = [{ value: "days", label: "Découper par jours" }];
    if (new Set(days.map(weekStartIso)).size > 1) {
        options.push({ value: "weeks", label: "Découper par semaines" });
    }
    if (new Set(days.map((d) => d.slice(0, 7))).size > 1) {
        options.push({ value: "months", label: "Découper par mois" });
    }
    return options;
}

function computeInitials(name) {
    return (name || "")
        .split(" ")
        .filter(Boolean)
        .slice(0, 2)
        .map((w) => w[0].toUpperCase())
        .join("");
}

/** "YYYY-MM-DD" -> "DD/MM/YYYY" (affichage). */
function formatIsoDateDisplay(iso) {
    if (!iso) return "?";
    const [y, m, d] = iso.split("-");
    return `${d}/${m}/${y}`;
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
        this.userStaffingOptionSlugs = USER_STAFFING_OPTION_SLUGS;
        this.replaceScopeOptions = REPLACE_SCOPE_OPTIONS;
        this.periodSelectPresets = ["Toutes les périodes", "Toutes les périodes passées", "Toutes les périodes futures"];
        this.assignmentStatusOptions = ASSIGNMENT_STATUS_OPTIONS;
        this.priorityOptions = PRIORITY_OPTIONS;
        this.commentMaxLength = COMMENT_MAX_LENGTH;
        this.finderWeekColumns = FINDER_WEEK_COLUMNS;
        this.finderPeople = FINDER_PEOPLE;
        this.previewDayColumns = PREVIEW_DAY_COLUMNS;
        this.previewWeekBlocks = PREVIEW_WEEK_BLOCKS;
        this.previewGroupOptions = PREVIEW_GROUP_OPTIONS;
        this._periodId = 0;

        const isEdit = this.props.mode === "edit";
        const record = this.props.record || null;

        this.state = useState({
            openSections: {},
            need: "",
            project: isEdit ? "" : "",
            title: this.defaultTitle,
            titleEditing: false,
            criteria: { skills: [], businessUnits: [], positions: [], offices: [], contractTypes: [] },
            criteriaOpenField: null,
            periods: [],
            periodsConfig: { planningMode: "Dates fixes", unit: "Jours", ignoreLeaves: false, autoSplit: false },
            periodMenuOpenId: null,
            periodSelectMenuOpen: false,
            periodSplitMenuOpen: false,
            conflictModalOpen: false,
            userOptionDropdownOpen: null,
            bulkEditOpen: false,
            bulkEdit: { amount: null, customFee: null, customFeeCurrency: "€", customCost: null, customCostCurrency: "€", status: "", description: "" },
            users: [],
            userOptions: {},
            userSearch: "",
            userSearchFocused: false,
            profileFinderOpen: false,
            finderExpanded: {},
            finderSelected: {},
            finderHoverId: null,
            finderStatusMenuOpen: null,
            previewOpen: false,
            previewBannerDismissed: false,
            previewExpanded: {},
            previewDisplayMenuOpen: false,
            previewInfoOpen: false,
            previewSettings: { unit: "tace", includeReal: true, includeSimulated: true, includePrebooked: false, groupBy: "Jour" },
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
            this.state.userOptions = Object.fromEntries(this.state.users.map((u) => [u.name, "Pré-positionner"]));
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
                tags: [
                    { icon: "fa-sitemap", label: "Départements", value: record.department || "—" },
                    { icon: "fa-map-marker", label: "Bureaux", value: record.office || "—" },
                ],
            };
        }
        return {
            title: record.project,
            subtitle: record.client,
            tags: [
                { icon: "fa-sitemap", label: "Départements", value: (record.businessUnits || []).join(", ") || "—" },
                { icon: "fa-map-marker", label: "Bureaux", value: "—" },
            ],
        };
    }

    // Titre fixe en création ; personnalisable en édition (champ éditable
    // avec icône crayon dans l'en-tête, observé en production).
    get defaultTitle() {
        if (this.props.mode === "create") {
            return "Créer une demande";
        }
        return this.props.kind === "staffing" ? "Personnaliser le titre du staffing" : "Personnaliser le titre de la demande";
    }

    startEditTitle(ev) {
        if (ev) ev.stopPropagation();
        if (this.props.mode !== "edit") return;
        this.state.titleEditing = true;
    }

    commitTitle(ev) {
        if (ev) ev.stopPropagation();
        if (!this.state.title.trim()) {
            this.state.title = this.defaultTitle;
        }
        this.state.titleEditing = false;
    }

    onTitleKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.commitTitle(ev);
        }
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
        this.state.periodSelectMenuOpen = false;
        this.state.periodSplitMenuOpen = false;
        this.state.userOptionDropdownOpen = null;
        this.state.finderStatusMenuOpen = null;
        this.state.previewDisplayMenuOpen = false;
        this.state.previewInfoOpen = false;
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
            holidayAcknowledged: false,
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

    // ---- Sélection par préréglage (icône "lasso") ----
    togglePeriodSelectMenu(ev) {
        if (ev) ev.stopPropagation();
        this.state.periodSelectMenuOpen = !this.state.periodSelectMenuOpen;
    }

    applyPeriodSelectPreset(preset, ev) {
        if (ev) ev.stopPropagation();
        const today = toIsoLocal(new Date());
        for (const p of this.state.periods) {
            if (preset === this.periodSelectPresets[0]) {
                p.selected = true;
            } else if (preset === this.periodSelectPresets[1]) {
                p.selected = !!p.end && p.end < today;
            } else {
                p.selected = !!p.start && p.start >= today;
            }
        }
        this.state.periodSelectMenuOpen = false;
    }

    // ---- Découper (doc staffing_les-calendriers §Découper le staffing :
    // scinde une période en sous-périodes jour/semaine/mois, en conservant
    // la charge totale. "Seules les options possibles sont proposées" en
    // fonction de l'étendue de la période sélectionnée. ----
    togglePeriodSplitMenu(ev) {
        if (ev) ev.stopPropagation();
        this.state.periodSplitMenuOpen = !this.state.periodSplitMenuOpen;
    }

    // Options de découpage dynamiques, calculées sur la première période
    // sélectionnée (cf. doc : le découpage semaine/mois n'est proposé que
    // si la période s'étend sur plusieurs semaines/mois).
    get periodSplitOptions() {
        if (!this.selectedPeriods.length) return [];
        return splitGranularityOptions(this.selectedPeriods[0]);
    }

    splitSelectedPeriods(granularity, ev) {
        if (ev) ev.stopPropagation();
        const targets = this.selectedPeriods.filter((p) => p.start && p.end);
        const keyFn = granularity === "weeks" ? weekStartIso : granularity === "months" ? (d) => d.slice(0, 7) : (d) => d;
        for (const period of targets) {
            const days = isoDatesInRange(period.start, period.end);
            if (days.length <= 1) continue;
            const chunks = chunkDatesByKey(days, keyFn);
            if (chunks.length <= 1) continue;
            const idx = this.state.periods.indexOf(period);
            const newPeriods = chunks.map((chunk) => {
                this._periodId++;
                const share = Math.round((period.amount * (chunk.length / days.length)) * 100) / 100;
                return { ...period, id: this._periodId, start: chunk[0], end: chunk[chunk.length - 1], amount: share, selected: false, expanded: false };
            });
            this.state.periods.splice(idx, 1, ...newPeriods);
        }
        this.state.periodMenuOpenId = null;
        this.state.periodSplitMenuOpen = false;
    }

    // ---- Conflit "congés ou jours fériés" (doc staffing_les-calendriers :
    // le système propose de déduire les jours de congé/férié de la charge) ----
    periodHolidays(period) {
        if (this.state.periodsConfig.planningMode !== "Dates fixes" || this.state.periodsConfig.unit !== "Jours") {
            return [];
        }
        return holidaysInRange(period.start, period.end);
    }

    isPeriodConflicting(period) {
        return !period.holidayAcknowledged && this.periodHolidays(period).length > 0;
    }

    get conflictingPeriods() {
        return this.state.periods.filter((p) => this.isPeriodConflicting(p));
    }

    get conflictCount() {
        return this.conflictingPeriods.length;
    }

    get conflictBadgeLabel() {
        return this.conflictCount > 9 ? "9+" : String(this.conflictCount);
    }

    get conflictDetails() {
        return this.conflictingPeriods.map((period) => {
            const count = this.periodHolidays(period).length;
            const before = Number(period.amount) || 0;
            const after = Math.max(before - count, 0);
            return { period, count, before, after };
        });
    }

    get conflictTotalDelta() {
        return this.conflictDetails.reduce((sum, d) => sum + (d.after - d.before), 0);
    }

    get conflictPersonName() {
        return this.state.users.length ? this.state.users[0].name : null;
    }

    formatPeriodDate(iso) {
        return formatIsoDateDisplay(iso);
    }

    openConflictModal(ev) {
        if (ev) ev.stopPropagation();
        if (!this.conflictCount) return;
        this.state.conflictModalOpen = true;
    }

    closeConflictModal(ev) {
        if (ev) ev.stopPropagation();
        this.state.conflictModalOpen = false;
    }

    applyConflictAdjustments(ev) {
        if (ev) ev.stopPropagation();
        for (const { period, after } of this.conflictDetails) {
            period.amount = after;
            period.holidayAcknowledged = true;
        }
        this.state.conflictModalOpen = false;
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
        this.state.userOptions[name] = "Suggérer";
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

    toggleUserOptionDropdown(name, ev) {
        if (ev) ev.stopPropagation();
        this.state.userOptionDropdownOpen = this.state.userOptionDropdownOpen === name ? null : name;
    }

    isUserOptionDropdownOpen(name) {
        return this.state.userOptionDropdownOpen === name;
    }

    setUserOption(name, option, ev) {
        if (ev) ev.stopPropagation();
        this.state.userOptions[name] = option;
        this.state.userOptionDropdownOpen = null;
    }

    focusUserSearch(ev) {
        if (ev) ev.stopPropagation();
        this.state.userSearchFocused = true;
    }

    // ---- Profile Finder (icône loupe de la section Utilisateurs) ----
    toggleProfileFinder(ev) {
        if (ev) ev.stopPropagation();
        this.state.profileFinderOpen = !this.state.profileFinderOpen;
        if (this.state.profileFinderOpen) {
            this.state.previewOpen = false;
        } else {
            this.state.finderSelected = {};
            this.state.finderStatusMenuOpen = null;
        }
    }

    closeProfileFinder(ev) {
        if (ev) ev.stopPropagation();
        this.state.profileFinderOpen = false;
        this.state.finderSelected = {};
        this.state.finderStatusMenuOpen = null;
    }

    // ---- Aperçu (bouton "Aperçu" du pied du tiroir) ----
    get previewRows() {
        return this.state.users.map((user, i) => buildPreviewRow(user, i));
    }

    openPreview(ev) {
        if (ev) ev.stopPropagation();
        this.state.profileFinderOpen = false;
        this.state.previewBannerDismissed = false;
        this.state.previewOpen = true;
    }

    closePreview(ev) {
        if (ev) ev.stopPropagation();
        this.state.previewOpen = false;
        this.state.previewDisplayMenuOpen = false;
        this.state.previewInfoOpen = false;
    }

    dismissPreviewBanner(ev) {
        if (ev) ev.stopPropagation();
        this.state.previewBannerDismissed = true;
    }

    togglePreviewExpand(rowId, ev) {
        if (ev) ev.stopPropagation();
        this.state.previewExpanded[rowId] = !this.state.previewExpanded[rowId];
    }

    isPreviewExpanded(rowId) {
        return !!this.state.previewExpanded[rowId];
    }

    togglePreviewDisplayMenu(ev) {
        if (ev) ev.stopPropagation();
        this.state.previewInfoOpen = false;
        this.state.previewDisplayMenuOpen = !this.state.previewDisplayMenuOpen;
    }

    togglePreviewInfo(ev) {
        if (ev) ev.stopPropagation();
        this.state.previewDisplayMenuOpen = false;
        this.state.previewInfoOpen = !this.state.previewInfoOpen;
    }

    previewCellClass(value) {
        return finderCellClass(value);
    }

    toggleFinderExpand(personId, ev) {
        if (ev) ev.stopPropagation();
        this.state.finderExpanded[personId] = !this.state.finderExpanded[personId];
    }

    isFinderExpanded(personId) {
        return !!this.state.finderExpanded[personId];
    }

    toggleFinderSelect(personId, ev) {
        if (ev) ev.stopPropagation();
        this.state.finderSelected[personId] = !this.state.finderSelected[personId];
    }

    isFinderSelected(personId) {
        return !!this.state.finderSelected[personId];
    }

    get finderSelectedCount() {
        return Object.values(this.state.finderSelected).filter(Boolean).length;
    }

    /** Ajoute (ou met à jour) un profil dans la section Utilisateurs du tiroir, avec le statut choisi. */
    addFinderPerson(person, option) {
        if (!this.state.users.some((u) => u.name === person.name)) {
            this.state.users.push({ name: person.name, role: person.role, initials: person.initials });
        }
        this.state.userOptions[person.name] = option;
    }

    isFinderPersonAdded(person) {
        return this.state.users.some((u) => u.name === person.name);
    }

    finderPersonStatus(person) {
        return this.state.userOptions[person.name] || null;
    }

    // Les profils déjà liés à la demande/au staffing remontent en tête de
    // liste (ordre d'origine conservé au sein de chaque groupe).
    get sortedFinderPeople() {
        const added = [];
        const rest = [];
        for (const person of this.finderPeople) {
            (this.isFinderPersonAdded(person) ? added : rest).push(person);
        }
        return added.concat(rest);
    }

    bulkAddFromFinder(option, ev) {
        if (ev) ev.stopPropagation();
        for (const person of this.finderPeople) {
            if (this.state.finderSelected[person.id]) {
                this.addFinderPerson(person, option);
            }
        }
        this.state.finderSelected = {};
    }

    finderCellClass(value) {
        return finderCellClass(value);
    }

    // Le déclencheur de statut par ligne (pilule + chevron) n'apparaît qu'au
    // survol d'une ligne de premier niveau — ailleurs, le statut déjà
    // affecté s'affiche en texte simple (non interactif).
    setFinderHover(personId, ev) {
        if (ev) ev.stopPropagation();
        this.state.finderHoverId = personId;
    }

    isFinderHovered(personId) {
        return this.state.finderHoverId === personId;
    }

    toggleFinderStatusMenu(personId, ev) {
        if (ev) ev.stopPropagation();
        this.state.finderStatusMenuOpen = this.state.finderStatusMenuOpen === personId ? null : personId;
    }

    isFinderStatusMenuOpen(personId) {
        return this.state.finderStatusMenuOpen === personId;
    }

    pickFinderStatus(person, option, ev) {
        if (ev) ev.stopPropagation();
        this.addFinderPerson(person, option);
        this.state.finderStatusMenuOpen = null;
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
        this.state.userOptions[this.state.replaceBy] = "Suggérer";
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
