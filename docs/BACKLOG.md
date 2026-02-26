# Product Backlog - Theses-DeepInsight RAG

# ⚙️ CONFIGURATION TECHNIQUE
- **Langage** : Python 3.11+
- **Framework RAG** : LlamaIndex
- **Observabilité** : Arize Phoenix
- **Évaluation** : Ragas
- **Modèles LLM** : GPT-4o-mini (Génération), Cohere v3 (Reranking)
- **Base de données Vectorielle** : Qdrant (Migration depuis ChromaDB prévue)
- **Stockage Objets** : MinIO (Compatible S3, auto-hébergé)
- **Infrastructure** : Docker Compose (Local & Cloud-Ready)

Ce backlog centralise l'ensemble des fonctionnalités et tâches techniques nécessaires pour passer d'un prototype à une plateforme industrielle multi-domaines.

## Sprints & Priorités

| ID | Titre | Description | État | Priorité |
| :--- | :--- | :--- | :--- | :--- |
| **PBI-000** | **Sprint 0 : Infra & CI/CD** | Setup initial de l'environnement. | DONE | CRITIQUE |
| **PBI-001** | **Connecteur theses.fr** | Extraction des métadonnées et fichiers. | DONE | HAUTE |
| **PBI-002** | **Ingestion & Parsing PDF** | Parsing structuré des thèses. | DONE | HAUTE |
| **PBI-003** | **Indexation Vectorielle** | Stockage sémantique initial (Chroma). | DONE | MOYENNE |
| **PBI-004** | **Moteur de Réponse RAG** | Pipeline de génération avec LLM. | DONE | MOYENNE |
| **PBI-005** | **Évaluation & Observabilité** | Arize Phoenix & Monitoring. | DONE | CRITIQUE |
| **PBI-006** | **Multi-Query Retrieval** | Variations de requête pour la recherche. | DONE | HAUTE |
| **PBI-008** | **Reranking & High Top-K** | Intégration Cohere Reranker. | DONE | HAUTE |
| **PBI-010** | **Recherche Hybride (BM25)** | Combinaison sémantique et lexicale. | DONE | HAUTE |
| **PBI-009** | **Évaluation Ragas** | Mesure scientifique de la fidélité. | DONE | HAUTE |
| **PBI-014** | **Optimisation Reranking** | Réduction latence Cohere. | DONE | HAUTE |
| **PBI-015** | **Diversité des Sources** | Filtre anti-overlap multi-thèse. | DONE | HAUTE |
| **PBI-016** | **Migration Docling GPU** | Parsing local via GPU (CUDA). | DONE | HAUTE |
| **PBI-017** | **Benchmark Qualitatif** | Comparaison Docling vs LlamaParse. | DONE | HAUTE |
| **PBI-018** | **Adaptation Filtre Diversité** | Compatibilité Docling pour le filtre. | DONE | MOYENNE |
| **PBI-019** | **Optimisation Latence (Async)** | Parallélisation via `asyncio.gather` pour Multi-Query. | DONE | HAUTE |
| **PBI-020** | **Docker-Compose Infra** | Setup MinIO & Qdrant en conteneurs (Gratuité & Portabilité). | DONE | HAUTE |
| **PBI-021** | **Abstraction S3 Storage** | Refactoring pour utiliser l'API S3 au lieu du FileSystem local. | DONE | HAUTE |
| **PBI-022** | **Migration Qdrant Production** | Bascule de ChromaDB vers Qdrant (gRPC, performance, Cloud-Ready). | DONE | MOYENNE |
| **PBI-023** | **Architecture Multi-Collections** | Gestionnaire de thèmes (Namespacing) pour l'isolation des données. | DONE | HAUTE |
| **PBI-024** | **Async Ingestion Pipeline** | Ingestion massive multi-threadée/asynchrone avec `IngestionPipeline`. | DONE | MOYENNE |
| **PBI-025** | **Ingesteur Thématique Robuste** | Script de scraping theses.fr dynamique par discipline/sujet. | DONE | MOYENNE |
| **PBI-026** | **Hygiène de l'Infrastructure** | Nettoyage des buckets MinIO inutiles et purge du stockage local `data/`. | DONE | MOYENNE |
| **PBI-027** | **Seeding Multi-Domaines & Validation PDF** | Ingestion massive de thèses avec validation d'intégrité et gestion des erreurs. | DONE | HAUTE |
| **PBI-028** | **Hygiène des Données : Dédoublonnage & Santé** | Mise en place du hashing ID pour éviter les doublons et dashboard de statut. | DONE | MOYENNE |
| **PBI-013** | **Nightly Audit Ragas** | Pipeline d'évaluation auto sur traces Phoenix réelles. | DONE | HAUTE |
| **PBI-030** | **Dataset de Test Synthétique** | Génération Q/A via `RagDatasetGenerator` (LlamaIndex). | DONE | HAUTE |
| **PBI-031** | **Interface Chainlit (MVP)** | WebApp conversationnelle avec visualisation des sources et CoT. | DONE | HAUTE |
| **PBI-032** | **Intégration Traces Phoenix** | Accès direct aux traces Arize Phoenix depuis l'interface. | DONE | MOYENNE |
| **PBI-033** | **Boucle de Feedback Humain** | Système de vote (👍/👎) Chainlit pour collecte de données. | DONE | MOYENNE |
| **PBI-034** | **Dockerisation de l'UI** | Conteneurisation de Chainlit pour déploiement complet. | DONE | BASSE |
| **PBI-035** | **Mapping Dynamique Qdrant** | Service de découverte automatique des collections/thèmes existants. | DONE | HAUTE |
| **PBI-036** | **Sélecteur de Domaine UI** | Menu interactif Chainlit pour router les questions vers le bon thème. | DONE | HAUTE |
| **PBI-037** | **Indicateurs de Volume Data** | Affichage dynamique du compteur de documents par thème dans l'UI. | DONE | MOYENNE |
| **PBI-038** | **Nettoyage Code Legacy (Sample)** | Suppression des dépendances aux fichiers PDF de test locaux. | DONE | MOYENNE |
| **PBI-039** | **Ingestion Massive & Indexation** | Ingestion de 3 thèmes complets pour test de charge. | DONE | HAUTE |
| **PBI-040** | **Simulation de Trafic & Stress Test** | Simulation de 50+ requêtes pour génération de traces. | DONE | HAUTE |
| **PBI-041** | **Rapport Performance Holistique** | Analyse Ragas + Latence sur le volume de données. | DONE | HAUTE |
| **PBI-042** | **[QUALITÉ] Prompt Engineering** | Durcissement des contraintes pour atteindre >0.85 de Faithfulness. | DONE | CRITIQUE |
| **PBI-043** | **[PROD] Automation de l'Audit** | Déclenchement périodique et export des rapports vers MinIO (S3). | DONE | HAUTE |
| **PBI-044** | **[UX/ADMIN] Dashboard de Confiance** | Affichage du score de fidélité moyen dans l'interface Chainlit. | DONE | MOYENNE |
| **PBI-045** | **[TECH] Migration Phoenix Prod** | Configuration OTLP robuste pour éviter les erreurs de connexion. | DONE | MOYENNE |
| **PBI-046** | **[TECH] Housekeeping & Structure** | Nettoyage des fichiers racine et réorganisation des dossiers de stockage. | DONE | BASSE |
| **PBI-047** | **[QUALITÉ] Dataset de Vérité (LLM-Generated)** | Génération d'un référentiel Q/A par un LLM à partir des thèses réelles. | DONE | HAUTE |
| **PBI-048** | **[UX] Nettoyage UI (Silence UX)** | Suppression des scores et metrics techniques de l'interface utilisateur. | DONE | HAUTE |
| **PBI-049** | **[ADMIN] Dashboard de Santé Dédié** | Création d'une interface admin séparée pour le suivi des metrics. | DONE | HAUTE |
| **PBI-050** | **[REPORTING] Rapports Structurés** | Formatage des rapports (PDF/MD) pour stockage et diffusion auto. | DONE | MOYENNE |
| **PBI-051** | **[ADMIN] Socle Cockpit Chainlit** | Intégration dans Chainlit, Auth sécurisée et isolation des performances. | DONE | CRITIQUE |
| **PBI-052** | **[ADMIN] Dashboard "Pouls" & Observabilité** | Monitoring santé (Qdrant/MinIO/Phoenix) and lien direct Phoenix. | DONE | HAUTE |
| **PBI-053** | **[ADMIN] Dashboard Qualité & Ragas** | Visualisation scores Fidélité/Pertinence et historique graphique. | DONE | HAUTE |
| **PBI-054** | **[ADMIN] Pilotage & Ingestion UI** | Interface de déclenchement d'ingestion/audit avec barre de progression. | DONE | HAUTE |
| **PBI-055** | **[ADMIN] Moniteur de Coûts & Thèmes** | Suivi des tokens OpenAI et statistiques détaillées des collections Qdrant. | DONE | MOYENNE |
| **PBI-056** | **[ADMIN] Gestionnaire de Thèmes Hybride** | Création/Sélection dynamique de thèmes et indexation via upload UI. | DONE | HAUTE |
| **PBI-057** | **[ADMIN] Ingestion thématique à la demande** | Scraping automatisé de theses.fr (Top 10) via mot-clé saisi dans l'UI. | DONE | HAUTE |
| **PBI-058** | **[ADMIN] Auto-Audit Qualité Post-Ingestion** | Validation immédiate de la fidélité (Faithfulness) après ajout de données. | DONE | MOYENNE |
| **PBI-061** | **[TECH] Infrastructure Résiliente** | Persistance du cache d'ingestion et de l'historique Arize Phoenix. | DONE | HAUTE |
| **PBI-062** | **[ADMIN] Gouvernance & Souveraineté** | Cycle de vie (Delete/Purge) et Re-Sync des thèmes depuis MinIO. | DONE | HAUTE |
| **PBI-070** | **[ADMIN] Cockpit Control Plane (Streamlit)** | Centralisation de la gouvernance dans une application Streamlit dédiée. | DONE | CRITIQUE |
| **PBI-071** | **[INFRA] Grand Nettoyage S3 (Housekeeping)** | Purge des buckets inutiles et migration des fichiers orphelins vers la structure cible. | DONE | CRITIQUE |
| **PBI-072** | **[INFRA] Réorganisation Thématique S3** | Migration physique des PDF du dossier `pdfs/` vers `themes/{nom_theme}/` pour plus de clarté visuelle. | DONE | HAUTE |
| **PBI-073** | **[ADMIN] Synchronisation Totale Purge UI** | Correction du bug de suppression : garantir que `delete_collection` (Qdrant) entraîne la purge physique sur MinIO. | DONE | CRITIQUE |
| **PBI-075** | **[UX/ADMIN] Guide Contextuel & Aide aux Metrics** | Intégration d'infobulles et d'une section "Interprétation" dans le Dashboard Qualité. | DONE | MOYENNE |
| **PBI-076** | **[TECH] Activation & Correction de Context Precision** | Re-câblage de `ground_truth.json` + Affichage Context Precision dans le Cockpit. | DONE | CRITIQUE |
| **PBI-077** | **[ADMIN] Sourcing Check (Prévisualisation)** | Affichage d'un tableau récapitulatif (Titres/Années) avant de déclencher l'ingestion massive. | DONE | MOYENNE |
| **PBI-078** | **[UX/ADMIN] Visualisation du Flux (Architecture View)** | Ajout d'un onglet pédagogique montrant le parcours d'une thèse (Parsing -> SLM -> Qdrant). | DONE | MOYENNE |
| **PBI-079** | **[TECH] Infra SLM Local (Ollama/vLLM)** | Intégration d'un service de LLM local (Llama 3.2) dans Docker pour les tâches asynchrones. | DONE | HAUTE |
| **PBI-080** | **[TECH] Handoff Métadonnées SLM** | Migration de `TitleExtractor` et `SummaryExtractor` vers le LLM local pour supprimer les coûts d'ingestion. | DONE | HAUTE |
| **PBI-081** | **[QUALITÉ] Durcissement Prompt & Anti-Hallucination** | Révision du System Prompt pour forcer la citation stricte et interdire les connaissances externes. | DONE | CRITIQUE |
| **PBI-082** | **[QUALITÉ] Optimisation Retrieval Hybride & Reranking** | Réglage alpha (0.7), fusion `relative_score` et seuil de score Cohere (>0.6) pour remonter la Pertinence. | DONE | CRITIQUE |
| **PBI-090** | **[ADMIN] Datasets de Vérité Thématiques** | Isolation des `ground_truth_{theme}.json` pour des tests indépendants par domaine. | IN_PROGRESS | HAUTE |
| **PBI-091** | **[ADMIN] Moteur d'Audit Dual (Trigger Mixte)** | Audit sur dataset (Lab) vs traces (Terrain). Déclenchement hybride : Automatique (Nightly) pour les tendances et Manuel (UI) pour le diagnostic. | IN_PROGRESS | HAUTE |
| **PBI-092** | **[UX/ADMIN] Vue Comparative & Benchmarking** | Tableau de bord centralisé inter-thèmes. Inclut des descriptions didactiques des modes d'audit (Auto vs Manuel). | IN_PROGRESS | CRITIQUE |
| **PBI-093** | **[UX/ADMIN] Module d'Interprétation Intelligente** | Traduction des metrics en langage naturel, conseils actionnables selon les scores et lexique hybride systématique. | IN_PROGRESS | HAUTE |

| **PBI-094** | **[UX/ADMIN] Courbes de Tendance (Timeline)** | Graphiques d'évolution historique des scores par thème pour mesurer l'impact des optimisations. | PENDING | MOYENNE |
| **PBI-095** | **[ADMIN] Traçabilité de Configuration** | Liaison automatique des scores à la version du Prompt et au modèle de LLM utilisé. | PENDING | MOYENNE |
| **PBI-096** | **[GOUVERNANCE] Certification & Seuils** | Système de badges `CERTIFIÉ` / `QUARANTAINE` selon des seuils de metrics configurables par thème. | PENDING | HAUTE |
| **PBI-097** | **[TECH] Sélecteur de Juge Hybride** | Option dans l'UI pour choisir entre GPT-4o-mini (Routine) et GPT-4o (Certification) comme juge. | PENDING | MOYENNE |

---

## 🛠️ Definition of Ready (DoR) pour les futurs tickets
Tout ticket entrant en Sprint doit comporter :
- User Story claire.
- Critères d'Acceptation (Gherkin).
- Estimation (XS à L).
- **Justification technologique (context7)** :
  - **Audit** : `EvaluationDataset.from_list()` de Ragas pour le chargement dynamique des datasets thématiques depuis des JSON.
  - **Cockpit** : `st.status` de Streamlit pour le streaming des logs `subprocess.Popen` et le suivi d'audit non-bloquant.
  - **Dataviz** : `plotly.graph_objects.Bar` avec `barmode='group'` pour la comparaison inter-thèmes des 4 metrics clés.
  - **UI** : Utilisation de `cl.ChatSettings` avec `Select` et `TextInput` pour la gestion hybride des thèmes.
  - **Data** : `SimpleDirectoryReader` couplé à `s3fs` pour l'interaction native avec MinIO (S3).
  - **Pipeline** : `IngestionPipeline` de LlamaIndex pour l'extraction de métadonnées (`TitleExtractor`) lors du sourcing.
- **Nouveauté Sprint 14** : Utilisation préférentielle des outils natifs LlamaIndex pour la génération de données.
- **Nouveauté Sprint 19** : Intégration asynchrone pour l'interface Admin afin de ne pas bloquer le thread principal Chainlit.

---
*Dernière mise à jour : 24/02/2026*