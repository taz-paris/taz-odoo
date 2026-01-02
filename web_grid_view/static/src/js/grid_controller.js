import { Component, useState, onWillStart, onWillUpdateProps, reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { GridRenderer } from "./grid_renderer";
import { GridModel } from "./grid_model";
import { Dialog } from "@web/core/dialog/dialog";
import { View } from "@web/views/view";
import { xml } from "@odoo/owl";

class GridFormViewDialog extends Component {
    static template = xml`
        <Dialog title="props.title">
            <div class="o_form_view_dialog">
                <View t-props="viewProps"/>
            </div>
            <t t-set-slot="footer">
                <!-- Buttons are handled by the FormView inside View -->
                <button class="btn btn-secondary" t-on-click="props.close">Close</button>
            </t>
        </Dialog>
    `;
    static components = { Dialog, View };

    get viewProps() {
        return {
            type: "form",
            resModel: this.props.resModel,
            context: this.props.context,
            arch: this.props.arch,
            fields: this.props.fields,
            relatedModels: {
                [this.props.resModel]: { fields: this.props.fields }
            },
            onSave: async () => {
                if (this.props.onSave) {
                    await this.props.onSave();
                }
                this.props.close();
            },
        };
    }
}

export class GridController extends Component {
    static template = "web_grid_view.GridView";
    static components = { Layout, GridRenderer, SearchBar };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialogService = useService("dialog");
        this.model = reactive(new GridModel(this.orm));
        this.searchBarToggler = useSearchBarToggler();

        const firstRange = this.props.archInfo.ranges[0] || { span: 'month', name: 'month' };
        const firstStepDef = this.props.archInfo.steps[0] || { step: 'day', name: 'day' };

        let initialSpan = firstRange.span;
        let initialStepName = firstStepDef.name; // Use name here
        let initialAnchor = null;

        const context = this.props.context || {};

        // Handle grid_range (name of the <range/> tag)
        if (context.grid_range) {
            const range = this.props.archInfo.ranges.find(r => r.name === context.grid_range);
            if (range) {
                initialSpan = range.span;
            }
        }

        // Handle grid_step (name of the <step/> tag or direct step value)
        if (context.grid_step) {
            const stepDef = (this.props.archInfo.steps || []).find(s => s.name === context.grid_step || s.step === context.grid_step);
            if (stepDef) {
                initialStepName = stepDef.name;
            }
        }

        // Handle grid_anchor (date string)
        if (context.grid_anchor) {
            initialAnchor = context.grid_anchor;
        }

        this.state = useState({
            currentSpan: initialSpan,
            currentStep: initialStepName,
            anchor: initialAnchor,
            sort: { field: 'group', order: null },
            rowFields: this.getRowFields(this.props), // Store rowFields in state
        });

        // Populations of dropdowns now strictly follows the XML tags
        this.availableSpans = this.props.archInfo.ranges.map(r => ({
            name: r.span,
            string: r.string
        }));
        this.availableSteps = this.props.archInfo.steps.map(s => ({
            name: s.name, // Use NAME here
            string: s.string
        }));

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
                const archRowField = archInfo.rowFields.find(f => f.name === name) || {};
                return {
                    name: fieldName,
                    string: fields[name] ? fields[name].string : fieldName,
                    stepDecorators: archRowField.stepDecorators || [],
                    readonly: archRowField.readonly,
                };
            });
        }
        return archInfo.rowFields.map(f => ({
            ...f,
            string: f.string || (fields[f.name] ? fields[f.name].string : f.name)
        }));
    }

    get rowFields() {
        return this.state.rowFields;
    }

    async loadData(props = this.props) {
        const { archInfo, resModel, domain, context } = props;
        this.state.rowFields = this.getRowFields(props);
        const rowFields = this.state.rowFields;

        const stepDef = this.props.archInfo.steps.find(s => s.name === this.state.currentStep) || { step: 'day' };

        await this.model.load({
            resModel,
            rowFields: rowFields.map(f => f.name),
            colFields: archInfo.colFields.map(f => f.name), // Use colFields
            colField: archInfo.colFields[0].name, // Legacy colField for backend compatibility if blindly used
            cellField: archInfo.cellField.name,
            domain,
            range: {
                span: this.state.currentSpan,
                step: stepDef.step, // Actual value for the backend
                stepName: this.state.currentStep, // Tag name for decoration lookup
                anchor: (this.model.metaData && this.model.metaData.range) ? this.model.metaData.range.anchor : this.state.anchor,
            },
            context,
            adjustment: archInfo.adjustment,
            adjustName: archInfo.adjustName,
            sort: this.state.sort,
            readonlyFieldExprs: {
                ...Object.fromEntries(rowFields.filter(f => f.readonly).map(f => [f.name, f.readonly])),
                ...Object.fromEntries(archInfo.colFields.filter(f => f.readonly).map(f => [f.name, f.readonly]))
            },
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

    get currentSpanLabel() {
        const span = this.availableSpans.find(s => s.name === this.state.currentSpan);
        return span ? span.string : '';
    }

    get currentStepLabel() {
        const step = this.availableSteps.find(s => s.name === this.state.currentStep);
        return step ? step.string : '';
    }

    get hasData() {
        return this.model.data && this.model.data.rows && this.model.data.rows.length > 0;
    }

    async onAddLine() {
        const { resModel, context, domain, archInfo } = this.props;

        // 1. Extract defaults from domain
        const domainDefaults = {};
        const extract = (d) => {
            if (!d || !Array.isArray(d)) return;
            d.forEach(leaf => {
                if (Array.isArray(leaf)) {
                    if (leaf.length === 3 && leaf[1] === '=') {
                        domainDefaults[leaf[0]] = leaf[2];
                    } else {
                        extract(leaf);
                    }
                }
            });
        };
        extract(domain);

        // 2. Identify fields to show and which should be readonly
        const rowFields = archInfo.rowFields.map(f => f.name);
        const colField = archInfo.colFields.length > 0 ? archInfo.colFields[0].name : 'date'; // Default to first col field or date
        const cellField = archInfo.cellField.name;

        const gridFields = new Set([colField, ...rowFields]);
        const contextFields = new Set();
        Object.keys(context).forEach(key => {
            if (key.startsWith('default_')) {
                contextFields.add(key.replace('default_', ''));
            }
        });
        const domainFields = new Set(Object.keys(domainDefaults));

        // Combined set of fields to display in the form (filtered by model fields)
        const allFieldsToShow = new Set();
        [...gridFields, ...contextFields, ...domainFields].forEach(fname => {
            if (this.props.fields[fname] && fname !== cellField) {
                allFieldsToShow.add(fname);
            }
        });

        // 3. Construct a dynamic XML arch for the form
        let arch = `<?xml version="1.0"?>
            <form string="${_t('Add a line')}">
                <sheet>
                    <group>
        `;

        allFieldsToShow.forEach(fieldName => {
            // Fields from domain or context are marked as readonly
            const isReadonly = domainFields.has(fieldName) || contextFields.has(fieldName);
            arch += `<field name="${fieldName}" ${isReadonly ? 'readonly="1"' : ''}/>\n`;
        });

        arch += `
                    </group>
                </sheet>
            </form>
        `;

        // 4. Prepare final context
        const finalContext = { ...context };
        Object.keys(domainDefaults).forEach(k => {
            finalContext[`default_${k}`] = domainDefaults[k];
        });

        // Set default date if it's not already in domain/context
        if (!finalContext.default_date && colField === 'date') {
            finalContext.default_date = this.model.metaData.range ? this.model.metaData.range.anchor || new Date().toISOString().split('T')[0] : null;
        }

        this.dialogService.add(GridFormViewDialog, {
            title: _t("Add a line"),
            resModel: resModel,
            context: finalContext,
            arch: arch,
            fields: this.props.fields,
            onSave: async () => {
                await this.loadData();
            },
        });
    }
}
