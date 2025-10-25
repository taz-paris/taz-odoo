from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

from datetime import datetime, timedelta
from odoo.tools import float_is_zero, float_compare, float_round

import json
import logging
_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit= "product.template"
    create_supplier_info_auto = fields.Boolean("Créer prix fournisseur auto", help="Si VRAI, lorsqu'un bon de commande fournisseur est confirmé, un objet supplierinfo est automatiquement créé pour les lignes du bon de commande fournisseur dont le produit / fournisseur n'existe pas pour la société. Ce supplier info n'est créé que s'il n'exite pas déjà 10 supplierinfo pour ce produit. Le prix associé est celui du bon de commande.")

    is_external_production = fields.Boolean("Génère de la prod externe en compta", tracking=True, help="Si VRAI, lorsque ce produit est intégré à une facture/un avoir de fournisseur, alors il sera compté comme de la production externe dans la clôture comptable")
