/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

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
    static props = { ...standardFieldProps };

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
