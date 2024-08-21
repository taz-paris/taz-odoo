/** @odoo-module **/


import { patch } from 'web.utils';
import { BoardController } from '@board/board_controller';


import { browser } from "@web/core/browser/browser";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { renderToString } from "@web/core/utils/render";
import { useSortable } from "@web/core/utils/sortable";
import { standardViewProps } from "@web/views/standard_view_props";
import { BoardAction } from "@board/board_action";


const xmlSerializer = new XMLSerializer();
const { blockDom, Component, useState, useRef } = owl;

patch(BoardController.prototype, 'board_controller', {
    saveBoard() {
        const templateFn = renderToString.app.getTemplate("board.arch");
        const bdom = templateFn(this.board, {});
        const root = document.createElement("rendertostring");
        blockDom.mount(bdom, root);
        const result = xmlSerializer.serializeToString(root);
        const arch = result.slice(result.indexOf("<", 1), result.indexOf("</rendertostring>"));
	if (typeof this.board.customViewId !== 'undefined'){
	    // On n'appelle pas ce endpoint si nous ne sommes par sur une vue personnalisable => évite une erreur
		this.rpc("/web/view/edit_custom", {
		    custom_id: this.board.customViewId,
		    arch,
		});
	}
        this.env.bus.trigger("CLEAR-CACHES");
    }
});
