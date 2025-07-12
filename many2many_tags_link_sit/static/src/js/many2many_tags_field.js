/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Many2ManyTagsFieldColorEditable } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { patch } from "@web/core/utils/patch";

patch(Many2ManyTagsFieldColorEditable.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
    },
    onBadgeClick(ev, record) {
        if (!this.props.canEditColor) {
	    this.action.doAction({
	        type: 'ir.actions.act_window',
	        res_model: this.props.record.fields[this.props.name].relation,
	        res_id: record.resId,
	        views: [[false, 'form']],
	        target: 'current',
	    });
        } else {
	    super.onBadgeClick(ev, record);
	}
    }
})

patch(Many2ManyTagsField.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
    },

    getTagProps(record) {
        const props = super.getTagProps(record);
        props.onClick = (ev) => this.onBadgeClick(ev, record);
        return props;
    },

    onBadgeClick(ev, record) {
	this.action.doAction({
	    type: 'ir.actions.act_window',
	    res_model: this.props.record.fields[this.props.name].relation,
	    res_id: record.resId,
	    views: [[false, 'form']],
	    target: 'current',
	});
    }
})
