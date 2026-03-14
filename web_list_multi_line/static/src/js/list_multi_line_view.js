/** @odoo-module **/

import { ListArchParser } from "@web/views/list/list_arch_parser";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { getActiveActions, getDecoration } from "@web/views/utils";
import { stringToOrderBy } from "@web/search/utils/order_by";
import { exprToBoolean } from "@web/core/utils/strings";
import { Component, xml, useSubEnv } from "@odoo/owl";
import { Field } from "@web/views/fields/field";

export class ListMultiLineArchParser extends ListArchParser {
    parse(originalXmlDoc, models, modelName) {
        const isMultiLine = originalXmlDoc.tagName === "list_multi_line";
        // Create a Proxy to trick super.parse into thinking it's a <list> tag.
        // This avoids read-only property errors on tagName and correctly initializes defaults.
        const xmlDoc = new Proxy(originalXmlDoc, {
            get(target, prop) {
                if (prop === "tagName") {
                    return "list";
                }
                const value = target[prop];
                if (typeof value === "function") {
                    return value.bind(target);
                }
                return value;
            }
        });

        const archInfo = super.parse(xmlDoc, models, modelName);
        
        // Ensure standard attributes are correctly captured if super.parse logic was partial
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
        
        archInfo.multiLineLayout = this.parseLayout(originalXmlDoc);
        return archInfo;
    }

    parseLayout(node) {
        const layout = [];
        for (const child of node.children) {
            if (child.tagName === "field") {
                layout.push({ 
                    type: "field", 
                    fieldId: child.getAttribute("field_id"),
                    name: child.getAttribute("name"),
                    nolabel: child.getAttribute("nolabel") === "1",
                    col: child.getAttribute("col"),
                });
            } else if (child.tagName === "group") {
                layout.push({
                    type: "group",
                    children: this.parseLayout(child),
                    string: child.getAttribute("string"),
                    class: child.getAttribute("class"),
                    col: child.getAttribute("col"),
                    childrenCol: child.getAttribute("col") || 2,
                });
            } else if (child.tagName === "newline") {
                layout.push({ type: "newline" });
            } else if (child.tagName === "div") {
                 layout.push({
                    type: "div",
                    children: this.parseLayout(child),
                    class: child.getAttribute("class"),
                    style: child.getAttribute("style"),
                });
            }
        }
        return layout;
    }
}

export class ListMultiLineRenderer extends ListRenderer {
    static template = "web_list_multi_line.Renderer";
    static recordRowTemplate = "web_list_multi_line.RecordRow";

    setup() {
        super.setup();
    }

    onCellClicked(record, column, ev) {
        if (this.props.list.model.useSampleModel) return;
        
        // Empêcher la propagation si on clique sur un input déjà actif ou un lien/bouton
        if (ev.target.tagName === 'INPUT' || ev.target.tagName === 'SELECT' || ev.target.tagName === 'TEXTAREA' || ev.target.closest('button') || ev.target.closest('a')) {
            return;
        }

        // Si la liste est non-éditable MAIS qu'on a l'option open_form_view="1", on ouvre le form
        // Sinon (éditable = top/bottom), un clic même hors du champ déclenche le mode édition de ligne
        if (!column && this.props.archInfo.openFormView && !this.props.archInfo.noOpen && !this.isInlineEditable(record)) {
            this.props.openRecord(record);
            return;
        }

        this.props.list.enterEditMode(record);
        if (column) {
            // On attend que Owl ait rendu le champ editable avant de focus
            setTimeout(() => this.focusCell(column), 0);
        }
    }

    onOpenFormViewClicked(record, ev) {
        if (!this.props.archInfo.noOpen) {
            this.props.openRecord(record);
        }
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
