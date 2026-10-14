import logging

logger = logging.getLogger(__name__)

# property_payment_bank_account (taz-common) is being replaced by the standard
# property_inbound_payment_method_line_id (account module) + account_payment_base_oca.
# This migrates existing data so that _compute_partner_bank_id in
# account_payment_base_oca picks the same bank account as the old override
# in project_accounting/models/account_move.py did, before that override is
# removed.
#
# Both fields are company_dependent and stored as a jsonb column directly on
# res_partner (not through ir_property). We write that jsonb column directly
# with raw SQL instead of going through env['res.partner'].write(): on this
# database (~3000 partners), the ORM write triggers an extremely expensive
# recompute cascade (observed: still not finished after 19+ minutes of CPU
# time for a single company), while the direct SQL update of the same jsonb
# structure Odoo itself uses completes in about 1 second and is read back
# correctly through the ORM afterwards.
#
# account_payment_base_oca adds a "selectable" boolean on
# account.payment.method.line and restricts the domain of
# property_inbound_payment_method_line_id (and the outbound equivalent) to
# selectable=True lines. It defaults to False, so every payment method line
# we actually point partners to here must be flagged selectable=True,
# otherwise the dropdown for that field is empty in the partner form.


def _mark_selectable(cr, line_id):
    cr.execute(
        "UPDATE account_payment_method_line SET selectable = true WHERE id = %s"
        " AND selectable IS DISTINCT FROM true",
        (line_id,),
    )


def migrate(cr, version):
    cr.execute("SELECT id FROM res_company")
    company_ids = [row[0] for row in cr.fetchall()]

    total_updated = 0
    total_missing_line = 0
    for company_id in company_ids:
        cr.execute(
            """
            SELECT id, (property_payment_bank_account->>%s)::integer AS bank_id
            FROM res_partner
            WHERE property_payment_bank_account ? %s
            """,
            (str(company_id), str(company_id)),
        )
        rows = cr.fetchall()
        if not rows:
            continue
        by_bank = {}
        for partner_id, bank_id in rows:
            by_bank.setdefault(bank_id, []).append(partner_id)
        for bank_id, partner_ids in by_bank.items():
            cr.execute(
                """
                SELECT pml.id
                FROM account_payment_method_line pml
                JOIN account_payment_method pm ON pm.id = pml.payment_method_id
                JOIN account_journal j ON j.id = pml.journal_id
                WHERE j.company_id = %s
                  AND pm.payment_type = 'inbound'
                  AND j.bank_account_id = %s
                LIMIT 1
                """,
                (company_id, bank_id),
            )
            line_row = cr.fetchone()
            if not line_row:
                logger.warning(
                    "No inbound payment method line found for company %s and "
                    "bank account %s: %d partner(s) left unmigrated (%s)",
                    company_id,
                    bank_id,
                    len(partner_ids),
                    partner_ids,
                )
                total_missing_line += len(partner_ids)
                continue
            line_id = line_row[0]
            _mark_selectable(cr, line_id)
            cr.execute(
                """
                UPDATE res_partner
                SET property_inbound_payment_method_line_id = jsonb_set(
                    coalesce(property_inbound_payment_method_line_id, '{}'::jsonb),
                    %s::text[], %s::jsonb
                )
                WHERE id = ANY(%s)
                """,
                ([str(company_id)], str(line_id), partner_ids),
            )
            logger.info(
                "Company %s, bank account %s -> payment method line %s: "
                "%d partner(s) updated",
                company_id,
                bank_id,
                line_id,
                len(partner_ids),
            )
            total_updated += len(partner_ids)

    logger.info(
        "property_payment_bank_account -> property_inbound_payment_method_line_id "
        "migration done: %d partner(s) updated, %d left unmigrated "
        "(missing payment method line).",
        total_updated,
        total_missing_line,
    )

    _migrate_ir_default(cr)


def _migrate_ir_default(cr):
    """property_payment_bank_account can also be set as a company-wide
    default (ir.default, with no res_id) rather than per-partner: a partner
    with no explicit value still gets a bank account through that default.
    That fallback is invisible to the per-partner migration above (it only
    looks at explicit jsonb entries), so it must be replicated separately:
    one new ir.default per existing one, pointing to the matching inbound
    payment method line instead of the bank account directly.
    """
    cr.execute(
        """
        SELECT id FROM ir_model_fields
        WHERE model = 'res.partner' AND name = 'property_payment_bank_account'
        """
    )
    old_field_row = cr.fetchone()
    if not old_field_row:
        logger.warning("Field property_payment_bank_account not found, skipping"
                        " ir.default migration.")
        return
    cr.execute(
        """
        SELECT id FROM ir_model_fields
        WHERE model = 'res.partner'
          AND name = 'property_inbound_payment_method_line_id'
        """
    )
    new_field_row = cr.fetchone()
    assert new_field_row, "property_inbound_payment_method_line_id field not found"
    new_field_id = new_field_row[0]

    cr.execute(
        """
        SELECT company_id, json_value::integer
        FROM ir_default
        WHERE field_id = %s AND company_id IS NOT NULL
        """,
        (old_field_row[0],),
    )
    defaults = cr.fetchall()
    migrated = 0
    for company_id, bank_id in defaults:
        cr.execute(
            """
            SELECT pml.id
            FROM account_payment_method_line pml
            JOIN account_payment_method pm ON pm.id = pml.payment_method_id
            JOIN account_journal j ON j.id = pml.journal_id
            WHERE j.company_id = %s
              AND pm.payment_type = 'inbound'
              AND j.bank_account_id = %s
            LIMIT 1
            """,
            (company_id, bank_id),
        )
        line_row = cr.fetchone()
        if not line_row:
            logger.warning(
                "No inbound payment method line found for company %s and "
                "default bank account %s: ir.default not migrated for this "
                "company.",
                company_id,
                bank_id,
            )
            continue
        _mark_selectable(cr, line_row[0])
        cr.execute(
            """
            SELECT id FROM ir_default
            WHERE field_id = %s AND company_id = %s
            """,
            (new_field_id, company_id),
        )
        existing = cr.fetchone()
        if existing:
            cr.execute(
                "UPDATE ir_default SET json_value = %s WHERE id = %s",
                (str(line_row[0]), existing[0]),
            )
        else:
            cr.execute(
                """
                INSERT INTO ir_default (field_id, company_id, json_value)
                VALUES (%s, %s, %s)
                """,
                (new_field_id, company_id, str(line_row[0])),
            )
        migrated += 1
        logger.info(
            "ir.default for company %s: bank account %s -> payment method "
            "line %s",
            company_id,
            bank_id,
            line_row[0],
        )
    logger.info(
        "ir.default migration done: %d company default(s) migrated out of %d.",
        migrated,
        len(defaults),
    )
