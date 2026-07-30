from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo import _

import logging
_logger = logging.getLogger(__name__)


class resPartner(models.Model):
    _inherit = "res.partner"

    #contact_created_on_public_event_registration = fields.Boolean("Contact créé suite à l'inscription à un évènement", help="When a guest fill the public event registration form, if its email can't be found in any partner, a new partner is created with that boolean set True")
    event_registration_ids = fields.One2many('event.registration', 'partner_id', string="Inscriptions aux évènements", groups="event.group_event_user,event.group_event_registration_desk,event.group_event_manager")

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        """
        Correction générique du bug ORM d'Odoo sur les filtres négatifs des One2many (avec chemin).
        Transforme un `not ilike` problématique en `['!', (..., 'ilike', ...)]` qui est
        géré de manière optimale par l'ORM et inclut correctement les contacts sans inscription.

        POURQUOI ODOO NE L'A PAS GÉNÉRALISÉ NATIVEMENT ?
        1. Ambiguïté mathématique : Pour Odoo, `not ilike` sur un One2many signifie "Trouve les parents
           qui ont au moins 1 enfant qui ne correspond pas" (inclusion partielle). Ce n'est pas ce qu'on
           attend intuitivement ("Exclure les parents dont un enfant correspond").
        2. Rétrocompatibilité : Changer ce comportement globalement casserait des milliers de modules
           existants qui s'appuient sur l'inclusion partielle.
        3. Solution officielle : Odoo a créé l'opérateur `!` pour exprimer spécifiquement l'exclusion totale
           (génère un "NOT IN (sous-requête)").

        POURQUOI NE PAS CORRIGER UNIQUEMENT LE "filter_domain" DANS LA VUE XML ?
        Si on corrige uniquement le `filter_domain` de la vue XML (en y mettant le `!`), cela ne fonctionnera
        que si l'utilisateur clique sur la suggestion de la barre de recherche globale.
        Si l'utilisateur ouvre le menu "Filtres personnalisés" de l'interface et sélectionne l'opérateur
        "ne contient pas", le front-end JS enverra systématiquement un domaine avec `not ilike`.
        La surcharge de `_search` ici permet d'intercepter cette requête (et toute autre requête Python)
        à la racine pour la réécrire de manière propre et robuste avec `!`.
        """
        if domain:
            new_domain = []
            for leaf in domain:
                if isinstance(leaf, (tuple, list)) and len(leaf) == 3:
                    left, operator, right = leaf
                    if left in ('event_registration_ids.event_id', 'event_registration_ids.event_id.name') and operator in ('not ilike', 'not like', '!=', 'not in'):
                        pos_op = {
                            'not ilike': 'ilike',
                            'not like': 'like',
                            '!=': '=',
                            'not in': 'in'
                        }[operator]
                        new_domain.extend(['!', (left, pos_op, right)])
                        continue
                new_domain.append(leaf)
            domain = new_domain

        return super()._search(domain, offset=offset, limit=limit, order=order)
