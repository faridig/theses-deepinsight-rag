# SPRINT PLAN N°20 : "Knowledge Autonomy & Resilience"

**Sprint Goal** : Donner une autonomie totale et résiliente à l'administrateur pour piloter le cycle de vie des données (Ingestion, Audit, Purge) via une interface robuste et conforme à la charte "DeepInsight".

**Statut** : VALIDÉ (Ready for Dev)

---

## [PBI-061] [TECH] Infrastructure Résiliente (Persistence)
**Priorité** : Haute | **Estimation** : S

**User Story** : "En tant que Développeur, je veux que les données critiques (Cache, Phoenix, Docs) soient persistées via des volumes Docker, afin d'éviter toute perte de données lors du redémarrage des services."
**Critères d'Acceptation** :
- [ ] Le `docker-compose.yml` inclut des volumes pour Arize Phoenix (DB locale).
- [ ] Le dossier `./storage` est monté dans le conteneur `ui` pour conserver l'`IngestionCache`.
- [ ] Les chemins de stockage sont unifiés et testés après un `docker compose restart`.

---

## [PBI-056] [ADMIN] Gestionnaire de Thèmes Hybride & Multi-Upload
**Priorité** : Haute | **Estimation** : M

**User Story** : "En tant qu'Administrateur, je veux pouvoir sélectionner un thème existant ou en créer un nouveau lors de l'upload d'un ou plusieurs PDF, afin de classer mes documents sans friction technique."
**Spécifications UX** : Combo-box (Select+Input), Radius 8px, Bleu #2563EB.
**Critères d'Acceptation** :
- [ ] Sélection/Saisie hybride via `cl.ChatSettings`.
- [ ] Ingestion Batch utilisant `SimpleDirectoryReader(fs=s3fs)` vers MinIO.

---

## [PBI-057] [ADMIN] Ingestion thématique à la demande (theses.fr)
**Priorité** : Haute | **Estimation** : M

**User Story** : "En tant qu'Administrateur, je veux déclencher l'ingestion d'un nouveau domaine depuis theses.fr via mot-clé, afin d'étendre rapidement la base RAG."
**Critères d'Acceptation** :
- [ ] Ingestion du Top 10 via `IngestionPipeline` + `TitleExtractor`.
- [ ] Feedback temps réel via `cl.TaskList`.

---

## [PBI-058] [ADMIN] Auto-Audit Qualité Post-Ingestion
**Priorité** : Moyenne | **Estimation** : S

**User Story** : "En tant qu'Administrateur, je veux un mini-audit automatique après chaque ajout de données pour vérifier la fidélité immédiate du RAG."
**Critères d'Acceptation** :
- [ ] Génération de 3 questions flash via `RagDatasetGenerator`.
- [ ] Affichage du score de Faithfulness dans l'UI Admin.

---

## [PBI-062] [ADMIN] Gouvernance Totale : Cycle de Vie & Souveraineté
**Priorité** : Haute | **Estimation** : M

**User Story** : "En tant qu'Administrateur, je veux pouvoir supprimer des thèmes et ré-indexer des données depuis MinIO, afin d'assurer la maintenance et l'évolution de ma base de connaissances."
**Critères d'Acceptation** :
- [ ] **Delete** : Bouton de suppression de collection Qdrant avec purge optionnelle des fichiers MinIO.
- [ ] **Re-Sync** : Fonction "Re-synchroniser" qui reconstruit l'index vectoriel à partir des PDF stockés dans MinIO pour un thème donné.
- [ ] **Health Pulse** : Indicateur visuel (pastille) de l'état de santé live de Qdrant, MinIO et Phoenix.

---

## 🏛️ JOURNAL DES DÉCISIONS (Sprint 20)
- **DÉCISION 20.1** : Limite Top 10 pour le scraping automatisé.
- **DÉCISION 20.2** : Dédoublonnage SHA-256 systématique.
- **DÉCISION 20.3** : Volume persistant obligatoire pour Arize Phoenix.
- **DÉCISION 20.4** : Application des tokens UX (Bleu #2563EB, Radius 8px) via Custom CSS dans Chainlit.

---
**PLANNING VALIDÉ - EN COURS D'EXÉCUTION**