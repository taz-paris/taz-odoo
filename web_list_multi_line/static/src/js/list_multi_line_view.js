/** @odoo-module **/

import { ListArchParser } from "@web/views/list/list_arch_parser";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { getActiveActions } from "@web/views/utils";
import { stringToOrderBy } from "@web/search/utils/order_by";
import { exprToBoolean } from "@web/core/utils/strings";
import { Component, xml } from "@odoo/owl";
import { Field } from "@web/views/fields/field";
import { Notebook } from "@web/core/notebook/notebook";

// Composant récursif universel pour le rendu des nœuds (Form-like)
class MultiLineNode extends Component {
    static template = "web_list_multi_line.Node";
    static components = { MultiLineNode, Field, Notebook };

    get column() {
        return this.props.archInfo.fieldNodes[this.props.node.fieldId];
    }

    get isVisible() {
        if (this.props.node.type === 'field') {
            const col = this.column;
            if (!col) return false;
            return !this.props.renderer.evalInvisible(col.invisible, this.props.record);
        }
        return true;
    }

    get colClass() {
        const parentCol = this.props.parentCol || 1;
        const colSpan = Math.max(1, Math.floor(12 / parentCol));
        return `col-lg-${colSpan}`;
    }
}

export class ListMultiLineArchParser extends ListArchParser {
    parse(originalXmlDoc, models, modelName) {
        const isMultiLine = originalXmlDoc.tagName.toUpperCase() === "LIST_MULTI_LINE";
        const xmlDoc = new Proxy(originalXmlDoc, {
            get(target, prop) {
                if (prop === "tagName" || prop === "nodeName") return "list";
                const value = target[prop];
                return typeof value === "function" ? value.bind(target) : value;
            }
        });

        // On utilise le parseur de liste pour les colonnes et métadonnées
        const archInfo = super.parse(xmlDoc, models, modelName);
        
        if (isMultiLine) {
            archInfo.activeActions = {
                ...getActiveActions(originalXmlDoc),
                exportXlsx: exprToBoolean(originalXmlDoc.getAttribute("export_xlsx") || "true", true),
            };
            archInfo.editable = originalXmlDoc.getAttribute("editable") || archInfo.editable;
            archInfo.limit = parseInt(originalXmlDoc.getAttribute("limit") || "80", 10);
            archInfo.noOpen = exprToBoolean(originalXmlDoc.getAttribute("no_open") || "false");
            archInfo.defaultOrder = stringToOrderBy(originalXmlDoc.getAttribute("default_order") || null) || archInfo.defaultOrder;
        }

        // On génère un layout universel récursif (supportant notebook, page, etc)
        archInfo.multiLineLayout = this.parseUniversalLayout(originalXmlDoc, true);
        archInfo.openFormView = exprToBoolean(originalXmlDoc.getAttribute("open_form_view") || "false");
        return archInfo;
    }

    parseUniversalLayout(node, isRoot = false) {
        const layout = [];
        for (const child of node.children) {
            const tagName = child.tagName.toLowerCase();
            if (["header", "control"].includes(tagName) && isRoot) continue;

            const item = {
                type: tagName,
                string: child.getAttribute("string"),
                class: child.getAttribute("class") || "",
                style: child.getAttribute("style") || "",
                fieldId: child.getAttribute("field_id"),
                name: child.getAttribute("name"),
                nolabel: child.getAttribute("nolabel") === "1",
                col: parseInt(child.getAttribute("col") || (tagName === "group" && isRoot ? "2" : "1"), 10),
                children: child.children.length ? this.parseUniversalLayout(child, false) : [],
            };

            if (tagName === "group") {
                item.isOuter = isRoot || Array.from(child.children).some(c => c.tagName === "group");
            }
            
            layout.push(item);
        }
        return layout;
    }
}

export class ListMultiLineRenderer extends ListRenderer {
    static template = "web_list_multi_line.Renderer";
    static rowsTemplate = "web_list_multi_line.Rows";
    static recordRowTemplate = "web_list_multi_line.RecordRow";
    static groupRowTemplate = "web_list_multi_line.GroupRow";
    static components = { ...ListRenderer.components, Field, MultiLineNode };
    
    setup() {
        super.setup();
        for (const col of Object.values(this.props.archInfo.fieldNodes || {})) {
            if (!col.options) col.options = {};
        }
    }

    get aggregateColumns() {
        return this.props.archInfo.columns.filter(c => c.type === 'field' && this.aggregates[c.name]);
    }

    onCellClicked(record, column, ev) {
        if (this.props.list.model.useSampleModel) return;
        if (ev.target.tagName === 'INPUT' || ev.target.tagName === 'SELECT' || ev.target.tagName === 'TEXTAREA' || ev.target.closest('button') || ev.target.closest('a')) {
            return;
        }
        this.props.list.enterEditMode(record);
        if (column) setTimeout(() => this.focusCell(column), 0);
    }

    onOpenFormViewClicked(record, ev) {
        this.props.openRecord(record);
    }

    focusCell(column) {
        if (!this.editedRecord) return;
        const cell = this.tableRef.el.querySelector(`.o_selected_row [name='${column.name}']`);
        if (cell) {
            const focusable = cell.querySelector('input, select, textarea, [tabindex="0"]');
            (focusable || cell).focus();
        }
    }
}

export const ListMultiLineView = {
    ...listView,
    ArchParser: ListMultiLineArchParser,
    Renderer: ListMultiLineRenderer,
};

registry.category("views").add("list_multi_line", ListMultiLineView);
