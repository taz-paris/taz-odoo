from unittest import mock

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import HttpCase, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillPoReconcile(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.supplier = cls.env["res.partner"].create({"name": "Fournisseur test rapprochement", "supplier_rank": 1})
        cls.product = cls.env["product.product"].create(
            {"name": "Prestation test", "type": "service", "purchase_ok": True, "supplier_taxes_id": False}
        )
        cls.customer = cls.env["res.partner"].create({"name": "Client final test", "is_company": True})
        cls.project = cls.env["project.project"].create({"name": "Projet rapprochement A", "partner_id": cls.customer.id})
        cls.project_b = cls.env["project.project"].create({"name": "Projet rapprochement B"})
        for project in cls.project | cls.project_b:
            # les écritures d'un projet doivent concerner le client ou l'un des fournisseurs déclarés (onglet Achats)
            project.project_outsourcing_link_ids = [
                Command.create({"partner_id": cls.supplier.id, "link_type": "outsourcing"})
            ]

    # ------------------------------------------------------------------ helpers
    def _analytic(self, project=None):
        project = project or self.project
        return {str(project.account_id.id): 100}

    def _make_po(self, lines, project=None):
        """lines = [(nom, quantité, prix unitaire)] ; BC confirmé."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.supplier.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "name": name,
                            "product_qty": qty,
                            "price_unit": price,
                            "taxes_id": [Command.clear()],
                            "analytic_distribution": self._analytic(project),
                            "reselling_price_unit": price * 1.2,
                            "reselling_subtotal": qty * price * 1.2,
                        }
                    )
                    for name, qty, price in lines
                ],
            }
        )
        po.button_confirm()
        return po

    def _make_bill(self, lines, project=None, analytic=True, purchase_lines=None):
        """lines = [(libellé, quantité, prix unitaire)] ; facture fournisseur brouillon."""
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.supplier.id,
                "invoice_date": "2026-11-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "name": name,
                            "quantity": qty,
                            "price_unit": price,
                            "tax_ids": [Command.clear()],
                            "analytic_distribution": self._analytic(project) if analytic else False,
                            "purchase_line_id": purchase_lines[i].id if purchase_lines else False,
                        }
                    )
                    for i, (name, qty, price) in enumerate(lines)
                ],
            }
        )
        return bill

    def _wizard(self, bill, project=None):
        project = project or self.project
        wiz = self.env["bill.po.reconcile.wizard"].create(
            {"move_id": bill.id, "project_ids": [Command.set(project.ids)]}
        )
        wiz._onchange_project_ids()
        return wiz

    def _select(self, wiz, pols, qty=None):
        for wl in wiz.po_line_ids:
            wl.selected = wl.purchase_line_id in pols
            if qty is not None and wl.purchase_line_id in pols:
                wl.qty_consumed = qty

    # ------------------------------------------------------------------ cas 1
    def test_add_to_po_values_carry_analytic(self):
        bill = self._make_bill([("Ligne", 1, 100.0)])
        vals = bill.invoice_line_ids._prepare_line_values_for_purchase()
        self.assertEqual(vals[0]["analytic_distribution"], self._analytic())

    def test_create_order(self):
        bill = self._make_bill([("Animation", 1, 1600.0), ("DISC", 59, 60.0)], analytic=False)
        wiz = self._wizard(bill)
        wiz.new_order = True
        wiz._onchange_order_ids()
        self.assertEqual(wiz.button_key, "create")
        self.assertTrue(wiz.is_valid, wiz.message)
        wiz.action_associate()
        pols = bill.invoice_line_ids.purchase_line_id
        self.assertEqual(len(pols), 2)
        order = pols.order_id
        self.assertEqual(order.state, "purchase")
        self.assertEqual(order.partner_id, self.supplier)
        self.assertTrue(all(p.analytic_distribution == self._analytic() for p in pols))

    def test_create_order_creates_outsourcing_link(self):
        project = self.env["project.project"].create({"name": "Projet sans fournisseur", "partner_id": self.customer.id})
        self.assertFalse(project.project_outsourcing_link_ids)
        bill = self._make_bill([("Animation", 1, 1600.0)], project=project, analytic=False)
        wiz = self._wizard(bill, project=project)
        wiz.new_order = True
        wiz._onchange_order_ids()
        self.assertTrue(wiz.needs_link_type)
        self.assertEqual(wiz.link_type, "other")  # valeur par défaut
        wiz.link_type = "cosourcing"  # choix de l'utilisateur
        self.assertTrue(wiz.is_valid, wiz.message)
        wiz.action_associate()
        link = project.project_outsourcing_link_ids
        self.assertEqual(len(link), 1)
        self.assertEqual(link.partner_id, self.supplier)
        self.assertEqual(link.link_type, "cosourcing")
        # un second BC pour le même projet et le même fournisseur ne duplique pas le lien
        bill2 = self._make_bill([("Suite", 1, 500.0)], project=project, analytic=False)
        wiz2 = self._wizard(bill2, project=project)
        wiz2.new_order = True
        wiz2._onchange_order_ids()
        self.assertFalse(wiz2.needs_link_type)  # le lien existe : plus de choix à faire
        wiz2.action_associate()
        self.assertEqual(len(project.project_outsourcing_link_ids), 1)

    # ------------------------------------------------------------------ cas 2 remplacement
    def test_replacement_ekuanim(self):
        po = self._make_po([("40%", 1, 4320.0), ("60%", 1, 6480.0)])
        bill = self._make_bill([("Cadrage", 1, 1800.0), ("Phase 1", 1, 2844.0), ("Phase 2", 1, 2844.0), ("Livraison", 1, 3312.0)])
        wiz = self._wizard(bill)
        self.assertEqual(wiz.mode, "replacement")
        # présélection automatique : combinaison unique (les deux lignes)
        self.assertEqual(len(wiz.po_line_ids.filtered("selected")), 2)
        self.assertEqual(wiz.button_key, "replace")
        self.assertTrue(wiz.is_valid, wiz.message)
        old_ids = po.order_line.ids
        wiz.action_associate()
        new_lines = po.order_line
        self.assertEqual(len(new_lines), 4)
        self.assertFalse(set(old_ids) & set(new_lines.ids))
        self.assertEqual(bill.invoice_line_ids.purchase_line_id, new_lines)
        self.assertEqual(sum(new_lines.mapped("price_subtotal")), 10800.0)
        self.assertTrue(all(p.analytic_distribution == self._analytic() for p in new_lines))
        self.assertAlmostEqual(sum(new_lines.mapped("reselling_subtotal")), 10800.0 * 1.2, places=2)
        self.assertEqual(set(new_lines.mapped("invoice_status")), {"invoiced"})

    def test_replacement_amount_mismatch(self):
        self._make_po([("40%", 1, 4320.0), ("60%", 1, 6480.0)])
        bill = self._make_bill([("Une ligne", 1, 5000.0)])
        wiz = self._wizard(bill)
        self._select(wiz, wiz.order_ids.order_line)
        self.assertFalse(wiz.is_valid)
        with self.assertRaises(UserError):
            wiz.action_associate()

    # ------------------------------------------------------------------ cas 2 consommation / cas 3
    def test_consumption_split_then_last_tranche(self):
        po = self._make_po([("Jours", 30, 800.0)])
        pol = po.order_line
        bill = self._make_bill([("12 jours à 800", 1, 9600.0)])
        wiz = self._wizard(bill)
        self.assertEqual(wiz.mode, "consumption")
        self._select(wiz, pol, qty=12)
        self.assertEqual(wiz.button_key, "split")
        self.assertTrue(wiz.is_valid, wiz.message)
        wiz.action_associate()
        self.assertEqual(pol.product_qty, 18)
        closed = bill.invoice_line_ids.purchase_line_id
        self.assertNotEqual(closed, pol)
        self.assertEqual(closed.product_qty, 12)
        self.assertTrue(closed.qty_invoiced_override)
        self.assertEqual(closed.qty_invoiced, 12)
        self.assertEqual(closed.invoice_status, "invoiced")
        self.assertEqual(pol.price_unit, 800.0)
        self.assertAlmostEqual(closed.reselling_price_unit, 960.0)
        self.assertAlmostEqual(pol.reselling_price_unit, 960.0)
        # facture suivante : quantité == reste exact -> pas de scission
        bill2 = self._make_bill([("18 jours", 1, 14400.0)])
        wiz2 = self._wizard(bill2)
        self._select(wiz2, pol, qty=18)
        self.assertEqual(wiz2.button_key, "attach")
        count = len(po.order_line)
        wiz2.action_associate()
        self.assertEqual(len(po.order_line), count)
        self.assertEqual(bill2.invoice_line_ids.purchase_line_id, pol)
        self.assertEqual(pol.qty_invoiced, 18)

    def test_consumption_over_remaining_refused(self):
        po = self._make_po([("Jours", 9, 950.0)])
        bill = self._make_bill([("x", 1, 8550.0)])
        wiz = self._wizard(bill)
        self._select(wiz, po.order_line, qty=60)
        self.assertFalse(wiz.is_valid)
        with self.assertRaises(UserError):
            wiz.action_associate()

    # ------------------------------------------------------------------ cas 2quinquies
    def test_partially_invoiced_line_is_split_never_deleted(self):
        po = self._make_po([("Tranche 1", 1, 5200.0), ("Tranche 2", 1, 2900.0)])
        tranche1, tranche2 = po.order_line
        # facture précédente : 1 500 € rattachés à la tranche 1
        self._make_bill([("Acompte", 1, 1500.0)], purchase_lines=tranche1)
        self.assertRaises(ValidationError, tranche1.unlink)
        bill = self._make_bill([("Solde tranche 1", 1, 3700.0), ("Tranche 2", 1, 2900.0)])
        wiz = self._wizard(bill)
        wl1 = wiz.po_line_ids.filtered(lambda l: l.purchase_line_id == tranche1)
        self.assertEqual(wl1.state, "partial")
        self.assertAlmostEqual(wl1.amount_open, 3700.0)
        self._select(wiz, tranche1 | tranche2)
        self.assertEqual(wiz.button_key, "associate")
        self.assertTrue(wiz.is_valid, wiz.message)
        wiz.action_associate()
        self.assertTrue(tranche1.exists())
        self.assertAlmostEqual(tranche1.price_subtotal, 1500.0)
        self.assertAlmostEqual(sum(po.order_line.mapped("reselling_subtotal")), 8100.0 * 1.2, places=2)
        self.assertFalse(tranche2.exists())
        lines = po.order_line
        self.assertEqual(len(lines), 3)
        self.assertAlmostEqual(sum(lines.mapped("price_subtotal")), 8100.0)
        self.assertEqual(bill.invoice_line_ids.purchase_line_id & tranche1, self.env["purchase.order.line"])

    # ------------------------------------------------------------------ protections
    def test_unlink_guard_and_free_write(self):
        po = self._make_po([("A", 1, 100.0), ("B", 1, 200.0)])
        pol_a, pol_b = po.order_line
        self._make_bill([("x", 1, 100.0)], purchase_lines=pol_a)
        with self.assertRaises(ValidationError):
            pol_a.unlink()
        pol_a.write({"name": "Libellé corrigé", "price_unit": 120.0})  # write non bloqué
        self.assertEqual(pol_a.name, "Libellé corrigé")

    def test_direct_payment_line_greyed_and_excluded(self):
        po = self._make_po([("Direct", 1, 1100.0), ("Normal", 1, 1100.0)])
        direct, normal = po.order_line
        sale = self.env["sale.order"].create({"partner_id": self.customer.id})
        sale_line = self.env["sale.order.line"].create(
            {
                "order_id": sale.id,
                "product_id": self.product.id,
                "product_uom_qty": 1,
                "price_unit": 1100.0,
                "tax_id": [Command.clear()],
                "analytic_distribution": self._analytic(),
                "direct_payment_purchase_order_line_id": direct.id,
            }
        )
        self.assertEqual(sale_line.direct_payment_purchase_order_line_id, direct)
        bill = self._make_bill([("x", 1, 1100.0)])
        wiz = self._wizard(bill)
        wl = wiz.po_line_ids.filtered(lambda l: l.purchase_line_id == direct)
        self.assertEqual(wl.state, "direct")
        self.assertFalse(wl.selectable)
        # présélection : seule la ligne normale est candidate (combinaison unique)
        self.assertEqual(wiz.po_line_ids.filtered("selected").purchase_line_id, normal)
        with self.assertRaises(ValidationError):
            direct.unlink()

    def test_multi_project_matching_filters_by_analytic(self):
        po = self._make_po([("P1", 1, 500.0)])
        extra = self.env["purchase.order.line"].create(
            {
                "order_id": po.id,
                "product_id": self.product.id,
                "name": "P2",
                "product_qty": 1,
                "price_unit": 500.0,
                "taxes_id": [Command.clear()],
                "analytic_distribution": self._analytic(self.project_b),
            }
        )
        bill = self._make_bill([("x", 1, 500.0)])  # analytique projet A
        wiz = self.env["bill.po.reconcile.wizard"].create(
            {"move_id": bill.id, "project_ids": [Command.set((self.project | self.project_b).ids)]}
        )
        wiz._onchange_project_ids()
        by_pol = {wl.purchase_line_id: wl for wl in wiz.po_line_ids}
        self.assertTrue(by_pol[po.order_line[0]].analytic_ok)
        self.assertFalse(by_pol[extra].analytic_ok)
        self.assertFalse(by_pol[extra].selectable)
        # combinaison unique grâce au filtre (sinon 2 lignes à 500 €)
        self.assertEqual(wiz.po_line_ids.filtered("selected").purchase_line_id, po.order_line[0])

    # ------------------------------------------------------------------ atomicité
    def test_atomic_rollback_on_error(self):
        po = self._make_po([("Tranche 1", 1, 5200.0), ("Tranche 2", 1, 2900.0)])
        tranche1, tranche2 = po.order_line
        self._make_bill([("Acompte", 1, 1500.0)], purchase_lines=tranche1)
        bill = self._make_bill([("Solde tranche 1", 1, 3700.0), ("Tranche 2", 1, 2900.0)])
        wiz = self._wizard(bill)
        self._select(wiz, tranche1 | tranche2)
        Wizard = type(wiz)
        original = Wizard._replace_in_order

        def failing(self_, order, group, amls, rounding):
            original(self_, order, group, amls, rounding)
            raise UserError("échec simulé après les écritures")

        with mock.patch.object(Wizard, "_replace_in_order", new=failing):
            with self.assertRaises(UserError), self.cr.savepoint():
                wiz.action_associate()
        self.assertEqual(po.order_line, tranche1 | tranche2)
        self.assertAlmostEqual(tranche1.price_subtotal, 5200.0)
        self.assertFalse(bill.invoice_line_ids.purchase_line_id)

    # ------------------------------------------------------------------ import BT-11 / BT-13
    def test_find_project_from_references(self):
        Import = self.env["account.invoice.import"]
        self.assertEqual(Import._find_project_from_references({"project_reference": self.project.number}), self.project)
        self.assertEqual(Import._find_project_from_references({"origin": self.project_b.number}), self.project_b)
        self.assertFalse(Import._find_project_from_references({"project_reference": "INCONNU"}))
        self.assertFalse(
            Import._find_project_from_references({"project_reference": "%s/%s" % (self.project.number, self.project_b.number)})
        )
        self.assertFalse(Import._find_project_from_references({}))
        xpaths = Import.prepare_facturx_xpath_dict()
        self.assertIn("origin", xpaths)
        self.assertIn("project_reference", xpaths)

    # ------------------------------------------------------------------ enveloppe « frais divers »
    def _setup_envelope(self, amount=3000.0):
        """Projet sans lien pour le fournisseur de la facture + BC « frais divers » de 3 000 € (revente x1,2)."""
        envelope_partner = self.env["res.partner"].create(
            {"name": "Fournisseur frais divers test", "is_company": True, "supplier_rank": 1}
        )
        self.company.expense_envelope_partner_id = envelope_partner
        project = self.env["project.project"].create({"name": "Projet enveloppe", "partner_id": self.customer.id})
        project.project_outsourcing_link_ids = [
            Command.create({"partner_id": envelope_partner.id, "link_type": "other"})
        ]
        po = self.env["purchase.order"].create(
            {
                "partner_id": envelope_partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "name": "Frais divers",
                            "product_qty": 1,
                            "price_unit": amount,
                            "taxes_id": [Command.clear()],
                            "analytic_distribution": self._analytic(project),
                            "reselling_price_unit": amount * 1.2,
                            "reselling_subtotal": amount * 1.2,
                            "previsional_invoice_date": "2026-12-15",
                        }
                    )
                ],
            }
        )
        po.button_confirm()
        return project, po

    def _create_order_wizard(self, project, amount):
        bill = self._make_bill([("Hôtel", 1, amount)], project=project, analytic=False)
        wiz = self._wizard(bill, project=project)
        wiz.new_order = True
        wiz._onchange_order_ids()
        return bill, wiz

    def _net(self, order):
        return order.amount_untaxed, sum(order.order_line.mapped("reselling_subtotal"))

    def test_envelope_consumed_with_new_order_and_restored_on_cancel(self):
        project, env_po = self._setup_envelope()
        env_line = env_po.order_line
        # BC jamais consommé : facturable normalement (facturation directe par le fournisseur « frais divers »)
        self.assertEqual(env_line.qty_to_invoice, 1.0)
        self.assertEqual(env_line.invoice_status, "to invoice")
        bill, wiz = self._create_order_wizard(project, 1200.0)
        self.assertEqual(wiz.allowed_envelope_line_ids, env_line)
        self.assertEqual(wiz.envelope_line_id, env_line)  # présélectionnée : fournisseur de type « autres »
        self.assertIn("3000.00 → 1800.00", wiz.envelope_message)
        wiz.action_associate()
        # trace visible dans le BC : une ligne négative nommée avec le numéro interne de la facture
        trace = env_po.order_line - env_line
        self.assertEqual(len(trace), 1)
        self.assertTrue(trace.name.startswith("Consommé par"))
        self.assertEqual(trace.consumed_by_move_id, bill)  # l'identification ne dépend pas du libellé
        self.assertAlmostEqual(env_line.price_subtotal, 3000.0)  # la ligne d'origine n'est pas modifiée
        self.assertEqual(self._net(env_po), (1800.0, 2160.0))
        # le BC est consommé par une facture réelle : il suit le flux PA, aucune de ses lignes n'est plus « à facturer »
        for pol in env_po.order_line:
            self.assertEqual(pol.qty_to_invoice, 0.0)
            self.assertEqual(pol.invoice_status, "no")
        real = bill.invoice_line_ids.purchase_line_id
        self.assertAlmostEqual(real.reselling_subtotal, 1440.0)
        self.assertEqual(str(real.previsional_invoice_date), "2026-12-15")
        self.assertEqual(env_po.state, "purchase")
        # le libellé est libre : le renommer ne change ni le statut ni le retour arrière
        trace.name = "Libellé modifié à la main"
        self.assertEqual(env_line.qty_to_invoice, 0.0)
        # retour arrière : annulation de la facture
        bill.button_cancel()
        self.assertFalse(trace.exists())
        self.assertEqual(self._net(env_po), (3000.0, 3600.0))
        self.assertAlmostEqual(real.reselling_subtotal, 0.0)
        # plus de consommation : la ligne d'enveloppe redevient facturable
        self.assertEqual(env_line.qty_to_invoice, 1.0)
        self.assertEqual(env_line.invoice_status, "to invoice")

    def test_envelope_overrun_deducts_remainder_and_cancels_then_restores_on_refund(self):
        project, env_po = self._setup_envelope()
        bill, wiz = self._create_order_wizard(project, 3500.0)
        self.assertIn("Dépassement de 500.00", wiz.envelope_message)
        self.assertIn("annulé", wiz.envelope_message)
        wiz.action_associate()
        # le dépassement est visible dans le BC : ligne négative de la facture entière + ligne positive du dépassement
        extra = env_po.order_line - env_po.order_line[:1]
        self.assertEqual(sorted(extra.mapped("price_subtotal")), [-3500.0, 500.0])
        self.assertTrue(any(l.name.startswith("Dépassement de l'enveloppe") for l in extra))
        self.assertTrue(all(l.consumed_by_move_id == bill for l in extra))
        self.assertAlmostEqual(env_po.amount_untaxed, 0.0)  # à 0 et non négatif
        self.assertEqual(env_po.state, "cancel")  # annulé, pas supprimé ; le lien projet/fournisseur reste
        self.assertTrue(project.project_outsourcing_link_ids.filtered(lambda l: l.partner_id == env_po.partner_id))
        # avoir : la moitié de ce qui a été retiré (3 000) est remise à l'enveloppe, le BC est réactivé
        bill._restore_envelope_consumptions(0.5)
        self.assertEqual(self._net(env_po), (1500.0, 1800.0))
        self.assertEqual(env_po.state, "purchase")
        # le reste de l'avoir ne peut pas restituer plus que ce qui avait été retiré
        bill._restore_envelope_consumptions(1.0)
        self.assertEqual(self._net(env_po), (3000.0, 3600.0))
        bill._restore_envelope_consumptions(1.0)
        self.assertEqual(self._net(env_po), (3000.0, 3600.0))

    def test_envelope_hidden_for_intellectual_supplier(self):
        project, env_po = self._setup_envelope()
        link = project.project_outsourcing_link_ids.create(
            {"project_id": project.id, "partner_id": self.supplier.id, "link_type": "outsourcing"}
        )
        self._make_po([("Prestation", 1, 800.0)], project=project)
        bill = self._make_bill([("Prestation facturée", 1, 800.0)], project=project)
        wiz = self._wizard(bill, project=project)
        self.assertFalse(wiz.allowed_envelope_line_ids)  # fournisseur de type « sous-traitance » : sélection masquée
        self.assertFalse(wiz.envelope_line_id)
        # même fournisseur, type « autres » : l'enveloppe est proposée et présélectionnée
        link.link_type = "other"
        wiz2 = self._wizard(bill, project=project)
        self.assertEqual(wiz2.allowed_envelope_line_ids, env_po.order_line)
        self.assertEqual(wiz2.envelope_line_id, env_po.order_line)
        wiz2.action_associate()
        # la revente transférée suit la ligne de BC existante qui porte la facture
        self.assertAlmostEqual(env_po.amount_untaxed, 2200.0)
        self.assertAlmostEqual(bill.invoice_line_ids.purchase_line_id.reselling_subtotal, 800.0 * 1.2 + 960.0)

    def test_envelope_hidden_when_supplier_is_the_envelope_partner(self):
        project, env_po = self._setup_envelope()
        bill = self._make_bill([("Frais", 1, 100.0)], project=project, analytic=False)
        bill.partner_id = env_po.partner_id
        wiz = self._wizard(bill, project=project)
        self.assertFalse(wiz.allowed_envelope_line_ids)

    def test_envelope_restored_by_credit_note(self):
        project, env_po = self._setup_envelope()
        bill, wiz = self._create_order_wizard(project, 1200.0)
        wiz.action_associate()
        self.assertAlmostEqual(env_po.amount_untaxed, 1800.0)
        bill.action_post()
        reversal = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=bill.ids)
            .create({"journal_id": bill.journal_id.id, "reason": "Avoir test"})
        )
        refund = self.env["account.move"].browse(reversal.refund_moves()["res_id"])
        self.assertEqual(refund.move_type, "in_refund")
        refund.action_post()
        self.assertEqual(self._net(env_po), (3000.0, 3600.0))

    def test_existing_envelope_lines_are_recomputed_when_partner_is_configured(self):
        """Un BC déjà consommé (ligne « Consommé par… » existante) est recalculé quand on désigne le fournisseur."""
        envelope_partner = self.env["res.partner"].create({"name": "Frais divers existant", "is_company": True})
        project = self.env["project.project"].create({"name": "Projet existant", "partner_id": self.customer.id})
        project.project_outsourcing_link_ids = [Command.create({"partner_id": envelope_partner.id, "link_type": "other"})]

        consuming_bill = self._make_bill([("Facture réelle", 1, 500.0)])

        def line(name, price, bill=None):
            return Command.create(
                {
                    "product_id": self.product.id,
                    "name": name,
                    "product_qty": 1,
                    "price_unit": price,
                    "taxes_id": [Command.clear()],
                    "analytic_distribution": self._analytic(project),
                    "consumed_by_move_id": bill.id if bill else False,
                }
            )

        po = self.env["purchase.order"].create(
            {
                "partner_id": envelope_partner.id,
                "order_line": [line("Frais divers", 2000.0), line("Libellé quelconque", -500.0, consuming_bill)],
            }
        )
        po.button_confirm()
        positive, trace = po.order_line
        self.assertEqual((positive.qty_to_invoice, trace.qty_to_invoice), (1.0, 1.0))  # avant le réglage
        self.company.expense_envelope_partner_id = envelope_partner
        self.assertEqual((positive.qty_to_invoice, trace.qty_to_invoice), (0.0, 0.0))
        self.assertEqual(positive.invoice_status, "no")
        # le fournisseur n'est plus désigné : la quantité à facturer est rétablie
        self.company.expense_envelope_partner_id = False
        self.assertEqual((positive.qty_to_invoice, trace.qty_to_invoice), (1.0, 1.0))

    # ------------------------------------------------------------------ facture sans projet : suggestions
    def _open_wizard(self, bill):
        action = bill.action_open_bill_po_reconcile()
        return self.env["bill.po.reconcile.wizard"].browse(action["res_id"])

    def test_suggestions_when_project_unknown(self):
        po1 = self._make_po([("Plaquettes", 1, 2340.0)], project=self.project)
        po2a = self._make_po([("Affiches", 1, 1500.0)], project=self.project_b)
        po2b = self._make_po([("Flyers", 1, 840.0)], project=self.project_b)
        bill = self._make_bill([("Impression", 1, 2340.0)], analytic=False)
        bill.ref = "Commande %s" % po1.name
        wiz = self._open_wizard(bill)
        self.assertFalse(wiz.project_ids)
        suggestions = wiz.suggestion_ids
        self.assertEqual(len(suggestions), 3)
        first = suggestions[0]  # classée par pertinence
        self.assertEqual((first.project_id, first.order_id), (self.project, po1))
        self.assertIn("montant identique", first.reasons)
        self.assertIn("nom du BC dans la référence", first.reasons)
        self.assertTrue(first.selected)
        project_b_lines = suggestions.filtered(lambda s: s.project_id == self.project_b)
        self.assertEqual(project_b_lines.order_id, po2a | po2b)
        self.assertTrue(all("combinaison" in s.reasons and s.selected for s in project_b_lines))
        # des BC de deux projets cochés : refusé
        with self.assertRaises(UserError):
            wiz.action_apply_suggestions()
        # plusieurs BC d'un même projet : accepté, le projet et les BC sont renseignés
        suggestions.filtered(lambda s: s.project_id == self.project).selected = False
        wiz.action_apply_suggestions()
        self.assertEqual(wiz.project_ids, self.project_b)
        self.assertEqual(wiz.order_ids, po2a | po2b)
        self.assertEqual(len(wiz.po_line_ids), 2)

    def test_single_candidate_project_is_preselected(self):
        po = self._make_po([("Plaquettes", 1, 2340.0)], project=self.project)
        bill = self._make_bill([("Impression", 1, 2340.0)], analytic=False)
        wiz = self._open_wizard(bill)
        self.assertEqual(wiz.project_ids, self.project)
        self.assertEqual(wiz.order_ids, po)
        self.assertFalse(wiz.suggestion_ids)  # pas de liste quand un seul projet est possible


@tagged("post_install", "-at_install")
class TestBillPoReconcileTour(HttpCase, TestBillPoReconcile):
    """Le widget OWL du wizard, dans un vrai navigateur."""

    def test_panel_tour(self):
        po = self._make_po([("Prestation tour", 1, 500)])
        bill = self._make_bill([("Prestation tour", 1, 500)], purchase_lines=None)
        self.start_tour(
            f"/odoo/action-account.action_move_in_invoice_type/{bill.id}",
            "bill_po_reconcile_tour",
            login="admin",
        )
        self.assertTrue(po)
