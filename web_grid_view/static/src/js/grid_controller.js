import { Component, useState, onWillStart, onWillUpdateProps, reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
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

        const defaultRange = this.props.archInfo.ranges[0] || { span: 'month', step: 'day' };
        this.state = useState({
            currentSpan: defaultRange.span,
            currentStep: defaultRange.step,
            sort: { field: 'group', order: null },
        });

        // Filter unique spans and steps from ranges
        this.availableSpans = [
            { name: 'week', string: _t('Week') },
            { name: 'month', string: _t('Month') },
            { name: 'quarter', string: _t('Quarter') },
            { name: 'year', string: _t('Year') },
        ];
        this.availableSteps = [
            { name: 'day', string: _t('Day') },
            { name: 'week', string: _t('Week') },
            { name: 'month', string: _t('Month') },
            { name: 'quarter', string: _t('Quarter') },
            { name: 'year', string: _t('Year') },
        ];

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
                span: this.state.currentSpan,
                step: this.state.currentStep,
                anchor: this.model.metaData && this.model.metaData.range ? this.model.metaData.range.anchor : null,
            },
            context,
            adjustment: archInfo.adjustment,
            adjustName: archInfo.adjustName,
            sort: this.state.sort,
        });

        this.render();
    }

    async onSpanSelected(spanName) {
        this.state.currentSpan = spanName;
        await this.loadData();
    }

    async onStepSelected(stepName) {
        this.state.currentStep = stepName;
        await this.loadData();
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
