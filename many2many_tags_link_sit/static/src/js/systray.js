/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";

export class HelpMenuView extends Component {

}
HelpMenuView.template = "many2many_tags_link_sit.HelpMenuView";

export const systrayItem = {
    Component: HelpMenuView,
};

//Add Help logo beside activity menu
// Check If HelpMenuView Already Exists Then don't Add
if (registry.category('systray').content.hasOwnProperty('HelpMenuView') == false){
   registry.category("systray").add("HelpMenuView", systrayItem, { sequence: 2 });
}
