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
        this.metaData = { ...this.metaData, ...params };
        // Reset expanded rows if fields change
        if (params.rowFields) {
            this.expandedRows.clear();
        }
        await this.fetchData();
    }

    async fetchData() {
        const { resModel, rowFields, colField, cellField, domain, range, context } = this.metaData;

        const result = await this.keepLast.add(
            this.orm.call(resModel, "read_grid", [
                rowFields,
                colField,
                cellField,
                domain,
                range
            ], { context })
        );

        this.data = result;
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
                this.metaData.colField,
                colDomain[0][2],
                fieldName,
                value
            ], { context });
        } else {
            console.warn("No adjustment method defined.");
        }

        await this.fetchData();
    }
}
