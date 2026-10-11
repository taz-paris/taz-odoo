/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

// Moteur de rendu (et d'édition) du contenu d'une évaluation de mission (project.evaluation.data),
// à partir du gabarit Napta. Deux dialectes de gabarit existent côté Napta :
//
// - project.evaluation.template.form_template (dialecte "riche", utilisé en priorité) : arbre de
//   noeuds {type, key, children/columns, ...}. C'est le seul des deux à porter tout ce dont on a
//   besoin pour éditer (placeholders, nombre de lignes des textarea, tables à lignes ajoutables
//   "hasRowAdd", séparateurs "divider") et le marqueur du module compétences ("type": "skills",
//   absent de form). Les options des champs "select" sont soit inline (node.options), soit
//   référencées via node.global_text_id dans template.form_template.globalText.select[].
// - project.evaluation.template.form (dialecte "simplifié", repli) : arbre de noeuds
//   {component, key, items/staticData, itemProps...}. Utilisé uniquement si form_template est
//   absent/invalide pour un gabarit donné. Lecture seule : ce dialecte ne porte aucune métadonnée
//   d'édition (pas de placeholder, pas d'indication de table à lignes libres).
//
// Dans les deux cas, chaque noeud qui porte une "key" correspond à une entrée du dict JSON
// evaluation.data sous ce nom ; les tableaux de data[key] portent les lignes saisies, les
// colonnes "statiques" (type text/MarkdownDisplay) viennent du gabarit (defaultRows/staticData),
// jamais de data.
export class EvaluationPreview extends Component {
    static template = "project_evaluation.EvaluationPreview";
    static props = { ...standardFieldProps };

    // ------------------------------------------------------------------
    // Gabarit : dialecte riche (form_template)
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

    get richNodes() {
        const parsed = this.formTemplateParsed;
        return parsed && Array.isArray(parsed.form) ? parsed.form : null;
    }

    get globalText() {
        const parsed = this.formTemplateParsed;
        return (parsed && parsed.globalText) || {};
    }

    // ------------------------------------------------------------------
    // Gabarit : dialecte simplifié (form), utilisé en repli lecture seule
    // ------------------------------------------------------------------

    get legacyNodes() {
        const raw = this.props.record.data.template_form;
        if (!raw) {
            return [];
        }
        try {
            const parsed = JSON.parse(raw);
            return Array.isArray(parsed) ? parsed : [];
        } catch {
            return [];
        }
    }

    get renderMode() {
        if (this.richNodes && this.richNodes.length) {
            return "rich";
        }
        if (this.legacyNodes.length) {
            return "legacy";
        }
        return "none";
    }

    get isReadonly() {
        return !!this.props.readonly;
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
    // Gestionnaires d'évènements (dialecte riche, formulaires éditables)
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
    // Tables (dialecte riche)
    // ------------------------------------------------------------------

    tableColumnTitle(col) {
        return col.title || col.text || "";
    }

    // Nombre de lignes à afficher : si la table accepte l'ajout de lignes (hasRowAdd), on se base
    // sur les lignes réellement saisies (au moins 1 en édition pour pouvoir commencer à saisir) ;
    // sinon (table à lignes fixes), le nombre de lignes vient du gabarit (defaultRows).
    tableRowCount(node) {
        const dataRows = this.getRows(node.key);
        if (node.hasRowAdd) {
            if (dataRows.length) {
                return dataRows.length;
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
    // Sélecteurs (dialecte riche) : résolution des options
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
    // Texte statique Draft.js, commun aux deux dialectes
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

    // ------------------------------------------------------------------
    // Dialecte simplifié (form) : repli en lecture seule uniquement
    // ------------------------------------------------------------------

    legacyFieldValue(node) {
        return this.evaluationData[node.key] || "";
    }

    legacySelectorLabel(node) {
        const code = this.evaluationData[node.key];
        if (!code) {
            return "";
        }
        const options = (node.itemProps && node.itemProps.options) || {};
        return options[code] || code;
    }

    legacyTableColumns(node) {
        return (node.items || []).map((col) => ({ key: col.key, title: col.title || "" }));
    }

    legacyTableRows(node) {
        const dataRows = this.evaluationData[node.key] || [];
        const staticRows = node.staticData || [];
        const rowCount = Math.max(dataRows.length, staticRows.length);
        const columns = node.items || [];
        const rows = [];
        for (let i = 0; i < rowCount; i++) {
            const dataRow = dataRows[i] || {};
            const staticRow = staticRows[i] || {};
            rows.push(
                columns.map((col) => {
                    if (col.component === "MarkdownDisplay") {
                        return staticRow[col.key] || "";
                    }
                    if (col.component === "Selector") {
                        const code = dataRow[col.key];
                        if (!code) {
                            return "";
                        }
                        const options = (col.itemProps && col.itemProps.options) || {};
                        return options[code] || code;
                    }
                    return dataRow[col.key] || "";
                })
            );
        }
        return rows;
    }

    legacyMarkdownText(node) {
        return (node.itemProps && node.itemProps.text) || "";
    }
}

export const evaluationPreview = { component: EvaluationPreview };

registry.category("fields").add("project_evaluation_preview", evaluationPreview);
