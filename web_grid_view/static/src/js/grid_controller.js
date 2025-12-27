import { Component, useState, onWillStart, onWillUpdateProps, reactive } from "@odoo/owl";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { GridRenderer } from "./grid_renderer";
import { GridModel } from "./grid_model";

export class GridController extends Component {
    static template = "web_grid_view.GridView";
    static components = { Layout, GridRenderer, SearchBar };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.model = reactive(new GridModel(this.orm));
        this.searchBarToggler = useSearchBarToggler();

        this.state = useState({
            currentRange: this.props.archInfo.ranges[0],
            sort: { field: 'group', order: null }, // field can be 'group' or a specific date/col value
        });

        onWillStart(async () => {
            await this.loadData();
        });

        onWillUpdateProps(async (nextProps) => {
            const domainChanged = JSON.stringify(nextProps.domain) !== JSON.stringify(this.props.domain);
            const groupByChanged = JSON.stringify(nextProps.groupBy) !== JSON.stringify(this.props.groupBy);
            if (domainChanged || groupByChanged) {
                await this.loadData(nextProps);
            }
        });
    }

    onSort(field) {
        if (this.state.sort.field === field) {
            if (!this.state.sort.order) {
                this.state.sort.order = 'asc';
            } else if (this.state.sort.order === 'asc') {
                this.state.sort.order = 'desc';
            } else {
                this.state.sort.order = null;
            }
        } else {
            this.state.sort.field = field;
            this.state.sort.order = 'asc';
        }
        this.loadData();
    }

    getRowFields(props) {
        const { groupBy, archInfo, fields } = props;
        if (groupBy && groupBy.length > 0) {
            return groupBy.map(fieldName => {
                const name = fieldName.split(':')[0];
                return {
                    name: fieldName,
                    string: fields[name] ? fields[name].string : fieldName
                };
            });
        }
        return archInfo.rowFields.map(f => ({
            ...f,
            string: f.string || (fields[f.name] ? fields[f.name].string : f.name)
        }));
    }

    get rowFields() {
        return this.getRowFields(this.props);
    }

    async loadData(props = this.props) {
        const { archInfo, resModel, domain, context } = props;
        const rowFields = this.getRowFields(props);

        await this.model.load({
            resModel,
            rowFields: rowFields.map(f => f.name),
            colField: archInfo.colField.name,
            cellField: archInfo.cellField.name,
            domain,
            range: {
                ...this.state.currentRange,
                anchor: this.model.metaData && this.model.metaData.range ? this.model.metaData.range.anchor : null,
            },
            context,
            adjustment: archInfo.adjustment,
            adjustName: archInfo.adjustName,
            sort: this.state.sort,
        });

        this.render();
    }

    async onRangeSelected(rangeName) {
        const range = this.props.archInfo.ranges.find(r => r.name === rangeName);
        if (range) {
            this.state.currentRange = range;
            await this.loadData();
        }
    }

    async onPrev() {
        if (this.model.data.prev) {
            const { grid_anchor } = this.model.data.prev;
            this.model.metaData.range = {
                ...this.model.metaData.range,
                anchor: grid_anchor
            };
            await this.model.fetchData();
            this.render();
        }
    }

    async onNext() {
        if (this.model.data.next) {
            const { grid_anchor } = this.model.data.next;
            this.model.metaData.range = {
                ...this.model.metaData.range,
                anchor: grid_anchor
            };
            await this.model.fetchData();
            this.render();
        }
    }

    async onToday() {
        this.model.metaData.range = {
            ...this.model.metaData.range,
            anchor: null
        };
        await this.model.fetchData();
        this.render();
    }

    async onCellUpdate(rowDomain, colDomain, value) {
        await this.model.updateCell(rowDomain, colDomain, this.props.archInfo.cellField.name, value);
        this.render();
    }

    onToggleRow(stringKey) {
        this.model.toggleRow(stringKey);
        this.render();
    }

    get hasData() {
        return this.model.data && this.model.data.rows && this.model.data.rows.length > 0;
    }

    async onAddLine() {
        const { resModel, context } = this.props;
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: resModel,
            views: [[false, "form"]],
            target: "new",
            context: {
                ...context,
                default_date: this.model.metaData.range ? this.model.metaData.range.anchor || new Date().toISOString().split('T')[0] : null,
            },
        }, {
            onClose: async () => {
                await this.loadData();
            },
        });
    }
}
