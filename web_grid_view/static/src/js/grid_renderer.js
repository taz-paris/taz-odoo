/** @odoo-module **/

import { Component } from "@odoo/owl";

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
        const widget = this.props.archInfo.cellField.widget;
        if (widget === 'float_time') {
            const val = parseFloat(value || 0);
            const hours = Math.floor(Math.abs(val));
            const minutes = Math.round((Math.abs(val) % 1) * 60);
            const sign = val < 0 ? "-" : "";
            return `${sign}${hours}:${minutes.toString().padStart(2, "0")}`;
        }
        return value;
    }

    onCellChange(rowIndex, colIndex, ev) {
        const value = ev.target.value;
        let parsedValue = parseFloat(value);
        if (this.props.archInfo.cellField.widget === 'float_time') {
            const parts = value.split(':');
            if (parts.length === 2) {
                parsedValue = parseInt(parts[0]) + parseInt(parts[1]) / 60;
            }
        }

        const row = this.rows[rowIndex];
        const col = this.cols[colIndex];

        this.props.onCellUpdate(row.domain, col.domain, parsedValue);
    }
}
