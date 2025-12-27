/** @odoo-module **/

import { visitXML } from "@web/core/utils/xml";
import { _t } from "@web/core/l10n/translation";

export class GridArchParser {
    parse(arch) {
        const archInfo = {
            rowFields: [],
            colField: null,
            cellField: null,
            ranges: [],
            buttons: [],
            adjustment: arch.getAttribute("adjustment"),
            adjustName: arch.getAttribute("adjust_name"),
            hideLineTotal: arch.getAttribute("hide_line_total") === "true",
            hideColumnTotal: arch.getAttribute("hide_column_total") === "true",
            createInline: arch.getAttribute("create_inline") === "true",
            displayEmpty: arch.getAttribute("display_empty") === "true",
        };

        visitXML(arch, (node) => {
            if (node.tagName === "field") {
                const type = node.getAttribute("type");
                const name = node.getAttribute("name");
                const string = node.getAttribute("string");

                if (type === "row") {
                    archInfo.rowFields.push({ name, string: _t(string) });
                } else if (type === "col") {
                    archInfo.colField = { name, string: _t(string) };
                    // Parse ranges
                    for (const child of node.children) {
                        if (child.tagName === "range") {
                            archInfo.ranges.push({
                                name: child.getAttribute("name"),
                                string: _t(child.getAttribute("string")),
                                span: child.getAttribute("span"),
                                step: child.getAttribute("step"),
                            });
                        }
                    }
                } else if (type === "measure") {
                    archInfo.cellField = {
                        name,
                        string: _t(string),
                        widget: node.getAttribute("widget")
                    };
                }
            } else if (node.tagName === "button") {
                archInfo.buttons.push({
                    name: node.getAttribute("name"),
                    string: node.getAttribute("string"),
                    type: node.getAttribute("type"),
                    icon: node.getAttribute("icon"),
                    invisible: node.getAttribute("invisible"),
                });
            }
        });

        // Default range if none
        if (archInfo.ranges.length === 0 && archInfo.colField) {
            archInfo.ranges.push({ name: "month", string: _t("Month"), span: "month", step: "day" });
        }

        return archInfo;
    }
}
