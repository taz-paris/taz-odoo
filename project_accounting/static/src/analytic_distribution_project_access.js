/** @odoo-module **/

import { AnalyticDistribution } from '@analytic/components/analytic_distribution/analytic_distribution';
import { patch } from "@web/core/utils/patch";
import { stateToUrl } from "@web/core/browser/router";

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
				// En Odoo 18, on utilise stateToUrl pour construire l'URL au format /odoo/{model}/{resId}
				const state = {
					model: "project.project",
					resId: target_project_id,
					view_type: "form",
				};
				const new_url = window.location + stateToUrl(state);
				window.open(new_url, "_blank");
			}
		}
	},
        
});
