from dateutil import relativedelta
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging
from odoo import _
_logger = logging.getLogger(__name__)

import datetime
from dateutil.relativedelta import relativedelta

class projectAccountingClosing(models.Model):
    _name = "project.accounting_closing"
    _description = "Project accounting closing"
    _order = "project_id_number desc, closing_date desc"
    _inherit = ['mail.thread']
    _sql_constraints = [
        ('project_date_uniq', 'UNIQUE (project_id, closing_date)',  "Impossible d'avoir deux clôtures à une même date pour un même projet.")
    ]
    _check_company_auto = True

    def _get_default_project_id(self):
        return self.env.context.get('default_project_id') or self.env.context.get('active_id')

    def _get_default_closing_date(self):
        if not self.project_id and not self._get_default_project_id():
            return False

        project_id = self.project_id
        if not project_id:
            project_id = self._get_default_project_id()

        accounting_closing_ids = self.env['project.accounting_closing'].search([('project_id', '=', project_id)], order="closing_date desc")
        if len(accounting_closing_ids) == 0 : 
            # si c'est la première cloture du projet, on met sa date de cloture par défaut au dernier jour du mois précédent le mois courant
            return datetime.date.today().replace(day=1) - datetime.timedelta(1)
        last_closing_date = accounting_closing_ids[0].closing_date
        # sinon, c'est le dernier jour du mois suivant celui de la dernière cloture
        return (last_closing_date + relativedelta(months=2)).replace(day=1) - datetime.timedelta(1)

    @api.constrains('closing_date', 'company_id')
    def _check_closing_date(self):
        for rec in self:
            accounting_closing_ids = self.env['project.accounting_closing'].search([('project_id', '=', rec.project_id.id)], order="closing_date desc")
            if accounting_closing_ids[0].id != rec.id:
                raise ValidationError(_("Il n'est pas possible de saisir une date de clôture antérieure à la dernière cloture enregistrée pour ce projet."))
    
    @api.constrains('closing_date', 'company_id', 'is_validated')
    def _check_accounting_lock_dates(self):
        for rec in self:
            # Vérification des dates de verrouillage comptable
            if rec.closing_date:
                company = rec.company_id
                lock_dates = {
                    'vente': company.sale_lock_date,
                    'achat': company.purchase_lock_date,
                    'fiscale': company.fiscalyear_lock_date,
                    'taxe': company.tax_lock_date,
                }
                for lock_type, lock_date in lock_dates.items():
                    if lock_date and lock_date < rec.closing_date:
                        raise ValidationError(_(
                            "La date de verrouillage %s de la société (%s) est antérieure à la date de clôture (%s). "
                            "Le verrouillage comptable doit être effectué avant la clôture du projet."
                        ) % (lock_type, lock_date, rec.closing_date))

    @api.model_create_multi
    def create(self, vals):
        _logger.info('-- model_create_multi project_accounting_closing')
        project_ids = [val['project_id'] for val in vals]
        not_validated_closing_ids = self.env['project.accounting_closing'].search([('project_id', 'in', project_ids), ('is_validated', '=', False)])
        not_validated_closing_projects = [closing.project_id.display_name for closing in not_validated_closing_ids]
        if len(not_validated_closing_ids) >0:
            raise ValidationError(_("Il n'est pas possible de générer de nouvelles clôtures, car les projets suivants ont au moins une cloture non validée : \n%s" % (',\n'.join(not_validated_closing_projects)) ))

        closing = super().create(vals)

        for rec in closing:
            if rec.project_id:
                rec.original_stage_id = rec.project_id.stage_id.id
            
            # Chez Tasmane, l'entrée dans l'alliance a conduit à basculer à une reconnaissance du CA à l'avancement
            #   - pour les mois de janvier / février / mars 2026, Denis à fait les clotures habituelles mais a desocké tout le stock chaque mois
            #   - fin mars 2026, on a créé l'objet project.progress et on l'a instancié pour le T1 2026. Un script a été xecuté pour retomber sur le CA déclaré
            #   - à partir de la clôture du 31/03/2026, on a mis valuation_from_progress=True et on calcule automatiquement les provisions à parir des project.progress
            if rec.closing_date and rec.closing_date >= datetime.date(2026, 3, 1) and not rec.is_validated:
                rec.valuation_from_progress = True
                ###### Auto-creation of project.progress records
                rec.create_project_progress()

        return closing


    def create_project_progress(self):
                self.ensure_one()
                # 1. For each outsourcing link
                for link in self.project_id.project_outsourcing_link_ids:
                    progress = self.env['project.progress'].search([
                        ('accounting_closing_id', '=', self.id),
                        ('outsourcing_link_id', '=', link.id)
                    ], limit=1)
                    if not progress:
                        outsourcing_progress_dic = {
                            'accounting_closing_id': self.id,
                            'outsourcing_link_id': link.id,
                        }
                        _logger.info("Creating project progress : %s " % str(outsourcing_progress_dic))
                        new_progress_outsourcing = self.env['project.progress'].create(outsourcing_progress_dic)
                        # Après le create, previous_progress_id est résolu.
                        # Pour le type 'autre', l'écriture à 0 déclenche _inverse_qty_period qui positionne
                        # outsourcing_product_qty = previous.outsourcing_product_qty + 0
                        # => l'avancement cumulé est repris de la période précédente.
                        # Pour le type S/T, on laisse à 0 par défaut pour forcer la saisie du nouvel avancement.
                        if link.link_type == 'outsourcing':
                            new_progress_outsourcing.outsourcing_product_qty_period = 0.0
                
                # 2. For internal production
                napta_id = getattr(self.project_id, 'napta_id', False)
                if napta_id or self.project_id.company_part_amount_current != 0.0:
                    _logger.info("XXXXXX Creating project progress for internal production napta_id=%s, company_part_amount_current=%s" % (napta_id, self.project_id.company_part_amount_current))
                    internal_progress = self.env['project.progress'].search([
                        ('accounting_closing_id', '=', self.id),
                        ('outsourcing_link_id', '=', False)
                    ], limit=1)
                    if not internal_progress:
                        internal_progress_dic = {
                            'accounting_closing_id': self.id,
                            'outsourcing_link_id': False,
                        }
                        _logger.info("Creating project progress : %s " % str(internal_progress_dic))
                        self.env['project.progress'].create(internal_progress_dic)
                        

    def write(self, vals):
        self._check_can_write(vals)
        for rec in self :
            # On ne peut pas valider la clôture si des avancements ne sont pas validés
            if vals.get('is_validated'):
                if len(vals) > 1:
                    raise ValidationError(_("Il n'est pas possible de valider la clôture et de modifier d'autres champs en même temps. Veuillez d'abord enregistrer vos modifications, puis valider la clôture."))
                if rec.purchase_period_mismatch:
                    raise ValidationError(_("Impossible de valider la clôture car le montant des achats de la période ne correspond pas à la somme des achats des lignes d'avancement."))
                
                not_validated_progress = rec.object_progress_ids.filtered(lambda p: not p.is_validated)
                if not_validated_progress:
                    progress_names = ", ".join(not_validated_progress.mapped('display_name'))
                    raise ValidationError(_("Impossible de valider la clôture car les avancements suivants ne sont pas validés : %s") % progress_names)
        super().write(vals)


    def _check_can_write(self, vals=None):
        for rec in self :
            if rec.next_closing :
                raise ValidationError(_("Il n'est pas possible de modifier cette clôture car une clôture postérieure existe pour ce projet."))
            if rec.is_validated :
                #import traceback
                #_logger.info("".join(traceback.format_stack()))
                #_logger.info(vals)
                if vals is None:
                    raise ValidationError(_("Il n'est pas possible de modifier cette clôture car elle est validée %s (ID = %s)." % (rec.name, rec.id)))
                else :
                    for val_key in vals.keys():
                        if val_key not in ['is_validated', 'rel_project_stage_id', 'rel_project_user_id', 'rel_project_manager_user_id', 'name']:
                        #il faut pouvoir écrire s'il on dévalide et lorsque le projet change de statut (rel_project_stage_id est stocké pour permettre de grouper sur cet attribut)
                            raise ValidationError(_("Il n'est pas possible de modifier cette clôture car elle est validée %s (ID = %s).\n\nTentative de modification des attributs suivants, dont au moins un n'est pas modifiable une fois la clôture validée : %s." % (rec.name, rec.id, ', '.join(vals.keys()))))
            

    def unlink(self):
        for rec in self:
            if rec.next_closing :
                raise ValidationError(_("Il n'est pas possible de supprimer cette clôture car une clôture postérieure existe pour ce projet."))
            if rec.is_validated :
                raise ValidationError(_("Il n'est pas possible de supprimer cette clôture car elle est validée."))
        super().unlink()

    #TODO : à réactiver une fois la base debuguée
    """
    @api.constrains('fae_balance', 'pca_balance', 'cca_balance', 'fnp_balance')
    def _check_balances_signs(self):
        for rec in self:
            if rec.is_validated : #dans la base de données, on a 7 FAE négative et 4 FNP positive
                continue
            if rec.fae_balance < 0:
                raise ValidationError(_("Clôture %s : le solde FAE ne peut pas être négatif (%s).") % (rec.name, rec.fae_balance))
            if rec.pca_balance > 0:
                raise ValidationError(_("Clôture %s : le solde PCA ne peut pas être positif (%s).") % (rec.name, rec.pca_balance))
            if rec.cca_balance < 0:
                raise ValidationError(_("Clôture %s : le solde CCA ne peut pas être négatif (%s).") % (rec.name, rec.cca_balance))
            if rec.fnp_balance > 0:
                raise ValidationError(_("Clôture %s : le solde FNP ne peut pas être positif (%s).") % (rec.name, rec.fnp_balance))
    """

    def check_provisions_consistency(self):
        for rec in self :
            if rec.object_progress_ids :
                # 1. CA Brut (Somme des variations de revenus)
                if rec.closing_date > datetime.date(2025, 12, 31):
                    if abs(rec.gross_revenue - sum(rec.object_progress_ids.mapped('progress_revenue_amount_period'))) > 0.10 :
                        _logger.info("; %s ; %s ; ATTENTION La somme des CA bruts DE LA PÉRIODE des avancements n'est pas égale au CA brut de la cloture." % (rec.project_id.display_name, rec.closing_date))
                
                somme_ca_cumulés_adv = sum(rec.object_progress_ids.mapped('progress_revenue_amount'))
                # Recherche de toutes les clôtures du même projet dont la date est <= à la clôture actuelle
                all_previous_closings = self.env['project.accounting_closing'].search([
                    ('project_id', '=', rec.project_id.id),
                    ('closing_date', '<=', rec.closing_date)
                ])
                # Somme des CA bruts de ces clôtures
                somme_ca_bruts_historiques = sum(all_previous_closings.mapped('gross_revenue'))
                if abs(somme_ca_cumulés_adv - somme_ca_bruts_historiques) > 0.10 :
                    _logger.info("; %s ; %s ; ATTENTION La somme des CA bruts CUMULES des avancements n'est pas égale à la somme des CA bruts des clôtures antérieures ou égales à celle-ci.; %s ; %s ;  %s" % (rec.project_id.display_name, rec.closing_date, somme_ca_cumulés_adv, somme_ca_bruts_historiques, somme_ca_cumulés_adv-somme_ca_bruts_historiques))

                # 2. FAE / PCA (Logique d'écart cumulé)
                total_adv_revenue = sum(rec.object_progress_ids.mapped('progress_revenue_amount'))
                cumul_invoiced = rec.get_invoice_period(rec.project_id, [], rec.closing_date)[0]
                
                revenue_gap = total_adv_revenue - cumul_invoiced
                if revenue_gap > 0:
                    computed_fae_period_amount = revenue_gap - rec.fae_previous_balance
                    computed_pca_period_amount = -rec.pca_previous_balance
                else:
                    computed_pca_period_amount = revenue_gap - rec.pca_previous_balance
                    computed_fae_period_amount = -rec.fae_previous_balance
                if rec.closing_date > datetime.date(2025, 12, 31):
                    if abs(computed_fae_period_amount - rec.fae_period_amount) > 0.01 :
                        _logger.info("; %s ; %s ; Le montant calculé de FAE est différent de celui qui a été saisi sur la cloture. L'algo le redressera sur le premier mois calculé automatiquement." % (rec.project_id.display_name, rec.closing_date))
                    if abs(computed_pca_period_amount - rec.pca_period_amount) > 0.01 :
                        _logger.info("; %s ; %s ; Le montant calculé de PCA est différent de celui qui a été saisi sur la cloture. L'algo le redressera sur le premier mois calculé automatiquement." % (rec.project_id.display_name, rec.closing_date))


                # 3. CCA / FNP (Somme des provisions des lignes)
                if rec.closing_date > datetime.date(2025, 12, 31):
                    if abs(rec.cca_balance - sum(rec.object_progress_ids.mapped('cca_balance'))) > 0.01 :
                        _logger.info("; %s ; %s ; ATTENTION La somme des soldes de CCA des avancements n'est pas égale au solde de CCA de la cloture. ; %s ; %s ;  %s" % (rec.project_id.display_name, rec.closing_date, rec.cca_balance, sum(rec.object_progress_ids.mapped('cca_balance')), rec.cca_balance-sum(rec.object_progress_ids.mapped('cca_balance'))))
                    if abs(rec.fnp_balance - sum(rec.object_progress_ids.mapped('fnp_balance'))) > 0.01 :
                        _logger.info("; %s ; %s ; ATTENTION La somme des soldes de FNP des avancements n'est pas égale au solde de FNP de la cloture. ; %s ; %s ;  %s" % (rec.project_id.display_name, rec.closing_date, rec.fnp_balance, sum(rec.object_progress_ids.mapped('fnp_balance')), rec.fnp_balance-sum(rec.object_progress_ids.mapped('fnp_balance'))))


                # 4. Déstockage total au fur et à mesure
                if rec.production_balance != 0 :
                    _logger.info("; %s ; %s ; Le solde de production interne n'est pas nulle. L'algo le mettra à 0 automatiquement sur le premier mois calculé automatiquement." % (rec.project_id.display_name, rec.closing_date))
                if rec.production_external_balance != 0 :
                    _logger.info("; %s ; %s ; Le solde de production externe n'est pas nulle. L'algo le mettra à 0 automatiquement sur le premier mois calculé automatiquement." % (rec.project_id.display_name, rec.closing_date))
                
                # Contrôle de cohérence sur les achats (uniquement si valorisé par l'avancement)
                total_progress_purchase = sum(rec.object_progress_ids.mapped('purchase_period_amount'))
                if abs(rec.purchase_period_amount - total_progress_purchase) > 0.01 :
                    _logger.info("; %s ; %s ; ATTENTION La somme des achats des avancements n'est pas égale aux achats de la cloture." % (rec.project_id.display_name, rec.closing_date))
                
                if rec.fae_balance < 0:
                    _logger.info("; %s ; %s ; Le solde FAE ne peut pas être négatif (%s)." % (rec.project_id.display_name, rec.closing_date, rec.fae_balance))
                if rec.pca_balance > 0:
                    _logger.info("; %s ; %s ; Le solde PCA ne peut pas être positif (%s)." % (rec.project_id.display_name, rec.closing_date, rec.pca_balance))
                if rec.cca_balance < 0:
                    _logger.info("; %s ; %s ; Le solde CCA ne peut pas être négatif (%s)." % (rec.project_id.display_name, rec.closing_date, rec.cca_balance))
                if rec.fnp_balance > 0:
                    _logger.info("; %s ; %s ; Le solde FNP ne peut pas être positif (%s)." % (rec.project_id.display_name, rec.closing_date, rec.fnp_balance))


    @api.depends('project_id', 'project_id.name', 'closing_date', 'valuation_from_progress', 
                 'object_progress_ids.progress_revenue_amount_period', 'object_progress_ids.purchase_period_amount', 
                 'object_progress_ids.cca_period_amount', 'object_progress_ids.fnp_period_amount')
    def compute(self):
        #self.check_provisions_consistency()
        #return
        _logger.info('-- compute project_accounting_closing')
        for rec in self :
            rec._check_can_write()

            proj_id = rec.project_id #quand on applique la fonction WRITE
            if '<NewId origin=' in str(proj_id) : #pour avoir la cloture précédente et les valeur de facturation du mois lorsque l'on modifie n'importe quel attribut de la popup (c'est à dire quand on est en mon onchange)
                proj_id = rec._origin.project_id
            if not proj_id : #pour avoir les valeurs de facturation du mois dès l'ouverture de la popup de création d'une nouvelle cloture
                proj_ids = rec.env['project.project'].search([('id', '=', rec._get_default_project_id())])
                if len(proj_ids) :
                    proj_id = proj_ids[0]

            # Il est important que la détermination de previous_closing soit fait avant la génération des Avancements
            previous_accounting_closing_ids = rec.env['project.accounting_closing'].search([('project_id', '=', proj_id.id), ('closing_date', '<', rec.closing_date)], order="closing_date desc")
            previous_closing = None
            previous_closing_date_filter = []

            if len(previous_accounting_closing_ids) > 0 :
                previous_closing = previous_accounting_closing_ids[0]
                previous_closing_date_filter.append(('date', '>', previous_closing.closing_date))
            if rec.previous_closing != previous_closing:
                if previous_closing == None and rec.previous_closing.id == False :
                    pass
                else :
                    _logger.info(rec.previous_closing)
                    _logger.info(previous_closing)
                    _logger.info("===== Nouvelle valeur poure previous_closing ID_closing=%s" % rec.id)
                    rec.previous_closing = previous_closing



            #Ces champs ne peuvent pas être de type related stored car les related stored ne sont calculés qu'après l'execution de cette fonction lors de la creation
            #   Donc celà ne permet pas de reporter correctement des provisions du mois précédent dès la création de la nouvelle cloture
            if rec.previous_closing :
                rec.pca_previous_balance = rec.previous_closing.pca_balance
                rec.fae_previous_balance = rec.previous_closing.fae_balance
                rec.cca_previous_balance = rec.previous_closing.cca_balance
                rec.fnp_previous_balance = rec.previous_closing.fnp_balance
                rec.production_previous_balance = rec.previous_closing.production_balance
                rec.production_external_previous_balance = rec.previous_closing.production_external_balance

            # Chez Tasmane, le mois de juillet 2023 est le mois de reprise des données
            #   La première cloture sur TazForce a été réalisée fin août 2023.
            #   Il est nécessaire de forcer à 0.0€ les attributs invoice_period_amount,
            #       purchase_period_amount, production_period_amount pour les clotures du 31/07/2025
            if rec.closing_date and (rec.closing_date == datetime.date(2023,7,31)) :
                rec.invoice_period_amount = 0.0
                rec.purchase_period_amount = 0.0
                rec.production_period_amount = 0.0
            else :
                rec.invoice_period_amount = rec.get_invoice_period(proj_id, previous_closing_date_filter, rec.closing_date)[0]
                purchase_period_subtotal, purchase_period_total, purchase_periode_paid, purchase_periode_line_ids = rec.get_purchase_period(proj_id, previous_closing_date_filter, rec.closing_date)
                rec.purchase_period_amount = -1 * purchase_period_subtotal
                production_period_amount, analytic_lines = rec.get_production_period(proj_id, previous_closing_date_filter, rec.closing_date, force_recompute_amount=False)
                rec.production_period_amount = -1 * production_period_amount



            purchase_outsourcing_period_amount = 0.0
            if rec.closing_date and (rec.closing_date > datetime.date(2025,9,30)) : # Les champs propres au stock externes ont été ajoutés en octobre 2025. Avant cette date, la production externe était gérée comme des achats "autres" (gestion avec des provisions et non suivant la logique de rpoduction / stock / destockage).
                for purchase_periode_line_id in purchase_periode_line_ids:
                    purchase_periode_line = self.env['account.move.line'].browse(purchase_periode_line_id)
                    if purchase_periode_line.product_id and purchase_periode_line.product_id.is_external_production == True :
                        purchase_outsourcing_period_amount += purchase_periode_line.price_subtotal_signed * purchase_periode_line.analytic_distribution[str(proj_id.account_id.id)]/100.0
            rec.purchase_outsourcing_period_amount = -1 * purchase_outsourcing_period_amount
            rec.purchase_other_period_amount = rec.purchase_period_amount - rec.purchase_outsourcing_period_amount

            if rec.valuation_from_progress:
                # 1. CA Brut (Somme des variations de revenus)
                rec.gross_revenue = sum(rec.object_progress_ids.mapped('progress_revenue_amount_period'))
                
                # 2. FAE / PCA (Logique d'écart cumulé)
                total_adv_revenue = sum(rec.object_progress_ids.mapped('progress_revenue_amount'))
                cumul_invoiced = rec.get_invoice_period(proj_id, [], rec.closing_date)[0]
                
                revenue_gap = total_adv_revenue - cumul_invoiced
                if revenue_gap > 0:
                    rec.fae_period_amount = revenue_gap - rec.fae_previous_balance
                    rec.pca_period_amount = -rec.pca_previous_balance
                else:
                    rec.pca_period_amount = revenue_gap - rec.pca_previous_balance
                    rec.fae_period_amount = -rec.fae_previous_balance
                
                # 3. CCA / FNP (Somme des provisions des lignes)
                rec.cca_period_amount = sum(rec.object_progress_ids.mapped('cca_period_amount'))
                rec.fnp_period_amount = sum(rec.object_progress_ids.mapped('fnp_period_amount'))

                # 4. Déstockage total au fur et à mesure
                rec.production_destocking = rec.production_previous_balance + rec.production_period_amount
                rec.production_external_destocking = rec.production_external_previous_balance + rec.purchase_outsourcing_period_amount
                
                # Contrôle de cohérence sur les achats (uniquement si valorisé par l'avancement)
                total_progress_purchase = sum(rec.object_progress_ids.mapped('purchase_period_amount'))
                rec.purchase_period_mismatch = abs(rec.purchase_period_amount - total_progress_purchase) > 0.01
            else:
                rec.gross_revenue = rec.invoice_period_amount + rec.pca_period_amount + rec.fae_period_amount
                rec.purchase_period_mismatch = False


            rec.pca_balance = rec.pca_previous_balance + rec.pca_period_amount
            rec.fae_balance = rec.fae_previous_balance + rec.fae_period_amount
            rec.cca_balance = rec.cca_previous_balance + rec.cca_period_amount
            rec.fnp_balance = rec.fnp_previous_balance + rec.fnp_period_amount
            rec.provision_previous_balance_sum = rec.pca_previous_balance + rec.fae_previous_balance + rec.cca_previous_balance + rec.fnp_previous_balance
            rec.provision_balance_sum = rec.pca_balance + rec.fae_balance + rec.cca_balance + rec.fnp_balance

            rec.production_external_period_amount = rec.purchase_outsourcing_period_amount

            rec.production_stock = rec.production_previous_balance + rec.production_period_amount
            rec.production_external_stock = rec.production_external_previous_balance + rec.production_external_period_amount

            rec.production_balance = rec.production_stock - rec.production_destocking
            rec.production_external_balance = rec.production_external_stock - rec.production_external_destocking

            rec.production_total_previous_balance = rec.production_previous_balance + rec.production_external_previous_balance
            rec.production_total_period_amount = rec.production_period_amount + rec.production_external_period_amount
            rec.production_total_stock = rec.production_stock + rec.production_external_stock
            rec.production_total_destocking = rec.production_destocking + rec.production_external_destocking
            rec.production_total_balance = rec.production_balance + rec.production_external_balance

            rec.internal_revenue = rec.gross_revenue - rec.purchase_other_period_amount + rec.cca_period_amount + rec.fnp_period_amount
            rec.internal_margin_amount = rec.internal_revenue - rec.production_destocking - rec.production_external_destocking
            rec.internal_margin_rate = 0.0
            if rec.internal_revenue :
                rec.internal_margin_rate = rec.internal_margin_amount / rec.internal_revenue * 100

            rec.name  = "%s - %s" % (proj_id.name, rec.closing_date)

            next_closing = self.env['project.accounting_closing'].search([('previous_closing', '=', rec.id)], limit=1)
            if next_closing :
                next_closing.compute()



    def get_invoice_period(self, proj_id, previous_closing_date_filter, closing_date):
        self.ensure_one()
        return proj_id.compute_account_move_total_all_partners(previous_closing_date_filter + [('date', '<=', closing_date), ('parent_state', 'in', ['posted']), ('move_type', 'in', ['out_refund', 'out_invoice'])])

    def get_purchase_period(self, proj_id, previous_closing_date_filter, closing_date):
        self.ensure_one()
        return proj_id.compute_account_move_total_all_partners(previous_closing_date_filter + [('date', '<=', closing_date), ('parent_state', 'in', ['posted']), ('move_type', 'in', ['in_refund', 'in_invoice'])])

    def get_production_period(self, proj_id, previous_closing_date_filter, closing_date, force_recompute_amount):
        self.ensure_one()
        return proj_id.get_production_cost(previous_closing_date_filter+[('date', '<=', closing_date), ('category', '=', 'project_employee_validated')], force_recompute_amount=force_recompute_amount)

    def action_open_out_account_move_lines(self):
        previous_closing_date_filter = []
        if self.previous_closing : 
            previous_closing_date_filter = [('date', '>', self.previous_closing.closing_date)]
        subtotal, total, paid, line_ids = self.get_invoice_period(self.project_id, previous_closing_date_filter, self.closing_date)
        action = {
            'name': _("Lignes de factures / avoirs clients"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'views': [[False, 'list'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', line_ids), ('display_type', 'in', ['product'])],
            'view_type': 'form',
            'view_mode': 'list',
            'target' : 'current',
            'view_id': self.env.ref("project_accounting.view_invoicelines_tree").id,
            'limit' : 150,
            'groups_limit' : 150,
            'context': {
                'create': False,
                'default_analytic_distribution': {str(self.project_id.account_id.id): 100},
                'search_default_group_by_move' : 1,
            }
        }
        return action

    def action_open_in_account_move_lines(self):
        previous_closing_date_filter = []
        if self.previous_closing : 
            previous_closing_date_filter = [('date', '>', self.previous_closing.closing_date)]
        subtotal, total, paid, line_ids = self.get_purchase_period(self.project_id, previous_closing_date_filter, self.closing_date)

        action = {
            'name': _('Lignes de factures / avoirs fournisseurs'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'views': [[False, 'list'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', line_ids), ('display_type', 'in', ['product'])],
            'view_type': 'form',
            'view_mode': 'list',
            'target' : 'current',
            'view_id': self.env.ref("project_accounting.view_invoicelines_tree").id,
            'limit' : 150,
            'groups_limit' : 150,
            'context': {
                'create': False,
                'default_analytic_distribution': {str(self.project_id.account_id.id): 100},
                'search_default_group_by_move' : 1,
            }
        }
        return action

    def action_open_analytic_lines(self):
        previous_closing_date_filter = []
        if self.previous_closing :
            previous_closing_date_filter = [('date', '>', self.previous_closing.closing_date)]
        production_period_amount, analytic_lines = self.get_production_period(self.project_id, previous_closing_date_filter, self.closing_date, force_recompute_amount=False)
        view_id = self.env.ref("hr_timesheet.timesheet_view_tree_user")
        return {
                'type': 'ir.actions.act_window',
                'name': 'Pointage du mois',
                'res_model': 'account.analytic.line',
                'view_type': 'tree',
                'view_mode': 'list',
                'view_id': view_id.id,
                'target': 'current',
                'domain': [('id', 'in', analytic_lines.ids)],
            }

    def goto_napta(self):
        napta_id = getattr(self.project_id, 'napta_id', False)
        if napta_id:
            return {
                'type': 'ir.actions.act_url',
                'url': 'https://app.napta.io/projects/%s?view=financial' % (napta_id),
                'target': 'new',
            }
        else : 
            raise ValidationError(_("Ce projet n'est lié à aucun identifiant Napta : impossible d'ouvrir sa page Napta."))

    name = fields.Char('Libellé', compute=compute, store=True)
    is_validated = fields.Boolean('Validée', tracking=True)
    valuation_from_progress = fields.Boolean('Valorisation par l’avancement', help="Si coché, les provisions et les déstockages sont calculés automatiquement à partir des objets d’avancement.")
    comment = fields.Text("Commentaire")
    comment_previous = fields.Text("Commentaire clôture précédente", related='previous_closing.comment')
    project_id = fields.Many2one('project.project', string="Projet", required=True, check_company=True, default=_get_default_project_id, ondelete='restrict')
    project_id_number = fields.Char(related='project_id.number', store=True)
    rel_project_partner_id = fields.Many2one(related='project_id.partner_id', store=True)
    rel_project_user_id = fields.Many2one(related='project_id.user_id', store=True)
    rel_project_date_start = fields.Date(related='project_id.date_start')
    rel_project_date = fields.Date(related='project_id.date')
    rel_project_stage_id = fields.Many2one(related='project_id.stage_id', string="Statut actuel", store=True)
    rel_project_accounting_closing_ids = fields.One2many(related='project_id.accounting_closing_ids')
    rel_project_manager_user_id = fields.Many2one(related='project_id.project_manager.user_id', string="Partner ou manager en appui de l'administration du projet", help="Personne à contacter par l'ADV, capable de répondre aux aspects économiques et contractuels du projet.", store=True)
    original_stage_id = fields.Many2one('project.project.stage', readonly=True, string='Statut début clôture', help='Statut du projet à la création de la clôture ("photo")')
    closing_date = fields.Date("Date de clôture", required=False, default=_get_default_closing_date)
    previous_closing = fields.Many2one('project.accounting_closing', string="Clôture précédente", compute=compute, store=True)
    next_closing = fields.One2many('project.accounting_closing', 'previous_closing', string="Clôture suivante", readonly=True)
    object_progress_ids = fields.One2many('project.progress', 'accounting_closing_id', string="Avancements")

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)

    invoice_period_amount = fields.Monetary('Facturation HT sur la période', compute=compute, store=True)
    purchase_period_amount = fields.Monetary('Achats HT sur la periode', compute=compute, store=True)
    purchase_outsourcing_period_amount = fields.Monetary('Achats de S/T (production externe) HT sur la periode', compute=compute, store=True, help="Somme des lignes d'achat dont la case 'Génère de la prod externe en compta' est cochée sur l'onglet Achats de la fiche du produit")
    purchase_other_period_amount = fields.Monetary('Autres achats HT sur la periode', compute=compute, store=True, help="Autres achats = Achats - Achats de S/T")
    
    pca_previous_balance = fields.Monetary('Précédent solde PCA', compute=compute, aggregator='sum', store=True)
    pca_period_amount = fields.Monetary('PCA(-)', compute=compute, store=True)
    pca_balance = fields.Monetary('Solde PCA', compute=compute, store=True, aggregator='sum')
    
    fae_previous_balance = fields.Monetary('Précédent solde FAE', compute=compute, aggregator='sum', store=True)
    fae_period_amount = fields.Monetary('FAE(+)', compute=compute, store=True)
    fae_balance = fields.Monetary('Solde FAE', compute=compute, store=True, aggregator='sum')
    
    cca_previous_balance = fields.Monetary('Précédent solde CCA', compute=compute, aggregator='sum', store=True)
    cca_period_amount = fields.Monetary('CCA(+)', compute=compute, store=True)
    cca_balance = fields.Monetary('Solde CCA', compute=compute, store=True, aggregator='sum')
    
    fnp_previous_balance = fields.Monetary('Précédent solde FNP', compute=compute, aggregator='sum', store=True)
    fnp_period_amount = fields.Monetary('FNP(-)', compute=compute, store=True)
    fnp_balance = fields.Monetary('Solde FNP', compute=compute, store=True, aggregator='sum')

    purchase_period_mismatch = fields.Boolean('Écart sur les achats', compute=compute, store=True, help="Indique s'il y a un écart entre le montant des achats de la période et la somme des achats des lignes d'avancement")

    provision_previous_balance_sum = fields.Monetary('Somme reprise prov.', compute=compute, store=True, aggregator=False)
    provision_balance_sum = fields.Monetary('Somme solde prov.', compute=compute, store=True, aggregator=False)
    
    production_previous_balance = fields.Monetary('Précédent stock interne', compute=compute, aggregator='sum', store=True)
    production_period_amount = fields.Monetary('Production interne sur la période', compute=compute, store=True, help="Somme des pointages internes de la période, valorisés au coût de revient")
    production_stock = fields.Monetary('Stock interne', compute=compute, store=True, aggregator='sum')
    production_destocking = fields.Monetary('Destockage interne', compute=compute, store=True)
    production_balance = fields.Monetary('Solde prod interne après destockage', compute=compute, store=True, aggregator='sum')
    
    production_external_previous_balance = fields.Monetary('Précédent stock externe', compute=compute, aggregator='sum', store=True)
    production_external_period_amount = fields.Monetary('Production externe sur la période', compute=compute, store=True, help="Somme du prix d'achat HT des lignes de factures/avoirs fournisseurs de la période lorsque l'article est configuré pour générer de la production externe - coche sur l'onglet Achat de la fiche produit")
    production_external_stock = fields.Monetary('Stock externe', compute=compute, store=True, aggregator='sum')
    production_external_destocking = fields.Monetary('Destockage externe', compute=compute, store=True)
    production_external_balance = fields.Monetary('Solde externe prod après destockage', compute=compute, store=True, aggregator='sum')
    
    production_total_previous_balance = fields.Monetary('Précédent stock total', compute=compute, aggregator='sum', store=True)
    production_total_period_amount = fields.Monetary('Production totale sur la période', compute=compute, store=True, help="Somme de la production interne et de la production externe sur la période")
    production_total_stock = fields.Monetary('Stock total', compute=compute, store=True, aggregator='sum')
    production_total_destocking = fields.Monetary('Destockage total', compute=compute, store=True, aggregator='sum')
    production_total_balance = fields.Monetary('Solde total prod après destockage', compute=compute, store=True, aggregator='sum')
    
    gross_revenue = fields.Monetary('CA brut', compute=compute, store=True, help="CA brut = factures/avoirs clients + PCA + FAE")
    internal_revenue = fields.Monetary('CA net d\'achats AUTRES (mais pas de S/T)', compute=compute, store=True, help="CA net d'achats AUTRES = CA brut - factures/avoires fournisseurs AUTRES + CCA + FNP")
    internal_margin_amount = fields.Monetary('Marge nette d\'achats AUTRES (€)', compute=compute, store=True, help="Marge nette (€) = CA net - destockage interne - destockage externe")
    internal_margin_rate = fields.Monetary('Marge nette d\'achats AURTES (%)', compute=compute, store=True, aggregator=False)

