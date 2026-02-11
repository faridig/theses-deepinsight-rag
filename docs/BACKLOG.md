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
| **PBI-019** | **Optimisation Latence (Async)** | Parallélisation via `asyncio.gather` pour Multi-Query. | EN ATTENTE | HAUTE |
| **PBI-020** | **Docker-Compose Infra** | Setup MinIO & Qdrant en conteneurs (Gratuité & Portabilité). | EN ATTENTE | HAUTE |
| **PBI-021** | **Abstraction S3 Storage** | Refactoring pour utiliser l'API S3 au lieu du FileSystem local. | EN ATTENTE | HAUTE |
| **PBI-022** | **Migration Qdrant Production** | Bascule de ChromaDB vers Qdrant (gRPC, performance, Cloud-Ready). | EN ATTENTE | MOYENNE |
| **PBI-023** | **Architecture Multi-Collections** | Gestionnaire de thèmes (Namespacing) pour l'isolation des données. | EN ATTENTE | HAUTE |
| **PBI-024** | **Async Ingestion Pipeline** | Ingestion massive multi-threadée/asynchrone avec `IngestionPipeline`. | EN ATTENTE | MOYENNE |
| **PBI-025** | **Ingesteur Thématique Robuste** | Script de scraping theses.fr dynamique par discipline/sujet. | EN ATTENTE | MOYENNE |
| **PBI-013** | **Nightly Audit Ragas** | Pipeline d'évaluation auto sur traces Phoenix réelles. | EN ATTENTE | HAUTE |

---

## 🛠️ Definition of Ready (DoR) pour les futurs tickets
Tout ticket entrant en Sprint doit comporter :
- User Story claire.
- Critères d'Acceptation (Gherkin).
- Estimation (XS à L).
- Justification technologique (context7).

---
*Dernière mise à jour : 11/02/2026*
