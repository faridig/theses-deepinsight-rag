# Product Backlog - Theses-DeepInsight RAG

# ⚙️ CONFIGURATION TECHNIQUE
- **Langage** : Python 3.11+
- **Framework RAG** : LlamaIndex
- **Observabilité** : Arize Phoenix
- **Évaluation** : Ragas
- **Modèles LLM** : GPT-4o-mini (Génération), Cohere v3 (Reranking)
- **Base de données Vectorielle** : ChromaDB

Ce backlog centralise l'ensemble des fonctionnalités et tâches techniques nécessaires au succès du projet.

## Sprints & Priorités

| ID | Titre | Description | État | Priorité |
| :--- | :--- | :--- | :--- | :--- |
| **PBI-000** | **Sprint 0 : Infrastructure & CI/CD** | Initialisation de l'environnement technique, Git, venv et CI/CD. | DONE | CRITIQUE |
| **PBI-001** | **Connecteur theses.fr** | Extraction des métadonnées et fichiers via l'API theses.fr. | DONE | HAUTE |
| **PBI-002** | **Ingestion & Parsing PDF** | Parsing structuré des thèses avec LlamaIndex (LlamaParse). | DONE | HAUTE |
| **PBI-003** | **Indexation Vectorielle** | Stockage sémantique avec filtrage par métadonnées. | DONE | MOYENNE |
| **PBI-004** | **Moteur de Réponse RAG** | Pipeline de génération (Query Engine) avec LLM. | DONE | MOYENNE |
| **PBI-005** | **Évaluation & Observabilité** | Implémentation d'Arize Phoenix pour le monitoring et la traçabilité. | DONE | CRITIQUE |
| **PBI-006** | **Multi-Query Retrieval** | Génération de 3 variations de requête pour élargir la recherche sémantique. | DONE | HAUTE |
| **PBI-008** | **Reranking & High Top-K** | Passage à top_k=20 et intégration d'un Reranker (Cohere) pour affiner la pertinence. | DONE | HAUTE |
| **PBI-010** | **Recherche Hybride (BM25)** | Combinaison de la recherche sémantique et lexicale pour les termes techniques. | IN_PROGRESS | HAUTE |
| **PBI-009** | **Évaluation Ragas** | Mesure scientifique de la fidélité, pertinence et précision du contexte (0-1). | IN_PROGRESS | HAUTE |
| **PBI-014** | **Optimisation Reranking** | Réduction de la latence Cohere en passant top_k de 20 à 10 avec validation Ragas. | EN ATTENTE | HAUTE |
| **PBI-015** | **Diversité des Sources (Anti-Overlap)** | Filtre de déduplication pour éviter le monopole d'une seule thèse dans le contexte. | EN ATTENTE | HAUTE |
| **PBI-013** | **Nightly Audit : Évaluation sur Production** | Pipeline automatisé d'extraction et d'évaluation Ragas des traces Phoenix. | EN ATTENTE | HAUTE |
| **PBI-007** | **LlamaParse Multimodal Premium** | Extraction avancée des graphiques et tableaux via GPT-4o. | EN ATTENTE | HAUTE |

---
*Dernière mise à jour : 10/02/2026*
