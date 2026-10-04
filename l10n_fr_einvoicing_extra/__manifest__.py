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
    "external_dependencies": {"python": ["pyfrctc>=0.22"]},
    "data": [
        "views/res_partner.xml",
    ],
    "installable": True,
}
