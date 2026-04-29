---
description: Proposer un message de commit détaillé (pédagogique, sans guillemets doubles)
model: gemini-3-flash
---

> **RÈGLE ABSOLUE SUR LES GUILLEMETS** : Le contenu du message de commit ne doit jamais contenir de guillemets doubles ("). En revanche, la commande finale DOIT obligatoirement utiliser des guillemets doubles comme délimiteurs externes : `git commit -am "..."`  — et NON des guillemets simples. Ne jamais écrire `git commit -am '...'`.
// turbo
1. Exécuter la commande `git status && git diff --unified=0 > .agents/workflow_cm_diff.patch` (en mode synchrone).
2. Utiliser obligatoirement l'outil `view_file` pour lire `.agents/workflow_cm_diff.patch`. Celui-ci est déjà ignoré par `.gitignore`.
3. Analyser les modifications pour identifier les impacts métier (modèles, vues, correctifs, évolutions).
4. Rédiger un message de commit détaillé et pédagogique en français, en suivant les conventions Odoo (TAG, nom du module, résumé détaillé).
5. **GUILLEMETS — deux règles distinctes à respecter simultanément :**
   - Le **contenu** du message NE doit contenir AUCUN guillemet double ("). Remplacer par des apostrophes (') ou reformuler si nécessaire.
   - La **commande** doit OBLIGATOIREMENT utiliser des guillemets doubles comme délimiteurs : `git commit -am "..."`. Ne JAMAIS utiliser des guillemets simples comme délimiteurs externes (`git commit -am '...'` est INTERDIT).
6. Dans votre réponse finale, COMMENCEZ par afficher la liste des fichiers qui ont été modifiés (basée sur le git status).
7. Étant donné que la commande proposée utilisera `git commit -am`, les fichiers *modifiés* mais non indexés seront pris en compte automatiquement. **En revanche**, si le `git status` (à l'étape 1) a révélé qu'il y a des fichiers **entièrement nouveaux et non suivis (Untracked files)**, affichez une **alerte claire** qui liste explicitement ces nouveaux fichiers. Rappelez-lui qu'il doit exécuter `git add` spécifiquement sur ces fichiers *avant* de lancer la commande.
8. ENFIN, formater le résultat sous la forme d'une commande `git commit -am "..."` dans un bloc de code Markdown. **Vérification finale obligatoire avant de répondre** : les délimiteurs externes sont bien des guillemets doubles `"`, et aucun guillemet double n'apparaît à l'intérieur du message.