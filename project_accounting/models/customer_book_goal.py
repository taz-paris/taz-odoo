from odoo import models, fields, api

class CustomerBookGoal(models.Model):
    _inherit = 'taz.customer_book_goal'

    """
    DOCUMENTATION ARCHITECTURALE :
    -----------------------------
    Pourquoi surcharger ce modèle dans 'project_accounting' plutôt que dans 'taz-common' ?

    1. Rendre les colonnes triables (Odoo limitation) :
       Pour qu'une colonne calculée (compute) soit cliquable et triable dans une vue liste (tree),
       Odoo exige obligatoirement qu'elle soit stockée en base de données ('store=True').

    2. La dépendance aux Projets (Le piège de taz-common) :
       Si l'on passe 'store=True' dans taz-common, Odoo va évaluer les champs au démarrage et 
       requérir l'accès à tous les champs mentionnés dans le @api.depends() pour construire ses abonnements.
       Or, de nombreux champs financiers cruciaux (stage_is_part_of_booking, prorated_revenue, etc.)
       n'existent PAS en standard : ils sont uniquement définis en aval, dans ce présent module 'project_accounting'.
       Faire le 'store=True' dans taz-common générerait donc un crash immédiat ('Invalid field') à l'installation.

    3. L'élégance de cette surcouche :
       - 'taz-common' (en amont) héberge toute la structure des champs et l'algorithme brut 
         (sans store ni depends imposés).
       - 'project_accounting' (ici, en aval) possède tous les champs financiers. On "force" donc
         le paramètre 'store=True', et on attache les fameux déclencheurs `@api.depends` introuvables plus haut.
       - Pour exécuter le calcul, on ne duplique aucun code : on appelle poliment `super()`.
    """

    period_book = fields.Monetary(compute="_compute_financial_aggregates", store=True)
    period_delta = fields.Monetary(compute="_compute_financial_aggregates", store=True)
    period_ratio = fields.Float(compute="_compute_financial_aggregates", store=True)
    book_last_month = fields.Monetary(compute="_compute_financial_aggregates", store=True)
    number_of_opportunities = fields.Integer(compute="_compute_financial_aggregates", store=True)
    done_commercial_interview_count = fields.Integer(compute="_compute_commercial_actions", store=True)
    inprogress_commercial_interview_count = fields.Integer(compute="_compute_commercial_actions", store=True)
    inprogress_other_business_action_count = fields.Integer(compute="_compute_commercial_actions", store=True)
    expected_prorated_revenue = fields.Monetary(compute="_compute_financial_aggregates", store=True)

    @api.depends(
        'industry_id', 'reference_period', 'company_id',
        'industry_id.business_action_ids.state',
        'industry_id.business_action_ids.action_type',
        'industry_id.business_action_ids.date_deadline'
    )
    def _compute_commercial_actions(self):
        super()._compute_commercial_actions()

    @api.depends(
        'industry_id', 'reference_period', 'company_id', 'period_goal',
        'industry_id.partner_ids.project_ids.state',
        'industry_id.partner_ids.project_ids.stage_is_part_of_booking',
        'industry_id.partner_ids.project_ids.reporting_sum_company_outsource_code3_code_4',
        'industry_id.partner_ids.project_ids.reporting_sum_company_outsource_code3_code_4_delta',
        'industry_id.partner_ids.project_ids.prorated_revenue',
        'industry_id.partner_ids.project_ids.date_win_loose'
    )
    def _compute_financial_aggregates(self):
        super()._compute_financial_aggregates()

    def trigger_goals_recompute(self):
        """ Méthode utilitaire appelée par le cron pour forcer le recalcul temporel nocturne """
        for record in self:
            record._compute_commercial_actions()
            record._compute_financial_aggregates()
