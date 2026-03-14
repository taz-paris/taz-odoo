# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.exceptions import ValidationError
from lxml import etree

class View(models.Model):
    _inherit = 'ir.ui.view'

    def _validate_tag_list(self, node, name_manager, node_info):
        # Bypass la validation des balises autorisées (field, button only)
        # On utilise node.get car js_class n'est pas un champ du modèle ir.ui.view mais un attribut XML
        if node.get('js_class') == 'list_multi_line':
            return
        return super()._validate_tag_list(node, name_manager, node_info)

    @api.constrains('arch_db')
    def _check_xml(self):
        for view in self:
            # On parse l'arch pour vérifier la présence de js_class sur le tag racine
            # car js_class n'est pas un champ de l'objet ir.ui.view
            arch_node = etree.fromstring(view.arch or '<data/>')
            if arch_node.get('js_class') == 'list_multi_line':
                # Si c'est notre vue, on valide tout SAUF le RNG (qui bloque sur <group>)
                try:
                    view._validate_view(view._get_combined_arch(), view.model)
                except Exception as e:
                    raise ValidationError(f"Erreur de validation multi-ligne : {e}")
                continue
            
            # Sinon validation standard
            super(View, view)._check_xml()
        return True
