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
        this.model = reactive(new GridModel(this.orm));
        this.searchBarToggler = useSearchBarToggler();

        this.state = useState({
            currentRange: this.props.archInfo.ranges[0],
        });

        onWillStart(async () => {
            await this.loadData();
        });

        onWillUpdateProps(async (nextProps) => {
            if (nextProps.domain !== this.props.domain) {
                await this.loadData(nextProps);
            }
        });
    }

    async loadData(props = this.props) {
        const { archInfo, resModel, domain, context } = props;

        await this.model.load({
            resModel,
            rowFields: archInfo.rowFields.map(f => f.name),
            colField: archInfo.colField.name,
            cellField: archInfo.cellField.name,
            domain,
            range: this.state.currentRange,
            context,
            adjustment: archInfo.adjustment,
            adjustName: archInfo.adjustName,
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

    async onAddLine() {
        // Placeholder for add line functionality
    }
}
