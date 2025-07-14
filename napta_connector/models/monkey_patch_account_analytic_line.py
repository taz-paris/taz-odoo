from odoo import models, fields, api
from odoo.addons.hr_timesheet.models.hr_timesheet import AccountAnalyticLine as AccountAnalyticLineInherit

############################################################################
############################################################################
#####
#####  Dans Napta une affectation peut avoir plusieurs userprojectperiod
#####  alors qu'aucun consultant n'est encore staffé sur ce user_project.
#####  Donc dans Odoo, puisque l'on importe les timesheeperiods et les 
#####  userprojectperiod sur le même objet AccountAnalyticLine, on doit 
#####  supprimer la contrainte qui impose d'avoir un employee_id sur chaque
#####  AccountAnalyticLine.
#####
#####  Inconvénients potentiels :
#####     - si du code natif présupose que l'employee_id est toujours déifini si le project_id est défini... ces potentielles fonctions pourraient planter
#####
#####  Alternatives : 
#####     - créer un objet Odoo dédié pour les userprojectperiod (impact : migration des données Fitnet existantes, ajustement des vues et fonctions de calculs du module staffing)
              # Impossibilité d'avoir le prévisionner te le pointer psur une même vue pivot
#####         TODO : réaliser une étude d'impact plus approfondie) 
#####
############################################################################
############################################################################

@api.model_create_multi
def create(self, vals_list):
    # Before creating a timesheet, we need to put a valid employee_id in the vals
    default_user_id = self._default_user()
    user_ids = []
    employee_ids = []
    # 1/ Collect the user_ids and employee_ids from each timesheet vals
    vals_list = self._timesheet_preprocess(vals_list)
    for vals in vals_list:
        if not vals.get('project_id'):
            continue
        if not vals.get('name'):
            vals['name'] = '/'
        employee_id = vals.get('employee_id', self._context.get('default_employee_id', False))
        if employee_id and employee_id not in employee_ids:
            employee_ids.append(employee_id)
        else:
            user_id = vals.get('user_id', default_user_id)
            if user_id not in user_ids:
                user_ids.append(user_id)

    """
    # 2/ Search all employees related to user_ids and employee_ids, in the selected companies
    HrEmployee_sudo = self.env['hr.employee'].sudo()
    employees = HrEmployee_sudo.search([
        '&', '|', ('user_id', 'in', user_ids), ('id', 'in', employee_ids), ('company_id', 'in', self.env.companies.ids)
    ])

    #                 ┌───── in search results = active/in companies ────────> was found with... ─── employee_id ───> (A) There is nothing to do, we will use this employee_id
    # 3/ Each employee                                                                          └──── user_id ──────> (B)** We'll need to select the right employee for this user
    #                 └─ not in search results = archived/not in companies ──> (C) We raise an error as we can't create a timesheet for an archived employee
    # ** We can rely on the user to get the employee_id if
    #    he has an active employee in the company of the timesheet
    #    or he has only one active employee for all selected companies
    valid_employee_per_id = {}
    employee_id_per_company_per_user = defaultdict(dict)
    for employee in employees:
        if employee.id in employee_ids:
            valid_employee_per_id[employee.id] = employee
        else:
            employee_id_per_company_per_user[employee.user_id.id][employee.company_id.id] = employee.id

    # 4/ Put valid employee_id in each vals
    error_msg = _lt('Timesheets must be created with an active employee in the selected companies.')
    for vals in vals_list:
        if not vals.get('project_id'):
            continue
        employee_in_id = vals.get('employee_id', self._context.get('default_employee_id', False))
        if employee_in_id:
            company = False
            if not vals.get('company_id'):
                company = HrEmployee_sudo.browse(employee_in_id).company_id
                vals['company_id'] = company.id
            if not vals.get('product_uom_id'):
                vals['product_uom_id'] = company.project_time_mode_id.id if company else self.env['res.company'].browse(vals.get('company_id', self.env.company.id)).project_time_mode_id.id
            if employee_in_id in valid_employee_per_id:
                vals['user_id'] = valid_employee_per_id[employee_in_id].sudo().user_id.id   # (A) OK
                continue
            else:
                raise ValidationError(error_msg)                                      # (C) KO
        else:
            user_id = vals.get('user_id', default_user_id)                                  # (B)...

        # ...Look for an employee, with ** conditions
        employee_per_company = employee_id_per_company_per_user.get(user_id)
        employee_out_id = False
        if employee_per_company:
            company_id = list(employee_per_company)[0] if len(employee_per_company) == 1\
                    else vals.get('company_id', self.env.company.id)
            employee_out_id = employee_per_company.get(company_id, False)

        if employee_out_id:
            vals['employee_id'] = employee_out_id
            vals['user_id'] = user_id
            company = False
            if not vals.get('company_id'):
                company = HrEmployee_sudo.browse(employee_out_id).company_id
                vals['company_id'] = company.id
            if not vals.get('product_uom_id'):
                vals['product_uom_id'] = company.project_time_mode_id.id if company else self.env['res.company'].browse(vals.get('company_id', self.env.company.id)).project_time_mode_id.id
        else:  # ...and raise an error if they fail
            raise ValidationError(error_msg)
    """

    # 5/ Finally, create the timesheets
    lines = super(AccountAnalyticLineInherit, self).create(vals_list)
    lines._check_can_create()
    for line, values in zip(lines, vals_list):
        if line.project_id:  # applied only for timesheet
            line._timesheet_postprocess(values)
    return lines


AccountAnalyticLineInherit.create = create
