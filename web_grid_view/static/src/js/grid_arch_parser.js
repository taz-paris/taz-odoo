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
            steps: [],
            buttons: [],
            adjustment: arch.getAttribute("adjustment"),
            adjustName: arch.getAttribute("adjust_name"),
            hideLineTotal: arch.getAttribute("hide_line_total") === "true",
            hideColumnTotal: arch.getAttribute("hide_column_total") === "true",
            createInline: arch.getAttribute("create_inline") === "true",
            displayEmpty: arch.getAttribute("display_empty") === "true",
        };

        const parseDecorations = (node) => {
            const decorations = {};
            for (const attr of node.attributes) {
                if (attr.name.startsWith("decoration-")) {
                    decorations[attr.name] = attr.value;
                }
            }
            return decorations;
        };

        const parseStep = (node) => {
            return {
                name: node.getAttribute("name"),
                string: _t(node.getAttribute("string")),
                step: node.getAttribute("step"),
                decorations: parseDecorations(node),
            };
        };

        const parseStepDecorator = (node) => {
            return {
                stepName: node.getAttribute("step"), // Reference to a <step name="..."/>
                decorations: parseDecorations(node),
            };
        };

        visitXML(arch, (node) => {
            if (node.tagName === "field") {
                const type = node.getAttribute("type");
                const name = node.getAttribute("name");
                const string = node.getAttribute("string");

                if (type === "row") {
                    const rowField = { name, string: _t(string), stepDecorators: [] };
                    for (const child of node.children) {
                        if (child.tagName === "step_decorator") {
                            rowField.stepDecorators.push(parseStepDecorator(child));
                        }
                    }
                    archInfo.rowFields.push(rowField);
                } else if (type === "col") {
                    archInfo.colField = { name, string: _t(string), decorations: parseDecorations(node) };
                    // Parse ranges and steps
                    for (const child of node.children) {
                        if (child.tagName === "range") {
                            archInfo.ranges.push({
                                name: child.getAttribute("name"),
                                string: _t(child.getAttribute("string")),
                                span: child.getAttribute("span"),
                                decorations: parseDecorations(child),
                            });
                        } else if (child.tagName === "step") {
                            archInfo.steps.push(parseStep(child));
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

        // Default range/step if none defined
        if (archInfo.ranges.length === 0 && archInfo.colField) {
            archInfo.ranges.push({ name: "month", string: _t("Month"), span: "month", decorations: {} });
        }
        if (archInfo.steps.length === 0 && archInfo.colField) {
            archInfo.steps.push({ name: "day", string: _t("Day"), step: "day", decorations: {} });
        }

        return archInfo;
    }
}
