# Changelog - Theses-DeepInsight RAG

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
