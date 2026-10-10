from odoo.addons.project_accounting.models.res_partner import PROTECTED_FIELD_LIST

PROTECTED_FIELD_LIST.extend([
    "fr_directory_entity_type",
    "fr_directory_name",
    "fr_directory_closed",
    "fr_directory_siren",
    "fr_directory_siret",
    "fr_directory_last_sync_date",
    "default_fr_directory_line_id",
])
