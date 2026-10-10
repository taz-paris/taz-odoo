/** @odoo-module **/

import { Component, useState, useRef, onWillUnmount } from "@odoo/owl";
import { AssignmentDrawer } from "../../components/assignment_drawer/assignment_drawer";

/**
 * Page « Staffing > Calendrier global », reconstruite à partir de
 * modules-napta/staffing_les-calendriers.md (section "Le calendrier global",
 * "Les actions" et "Design" qui s'appliquent à tous les calendriers).
 *
 * Contrairement aux autres pages du prototype, les données ne sont pas une
 * liste figée : chaque collaborateur reçoit un planning généré de façon
 * déterministe (PRNG à seed fixe) sur une plage de 3 ans (2025-2027), afin
 * que la navigation temporelle (flèches, "Aujourd'hui", "Aller à") et le
 * zoom (semaine/mois/semestre) aient un vrai effet au lieu d'être des
 * boutons décoratifs.
 */

// ---- Utilitaires dates ----
function addDays(date, n) {
    const d = new Date(date);
    d.setDate(d.getDate() + n);
    return d;
}
function startOfWeek(date) {
    const d = new Date(date);
    d.setHours(0, 0, 0, 0);
    const day = (d.getDay() + 6) % 7; // 0 = lundi
    return addDays(d, -day);
}
function startOfMonth(date) {
    return new Date(date.getFullYear(), date.getMonth(), 1);
}
function sameDay(a, b) {
    return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}
function isWeekend(date) {
    const d = date.getDay();
    return d === 0 || d === 6;
}
function businessDays(start, end) {
    let n = 0;
    for (let d = new Date(start); d <= end; d = addDays(d, 1)) {
        if (!isWeekend(d)) n++;
    }
    return n;
}
const MONTH_ABBR = ["Janv.", "Févr.", "Mars", "Avr.", "Mai", "Juin", "Juil.", "Août", "Sept.", "Oct.", "Nov.", "Déc."];
const DAY_ABBR = ["Di", "Lu", "Ma", "Me", "Je", "Ve", "Sa"];
function fmtShort(date) {
    return String(date.getDate()).padStart(2, "0") + "/" + String(date.getMonth() + 1).padStart(2, "0") + "/" + String(date.getFullYear()).slice(2);
}

// ---- PRNG déterministe (mulberry32) pour générer un planning stable ----
function mulberry32(seed) {
    let s = seed >>> 0;
    return function () {
        s = (s + 0x6d2b79f5) >>> 0;
        let t = Math.imul(s ^ (s >>> 15), 1 | s);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

const SCHEDULE_START = new Date(2025, 0, 1);
const SCHEDULE_END = new Date(2027, 11, 31);
const HOLIDAYS_MMDD = ["01-01", "05-01", "05-08", "07-14", "08-15", "11-01", "11-11", "12-25"];

const PROJECT_POOL = [
    { client: "LVMH", project: "Amélioration process" },
    { client: "BackMarket", project: "Refonte" },
    { client: "Orange", project: "Audit Interne" },
    { client: "INTERNE", project: "Amélioration des process de déploiement" },
    { client: "Aircall", project: "Audit data" },
    { client: "VEOLIA", project: "Accompagnement" },
    { client: "BNP Paribas", project: "Déploiement Salesforce" },
    { client: "PSG", project: "Optimisation fiscale" },
    { client: "ManoMano", project: "Audit Interne" },
    { client: "Google", project: "Audit Interne" },
    { client: "Decathlon", project: "Diffusion de l'innovation" },
];
const CO_OWNERS_POOL = ["Hugo LEGRAND", "Camille FABRE", "Nicolas ROUX", "Léa PERRIN", "Antoine GUERIN"];

const SURNAMES = ["AMERI", "BARBIER", "BARTOL", "BARTOLIE", "BOLE", "BERGER", "BOMPARD", "DUBOIS", "LEFORT", "MAGGAL", "NGUYEN", "MEROT", "JOHNSON", "DAVOS", "BERARDA", "BRUN", "DOMETTE", "RODRIGUES", "GALLO", "CONSTABLE", "FOURNIER", "ANDRE", "MERCIER", "BLANCHARD", "GAUTIER", "BOYER", "GARNIER", "CHEVALIER", "MARCHAND", "ROUSSEL", "MOREL", "GIRARD", "LAMBERT", "FONTAINE"];
const FIRSTNAMES = ["Armand", "Gilles", "Jérémie", "Aurore", "Timothée", "Claire", "Jess", "Marie", "Benjamin", "Fiona", "Oliver", "Isabelle", "Christopher", "Maria", "Katharina", "Arnaude", "Christophe", "Marie-Claire", "Stéphane", "Etienne", "Sophie", "Julie", "Nicolas", "Camille", "Hugo", "Léa", "Antoine", "Paul", "Marc", "Emma", "Louis", "Clara", "David", "Alice"];
const ROLES = ["Consultant Junior", "Consultant Senior", "Manager", "Directeur", "Analyste"];
const DEPTS = ["Data & Analytics", "Management des organisations", "Stratégie", "Finance"];
const OFFICES = ["Paris", "Londres", "Lyon"];

function computeInitials(name) {
    return name
        .split(" ")
        .filter(Boolean)
        .slice(0, 2)
        .map((p) => p[0])
        .join("")
        .toUpperCase();
}

/** Génère le planning (segments "travail" + segments "absence/férié") d'un collaborateur. */
function generateSchedule(seed) {
    const rand = mulberry32(seed);
    const work = [];
    let cursor = new Date(SCHEDULE_START);
    let segId = 0;
    while (cursor < SCHEDULE_END) {
        const weeks = 1 + Math.floor(rand() * 3);
        const end = addDays(cursor, weeks * 7 - 1);
        const proj = PROJECT_POOL[Math.floor(rand() * PROJECT_POOL.length)];
        const rate = [100, 80, 75, 60, 50, 40, 33, 25][Math.floor(rand() * 8)];
        const type = rand() < 0.25 ? "simulated" : "real";
        work.push({
            id: "w" + seed + "-" + segId++,
            start: new Date(cursor),
            end,
            type,
            client: proj.client,
            project: proj.project,
            rate,
            billed: rand() < 0.5,
            fee: 400 + Math.floor(rand() * 10) * 50,
        });
        if (rand() < 0.22) {
            const overlapStart = addDays(cursor, Math.floor((rand() * weeks * 7) / 2));
            const overlapLen = 1 + Math.floor(rand() * 5);
            const proj2 = PROJECT_POOL[Math.floor(rand() * PROJECT_POOL.length)];
            work.push({
                id: "w" + seed + "-" + segId++,
                start: overlapStart,
                end: addDays(overlapStart, overlapLen - 1),
                type: rand() < 0.5 ? "simulated" : "real",
                client: proj2.client,
                project: proj2.project,
                rate: 20 + Math.floor(rand() * 60),
                billed: rand() < 0.5,
                fee: 400 + Math.floor(rand() * 10) * 50,
            });
        }
        cursor = addDays(end, 1 + Math.floor(rand() * 3));
    }
    // Marque "conflit" tout segment qui chevauche un autre segment de travail
    for (const seg of work) {
        seg.conflict = work.some((other) => other !== seg && other.start <= seg.end && other.end >= seg.start);
    }

    const leave = [];
    let leaveId = 0;
    for (let i = 0; i < 4; i++) {
        const offsetDays = Math.floor(rand() * ((SCHEDULE_END - SCHEDULE_START) / 86400000));
        const start = addDays(SCHEDULE_START, offsetDays);
        const len = 3 + Math.floor(rand() * 8);
        leave.push({ id: "a" + seed + "-" + leaveId++, start, end: addDays(start, len - 1), type: "absence", label: "Absence" });
    }
    for (const mmdd of HOLIDAYS_MMDD) {
        const [mm, dd] = mmdd.split("-").map(Number);
        for (let y = SCHEDULE_START.getFullYear(); y <= SCHEDULE_END.getFullYear(); y++) {
            const d = new Date(y, mm - 1, dd);
            if (d >= SCHEDULE_START && d <= SCHEDULE_END) {
                leave.push({ id: "h" + seed + "-" + leaveId++, start: d, end: d, type: "holiday", label: "Jour férié" });
            }
        }
    }
    return { work, leave };
}

function buildPeople() {
    return SURNAMES.map((surname, i) => {
        const first = FIRSTNAMES[i];
        const seed = i * 101 + 7;
        const schedule = generateSchedule(seed);
        return {
            id: i + 1,
            name: `${surname} ${first}`,
            initials: computeInitials(`${first} ${surname}`),
            role: `${ROLES[seed % ROLES.length]} - ${DEPTS[(seed * 3) % DEPTS.length]} - ${OFFICES[seed % OFFICES.length]}`,
            ...schedule,
        };
    });
}

/** Range gloutonne en "lanes" (sous-lignes) pour que deux segments qui se chevauchent dans le temps ne se superposent jamais visuellement. */
function packLanes(segments) {
    const sorted = [...segments].sort((a, b) => a.start - b.start);
    const lanes = [];
    for (const seg of sorted) {
        let lane = lanes.find((l) => l[l.length - 1].end < seg.start);
        if (!lane) {
            lane = [];
            lanes.push(lane);
        }
        lane.push(seg);
    }
    return lanes;
}

const ZOOM_DAYS = { semaine: 7, mois: 35, semestre: 182 };

function weekNumber(weekStart) {
    const jan1 = new Date(weekStart.getFullYear(), 0, 1);
    return Math.ceil(((weekStart - jan1) / 86400000 + jan1.getDay() + 1) / 7);
}

const FILTER_SECTIONS = [
    { title: "Statuts", items: ["Statut de période de staffing", "Statut de staffing"] },
    { title: "Affectation", items: ["Type d'affectation", "Unité commerciale (Utilisateur)", "Client", "Bureau", "Poste", "Projet", "Compétence", "Type de contrat"] },
    { title: "Autre", items: ["Utilisateur"] },
];

export class StaffingGlobalCalendarPage extends Component {
    static template = "staffing.StaffingGlobalCalendarPage";
    static props = { page: Object };
    static components = { AssignmentDrawer };

    setup() {
        this.monthAbbr = MONTH_ABBR;
        this.filterSections = FILTER_SECTIONS;
        this.legend = [
            { type: "real", label: "Staffing réel" },
            { type: "simulated", label: "Staffing simulé" },
            { type: "conflict", label: "Conflit (charge > 100%)" },
            { type: "absence", label: "Absence / Jour férié" },
        ];
        this.rightsTooltip =
            "L'utilisateur connecté ne peut voir que les utilisateurs et les projets que ses " +
            "droits lui permettent de voir. Les périodes en conflit (charge supérieure à 100% " +
            "d'occupation) sont affichées en rouge.";

        const today = new Date();
        today.setHours(0, 0, 0, 0);
        this.today = today;

        this.state = useState({
            people: buildPeople(),
            anchor: new Date(today),
            zoom: "mois",
            unit: "jours",
            sort: "user",
            filterOpen: false,
            sortOpen: false,
            displayOpen: false,
            goToOpen: false,
            goToMonth: today.getMonth(),
            goToYear: today.getFullYear(),
            page: 1,
            pageSize: 30,
            pinned: {},
            hoverPersonId: null,
            openPeriod: null, // { personId, pool: 'work'|'leave', segmentId }
            repeatFormOpen: false,
            repeatWeeks: 1,
            repeatCount: 2,
            drag: null,
            assignmentDrawer: null,
            quickFilterActive: false,
        });

        this.gridRef = useRef("grid");

        this._onKeydown = (ev) => {
            if (ev.key === "Escape" && this.state.drag) {
                this.state.drag = null;
            }
        };
        window.addEventListener("keydown", this._onKeydown);
        onWillUnmount(() => window.removeEventListener("keydown", this._onKeydown));
    }

    // ---- Fenêtre de dates visible (zoom + ancre) ----
    get windowStart() {
        if (this.state.zoom === "semestre") return startOfMonth(this.state.anchor);
        return startOfWeek(this.state.anchor);
    }

    get days() {
        const n = ZOOM_DAYS[this.state.zoom];
        const start = this.windowStart;
        return Array.from({ length: n }, (_, i) => {
            const d = addDays(start, i);
            return { date: d, weekend: isWeekend(d), isToday: sameDay(d, this.today), dayNum: d.getDate(), dayAbbr: DAY_ABBR[d.getDay()] };
        });
    }

    get headerGroups() {
        const days = this.days;
        const groups = [];
        if (this.state.zoom === "semestre") {
            for (const d of days) {
                const label = MONTH_ABBR[d.date.getMonth()] + " " + d.date.getFullYear();
                const last = groups[groups.length - 1];
                if (last && last.label === label) last.span++;
                else groups.push({ label, span: 1 });
            }
        } else {
            for (const d of days) {
                const wkStart = startOfWeek(d.date);
                const label = "S" + weekNumber(wkStart) + " " + MONTH_ABBR[wkStart.getMonth()] + " " + wkStart.getFullYear();
                const last = groups[groups.length - 1];
                if (last && last.label === label) last.span++;
                else groups.push({ label, span: 1 });
            }
        }
        return groups;
    }

    get showDayNumbers() {
        return this.state.zoom !== "semestre";
    }

    // ---- Tri + pagination ----
    get sortedPeople() {
        const people = [...this.state.people];
        if (this.state.sort === "position") {
            people.sort((a, b) => a.role.localeCompare(b.role, "fr"));
        } else {
            people.sort((a, b) => a.name.localeCompare(b.name, "fr"));
        }
        return people;
    }

    get visiblePeople() {
        if (this.quickFilterActive) {
            return this.sortedPeople.filter((p) => this.state.pinned[p.id]);
        }
        const start = (this.state.page - 1) * this.state.pageSize;
        return this.sortedPeople.slice(start, start + this.state.pageSize);
    }

    get pageCount() {
        return Math.max(1, Math.ceil(this.sortedPeople.length / this.state.pageSize));
    }

    goPage(delta, ev) {
        if (ev) ev.stopPropagation();
        this.state.page = Math.min(this.pageCount, Math.max(1, this.state.page + delta));
    }

    // ---- Lanes (sous-lignes) visibles pour un collaborateur ----
    personLanes(person) {
        const days = this.days;
        const winStart = days[0].date;
        const winEnd = days[days.length - 1].date;
        const clip = (segs) => segs.filter((s) => s.end >= winStart && s.start <= winEnd);
        const workLanes = packLanes(clip(person.work));
        const leaveLanes = packLanes(clip(person.leave));
        return { workLanes, leaveLanes, laneCount: Math.max(1, workLanes.length) + leaveLanes.length };
    }

    segmentGridStyle(segment, laneIndex) {
        const days = this.days;
        let colStart = -1;
        let colEnd = -1;
        for (let i = 0; i < days.length; i++) {
            if (days[i].date >= segment.start && days[i].date <= segment.end) {
                if (colStart === -1) colStart = i;
                colEnd = i;
            }
        }
        if (colStart === -1) return null;
        return `grid-column: ${colStart + 1} / span ${colEnd - colStart + 1}; grid-row: ${laneIndex + 1};`;
    }

    weekendOverlaysForLane(segments, laneIndex) {
        const days = this.days;
        const overlays = [];
        for (const seg of segments) {
            for (let i = 0; i < days.length; i++) {
                if (days[i].weekend && days[i].date >= seg.start && days[i].date <= seg.end) {
                    overlays.push({ key: seg.id + "-wk" + i, style: `grid-column: ${i + 1}; grid-row: ${laneIndex + 1};` });
                }
            }
        }
        return overlays;
    }

    segmentDays(segment) {
        return businessDays(segment.start, segment.end);
    }

    formatPeriodDate(date) {
        return fmtShort(date);
    }

    segmentLabel(segment) {
        const days = Math.round(this.segmentDays(segment) * (segment.rate / 100) * 10) / 10;
        if (this.state.unit === "heures") return days * 8 + "h";
        if (this.state.unit === "taux") return segment.rate + "%";
        return days + "j";
    }

    // ---- Navigation temporelle ----
    get windowLabel() {
        const start = this.windowStart;
        const end = addDays(start, ZOOM_DAYS[this.state.zoom] - 1);
        return fmtShort(start) + " → " + fmtShort(end);
    }

    goPrev(ev) {
        if (ev) ev.stopPropagation();
        this.state.anchor = addDays(this.windowStart, -ZOOM_DAYS[this.state.zoom]);
    }

    goNext(ev) {
        if (ev) ev.stopPropagation();
        this.state.anchor = addDays(this.windowStart, ZOOM_DAYS[this.state.zoom]);
    }

    goToday(ev) {
        if (ev) ev.stopPropagation();
        this.state.anchor = new Date(this.today);
    }

    toggleGoTo(ev) {
        if (ev) ev.stopPropagation();
        this.closeMenus({ keep: "goToOpen" });
        this.state.goToOpen = !this.state.goToOpen;
    }

    get goToMonthLabel() {
        return MONTH_ABBR[this.state.goToMonth];
    }

    shiftGoToMonth(delta, ev) {
        if (ev) ev.stopPropagation();
        let m = this.state.goToMonth + delta;
        let y = this.state.goToYear;
        if (m < 0) {
            m = 11;
            y--;
        } else if (m > 11) {
            m = 0;
            y++;
        }
        this.state.goToMonth = m;
        this.state.goToYear = y;
    }

    get goToDays() {
        const first = new Date(this.state.goToYear, this.state.goToMonth, 1);
        const start = startOfWeek(first);
        return Array.from({ length: 42 }, (_, i) => addDays(start, i));
    }

    pickGoToDate(date, ev) {
        if (ev) ev.stopPropagation();
        this.state.anchor = new Date(date);
        this.state.goToOpen = false;
    }

    // ---- Menus toolbar ----
    closeMenus(opts = {}) {
        if (opts.keep !== "filterOpen") this.state.filterOpen = false;
        if (opts.keep !== "sortOpen") this.state.sortOpen = false;
        if (opts.keep !== "displayOpen") this.state.displayOpen = false;
        if (opts.keep !== "goToOpen") this.state.goToOpen = false;
        if (opts.keep !== "openPeriod") this.state.openPeriod = null;
        this.state.repeatFormOpen = false;
    }

    toggleFilter(ev) {
        if (ev) ev.stopPropagation();
        const next = !this.state.filterOpen;
        this.closeMenus({ keep: "filterOpen" });
        this.state.filterOpen = next;
    }

    toggleSort(ev) {
        if (ev) ev.stopPropagation();
        const next = !this.state.sortOpen;
        this.closeMenus({ keep: "sortOpen" });
        this.state.sortOpen = next;
    }

    setSort(key, ev) {
        if (ev) ev.stopPropagation();
        this.state.sort = key;
        this.state.sortOpen = false;
    }

    toggleDisplay(ev) {
        if (ev) ev.stopPropagation();
        const next = !this.state.displayOpen;
        this.closeMenus({ keep: "displayOpen" });
        this.state.displayOpen = next;
    }

    setUnit(unit, ev) {
        if (ev) ev.stopPropagation();
        this.state.unit = unit;
    }

    setZoom(zoom, ev) {
        if (ev) ev.stopPropagation();
        this.state.anchor = this.windowStart;
        this.state.zoom = zoom;
    }

    // ---- Filtre utilisateur rapide (épingler) ----
    togglePin(personId, ev) {
        if (ev) ev.stopPropagation();
        this.state.pinned[personId] = !this.state.pinned[personId];
        if (!this.state.pinned[personId]) delete this.state.pinned[personId];
    }

    get pinnedCount() {
        return Object.keys(this.state.pinned).length;
    }

    get quickFilterActive() {
        return this.state.quickFilterActive;
    }

    toggleQuickFilter(ev) {
        if (ev) ev.stopPropagation();
        this.state.quickFilterActive = !this.state.quickFilterActive;
    }

    clearPins(ev) {
        if (ev) ev.stopPropagation();
        this.state.pinned = {};
        this.state.quickFilterActive = false;
    }

    // ---- Survol d'une ligne collaborateur ----
    setHoverPerson(personId, ev) {
        if (ev) ev.stopPropagation();
        this.state.hoverPersonId = personId;
    }

    openAddStaffing(person, ev) {
        if (ev) ev.stopPropagation();
        this.state.hoverPersonId = null;
        this.state.assignmentDrawer = {
            mode: "create",
            kind: "staffing",
            record: null,
            presetUsers: [{ name: person.name, role: person.role, initials: person.initials }],
        };
    }

    seeProfile(person, ev) {
        if (ev) ev.stopPropagation();
        this.state.hoverPersonId = null;
    }

    closeAssignmentDrawer() {
        this.state.assignmentDrawer = null;
    }

    // ---- Pop-in d'une période de staffing ----
    openPeriod(person, pool, segment, ev) {
        if (ev) ev.stopPropagation();
        this.closeMenus({ keep: "openPeriod" });
        this.state.openPeriod = { personId: person.id, pool, segmentId: segment.id };
    }

    closePeriod(ev) {
        if (ev) ev.stopPropagation();
        this.state.openPeriod = null;
        this.state.repeatFormOpen = false;
    }

    get openPeriodCtx() {
        const o = this.state.openPeriod;
        if (!o) return null;
        const person = this.state.people.find((p) => p.id === o.personId);
        if (!person) return null;
        const segment = person[o.pool].find((s) => s.id === o.segmentId);
        if (!segment) return null;
        return { person, pool: o.pool, segment };
    }

    get openPeriodProject() {
        const ctx = this.openPeriodCtx;
        if (!ctx) return null;
        return {
            start: fmtShort(SCHEDULE_START),
            end: fmtShort(SCHEDULE_END),
            coOwners: CO_OWNERS_POOL.slice(0, 2 + (ctx.segment.id.length % 2)).join(", "),
        };
    }

    editPeriod(ev) {
        if (ev) ev.stopPropagation();
        const ctx = this.openPeriodCtx;
        if (!ctx) return;
        const seg = ctx.segment;
        this.state.assignmentDrawer = {
            mode: "edit",
            kind: "staffing",
            record: {
                project: seg.client,
                subproject: seg.project,
                employee: { name: ctx.person.name, role: ctx.person.role, initials: ctx.person.initials },
                kind: seg.type === "simulated" ? "simulated" : "real",
                status: "en_cours",
                period: fmtShort(seg.start) + " → " + fmtShort(seg.end),
                rate: seg.rate + "% (" + this.segmentDays(seg) + " jours)",
            },
        };
        this.closePeriod();
    }

    duplicatePeriod(ev) {
        if (ev) ev.stopPropagation();
        const ctx = this.openPeriodCtx;
        if (!ctx) return;
        const seg = ctx.segment;
        const len = Math.round((seg.end - seg.start) / 86400000);
        const newStart = addDays(seg.end, 2);
        ctx.person[ctx.pool].push({ ...seg, id: seg.id + "-copy" + Date.now(), start: newStart, end: addDays(newStart, len) });
        this.closePeriod();
    }

    shiftPeriod(days, ev) {
        if (ev) ev.stopPropagation();
        const ctx = this.openPeriodCtx;
        if (!ctx) return;
        const seg = ctx.segment;
        seg.start = addDays(seg.start, days);
        seg.end = addDays(seg.end, days);
    }

    splitPeriod(ev) {
        if (ev) ev.stopPropagation();
        const ctx = this.openPeriodCtx;
        if (!ctx) return;
        const seg = ctx.segment;
        const arr = ctx.person[ctx.pool];
        const idx = arr.indexOf(seg);
        if (idx === -1) return;
        const pieces = [];
        for (let d = new Date(seg.start); d <= seg.end; d = addDays(d, 1)) {
            pieces.push({ ...seg, id: seg.id + "-d" + d.getTime(), start: new Date(d), end: new Date(d) });
        }
        arr.splice(idx, 1, ...pieces);
        this.closePeriod();
    }

    reassignProject(ev) {
        if (ev) ev.stopPropagation();
        const ctx = this.openPeriodCtx;
        if (!ctx) return;
        const seg = ctx.segment;
        const idx = PROJECT_POOL.findIndex((p) => p.client === seg.client && p.project === seg.project);
        const next = PROJECT_POOL[(idx + 1) % PROJECT_POOL.length];
        seg.client = next.client;
        seg.project = next.project;
    }

    toggleRealSimulated(ev) {
        if (ev) ev.stopPropagation();
        const ctx = this.openPeriodCtx;
        if (!ctx) return;
        ctx.segment.type = ctx.segment.type === "real" ? "simulated" : "real";
    }

    deletePeriod(ev) {
        if (ev) ev.stopPropagation();
        const ctx = this.openPeriodCtx;
        if (!ctx) return;
        const arr = ctx.person[ctx.pool];
        const idx = arr.indexOf(ctx.segment);
        if (idx !== -1) arr.splice(idx, 1);
        this.closePeriod();
    }

    toggleRepeatForm(ev) {
        if (ev) ev.stopPropagation();
        this.state.repeatFormOpen = !this.state.repeatFormOpen;
    }

    applyRepeat(ev) {
        if (ev) ev.stopPropagation();
        const ctx = this.openPeriodCtx;
        if (!ctx) return;
        const seg = ctx.segment;
        const len = Math.round((seg.end - seg.start) / 86400000);
        for (let i = 1; i <= this.state.repeatCount; i++) {
            const start = addDays(seg.start, i * this.state.repeatWeeks * 7);
            ctx.person[ctx.pool].push({ ...seg, id: seg.id + "-rep" + i, start, end: addDays(start, len) });
        }
        this.closePeriod();
    }

    // ---- Drag & drop ----
    startCreate(person, dayIndex, ev) {
        if (ev.button !== 0) return;
        ev.preventDefault();
        ev.stopPropagation();
        this.state.drag = { kind: "create", personId: person.id, startIndex: dayIndex, currentIndex: dayIndex };
        this._attachDragListeners();
    }

    startMove(person, pool, segment, ev) {
        if (ev.button !== 0) return;
        ev.preventDefault();
        ev.stopPropagation();
        const days = this.days;
        const originIndex = days.findIndex((d) => sameDay(d.date, segment.start));
        // Bord gauche/droit (8px) de la barre : raccourcir/prolonger plutôt que déplacer.
        const rect = ev.currentTarget.getBoundingClientRect();
        const offsetX = ev.clientX - rect.left;
        let kind = "move";
        if (pool === "work" && offsetX <= 8) kind = "resize-left";
        else if (pool === "work" && rect.width - offsetX <= 8) kind = "resize-right";
        this.state.drag = { kind, personId: person.id, pool, segmentId: segment.id, originIndex, deltaDays: 0, edgeIndex: null };
        this._attachDragListeners();
    }

    _attachDragListeners() {
        this._onDragMove = (ev) => this._handleDragMove(ev);
        this._onDragUp = () => this._handleDragUp();
        window.addEventListener("pointermove", this._onDragMove);
        window.addEventListener("pointerup", this._onDragUp);
    }

    _detachDragListeners() {
        window.removeEventListener("pointermove", this._onDragMove);
        window.removeEventListener("pointerup", this._onDragUp);
    }

    _handleDragMove(ev) {
        const drag = this.state.drag;
        const gridEl = this.gridRef.el;
        if (!drag || !gridEl) return;
        const rect = gridEl.getBoundingClientRect();
        const dayWidth = (rect.width - 240) / this.days.length;
        const x = ev.clientX - rect.left - 240;
        const index = Math.max(0, Math.min(this.days.length - 1, Math.floor(x / dayWidth)));
        if (drag.kind === "create") {
            drag.currentIndex = index;
        } else if (drag.kind === "move") {
            drag.deltaDays = index - drag.originIndex;
        } else if (drag.kind === "resize-left" || drag.kind === "resize-right") {
            drag.edgeIndex = index;
        }
    }

    _handleDragUp() {
        const drag = this.state.drag;
        this._detachDragListeners();
        if (!drag) return;
        const days = this.days;
        if (drag.kind === "create") {
            const person = this.state.people.find((p) => p.id === drag.personId);
            if (person) {
                const lo = Math.min(drag.startIndex, drag.currentIndex);
                const hi = Math.max(drag.startIndex, drag.currentIndex);
                const seed = person.id + lo;
                const proj = PROJECT_POOL[seed % PROJECT_POOL.length];
                person.work.push({
                    id: "w" + person.id + "-new" + Date.now(),
                    start: days[lo].date,
                    end: days[hi].date,
                    type: "real",
                    client: proj.client,
                    project: proj.project,
                    rate: 100,
                    billed: false,
                    fee: 500,
                });
            }
        } else if (drag.kind === "move") {
            const person = this.state.people.find((p) => p.id === drag.personId);
            const seg = person && person[drag.pool].find((s) => s.id === drag.segmentId);
            if (seg && drag.deltaDays) {
                seg.start = addDays(seg.start, drag.deltaDays);
                seg.end = addDays(seg.end, drag.deltaDays);
            } else if (seg && !drag.deltaDays) {
                // Pas de déplacement : c'était un simple clic -> ouvre la pop-in d'informations.
                this.state.openPeriod = { personId: person.id, pool: drag.pool, segmentId: seg.id };
            }
        } else if (drag.kind === "resize-left" || drag.kind === "resize-right") {
            const person = this.state.people.find((p) => p.id === drag.personId);
            const seg = person && person[drag.pool].find((s) => s.id === drag.segmentId);
            if (seg && drag.edgeIndex !== null) {
                const target = days[drag.edgeIndex].date;
                if (drag.kind === "resize-left" && target <= seg.end) seg.start = target;
                else if (drag.kind === "resize-right" && target >= seg.start) seg.end = target;
            }
        }
        this.state.drag = null;
    }

    isDragPreviewCell(dayIndex) {
        const drag = this.state.drag;
        if (!drag || drag.kind !== "create") return false;
        const lo = Math.min(drag.startIndex, drag.currentIndex);
        const hi = Math.max(drag.startIndex, drag.currentIndex);
        return dayIndex >= lo && dayIndex <= hi;
    }

    moveDragStyle(segment, laneIndex) {
        const drag = this.state.drag;
        if (!drag || drag.segmentId !== segment.id) return null;
        const days = this.days;
        let colStart = -1;
        let colEnd = -1;
        for (let i = 0; i < days.length; i++) {
            if (days[i].date >= segment.start && days[i].date <= segment.end) {
                if (colStart === -1) colStart = i;
                colEnd = i;
            }
        }
        if (colStart === -1) return null;
        if (drag.kind === "move") {
            if (!drag.deltaDays) return null;
            const newStart = Math.max(0, Math.min(days.length - 1, colStart + drag.deltaDays));
            return `grid-column: ${newStart + 1} / span ${colEnd - colStart + 1}; grid-row: ${laneIndex + 1};`;
        }
        if (drag.kind === "resize-left" && drag.edgeIndex !== null) {
            const newStart = Math.max(0, Math.min(colEnd, drag.edgeIndex));
            return `grid-column: ${newStart + 1} / span ${colEnd - newStart + 1}; grid-row: ${laneIndex + 1};`;
        }
        if (drag.kind === "resize-right" && drag.edgeIndex !== null) {
            const newEnd = Math.max(colStart, Math.min(days.length - 1, drag.edgeIndex));
            return `grid-column: ${colStart + 1} / span ${newEnd - colStart + 1}; grid-row: ${laneIndex + 1};`;
        }
        return null;
    }
}
