/** @odoo-module **/

import { AnalyticDistribution } from '@analytic/components/analytic_distribution/analytic_distribution';
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

import { patch } from "@web/core/utils/patch";

const components = { AnalyticDistribution };

patch(components.AnalyticDistribution.prototype, {
	async getProjectUrl(ev) {
		ev.stopPropagation();

		const jsonFieldValue = this.props.record.data[this.props.name];
		const analytic_account_ids = jsonFieldValue ? Object.keys(jsonFieldValue).map((key) => key.split(',')).flat().map((id) => parseInt(id)) : [];
		const args = {
			    domain: [["id", "in", analytic_account_ids]],
			    fields: ["id", "project_ids"],
			    context: [],
			}
		this.analytic_account_object_list = await this.orm.call("account.analytic.account", "search_read", [], args);

		if (typeof this.analytic_account_object_list[0] === 'undefined') {
			alert("Pas de compte analytic sur la ligne.");
		} else {
			var project_ids = [];
			for (const account of this.analytic_account_object_list){
				for (const project_id of account["project_ids"]){
					project_ids.push(project_id);
				}
			}

			if (project_ids.length > 1) {
				alert("Deux projets (ou plus) sont rattachés à ces comptes analytiques. Le premier de ces projets va s'ouvrir dans un nouvel onglet.");
			} 
			var target_project_id = project_ids[0];
			if (typeof target_project_id === 'undefined'){
				alert("Le compte analytique n'est rattaché à aucun projet.");
			} else {
				var searchParams = new URLSearchParams();
				searchParams.set("view_type", "form");
				searchParams.set("model", "project.project");
				searchParams.set("id", target_project_id);
				searchParams.set("menu_id", this.env.services.router.current.hash.menu_id);
				var url = window.location.href;
				var new_url = url.split("#")[0] + "#" + searchParams.toString();
				window.open(new_url, "_blank");
			}
		}
	},
        
});

