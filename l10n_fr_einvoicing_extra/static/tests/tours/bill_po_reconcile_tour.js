/** @odoo-module **/
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("bill_po_reconcile_tour", {
    steps: () => [
        {
            trigger: "button[name='action_open_bill_po_reconcile']",
            run: "click",
        },
        {
            trigger: ".o_bill_po_panel .o_bill_po_col:nth-child(2) .o_bill_po_line",
        },
        {
            // rien de coché : le total BC est nul
            trigger: ".o_bill_po_po_total:contains('0,00')",
        },
        {
            trigger: ".o_bill_po_panel .o_bill_po_col:nth-child(2) .o_bill_po_line input[type='checkbox']",
            run: "click",
        },
        {
            trigger: ".o_bill_po_line.o_bill_po_selected",
        },
        {
            trigger: ".o_bill_po_po_total:not(:contains('0,00'))",
        },
    ],
});
