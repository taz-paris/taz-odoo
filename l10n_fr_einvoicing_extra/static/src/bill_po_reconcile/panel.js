/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { formatMonetary, formatFloat } from "@web/views/fields/formatters";

const STATE_LABELS = {
    open: "Ouverte",
    partial: "Partiellement facturée",
    full: "Facturée",
    direct: "Facturation directe",
};
const GROUP_COLORS = 6;

/**
 * Panneau à deux colonnes : lignes de la facture (gauche) / lignes des BC groupées par BC (droite).
 * Posé sur le champ po_line_ids ; lit invoice_line_ids sur le même enregistrement.
 * Le serveur reste l'autorité : chaque modification déclenche l'onchange du wizard.
 */
export class BillPoReconcilePanel extends Component {
    static template = "l10n_fr_einvoicing_extra.BillPoReconcilePanel";
    static props = { ...standardFieldProps };

    get wizard() {
        return this.props.record;
    }
    get currencyId() {
        return this.wizard.data.currency_id && this.wizard.data.currency_id[0];
    }
    get consumption() {
        return this.wizard.data.mode === "consumption";
    }
    get invoiceLines() {
        return this.wizard.data.invoice_line_ids.records;
    }
    get groups() {
        const groups = [];
        const byOrder = new Map();
        for (const rec of this.wizard.data.po_line_ids.records) {
            const order = rec.data.order_id;
            const key = order ? order[0] : 0;
            if (!byOrder.has(key)) {
                const group = {
                    key,
                    name: order ? order[1] : "Nouveau BC",
                    color: groups.length % GROUP_COLORS,
                    lines: [],
                };
                byOrder.set(key, group);
                groups.push(group);
            }
            byOrder.get(key).lines.push(rec);
        }
        return groups;
    }
    /** Totaux instantanés (la valeur serveur écrase après l'onchange). */
    get invoiceTotal() {
        return this.invoiceLines
            .filter((r) => r.data.selected)
            .reduce((s, r) => s + r.data.price_subtotal, 0);
    }
    get poTotal() {
        return this.wizard.data.po_line_ids.records
            .filter((r) => r.data.selected)
            .reduce((s, r) => s + r.data.amount_open, 0);
    }
    money(value) {
        return formatMonetary(value, { currencyId: this.currencyId });
    }
    num(value) {
        return formatFloat(value);
    }
    stateLabel(rec) {
        return STATE_LABELS[rec.data.state] || "";
    }
    toggle(rec) {
        if (this.props.readonly) {
            return;
        }
        rec.update({ selected: !rec.data.selected });
    }
    onQtyChange(rec, ev) {
        const value = parseFloat(String(ev.target.value).replace(",", "."));
        if (!isNaN(value)) {
            rec.update({ qty_consumed: value });
        }
    }
}

registry.category("fields").add("bill_po_reconcile_panel", {
    component: BillPoReconcilePanel,
    supportedTypes: ["one2many"],
});
