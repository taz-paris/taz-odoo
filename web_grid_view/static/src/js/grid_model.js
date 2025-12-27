/** @odoo-module **/

import { KeepLast } from "@web/core/utils/concurrency";

export class GridModel {
    constructor(orm) {
        this.orm = orm;
        this.keepLast = new KeepLast();
        this.data = null;
        this.metaData = {};
    }

    async load(params) {
        this.metaData = { ...this.metaData, ...params };
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
