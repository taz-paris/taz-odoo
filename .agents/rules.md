# 📋 Charte du Projet et Règles de l'Agent

Dernière mise à jour : 2026-04-04

### 🏗 Environnement et Contexte
- **Framework** : Odoo 18.0 Communautaire (Community Edition).
- **OS** : VM GNU/Linux.
- **Service SystemD** : `/usr/lib/systemd/system/odoo18.service`
  - *Fichier de configuration Odoo* : `/home/ubuntu/odoo_dev_V18.conf`

### 📂 Gestion des Répertoires
- **Répertoire Odoo (Core)** : `/home/ubuntu/odoo18`
  - *Règle* : Lecture autorisée uniquement. **INTERDICTION DE MODIFIER**.
- **Répertoire Modules (Custom)** : `/home/ubuntu/taz-odoo18`
  - *Règle* : Lecture et modification autorisées. C'est ici que le code spécifique est écrit.

### 🚫 Interdictions et Limites
- **Test UI/Front** : **INTERDICTION STRICTE** d'utiliser les outils de navigation (Chrome, Chromium, Playwright) pour tester l'IHM Odoo. 
  - *Raison* : L'agent se perd dans l'interface complexe d'Odoo, ce qui entraîne une perte de temps et de crédibilité. Les tests doivent être faits manuellement par l'utilisateur ou par tests unitaires Python/JS côté code uniquement.

### 💡 Objectif Agentique
Toutes les réponses de l'IA (Antigravity) doivent être formulées en français, avec un ton pédagogique, en prenant soin de respecter les conventions Odoo (TAG, nom du module, code propre).
