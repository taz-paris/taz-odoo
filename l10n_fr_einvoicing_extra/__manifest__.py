{
    "name": "France eInvoicing: Extra Customizations",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "summary": "Extra customizations on top of l10n_fr_einvoicing and l10n_fr_ereporting",
    "author": "Aurélien Dumaine",
    "website": "https://www.dumaine.me",
    "depends": [
        "l10n_fr_einvoicing",
        "l10n_fr_ereporting",
        "l10n_fr_siret",
        "l10n_fr_einvoicing_import",
    ],
    "external_dependencies": {
        "python": [
            # account_invoice_en16931 and l10n_fr_ereporting were updated
            # (2026-09-29) to the data_dict format required by factur-x>=7.0
            # (generate_cii_xml() expects pre-nested "BG-*" keys). Older
            # factur-x/pyfrctc raise "KeyError: 'BG-4'" with this code.
            "pyfrctc>=0.23",
            "factur-x>=7.3",
        ]
    },
    "data": [
        "views/res_partner.xml",
    ],
    "installable": True,
}
