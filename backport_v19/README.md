# Backport v19

Ce module backporte le correctif suivant de la version 19/18.4 vers la version 18.0 :
[FIX] account: invoice_outstanding_credits_debits_widget badly computed
Commit: 9304d590d882d613496bde4cb48092e5970949da

## Changements
- Redéfinition du champ `invoice_has_outstanding` pour utiliser une méthode de calcul séparée.
- Mise à jour de `_compute_payments_widget_to_reconcile_info` pour inclure les factures en brouillon et optimiser le domaine de recherche.
- Ajout de la méthode `_compute_invoice_has_outstanding`.
