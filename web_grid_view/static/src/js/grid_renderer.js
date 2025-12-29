/** @odoo-module **/

import { Component } from "@odoo/owl";
import { formatFloat, formatFloatTime } from "@web/views/fields/formatters";
import { parseFloat as odooParseFloat, parseFloatTime } from "@web/views/fields/parsers";
import { evaluateExpr } from "@web/core/py_js/py";

export class GridRenderer extends Component {
    static template = "web_grid_view.GridRenderer";
    static props = {
        model: Object,
        archInfo: Object,
        rowFields: Array,
        fields: Object,
        onCellUpdate: Function,
        onToggleRow: Function,
        onAddLine: Function,
        onSort: Function,
        sort: Object,
        range: Object,
    };

    isMany2one(row) {
        const fieldName = this.props.rowFields[row.depth].name.split(':')[0];
        const field = this.props.fields[fieldName];
        return field && field.type === "many2one" && row.full_key && row.full_key[row.depth];
    }

    onLabelClick(row) {
        const fieldName = this.props.rowFields[row.depth].name.split(':')[0];
        const field = this.props.fields[fieldName];
        const resId = row.full_key ? row.full_key[row.depth] : null;

        if (field && field.type === "many2one" && resId) {
            const url = `/web#id=${resId}&model=${field.relation}&view_type=form`;
            window.open(url, '_blank');
        }
    }

    get rows() {
        return this.props.model.data ? (this.props.model.data.processedRows || this.props.model.data.rows) : [];
    }

    get cols() {
        return this.props.model.data ? this.props.model.data.cols : [];
    }

    getRowGrid(row) {
        return row.grid || [];
    }

    get rowTotals() {
        return this.props.model.data ? this.props.model.data.row_totals : [];
    }

    get colTotals() {
        return this.props.model.data ? this.props.model.data.col_totals : [];
    }

    get grandTotal() {
        return this.props.model.data ? this.props.model.data.grand_total : 0;
    }

    formatValue(value) {
        const fieldName = this.props.archInfo.cellField.name;
        const field = this.props.fields[fieldName];
        const widget = this.props.archInfo.cellField.widget;
        const options = { field, digits: [42, 2] };
        if (widget === 'float_time') {
            return formatFloatTime(value || 0, options);
        }
        return formatFloat(value || 0, options);
    }

    getCellClass(cell, row) {
        // Use the active step name to find the appropriate decorations
        const activeStepName = this.props.range.stepName;
        let decorations = null;

        // 1. Try to find decorations in the specific ROW FIELD definition first (nested <step_decorator/>)
        // Use this.props.rowFields which reflects the CURRENT grouping order
        if (row && row.depth !== undefined && this.props.rowFields[row.depth]) {
            const rowField = this.props.rowFields[row.depth];
            if (rowField.stepDecorators) {
                const rowDef = rowField.stepDecorators.find(d => d.stepName === activeStepName);
                if (rowDef) {
                    decorations = rowDef.decorations;
                }
            }
        }

        // 2. Fallback to global <step/> tags if none in row field
        if (!decorations || Object.keys(decorations).length === 0) {
            const stepDef = (this.props.archInfo.steps || []).find(s => s.name === activeStepName);
            if (stepDef) {
                decorations = stepDef.decorations;
            }
        }

        // 3. Fallback to <range/> decorations (contextual by step value, but here we prioritize step names)
        if (!decorations || Object.keys(decorations).length === 0) {
            const activeStepValue = this.props.range.step;
            const rangeDef = (this.props.archInfo.ranges || []).find(r =>
                r.step === activeStepValue && r.decorations && Object.keys(r.decorations).length > 0
            );
            if (rangeDef) {
                decorations = rangeDef.decorations;
            }
        }

        // 4. Fallback to colField decorations if none found
        if (!decorations || Object.keys(decorations).length === 0) {
            decorations = this.props.archInfo.colField.decorations;
        }

        if (!decorations || Object.keys(decorations).length === 0) return "";

        const cellFieldName = this.props.archInfo.cellField.name;

        // Prepare context with row values
        const context = {
            [cellFieldName]: cell.value,
            value: cell.value,
            __depth: row ? row.depth : undefined,
            __is_leaf: row ? row.isLeaf : undefined,
        };

        // Add row field values to context
        if (row && row.values) {
            for (const [key, val] of Object.entries(row.values)) {
                // If many2one [id, name], we take just the ID for easier logic
                if (Array.isArray(val) && val.length === 2) {
                    context[key] = val[0];
                } else {
                    context[key] = val;
                }
            }
        }

        const classes = [];
        for (const [attr, expr] of Object.entries(decorations)) {
            try {
                if (evaluateExpr(expr, context)) {
                    const deco = attr.replace("decoration-", "");
                    if (["info", "success", "danger", "warning", "muted", "primary"].includes(deco)) {
                        classes.push(`text-${deco}`);
                    } else if (deco === "bf") {
                        classes.push("fw-bold");
                    } else if (deco === "it") {
                        classes.push("fst-italic");
                    }
                }
            } catch (e) {
                // Ignore evaluation errors
            }
        }
        return classes.join(" ");
    }

    onCellChange(rowIndex, colIndex, ev) {
        const value = ev.target.value;
        let parsedValue;
        try {
            if (this.props.archInfo.cellField.widget === 'float_time') {
                parsedValue = parseFloatTime(value);
            } else {
                parsedValue = odooParseFloat(value);
            }
        } catch (e) {
            // If parsing fails (e.g. invalid characters), fallback to 0 or previous value
            parsedValue = 0;
        }

        const row = this.rows[rowIndex];
        const col = this.cols[colIndex];

        this.props.onCellUpdate(row.domain, col.domain, parsedValue);
    }
}
