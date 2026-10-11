/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Component, useState, onWillStart } from "@odoo/owl";

// Moteur de rendu (et d'édition) du contenu d'une évaluation de mission (project.evaluation.data),
// à partir du gabarit Napta project.evaluation.template.form_template : arbre de noeuds
// {type, key, children/columns, ...}. C'est le seul dialecte exploité ici (l'ancien dialecte
// simplifié "form", en lecture seule, a été retiré : un seul rendu, les champs passent juste en
// readonly/disabled classique quand l'évaluation est clôturée).
//
// Chaque noeud qui porte une "key" correspond à une entrée du dict JSON evaluation.data sous ce
// nom ; les tableaux de data[key] portent les lignes saisies, les colonnes "statiques" (type
// text) viennent du gabarit (defaultRows), jamais de data. Les options des champs "select" sont
// soit inline (node.options), soit référencées via node.global_text_id dans
// template.form_template.globalText.select[].
export class EvaluationPreview extends Component {
    static template = "project_evaluation.EvaluationPreview";
    static components = { AutoComplete };
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        // hr.employee de l'utilisateur courant : pas dans les infos de session (qui ne connaissent que
        // le res.users), donc un aller-retour RPC dédié, fait une fois au montage. Sert à savoir si
        // l'utilisateur a déjà noté une compétence donnée sur cette évaluation (masque alors "Ajouter
        // ma note" pour cette compétence).
        this.currentEmployeeId = null;
        onWillStart(async () => {
            const employees = await this.orm.searchRead(
                "hr.employee",
                [["user_id", "=", user.userId]],
                ["id"],
                { limit: 1 }
            );
            this.currentEmployeeId = employees.length ? employees[0].id : null;
        });

        // Formulaire d'ajout de note de compétence (propre à Odoo, cf. add_skill_grade côté modèle :
        // jamais remonté à Napta). Un seul formulaire ouvert à la fois ; skillId/skillTypeId/skillName
        // sont pré-remplis quand on clique "Ajouter ma note" sur une compétence déjà présente, vides
        // quand on part du bouton général "Ajouter une compétence" (choix via l'autocomplete).
        this.skillGradeForm = useState({
            open: false,
            skillId: null,
            skillName: "",
            skillTypeId: null,
            levels: [],
            levelId: null,
            levelName: "Aucun niveau",
            comment: "",
            saving: false,
        });
    }

    // ------------------------------------------------------------------
    // Gabarit (form_template)
    // ------------------------------------------------------------------

    get formTemplateParsed() {
        const raw = this.props.record.data.template_form_template;
        if (!raw) {
            return null;
        }
        try {
            return JSON.parse(raw);
        } catch {
            return null;
        }
    }

    get formNodes() {
        const parsed = this.formTemplateParsed;
        return parsed && Array.isArray(parsed.form) ? parsed.form : [];
    }

    get globalText() {
        const parsed = this.formTemplateParsed;
        return (parsed && parsed.globalText) || {};
    }

    get isReadonly() {
        return !!this.props.readonly;
    }

    // ------------------------------------------------------------------
    // Notes de compétences (hr.employee.skill.grade) : hors du rendu form_template/data. Les notes
    // elles-mêmes viennent de Napta (lecture seule), mais l'évalué/les évaluateurs peuvent en ajouter
    // de nouvelles depuis Odoo (cf. add_skill_grade) -- jamais remontées vers Napta, l'API ne le
    // permet pas.
    // ------------------------------------------------------------------

    // Groupé par skill_type_id puis par compétence : Napta a une hiérarchie de catégories à 2
    // niveaux (ex. "Certifications Agilité" sous "Certifications"), mais hr.skill (Odoo) ne porte
    // qu'un seul niveau de regroupement (skill_type_id, sans parent) -- donc le regroupement ici est
    // forcément plus plat que sur le profil Napta. Le sous-regroupement par compétence permet de
    // n'afficher qu'un seul bouton "Ajouter ma note" par compétence, même si plusieurs personnes
    // l'ont déjà notée.
    get skillGradesByType() {
        const records = (this.props.record.data.skill_grade_ids && this.props.record.data.skill_grade_ids.records) || [];
        const typeGroups = new Map();
        for (const r of records) {
            const d = r.data;
            const typeName = (d.skill_type_id && d.skill_type_id[1]) || "Autres";
            if (!typeGroups.has(typeName)) {
                typeGroups.set(typeName, new Map());
            }
            const skillGroups = typeGroups.get(typeName);
            const skillId = d.skill_id && d.skill_id[0];
            if (!skillGroups.has(skillId)) {
                skillGroups.set(skillId, {
                    skillId,
                    skillName: (d.skill_id && d.skill_id[1]) || "",
                    skillDescription: d.skill_description || "",
                    skillTypeId: d.skill_type_id && d.skill_type_id[0],
                    grades: [],
                });
            }
            skillGroups.get(skillId).grades.push({
                levelName: (d.skill_level_id && d.skill_level_id[1]) || "",
                levelDescription: d.skill_level_description || "",
                raterEmployeeId: d.rater_employee_id && d.rater_employee_id[0],
                raterName: (d.rater_employee_id && d.rater_employee_id[1]) || "",
                isSelf: !!d.is_self_assessment,
                comment: d.comment || "",
            });
        }
        return Array.from(typeGroups.entries()).map(([typeName, skillGroups]) => [
            typeName,
            Array.from(skillGroups.values()).map((skill) => ({
                ...skill,
                // Empêche de redonner une 2e note sur la même compétence dans la même évaluation :
                // "Ajouter ma note" ne doit proposer QUE les compétences que l'utilisateur courant n'a
                // pas encore notées lui-même ici.
                alreadyGradedByMe: this.currentEmployeeId
                    ? skill.grades.some((g) => g.raterEmployeeId === this.currentEmployeeId)
                    : false,
            })),
        ]);
    }

    // ------------------------------------------------------------------
    // Ajout d'une note de compétence (hr.employee.skill.grade, propre à Odoo -- cf.
    // project.evaluation.add_skill_grade). Le formulaire est générique : ouvert sans compétence
    // pré-choisie (bouton "Ajouter une compétence", recherche via autocomplete) ou avec une
    // compétence déjà fixée (bouton "Ajouter ma note" sur une ligne existante).
    // ------------------------------------------------------------------

    get skillAutocompleteSources() {
        return [
            {
                optionTemplate: "project_evaluation.SkillGradeFormAutocompleteOption",
                options: async (query) => {
                    if (!query) {
                        return [];
                    }
                    const skills = await this.orm.searchRead(
                        "hr.skill",
                        [["name", "ilike", query]],
                        ["name", "description", "skill_type_id"],
                        { limit: 8 }
                    );
                    return skills.map((skill) => ({
                        label: skill.name,
                        skillId: skill.id,
                        skillName: skill.name,
                        skillDescription: skill.description || "",
                        skillTypeId: skill.skill_type_id && skill.skill_type_id[0],
                    }));
                },
            },
        ];
    }

    // Même mécanisme que skillAutocompleteSources, mais en liste statique (pas de recherche serveur :
    // il y a peu de niveaux, déjà chargés par loadSkillLevels) -- un AutoComplete dont la source
    // "options" est un tableau (et non une fonction) affiche directement tout son contenu au clic,
    // sans attendre de saisie, exactement comme un <select> mais avec un rendu riche (description).
    get levelAutocompleteSources() {
        const noneOption = { label: "Aucun niveau", levelId: null, levelName: "Aucun niveau", levelDescription: "" };
        const levelOptions = this.skillGradeForm.levels.map((level) => ({
            label: level.name,
            levelId: level.id,
            levelName: level.name,
            levelDescription: level.description || "",
        }));
        return [
            {
                optionTemplate: "project_evaluation.SkillGradeFormLevelAutocompleteOption",
                options: [noneOption, ...levelOptions],
            },
        ];
    }

    async openSkillGradeForm(skillId = null, skillName = "", skillTypeId = null) {
        Object.assign(this.skillGradeForm, {
            open: true,
            skillId,
            skillName,
            skillTypeId,
            levels: [],
            levelId: null,
            levelName: "Aucun niveau",
            comment: "",
            saving: false,
        });
        if (skillTypeId) {
            await this.loadSkillLevels(skillTypeId);
        }
    }

    closeSkillGradeForm() {
        Object.assign(this.skillGradeForm, { open: false, skillId: null, skillTypeId: null, levels: [] });
    }

    async loadSkillLevels(skillTypeId) {
        this.skillGradeForm.levels = await this.orm.searchRead(
            "hr.skill.level",
            [["skill_type_id", "=", skillTypeId]],
            ["name", "description"],
            { order: "level_progress asc" }
        );
    }

    async onSkillGradeAutocompleteSelect(option) {
        this.skillGradeForm.skillId = option.skillId;
        this.skillGradeForm.skillName = option.skillName;
        this.skillGradeForm.skillTypeId = option.skillTypeId;
        this.skillGradeForm.levelId = null;
        this.skillGradeForm.levelName = "Aucun niveau";
        if (option.skillTypeId) {
            await this.loadSkillLevels(option.skillTypeId);
        }
    }

    onSkillGradeLevelAutocompleteSelect(option) {
        this.skillGradeForm.levelId = option.levelId;
        this.skillGradeForm.levelName = option.levelName;
    }

    onSkillGradeCommentInput(ev) {
        this.skillGradeForm.comment = ev.target.value;
    }

    async submitSkillGradeForm() {
        if (!this.skillGradeForm.skillId || this.skillGradeForm.saving) {
            return;
        }
        this.skillGradeForm.saving = true;
        try {
            await this.orm.call("project.evaluation", "add_skill_grade", [
                [this.props.record.resId],
                this.skillGradeForm.skillId,
                this.skillGradeForm.levelId || false,
                this.skillGradeForm.comment || false,
            ]);
            this.closeSkillGradeForm();
            await this.props.record.load();
        } finally {
            this.skillGradeForm.saving = false;
        }
    }

    // ------------------------------------------------------------------
    // Lecture/écriture du contenu de l'évaluation (evaluation.data)
    // ------------------------------------------------------------------

    get evaluationData() {
        const raw = this.props.record.data[this.props.name];
        if (!raw) {
            return {};
        }
        try {
            return JSON.parse(raw) || {};
        } catch {
            return {};
        }
    }

    async commitData(data) {
        await this.props.record.update({ [this.props.name]: JSON.stringify(data) });
    }

    getValue(key) {
        return this.evaluationData[key] ?? "";
    }

    async setValue(key, value) {
        const data = { ...this.evaluationData };
        data[key] = value;
        await this.commitData(data);
    }

    getRows(key) {
        return this.evaluationData[key] || [];
    }

    getCell(key, rowIndex, colKey) {
        const row = this.getRows(key)[rowIndex];
        return (row && row[colKey]) || "";
    }

    async setCell(tableKey, rowIndex, colKey, value) {
        const data = { ...this.evaluationData };
        const rows = (data[tableKey] || []).map((row) => ({ ...row }));
        while (rows.length <= rowIndex) {
            rows.push({});
        }
        rows[rowIndex][colKey] = value;
        data[tableKey] = rows;
        await this.commitData(data);
    }

    async addRow(tableKey) {
        const data = { ...this.evaluationData };
        const rows = (data[tableKey] || []).map((row) => ({ ...row }));
        if (rows.length === 0) {
            // Une ligne vide "fantôme" (non stockée dans data) est affichée quand la table est
            // vide, pour pouvoir saisir tout de suite. Le bouton doit alors matérialiser CETTE
            // ligne ET en ajouter une nouvelle, sinon le total affiché ne bouge pas (1 -> 1) et le
            // clic paraît sans effet.
            rows.push({});
        }
        rows.push({});
        data[tableKey] = rows;
        await this.commitData(data);
    }

    async removeRow(tableKey, rowIndex) {
        const data = { ...this.evaluationData };
        const rows = (data[tableKey] || []).map((row) => ({ ...row }));
        rows.splice(rowIndex, 1);
        data[tableKey] = rows;
        await this.commitData(data);
    }

    // ------------------------------------------------------------------
    // Gestionnaires d'évènements
    // ------------------------------------------------------------------

    onFieldInput(node, ev) {
        this.setValue(node.key, ev.target.value);
    }

    onFieldSelectChange(node, ev) {
        this.setValue(node.key, ev.target.value);
    }

    onCellInput(node, rowIndex, col, ev) {
        this.setCell(node.key, rowIndex, col.key, ev.target.value);
    }

    onCellSelectChange(node, rowIndex, col, ev) {
        this.setCell(node.key, rowIndex, col.key, ev.target.value);
    }

    onAddRowClick(node) {
        this.addRow(node.key);
    }

    onRemoveRowClick(node, rowIndex) {
        this.removeRow(node.key, rowIndex);
    }

    // ------------------------------------------------------------------
    // Tables
    // ------------------------------------------------------------------

    tableColumnTitle(col) {
        return col.title || col.text || "";
    }

    // Nombre de lignes à afficher : si la table accepte l'ajout de lignes (hasRowAdd), on se base
    // sur les lignes réellement saisies (au moins 1 en édition, pour pouvoir commencer à saisir
    // sans avoir à cliquer sur "Ajouter une ligne" d'abord) ; sinon (table à lignes fixes), le
    // nombre de lignes vient du gabarit (defaultRows).
    // Cette première ligne, quand data est vide, est "fantôme" (pas encore dans data) : voir
    // addRow() qui compense pour que le bouton "Ajouter une ligne" reste toujours visible à l'effet.
    tableRowCount(node) {
        if (node.hasRowAdd) {
            const count = this.getRows(node.key).length;
            if (count) {
                return count;
            }
            return this.isReadonly ? 0 : 1;
        }
        return (node.defaultRows || []).length;
    }

    tableStaticCellText(node, colKey, rowIndex) {
        const row = (node.defaultRows || [])[rowIndex];
        return (row && row[colKey] && row[colKey].text) || "";
    }

    tableCellPlaceholder(node, colKey, rowIndex) {
        const row = (node.defaultRows || [])[rowIndex];
        return (row && row[colKey] && row[colKey].placeholder) || "";
    }

    // ------------------------------------------------------------------
    // Sélecteurs : résolution des options
    // ------------------------------------------------------------------

    selectOptions(node) {
        if (Array.isArray(node.options)) {
            return node.options;
        }
        if (node.options && typeof node.options === "object") {
            return Object.entries(node.options).map(([id, text]) => ({ id, text }));
        }
        if (node.global_text_id) {
            const sets = this.globalText.select || [];
            const found = sets.find((set) => set.id === node.global_text_id);
            if (found && found.text && Array.isArray(found.text.options)) {
                return found.text.options;
            }
        }
        return [];
    }

    selectLabel(node, code) {
        if (!code) {
            return "";
        }
        const option = this.selectOptions(node).find((opt) => opt.id === code);
        return option ? option.text : code;
    }

    // ------------------------------------------------------------------
    // Texte statique Draft.js
    // ------------------------------------------------------------------

    // Retourne un texte Draft.js (ou une chaîne brute) sous forme de paragraphes : chaque
    // paragraphe est une liste de segments {text, bold, italic} à concaténer en ligne.
    parseMarkdown(raw) {
        if (!raw) {
            return [];
        }
        let blocks = null;
        try {
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed.blocks)) {
                blocks = parsed.blocks;
            }
        } catch {
            blocks = null;
        }
        if (!blocks) {
            return [[{ text: raw, bold: false, italic: false }]];
        }
        return blocks.map((block) => {
            const text = block.text || "";
            if (!text) {
                return [];
            }
            const ranges = block.inlineStyleRanges || [];
            const boundarySet = new Set([0, text.length]);
            for (const range of ranges) {
                boundarySet.add(range.offset);
                boundarySet.add(range.offset + range.length);
            }
            const bounds = Array.from(boundarySet).sort((a, b) => a - b);
            const segments = [];
            for (let i = 0; i < bounds.length - 1; i++) {
                const start = bounds[i];
                const end = bounds[i + 1];
                if (start >= end) {
                    continue;
                }
                const active = ranges
                    .filter((range) => range.offset <= start && start < range.offset + range.length)
                    .map((range) => range.style);
                segments.push({
                    text: text.slice(start, end),
                    bold: active.includes("BOLD"),
                    italic: active.includes("ITALIC"),
                });
            }
            return segments;
        });
    }
}

export const evaluationPreview = { component: EvaluationPreview };

registry.category("fields").add("project_evaluation_preview", evaluationPreview);
