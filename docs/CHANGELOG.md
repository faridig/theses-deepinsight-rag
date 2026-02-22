# Changelog - Theses-DeepInsight RAG

## [1.11.0] - 2026-02-21
### Ajouté
- **Sprint 20 : Cockpit Control Plane & Silence UX (PBI-070)**
    - Migration complète de la logique d'administration et de gouvernance vers une application Streamlit dédiée (Control Plane).
    - Déploiement d'un "Health Pulse" visuel pour le monitoring live de Qdrant, MinIO et Arize Phoenix.
    - Orchestration asynchrone des tâches d'ingestion, de synchronisation S3 et de purge via `subprocess.Popen`.
    - Application du concept "Silence UX" sur Chainlit : suppression des widgets admin, simplification de l'authentification et focalisation exclusive sur la recherche.
    - Conteneurisation du Cockpit (`Dockerfile.cockpit`) et intégration multi-services dans `docker-compose.yml`.

## 💡 LEÇONS APPRISES
- **Découplage UI (Streamlit vs Chainlit)** : L'utilisation de Streamlit pour le Control Plane offre une liberté de design et une gestion des états (widgets complexes, graphiques Plotly) bien supérieure à Chainlit pour les besoins d'administration.
- **Asynchronisme par Processus** : Le déport des tâches lourdes dans des processus séparés via `subprocess` dans Streamlit permet de garder une interface fluide sans complexité excessive de gestion de threads partagés.
- **Minimalisme UX** : Réduire l'interface Chainlit à sa fonction primaire (le chat) améliore la clarté pour l'utilisateur final et réduit les risques d'erreurs de manipulation sur les données sensibles.
- **Homogénéité Docker** : Maintenir des images Docker distinctes pour l'UI et le Cockpit facilite la scalabilité et permet des cycles de mise à jour indépendants pour les fonctions métier et admin.
- **Sélecteur Hybride & Gouvernance** : L'implémentation d'un pattern "Select or Create" dynamique est la réponse optimale pour éviter la duplication de thèmes. L'utilisation de callbacks `on_change` dans Streamlit est impérative pour garantir que la prévisualisation des données reste cohérente avec les paramètres sélectionnés.
- **Sourcing Éclairé** : L'ajout d'une étape de prévisualisation (Sourcing Check) avant l'ingestion massive permet d'éviter la pollution de l'index vectoriel par des documents hors-sujet, renforçant la fiabilité du RAG dès la source.

## [1.10.0] - 2026-02-20
### Ajouté
- **Sprint 19 : Cockpit Governance UI (PBI-051, 052, 053, 054, 055)**
    - Migration complète du cockpit d'administration vers une interface graphique sécurisée dans Chainlit.
    - **PBI-051** : Authentification Admin sécurisée et profils de chat restreints.
    - **PBI-052** : Dashboard "Pouls" pour le monitoring temps réel (Qdrant, MinIO, Phoenix).
    - **PBI-053** : Visualisation historique de la qualité RAG (Plotly Charts).
    - **PBI-054** : Orchestration interactive des tâches d'ingestion et d'audit via l'UI.
    - **PBI-054 Scenario 2** : Gestion native des uploads PDF avec dédoublonnage SHA-256 vers MinIO.
    - **PBI-055** : Moniteur de coûts OpenAI et statistiques de collections Qdrant.
    - **PBI-055 Flexibilité** : Sélection dynamique du thème partagée entre les modes User et Admin.

## 💡 LEÇONS APPRISES
- **Sécurité Chainlit** : L'activation de l'authentification nécessite impérativement un `CHAINLIT_AUTH_SECRET`. Son absence est un point de blocage critique pour le déploiement.
- **Dédoublonnage proactif** : L'intégration du hash SHA-256 lors de l'upload admin permet d'éviter la saturation inutile du stockage S3 (MinIO) dès la source.
- **Orchestration Asynchrone** : L'utilisation de `subprocess.Popen` pour les tâches lourdes (Audit/Ingestion) est vitale pour ne pas bloquer l'Event Loop de Chainlit et préserver la réactivité de l'UI.
- **Health Pulse & Résilience** : L'implémentation d'un "Health Pulse" dynamique permet de détecter les pannes d'infrastructure (Qdrant/MinIO) AVANT que l'utilisateur ne rencontre une erreur, améliorant drastiquement la perception de fiabilité du système.
- **Isolation Thématique** : La structuration par silos (collections Qdrant dédiées) facilite la maintenance et la suppression propre d'un domaine d'étude sans affecter le reste de l'index.

## [1.9.0] - 2026-02-20
### Ajouté
- **Sprint 18 : Gouvernance Admin & Silence UX (PBI-048, 049, 050)**
    - Isolation des metrics techniques dans un Cockpit Admin dédié (`scripts/admin_cockpit.py`).
    - Silençage complet de l'interface utilisateur (suppression des dashboards de confiance perturbateurs).
    - Refonte de la hiérarchie des rapports d'audit (`docs/AUDITS/YYYY-MM-DD/`).
    - Durcissement du "Silence Technique" (filtrage des logs `llama_index`, `phoenix`, `openai`).
    - Correction de la persistance de l'UX lors des changements de thèmes.

## 💡 LEÇONS APPRISES
- **Silençage des Logs** : L'utilisation de `logging.getLogger("...").setLevel(logging.ERROR)` est indispensable pour maintenir un cockpit d'administration lisible face à des librairies verbeuses (LlamaIndex, Phoenix).
- **Hiérarchie de Stockage** : La structuration temporelle des audits facilite le versioning et la récupération automatique des données par les outils de dashboarding sans collision de fichiers.
- **Expérience Utilisateur (UX)** : L'utilisateur final n'a pas besoin de preuves de fidélité mathématiques à chaque message ; la confiance doit être gérée par le monitoring interne plutôt que par l'exposition brute de metrics complexes.

## [1.8.0] - 2026-02-18
### Ajouté
- **Sprint 17 : Excellence Académique & Robustesse (PBI-042, 043, 045, 046, 047)**
    - Durcissement des prompts système pour garantir une fidélité (>0.85) aux sources.
    - Automation des audits de qualité avec export automatique des rapports vers le stockage S3 (MinIO).
    - Génération d'un dataset de vérité (Ground Truth) automatisée à partir des documents réels.
    - Refactoring complet de la structure du projet (nettoyage de la racine, purge du stockage de test).
    - Stabilisation de l'observabilité (OTLP Phoenix) pour les environnements de production.
    - Prototype du Dashboard de Confiance UI (ayant conduit à la décision de découplage Admin/User).

## 💡 LEÇONS APPRISES
- **Fidélité vs Créativité** : Un durcissement excessif du prompt peut limiter la fluidité de la réponse. Le compromis trouvé privilégie la citation exacte au détriment de la synthèse trop libre.
- **Dette de Structure** : Les sprints rapides accumulent des fichiers parasites à la racine. Une phase de "Housekeeping" périodique est indispensable pour maintenir la maintenabilité du projet.
- **Séparation des Préoccupations (Admin/UI)** : Les metrics techniques (Faithfulness, Latence) perturbent l'utilisateur final. Elles doivent être isolées dans un cockpit d'administration dédié.

## [1.7.0] - 2026-02-18
### Ajouté
- **Sprint 16 : Performance d'Ingestion Massive & Audit Holistique (PBI-024, 025, 026, 027, 028)**
    - Nouveau script `scripts/ingest_theme.py` pour l'ingestion thématique automatisée à grande échelle.
    - Script de simulation de trafic `scripts/simulate_traffic.py` combinant questions synthétiques et manuelles.
    - Audit de qualité enrichi avec analyse de latence granulaire par étape (LLM, Embedding, Retriever).
    - Robustesse accrue de l'extraction des traces Phoenix pour les évaluations Ragas.
    - Nettoyage de la pollution console via une gestion fine des niveaux de log des dépendances.

## 💡 LEÇONS APPRISES
- **Instrumentation Phoenix/Ragas** : La récupération des traces Phoenix pour l'évaluation Ragas nécessite une sélection précise des spans de type `CHAIN` et un filtrage des entrées/sorties non textuelles (JSON) pour éviter les erreurs de parsing.
- **Analyse de Latence Holistique** : L'intégration de l'analyse de latence par étape (`EMBEDDING`, `LLM`, `RERANKER`) directement dans le rapport d'audit permet d'identifier immédiatement les goulots d'étranglement sans outils externes.
- **Simulation de Trafic Mixte** : Combiner des questions synthétiques (générées à partir des nœuds Qdrant via LLM) et des questions manuelles "gold standard" offre une couverture de test plus représentative du comportement utilisateur réel.

## [1.6.0] - 2026-02-17
### Ajouté
- **Sprint 15 : Raffinement UI & Dynamisme Qdrant (PBI-035, 036, 037, 038)**
    - Mapping dynamique des thèmes via `VectorService.list_collections()` avec filtrage technique.
    - Sélecteur de domaine intelligent dans la barre latérale Chainlit avec gestion de fallback.
    - Indicateurs de volume de collection (points indexés) affichés au démarrage et au changement de thème.
    - Messages d'alerte explicites pour les collections vides ou inaccessibles.
    - Nettoyage intégral des dépendances aux données de test (`sample.pdf`, `data/test`) dans le code de production.
    - Optimisation de la structure `cl.ChatSettings` pour une séparation propre entre widgets et éléments d'affichage.

## 💡 LEÇONS APPRISES
- **Détection Dynamique Qdrant** : L'utilisation de `client.get_collections()` nécessite un filtrage rigoureux (Regex ou préfixe) pour éviter de polluer l'UI avec des collections de test ou des snapshots persistants.
- **Récupération des Stats (PBI-037)** : La propriété `points_count` de `get_collection` peut varier ou être `None` selon l'état d'indexation (optimisation en cours). Utiliser `getattr(info, "points_count", 0)` garantit la robustesse du code UI.
- **UX Chainlit** : Ne pas mélanger `cl.ChatSettings` (widgets interactifs) et `cl.Text.send()` (éléments d'affichage) au démarrage permet de garder une barre latérale claire et réactive.

## [1.5.0] - 2026-02-16
### Ajouté
- **Sprint 14 : Visualisation & Auto-Évaluation (PBI-030, 031, 032, 033, 034)**
    - Génération de datasets de test synthétiques via LlamaIndex (`scripts/generate_synthetic_data.py`).
    - Interface utilisateur conversationnelle avec **Chainlit** (`main_ui.py`).
    - Visualisation du raisonnement (Chain-of-Thought) et affichage des sources.
    - Tableau de bord de qualité intégré avec les scores **Ragas** et les traces **Arize Phoenix**.
    - Boucle de feedback humain (thumbs up/down) stockée dans Phoenix.
    - Conteneurisation de l'UI Chainlit (`Dockerfile.ui`) et intégration `docker-compose.yml`.

## 💡 LEÇONS APPRISES
- **Stabilité de Chainlit/Docker** : Le montage des volumes locaux (`/app`) dans Docker peut causer des problèmes de permission avec Phoenix si les dossiers de traces ne sont pas pré-existants. Toujours s'assurer que les répertoires de logs/données sont initialisés avec les bons droits.
- **Ragas Synthetic Generation** : La génération native de LlamaIndex est plus simple à intégrer pour la diversité thématique que le wrapper Ragas externe, mais nécessite un post-traitement pour correspondre au format attendu par les scripts d'audit.
- **Incompatibilité Ragas/OpenAIEmbeddings** (Sprint 13) : Résolue par l'utilisation de wrappers standardisés.

## [1.4.0] - 2026-02-15
### Ajouté
- **Sprint 13 : Durcissement & Audit (PBI-022, 013)**
    - Migration vers le protocole **gRPC** (port 6334) pour Qdrant.
    - Activation de la **Scalar Quantization (Int8)** et du stockage **On-Disk** pour les vecteurs.
    - Script `scripts/audit_quality.py` pour l'évaluation automatique via **Ragas**.
    - Intégration des scores de qualité (`faithfulness`, `relevancy`) dans **Arize Phoenix**.
    - Génération de rapports d'audit automatiques dans `docs/AUDITS/`.

## 💡 LEÇONS APPRISES
- **Incompatibilité Ragas/OpenAIEmbeddings** : La version actuelle de `ragas` attend une méthode `embed_query` spécifique. Pour le PBI-030 (Générateur synthétique), il faudra wrapper l'embedding LlamaIndex dans `langchain_openai.OpenAIEmbeddings` pour obtenir des scores non nuls.
- **Optimisation Qdrant** : L'activation de `on_disk=True` sur les vecteurs est immédiate mais nécessite une surveillance de la latence IO lors des premières recherches massives.

## [1.3.0] - 2026-02-14
### Ajouté
- **Sprint 12 : Qualité de Données & Hygiène (PBI-026, 027, 028)**
    - Enrichment des métadonnées (`year`, `university`) pour chaque document indexé via API theses.fr.
    - `PDFValidator` proactif pour garantir l'intégrité et la taille minimale (10Ko) des fichiers.
    - Script `scripts/cleanup_infra.py` pour la maintenance des buckets S3 et du stockage local.
    - Système de **Dédoublonnage SHA-256** (Stockage unique par contenu PDF).
    - Commande `python manage.py health` pour le monitoring de la santé du système.
    - Réduction du bruit technique via la configuration du logger `httpx`.
    - Système de mise en quarantaine pour les PDF suspects ou corrompus.

## [1.2.0] - 2026-02-13
### Ajouté
- **Sprint 11 : Architecture Multi-Thèmes & Ingestion Massive (PBI-023, 024, 025)**
    - Isolation des domaines via une architecture multi-collections Qdrant.
    - Pipeline d'ingestion asynchrone haute performance (`IngestionPipeline`).
    - Ingesteur thématique dynamique pour theses.fr avec support de la pagination.

## [1.1.0] - 2026-02-11
### Ajouté
- **Sprint 10 : Industrialisation & Performance (PBI-019, 020, 021)**
    - Parallélisation asynchrone des recherches (réduction de la latence de 9s à < 3s).
    - Mise en place de l'infrastructure Docker avec MinIO et Qdrant.
    - Abstraction complète du stockage via l'API S3 (MinIO local).

## [1.0.0] - 2026-02-11
### Ajouté
- **Sprint 9 : Migration Docling GPU & Souveraineté (PBI-016, 017, 018)**
    - Parsing 100% local avec Docling.
    - Accélération GPU CUDA (8Go VRAM).
    - Maintien des scores Ragas.

## [0.9.0] - 2026-02-10
### Ajouté
- **Sprint 8 : Efficacité & Diversité (PBI-014, 015)**
    - Optimisation Cohere et filtre anti-overlap.

## [0.8.0] - 2026-02-10
### Ajouté
- **Sprint 7 : Hybride & Ragas (PBI-010, 009)**
    - BM25 et framework d'évaluation scientifique.
