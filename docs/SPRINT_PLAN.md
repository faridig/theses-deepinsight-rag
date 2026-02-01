# Sprint Plan 0 - Infrastructure & CI/CD

**ID :** PBI-000  
**Objectif :** Établir une base de développement saine, sécurisée et automatisée (DevOps First).

## Tâches à réaliser (Lead-Dev)

### 1. Initialisation Git
- [ ] Initialiser le dépôt local.
- [ ] Créer un fichier `.gitignore` complet (Python standard + `.opencode`, `.env`, `__pycache__`, `venv/`).
- [ ] Créer un dépôt distant sur GitHub (si accès configuré).

### 2. Environnement de Développement
- [ ] Créer l'environnement virtuel Python (`python -m venv venv`).
- [ ] Initialiser `requirements.txt` avec les dépendances de base :
    - `llama-index`
    - `ragas`
    - `arize-phoenix`
    - `pytest`
    - `python-dotenv`

### 3. Automatisation CI/CD
- [ ] Configurer une GitHub Action (`.github/workflows/main.yml`) pour :
    - Vérification du linting (flake8 ou black).
    - Exécution des tests unitaires (pytest).

### 4. Structure du Projet
- [ ] Créer l'arborescence :
    - `src/` (code source)
    - `tests/` (tests unitaires et intégration)
    - `data/` (stockage local temporaire, ignoré par git)

## Critères d'Acceptation (CA)
- **CA-1** : `git status` ne montre aucun fichier sensible ou inutile (grâce au `.gitignore`).
- **CA-2** : L'environnement virtuel est activable et les dépendances s'installent sans erreur.
- **CA-3** : Le pipeline CI/CD se déclenche lors d'un push (si repo distant).
- **CA-4** : Aucune fonctionnalité métier (PBI-001+) n'est entamée durant ce sprint.

---
**STATUT : PRÊT POUR EXÉCUTION**
