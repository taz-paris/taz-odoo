/** @odoo-module **/
import { _t } from 'web.core';
import { useService } from "@web/core/utils/hooks";
import { Many2ManyTagsFieldColorEditable } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { patch } from "@web/core/utils/patch";


patch(Many2ManyTagsFieldColorEditable.prototype, '/advanced_many2many_tags/static/src/js/many2many_tags_field.js', {
    /*Here Many2ManyTagsFieldColorEditable is patched to over ride onBadgeClick()*/
    setup() {
        this._super.apply(this, arguments);
        this.notification = useService("notification");
        this.action = useService("action");
    },
    onBadgeClick(ev, record) {
                        this.action.doAction({
                            type: 'ir.actions.act_window',
                            res_model: this.props.relation,
                            res_id: record.data.id,
                            views: [[false, 'form']],
                            target: 'current',
                        });

        return this._super.apply(this, arguments);
    }
})

patch(Many2ManyTagsField.prototype, '/advanced_many2many_tags/static/src/js/many2many_tags_field.js', {
    /*Here Many2ManyTagsFieldColorEditable is patched to over ride onBadgeClick()*/
    setup() {
        this._super.apply(this, arguments);
        this.notification = useService("notification");
        this.action = useService("action");
    },

	/*
    getTagProps(record) {
        const props = this.super().getTagProps(record);
        props.onClick = (ev) => this.onBadgeClick(ev, record);
        return props;
    },
    */

    getTagProps(record) {
        return {
            id: record.id, // datapoint_X
            resId: record.resId,
            text: record.data.display_name,
            colorIndex: record.data[this.props.colorField],
            onDelete: !this.props.readonly ? () => this.deleteTag(record.id) : undefined,
            onKeydown: (ev) => {
                if (this.props.readonly) {
                    return;
                }
                this.onTagKeydown(ev);
            },
	    onClick : (ev) => {this.onBadgeClick(ev, record);},
        };
    },

    onBadgeClick(ev, record) {
                        this.action.doAction({
                            type: 'ir.actions.act_window',
                            res_model: this.props.relation,
                            res_id: record.data.id,
                            views: [[false, 'form']],
                            target: 'current',
                        });

        //return this.apply(this, arguments);
    }
})
