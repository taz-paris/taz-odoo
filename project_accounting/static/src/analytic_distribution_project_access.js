/** @odoo-module **/

import { AnalyticDistribution } from '@analytic/components/analytic_distribution/analytic_distribution';
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

import { patch } from 'web.utils';

const components = { AnalyticDistribution };

patch(components.AnalyticDistribution.prototype, 'analytic_distribution', {
	searchAnalyticDomain(searchTerm) {
		return [
		    '|',
		    ["display_name", "ilike", searchTerm],
		    '|',
		    ['code', 'ilike', searchTerm],
		    ['partner_id', 'ilike', searchTerm],
		];
	},

	async getProjectUrl(ev) {
		ev.stopPropagation();

		var analytic_account_ids = Object.keys(this.listForJson).map(Number);
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

			var url = window.location.href;
			var searchParams = new URLSearchParams();
			if (project_ids.lenght > 1) {
				alert("Deux projets (ou plus) sont rattachés à ces comptes analytiques. Le premier de ces projets va s'ouvrir dans un nouvel onglet.");
				// TODO : ça serait bien d'ouvrir la vue liste et d'afficher les N projets dans ce cas.
			} 
			searchParams.set("view_type", "form");
			var target_project_id = project_ids[0];
			searchParams.set("model", "project.project");
			if (typeof target_project_id === 'undefined'){
				alert("Le compte analytique n'est rattaché à aucun projet.");
			} else {
				searchParams.set("id", target_project_id);
				//searchParams.delete("action");
				// TODO : est-ce que la barre de menus serait alimentée sur l'ID action était défini ? Commment l'obtenir dynamiquement depuis le front ?
				var new_url = url.split("#")[0] + "#" + searchParams.toString();
				window.open(new_url, "_blank");
			}
		}
	},
        
});

