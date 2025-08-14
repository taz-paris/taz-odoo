# Tests inspired by those of the OCA module account_invoice_inter_company. Inhereted copyrights :
#   Copyright 2015-2017 Chafique Delli <chafique.delli@akretion.com>
#   Copyright 2020 Tecnativa - David Vidal
#   Copyright 2020 Tecnativa - Pedro M. Baeza

# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form, TransactionCase
from unittest.mock import patch
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)

@tagged("post_install", "-at_install")
class TestAccountInvoiceInterCompanyBase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        logging.getLogger('odoo.addons.napta_connector.models.napta').setLevel(logging.CRITICAL+1)
        logging.getLogger('odoo.addons.staffing.models.employee_staffing_report').setLevel(logging.CRITICAL+1)

        # Mock IrSequence.next_by_code to not change the db value (next_by_code make a commit so it's not rollbacked at the end of the test)
        cls._seq_counter = 1
        def fake_seq_generator(*args, **kwargs):
            cls._seq_counter += 1
            return f"TESTSEQ-{cls._seq_counter:03d}"
        cls.patcher_code = patch(
            'odoo.addons.base.models.ir_sequence.IrSequence.next_by_code',
            side_effect=fake_seq_generator
        )
        cls.mock_next_by_code = cls.patcher_code.start()


        cls.account_obj = cls.env["account.account"]
        cls.account_move_obj = cls.env["account.move"]
        cls.project_obj = cls.env["project.project"]
        cls.project_link_obj = cls.env["project.outsourcing.link"]
        cls.po_obj = cls.env["purchase.order"]
        cls.so_obj = cls.env["sale.order"]

        cls.company_a = cls.env["res.company"].create(
            {
                "name": "Company AA",
                "invoice_auto_validation": True,
                "intercompany_invoicing": True,
                "so_from_po" : True,
                "sale_auto_validation" : True,
            }
        )
        cls.partner_company_a = cls.env["res.partner"].create(
            {"name": "Partner company A", "is_company": True, "external_auxiliary_code" : "A1"}
        )
        cls.company_a.partner_id = cls.partner_company_a
        cls.company_b = cls.env["res.company"].create(
            {
                "name": "Company BB",
                "invoice_auto_validation": True,
                "intercompany_invoicing": True,
                "so_from_po" : True,
                "sale_auto_validation" : True,
            }
        )
        cls.partner_company_b = cls.env["res.partner"].create(
            {"name": "Partner company B", "is_company": True, "external_auxiliary_code" : "B1"}
        )
        cls.child_partner_company_b = cls.env["res.partner"].create(
            {
                "name": "Child, Company B",
                "is_company": False,
                "company_id": False,
                "parent_id": cls.partner_company_b.id,
            }
        )
        cls.company_b.partner_id = cls.partner_company_b
        cls.user_company_a = cls.env["res.users"].create(
            {
                "name": "User A",
                "login": "usera",
                "company_type": "person",
                "email": "usera@yourcompany.com",
                "password": "usera_p4S$word",
                "company_id": cls.company_a.id,
                "company_ids": [(6, 0, [cls.company_a.id, cls.company_b.id])],
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_partner_manager").id,
                            cls.env.ref("account.group_account_manager").id,
                            cls.env.ref("account.group_account_readonly").id,
                            cls.env.ref("taz-common.taz-management").id,
                        ],
                    )
                ],
            }
        )
        cls.company_a.intercompany_sale_user_id = cls.user_company_a.id
        cls.company_a.intercompany_invoice_user_id = cls.user_company_a.id
        cls.company_b.intercompany_sale_user_id = cls.user_company_a.id
        cls.company_b.intercompany_invoice_user_id = cls.user_company_a.id

        cls.user_company_b = cls.env["res.users"].create(
            {
                "name": "User B",
                "login": "userb",
                "company_type": "person",
                "email": "userb@yourcompany.com",
                "password": "userb_p4S$word",
                "company_id": cls.company_b.id,
                "company_ids": [(6, 0, [cls.company_b.id, cls.company_a.id])],
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_partner_manager").id,
                            cls.env.ref("account.group_account_manager").id,
                            cls.env.ref("taz-common.taz-management").id,
                        ],
                    )
                ],
            }
        )
        cls.sequence_sale_journal_company_a = cls.env["ir.sequence"].create(
            {
                "name": "Account Sales Journal Company A",
                "padding": 3,
                "prefix": "SAJ-A/%(year)s/",
                "company_id": cls.company_a.id,
            }
        )
        cls.sequence_misc_journaal_company_a = cls.env["ir.sequence"].create(
            {
                "name": "Miscellaneous Journal Company A",
                "padding": 3,
                "prefix": "MISC-A/%(year)s/",
                "company_id": cls.company_a.id,
            }
        )
        cls.sequence_purchase_journal_company_a = cls.env["ir.sequence"].create(
            {
                "name": "Account Expenses Journal Company A",
                "padding": 3,
                "prefix": "EXJ-A/%(year)s/",
                "company_id": cls.company_a.id,
            }
        )
        cls.sequence_sale_journal_company_b = cls.env["ir.sequence"].create(
            {
                "name": "Account Sales Journal Company B",
                "padding": 3,
                "prefix": "SAJ-B/%(year)s/",
                "company_id": cls.company_b.id,
            }
        )
        cls.sequence_misc_journal_company_b = cls.env["ir.sequence"].create(
            {
                "name": "Miscellaneous Journal Company B",
                "padding": 3,
                "prefix": "MISC-B/%(year)s/",
                "company_id": cls.company_b.id,
            }
        )
        cls.sequence_purchase_journal_company_b = cls.env["ir.sequence"].create(
            {
                "name": "Account Expenses Journal Company B",
                "padding": 3,
                "prefix": "EXJ-B/%(year)s/",
                "company_id": cls.company_b.id,
            }
        )

        cls.sequence_misc_journal_company_a = cls.env["ir.sequence"].create(
            {
                "name": "Miscellaneous Journal Company A",
                "padding": 3,
                "prefix": "MISC-A/%(year)s/",
                "company_id": cls.company_a.id,
            }
        )
        cls.sequence_purchase_journal_company_a = cls.env["ir.sequence"].create(
            {
                "name": "Account Expenses Journal Company A",
                "padding": 3,
                "prefix": "EXJ-A/%(year)s/",
                "company_id": cls.company_a.id,
            }
        )
        cls.sequence_sale_journal_company_b = cls.env["ir.sequence"].create(
            {
                "name": "Account Sales Journal Company B",
                "padding": 3,
                "prefix": "SAJ-B/%(year)s/",
                "company_id": cls.company_b.id,
            }
        )
        cls.sequence_misc_journal_company_b = cls.env["ir.sequence"].create(
            {
                "name": "Miscellaneous Journal Company B",
                "padding": 3,
                "prefix": "MISC-B/%(year)s/",
                "company_id": cls.company_b.id,
            }
        )
        cls.sequence_purchase_journal_company_b = cls.env["ir.sequence"].create(
            {
                "name": "Account Expenses Journal Company B",
                "padding": 3,
                "prefix": "EXJ-B/%(year)s/",
                "company_id": cls.company_b.id,
            }
        )

        cls.a_sale_company_a = cls.account_obj.create(
            {
                "code": "X2001.A",
                "name": "Product Sales - (company A)",
                "account_type": "income_other",
                "company_id": cls.company_a.id,
            }
        )
        cls.a_expense_company_a = cls.account_obj.create(
            {
                "code": "X2110.A",
                "name": "Expenses - (company A)",
                "account_type": "income_other",
                "company_id": cls.company_a.id,
            }
        )
        cls.a_bank_company_a = cls.account_obj.create(
            {
                "code": "512001.A",
                "name": "Bank - (company A)",
                "account_type": "asset_cash",
                "company_id": cls.company_a.id,
            }
        )
        cls.a_recv_company_b = cls.account_obj.create(
            {
                "code": "X11002.B",
                "name": "Debtors - (company B)",
                "account_type": "asset_receivable",
                "reconcile": "True",
                "company_id": cls.company_b.id,
            }
        )
        cls.a_pay_company_b = cls.account_obj.create(
            {
                "code": "X1111.B",
                "name": "Creditors - (company B)",
                "account_type": "liability_payable",
                "reconcile": "True",
                "company_id": cls.company_b.id,
            }
        )
        cls.a_sale_company_b = cls.account_obj.create(
            {
                "code": "X2001.B",
                "name": "Product Sales - (company B)",
                "account_type": "income_other",
                "company_id": cls.company_b.id,
            }
        )
        cls.a_expense_company_b = cls.account_obj.create(
            {
                "code": "X2110.B",
                "name": "Expenses - (company B)",
                "account_type": "expense",
                "company_id": cls.company_b.id,
            }
        )
        cls.a_bank_company_b = cls.account_obj.create(
            {
                "code": "512001.B",
                "name": "Bank - (company B)",
                "account_type": "asset_cash",
                "company_id": cls.company_b.id,
            }
        )

        cls.sales_journal_company_a = cls.env["account.journal"].create(
            {
                "name": "Sales Journal - (Company A)",
                "code": "SAJ-A",
                "type": "sale",
                "secure_sequence_id": cls.sequence_sale_journal_company_a.id,
                "default_account_id": cls.a_sale_company_a.id,
                "company_id": cls.company_a.id,
            }
        )
        cls.sales_journal_company_b = cls.env["account.journal"].create(
            {
                "name": "Sales Journal - (Company B)",
                "code": "SAJ-A",
                "type": "sale",
                "secure_sequence_id": cls.sequence_sale_journal_company_b.id,
                "default_account_id": cls.a_sale_company_b.id,
                "company_id": cls.company_b.id,
            }
        )

        cls.bank_journal_company_a = cls.env["account.journal"].create(
            {
                "name": "Bank Journal - (Company A)",
                "code": "BNK-A",
                "type": "bank",
                "default_account_id": cls.a_sale_company_a.id,
                "company_id": cls.company_a.id,
            }
        )
        cls.misc_journal_company_a = cls.env["account.journal"].create(
            {
                "name": "Miscellaneous Operations - (Company A)",
                "code": "MISC-A",
                "type": "general",
                "secure_sequence_id": cls.sequence_misc_journal_company_a.id,
                "company_id": cls.company_a.id,
            }
        )
        cls.purchases_journal_company_a = cls.env["account.journal"].create(
            {
                "name": "Purchases Journal - (Company A)",
                "code": "EXJ-B",
                "type": "purchase",
                "secure_sequence_id": cls.sequence_purchase_journal_company_a.id,
                "default_account_id": cls.a_expense_company_a.id,
                "company_id": cls.company_a.id,
            }
        )
        cls.purchases_journal_company_b = cls.env["account.journal"].create(
            {
                "name": "Purchases Journal - (Company B)",
                "code": "EXJ-B",
                "type": "purchase",
                "secure_sequence_id": cls.sequence_purchase_journal_company_b.id,
                "default_account_id": cls.a_expense_company_b.id,
                "company_id": cls.company_b.id,
            }
        )
        cls.bank_journal_company_b = cls.env["account.journal"].create(
            {
                "name": "Bank Journal - (Company B)",
                "code": "BNK-B",
                "type": "bank",
                "default_account_id": cls.a_sale_company_b.id,
                "company_id": cls.company_b.id,
            }
        )
        cls.misc_journal_company_b = cls.env["account.journal"].create(
            {
                "name": "Miscellaneous Operations - (Company B)",
                "code": "MISC-B",
                "type": "general",
                "secure_sequence_id": cls.sequence_misc_journal_company_b.id,
                "company_id": cls.company_b.id,
            }
        )
        cls.env["ir.sequence"].create(
            {
                "name": "Account Sales Journal Company A",
                "prefix": "SAJ-A/%(year)s/",
                "company_id": cls.company_a.id,
            }
        )
        cls.a_recv_company_a = cls.account_obj.create(
            {
                "code": "X11002.A",
                "name": "Debtors - (company A)",
                "account_type": "asset_receivable",
                "reconcile": "True",
                "company_id": cls.company_a.id,
            }
        )
        cls.a_pay_company_a = cls.account_obj.create(
            {
                "code": "X1111.A",
                "name": "Creditors - (company A)",
                "account_type": "liability_payable",
                "reconcile": "True",
                "company_id": cls.company_a.id,
            }
        )

        cls.partner_company_a.property_account_receivable_id = cls.a_recv_company_a.id
        cls.partner_company_a.property_account_payable_id = cls.a_pay_company_a.id

        cls.partner_company_b.with_user(
            cls.user_company_a.id
        ).sudo().property_account_receivable_id = cls.a_recv_company_a.id
        cls.partner_company_b.with_user(
            cls.user_company_a.id
        ).sudo().property_account_payable_id = cls.a_pay_company_a.id
        cls.partner_company_b.with_user(
            cls.user_company_b.id
        ).sudo().property_account_receivable_id = cls.a_recv_company_b.id
        cls.partner_company_b.with_user(
            cls.user_company_b.id
        ).sudo().property_account_payable_id = cls.a_pay_company_b.id

        cls.partner_final_customer = cls.env["res.partner"].create(
            {"name": "test final customer", "is_company": True, "external_auxiliary_code" : "C1"}
        )

        cls.project_b = cls.project_obj.with_user(cls.user_company_b.id).create(
            {
                "name" : "test project B",
                "partner_id" : cls.partner_final_customer.id,
            }
        )
        cls.project_link_b = cls.project_link_obj.with_user(cls.user_company_b.id).create(
            {
                "project_id" : cls.project_b.id,
                "partner_id" : cls.partner_company_a.id,
                "link_type" : "outsourcing",
            }
        )

        cls.product_1 = cls.env['product.product'].with_user(cls.user_company_b.id).create(
            {
                'name': 'test product 1',
                'list_price': 1022.0,
            }
        )

        cls.payment_term1 = cls.env["account.payment.term"].create(
            {
                'name' : 'immediat',
            }
        )

        cls.project_b_po = Form(
            cls.po_obj.with_user(cls.user_company_b.id).with_context(
                default_company_id = cls.project_b.company_id.id,
                default_partner_id = cls.project_link_b.partner_id.id,
                default_agreement_id = cls.project_b.agreement_id.id,
                default_analytic_distribution = {str(cls.project_b.analytic_account_id.id): 100},
                default_previsional_invoice_date = datetime.today()
                )
        )
        with cls.project_b_po.order_line.new() as line:
            line.product_id = cls.product_1
            line.name = "B-PO line 1"
            line.product_qty = 1
            line.price_unit = 1111

        with cls.project_b_po.order_line.new() as line:
            line.product_id = cls.product_1
            line.name = "B PO line 2"
            line.product_qty = 2
            line.price_unit = 2222

        cls.project_b_po.payment_term_id = cls.payment_term1
        cls.project_b_po = cls.project_b_po.save()
        cls.project_b_po_line_ids = cls.project_b_po.order_line

        cls.project_b_po.with_user(cls.user_company_b.id).button_approve()



class TestAccountInvoiceInterCompany(TestAccountInvoiceInterCompanyBase):
    def test01_create_mirror_project_from_buyer_project(self):
        self.assertNotEqual(self.project_link_b.inter_company_mirror_project.id, False)


    def test02_create_so_on_po_validation(self):
        self.assertEqual(self.project_b_po_line_ids[0].intercompany_sale_line_id.distribution_analytic_account_ids[0].id, self.project_link_b.inter_company_mirror_project.analytic_account_id.id)
        self.assertEqual(self.project_b_po.id, self.project_b_po_line_ids[0].intercompany_sale_line_id.order_id.auto_purchase_order_id.id)


    def test03_create_out_invoice_from_in_invoice(self):
        # Générate de out_invoice from project_b PO (and thus in_invoice)
        self.project_b_po_line_ids[0].qty_received = self.project_b_po_line_ids[0].product_qty
        self.project_b_po.action_create_invoice()
        invoice_line = self.project_b_po_line_ids[0].invoice_lines[0]
        self.assertNotEqual(invoice_line.id, False)

        project_b_invoice = self.project_b_po_line_ids[0].invoice_lines[0].move_id
        project_b_invoice.invoice_date = datetime.today()
        project_b_invoice.action_post()

        _logger.info(self.project_b_po_line_ids[0].intercompany_sale_line_id.read())
        mirror_invoice_line = self.project_b_po_line_ids[0].intercompany_sale_line_id.invoice_lines[0]
        self.assertNotEqual(mirror_invoice_line.id, False)

        self.assertEqual(mirror_invoice_line.distribution_analytic_account_ids[0].id, self.project_link_b.inter_company_mirror_project.analytic_account_id.id)

        self.assertEqual(mirror_invoice_line.price_unit, invoice_line.price_unit)
        self.assertEqual(mirror_invoice_line.product_id, invoice_line.product_id)
        self.assertEqual(mirror_invoice_line.quantity, invoice_line.quantity)
        self.assertEqual(mirror_invoice_line.discount, invoice_line.discount)
