/** @odoo-module **/

import { KeepLast } from "@web/core/utils/concurrency";

export class GridModel {
    constructor(orm) {
        this.orm = orm;
        this.keepLast = new KeepLast();
        this.data = null;
        this.metaData = {};
        this.expandedRows = new Set();
    }

    async load(params) {
        const { resModel, rowFields, colFields, cellField, domain, range, context, adjustment, adjustName, readonlyFieldExprs } = params;
        this.metaData = {
            resModel,
            rowFields,
            colFields,
            cellField,
            domain,
            range,
            context,
            adjustment,
            adjustName,
            sort: params.sort || { field: 'group', order: null },
            readonlyFieldExprs: readonlyFieldExprs || {},
        };
        return this.fetchData();
    }

    async fetchData() {
        const { resModel, rowFields, colFields, cellField, domain, range, context, sort, readonlyFieldExprs } = this.metaData;

        let orderby = null;
        if (sort && sort.order) {
            if (sort.field === 'group') {
                orderby = `${rowFields[0]} ${sort.order}`;
            } else {
                // sort.field is the date value, e.g. "2025-10-23"
                // For now, we only support sorting by the primary column (Date)
                orderby = `${colFields[0].name}:${sort.field} ${sort.order}`;
            }
        }

        const data = await this.orm.call(resModel, "read_grid", [], {
            row_fields: rowFields,
            col_fields: colFields,
            cell_field: cellField,
            domain,
            grid_range: range,
            orderby: orderby,
            context,
            readonly_field_exprs: readonlyFieldExprs, // Pass expression map
        });

        this.data = data;
        this._processData();
    }

    _processData() {
        if (!this.data || !this.data.rows) return;

        const rowFields = this.metaData.rowFields;

        // Build tree from backend rows
        const tree = this._buildTreeFromBackendRows(this.data.rows, rowFields);
        this.data.processedRows = this._flattenTree(tree);
    }

    _buildTreeFromBackendRows(rows, rowFields, depth = 1, parentKey = []) {
        // Find rows at the current level that belong to the current parent
        const currentLevelRows = rows.filter(r => {
            if (r.level !== depth) return false;
            if (parentKey.length === 0) return true;

            // Check if all parent values match (using full_key from backend)
            return parentKey.every((val, idx) => r.full_key[idx] === val);
        });

        return currentLevelRows.map(r => {
            const stringKey = JSON.stringify(r.full_key);
            const isLastLevel = depth === rowFields.length;

            return {
                ...r,
                depth: depth - 1,
                stringKey: stringKey,
                label: r.values[rowFields[depth - 1]],
                isLeaf: isLastLevel,
                children: isLastLevel ? [] : this._buildTreeFromBackendRows(rows, rowFields, depth + 1, r.full_key)
            };
        });
    }

    _flattenTree(tree) {
        let flat = [];
        tree.forEach(node => {
            flat.push(node);
            if (this.expandedRows.has(node.stringKey) && node.children && node.children.length > 0) {
                flat = flat.concat(this._flattenTree(node.children));
            }
        });
        return flat;
    }

    toggleRow(stringKey) {
        if (this.expandedRows.has(stringKey)) {
            this.expandedRows.delete(stringKey);
        } else {
            this.expandedRows.add(stringKey);
        }
        this._processData();
    }

    async updateCell(rowDomain, colDomain, fieldName, value) {
        const { resModel, adjustment, adjustName, context } = this.metaData;

        if (adjustment === 'object' && adjustName) {
            await this.orm.call(resModel, adjustName, [
                rowDomain,
                this.metaData.colFields[0], // Pass the first column field name
                colDomain,
                fieldName,
                value
            ], {
                context: {
                    ...context,
                    grid_step: this.metaData.range.step,
                    grid_span: this.metaData.range.span,
                }
            });
        } else {
            console.warn("No adjustment method defined.");
        }

        await this.fetchData();
    }
}
