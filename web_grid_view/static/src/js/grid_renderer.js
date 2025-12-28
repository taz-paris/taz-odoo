/** @odoo-module **/

import { Component } from "@odoo/owl";
import { formatFloat, formatFloatTime } from "@web/views/fields/formatters";
import { parseFloat as odooParseFloat, parseFloatTime } from "@web/views/fields/parsers";

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
