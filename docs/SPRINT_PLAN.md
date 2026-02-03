# Sprint Plan 6 - Advanced Retrieval & Reranking

**ID :** PBI-006 & PBI-008  
**Objectif :** Optimiser la pertinence sémantique du moteur RAG en remplaçant HyDE par une stratégie de Fusion de Requêtes (Multi-Query) couplée à un Reranking Cohere.

## Tâches à réaliser (Lead-Dev)

### 1. Refactoring & Nettoyage
- [ ] Supprimer intégralement le code lié à `HyDEQueryTransform` et `TransformQueryEngine` dans `src/generation/rag_engine.py`.
- [ ] S'assurer que le pipeline redevient un flux "propre" avant l'injection des nouveaux composants.

### 2. Implémentation du QueryFusionRetriever (PBI-006)
- [ ] Configurer le `QueryFusionRetriever` en enveloppant le retriever vectoriel existant.
- [ ] **Paramétrage :**
    - `num_queries=3` (Utiliser `gpt-4o-mini` pour générer 2 variations + la question originale).
    - `similarity_top_k=20` (Retenir 20 candidats par sous-requête).
    - `mode="reciprocal_rerank"` (Fusion standard des rangs).
    - `use_async=True` (Pour paralléliser les 3 recherches et minimiser la latence).

### 3. Intégration de CohereRerank (PBI-008)
- [ ] Installer le plugin : `llama-index-postprocessor-cohere-rerank`.
- [ ] Configurer le `CohereRerank` en `node_postprocessor` :
    - `api_key` : Récupérée depuis les variables d'environnement.
    - `model` : `rerank-english-v3.0` (ou multilingual).
    - `top_n=5` (Filtrage final pour ne garder que les 5 meilleurs fragments pour le LLM).

### 4. Validation Observabilité (Phoenix)
- [ ] Vérifier dans l'interface Arize Phoenix que :
    1. Les 3 requêtes sont bien générées.
    2. Le nombre de Nodes passe bien de 20 (retrieval) à 5 (après reranking).
    3. Le temps total de traitement reste fluide (< 4s).

## Critères d'Acceptation (CA)
- **CA-1** : HyDE est totalement supprimé du code source.
- **CA-2** : Le système génère et exécute 3 variations de la question utilisateur.
- **CA-3** : Le Reranker de Cohere affine la sélection des Nodes, améliorant la pertinence des réponses aux questions complexes.
- **CA-4** : Les traces Phoenix confirment le bon déroulement du pipeline "Fusion -> Rerank -> Synthesize".

---
**STATUT : PRÊT POUR EXÉCUTION**
