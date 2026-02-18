# Changelog - Theses-DeepInsight RAG

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
