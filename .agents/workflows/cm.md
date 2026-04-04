---
description: Proposer un message de commit détaillé (pédagogique, sans guillemets doubles)
model: gemini-3-flash
---

// turbo
1. Exécuter la commande `git status && git diff --unified=0 > .agents/workflow_cm_diff.patch` (en mode synchrone).
2. Utiliser obligatoirement l'outil `view_file` pour lire `.agents/workflow_cm_diff.patch`. Celui-ci est déjà ignoré par `.gitignore`.
3. Analyser les modifications pour identifier les impacts métier (modèles, vues, correctifs, évolutions).
4. Rédiger un message de commit détaillé et pédagogique en français, en suivant les conventions Odoo (TAG, nom du module, résumé détaillé).
5. S'assurer que le message de commit NE contient AUCUN guillemet double ("). Les apostrophes (') sont en revanche autorisées.
6. Dans votre réponse finale, COMMENCEZ par afficher la liste des fichiers qui ont été modifiés (basée sur le git status).
7. Étant donné que la commande proposée utilisera `git commit -am`, les fichiers *modifiés* mais non indexés seront pris en compte automatiquement. **En revanche**, si le `git status` (à l'étape 1) a révélé qu'il y a des fichiers **entièrement nouveaux et non suivis (Untracked files)**, affichez une **alerte claire** qui liste explicitement ces nouveaux fichiers. Rappelez-lui qu'il doit exécuter `git add` spécifiquement sur ces fichiers *avant* de lancer la commande.
8. ENFIN, formater le résultat de la proposition de message sous la forme d'une commande `git commit -am "..."` à l'intérieur d'un "bloc de code" Markdown pour qu'un bouton de copie apparaisse automatiquement.