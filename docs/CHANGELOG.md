# Changelog - Theses-DeepInsight RAG

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
