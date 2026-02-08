# Changelog - Theses-DeepInsight RAG

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

## [0.8.0] - 2026-02-06
### Rejeté
- **Sprint 7 : Puissance de Recherche Hybride & Certification Ragas (PBI-010 & PBI-009)**
    - **CAUSE DU REJET** : Défaillance structurelle majeure. L'indexation était limitée aux 10 premières pages des PDF.
    - **INCIDENT D'INTÉGRITÉ** : Masquage du problème par l'injection de métadonnées non extraites du corps du texte.
    - **ACTION** : Réouverture des PBI concernés et lancement d'un Sprint de redressement (Sprint 8).

## [0.7.0] - 2026-02-03
### Ajouté
- **Sprint 6 : Advanced Retrieval & Reranking (PBI-006 & PBI-008)**
    - Mise en œuvre du `QueryFusionRetriever` pour une recherche Multi-Query robuste.
    - Intégration du post-processeur `CohereRerank` (modèle v3.0) pour affiner la pertinence (Top-20 vers Top-5).
    - Suppression (Refactoring) de la couche HyDE pour garantir l'adhérence aux faits scientifiques.

## [0.6.0] - 2026-02-02
### Ajouté
- **Sprint 5 : Observabilité & Traçabilité (PBI-005)**
    - Intégration d'Arize Phoenix pour le monitoring en temps réel.
    - Instrumentation complète du pipeline LlamaIndex via `set_global_handler`.
    - Analyse des latences et des coûts (tokens) par étape de requête.

## [0.5.0] - 2026-02-01
### Ajouté
- **Sprint 4 : Moteur de Réponse RAG (PBI-004)**
    - Implémentation du `RAGEngine` avec intégration de GPT-4o-mini.
    - Configuration du `MetadataReplacementPostProcessor` pour la stratégie Sentence Window.
    - Correction d'un incident d'intégrité des données (Hotfix) : bascule sur les documents réels (PDF) et purge des données de test.

## [0.4.0] - 2026-02-01
### Ajouté
- **Sprint 3 : Indexation Vectorielle (PBI-003)**
    - Intégration de ChromaDB pour le stockage persistant des vecteurs.
    - Implémentation du `VectorService` utilisant le `StorageContext` de LlamaIndex.
    - Configuration de la persistance locale dans `storage/chroma/`.

## [0.3.0] - 2026-02-01
### Ajouté
- **Sprint 2 : Ingestion & Parsing PDF (PBI-002)**
    - Intégration de LlamaParse pour le parsing de documents PDF complexes.
    - Transformation des documents en `Nodes` structurés avec gestion du contexte.
    - Ajout de métadonnées enrichies aux fragments de texte.

## [0.2.0] - 2026-02-01
### Ajouté
- **Sprint 1 : Connecteur theses.fr (PBI-001)**
    - Mise en place du connecteur d'API pour theses.fr.
    - Script de téléchargement automatique des PDFs et extraction des métadonnées.
    - Organisation des données brutes dans le dossier `data/`.

## [0.1.0] - 2026-02-01
### Ajouté
- **Sprint 0 : Infrastructure & CI/CD (PBI-000)**
    - Initialisation du dépôt Git et configuration du `.gitignore`.
    - Création de l'environnement virtuel et installation des dépendances de base (LlamaIndex, Pytest, etc.).
    - Configuration de la CI/CD via GitHub Actions (linting et tests).
    - Définition de l'arborescence standard du projet (`src/`, `tests/`, `docs/`, `data/`).
