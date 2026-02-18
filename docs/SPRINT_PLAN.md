# SPRINT PLAN N°17 : "Accuracy & Production Readiness"

**Sprint Goal** : Atteindre l'excellence académique en durcissant la fidélité du RAG (>0.85) et en automatisant les processus d'audit pour la production.

**Statut** : VALIDÉ (PO)

---

## [PBI-042] [QUALITÉ] Prompt Engineering : Durcissement des sources
**Priorité** : Haute | **Estimation** : S

**User Story** : "En tant qu'étudiant, je veux que l'IA ne cite que les informations présentes dans les thèses, afin de garantir la rigueur scientifique des réponses."
**Critères d'Acceptation (Gherkin)** :
- [ ] **Scenario 1** : Réduction des hallucinations
  - **GIVEN** Un prompt système mis à jour avec des contraintes strictes
  - **WHEN** On teste avec des questions "hors-contexte"
  - **THEN** Le score de Faithfulness (Ragas) doit être > 0.85.
- [ ] **Scenario 2** : Citation systématique
  - **GIVEN** Une réponse générée
  - **WHEN** L'utilisateur vérifie les sources
  - **THEN** Chaque affirmation doit être liée à un extrait de texte indexé.

---

## [PBI-043] [PROD] Automation de l'Audit & Export S3
**Priorité** : Haute | **Estimation** : M

**User Story** : "En tant que PO, je veux recevoir des rapports de santé hebdomadaires automatisés, afin de surveiller la dérive de qualité en production."
**Critères d'Acceptation (Gherkin)** :
- [ ] **Scenario 1** : Tâche planifiée
  - **GIVEN** Le script `scripts/audit_quality.py`
  - **WHEN** Le job est déclenché (simulation Cron)
  - **THEN** Le rapport est généré sans intervention manuelle.
- [ ] **Scenario 2** : Export MinIO
  - **GIVEN** Un rapport généré
  - **WHEN** Le script se termine
  - **THEN** Le fichier est uploadé dans le bucket `reports` de MinIO.

---

## [PBI-044] [UX/ADMIN] Dashboard de Confiance UI
**Priorité** : Moyenne | **Estimation** : S

**User Story** : "En tant qu'administrateur, je veux voir le score de fidélité global dans l'UI, afin d'assurer la transparence sur la qualité du service."
**Critères d'Acceptation (Gherkin)** :
- [ ] **Scenario 1** : Affichage sidebar
  - **GIVEN** Les dernières metrics calculées
  - **WHEN** On ouvre l'interface admin de Chainlit
  - **THEN** Un badge "Confiance" affiche le score moyen de Faithfulness.

---

## [PBI-045] [TECH] Migration Phoenix Prod & OTLP
**Priorité** : Moyenne | **Estimation** : S

**User Story** : "En tant que DevOps, je veux une connexion stable vers Phoenix, afin de ne perdre aucune trace en production."
**Critères d'Acceptation (Gherkin)** :
- [ ] **Scenario 1** : Config Env
  - **GIVEN** Les variables d'environnement OTLP
  - **WHEN** Le conteneur UI démarre
  - **THEN** La connexion vers Phoenix est établie du premier coup sans erreur "Refused".

---

## [PBI-046] [TECH] Housekeeping & Structure des Fichiers
**Priorité** : Basse | **Estimation** : S

**User Story** : "En tant que nouveau développeur, je veux une structure de projet claire et sans fichiers parasites, afin de comprendre immédiatement l'organisation du code."
**Critères d'Acceptation (Gherkin)** :
- [ ] **Scenario 1** : Nettoyage racine
  - **GIVEN** Les fichiers à la racine du projet
  - **WHEN** On déplace les scripts utilitaires vers `/scripts` ou `/tools`
  - **THEN** Seuls les fichiers de configuration essentiels (`requirements.txt`, `docker-compose.yml`, etc.) restent à la racine.
- [ ] **Scenario 2** : Purge du stockage
  - **GIVEN** Le dossier `/storage`
  - **WHEN** On supprime les répertoires `test_*` et les collections obsolètes
  - **THEN** Seul le stockage persistant de production (Qdrant/MinIO) est conservé.
- [ ] **Scenario 3** : Suppression junk
  - **GIVEN** Le dossier `invalid_path` ou autres dossiers vides
  - **WHEN** On lance le script de nettoyage
  - **THEN** Ces dossiers n'existent plus.

---

## [PBI-047] [QUALITÉ] Dataset de Vérité (LLM-Generated Ground Truth)
**Priorité** : Haute | **Estimation** : M

**User Story** : "En tant que PO, je veux utiliser un LLM pour générer un dataset de questions/réponses à partir des documents réels, afin de disposer d'un référentiel de 'vérité terrain' (Ground Truth) pour des tests de régression automatisés."
**Critères d'Acceptation (Gherkin)** :
- [ ] **Scenario 1** : Génération automatisée
  - **GIVEN** Un échantillon de 50 nœuds (extraits) issus des thèses réelles
  - **WHEN** On utilise le `RagDatasetGenerator` pour extraire des couples Q/A
  - **THEN** Un fichier `data/ground_truth.json` est produit contenant l'extrait source et la réponse "idéale".
- [ ] **Scenario 2** : Évaluation croisée
  - **GIVEN** Le dataset de vérité généré
  - **WHEN** On lance le moteur RAG sur ces questions
  - **THEN** On calcule le score de `Context Precision` et `Answer Semantic Similarity` par rapport à la vérité terrain.

---

## 🏛️ JOURNAL DES DÉCISIONS (Sprint 17)
- **DÉCISION 17.1** : On sacrifie un peu de "créativité" du LLM au profit d'une fidélité stricte au texte source.
- **DÉCISION 17.2** : L'audit automatisé utilisera un échantillonnage de 10% des requêtes pour optimiser les coûts.

---
**PLANNING VALIDÉ. À TOI LEAD-DEV.**
