# Sprint Plan 7 - Puissance de Recherche Hybride & Certification Ragas

**ID :** PBI-010 & PBI-009  
**Objectif :** Atteindre une précision chirurgicale sur les termes techniques via la recherche Hybride (Dense + Sparse) et valider la qualité du système par des métriques scientifiques Ragas.

## Tâches à réaliser (Lead-Dev)

### 1. Implémentation de la Recherche Hybride (PBI-010)
- [ ] Installer la dépendance : `rank_bm25`.
- [ ] Initialiser le `BM25Retriever` à partir du `docstore` de l'index existant.
- [ ] Configurer le `QueryFusionRetriever` pour orchestrer :
    - Le retriever vectoriel actuel (Dense).
    - Le nouveau `BM25Retriever` (Sparse).
- [ ] Utiliser le mode `reciprocal_rerank` pour la fusion des résultats.
- [ ] S'assurer que le `CohereRerank` intervient toujours en post-traitement sur les résultats fusionnés.

### 2. Mise en place du Framework d'Évaluation (PBI-009)
- [ ] Installer `ragas`.
- [ ] Créer un module `src/evaluation/evaluator.py` utilisant l'intégration native LlamaIndex.
- [ ] Configurer les 4 métriques clés : `Faithfulness`, `AnswerRelevancy`, `ContextPrecision`, `ContextRecall`.
- [ ] Développer un script de test sur un "Golden Dataset" de 10-15 questions complexes pour obtenir un score global de performance.

### 3. Intégration Phoenix
- [ ] Configurer l'export des scores Ragas vers Arize Phoenix pour visualiser la qualité des réponses directement dans les traces.

## Critères d'Acceptation (CA)
- **CA-1** : Le système remonte correctement des documents contenant des termes techniques exacts ou acronymes, même si la sémantique est floue (Grâce au BM25).
- **CA-2** : Un rapport Ragas est généré automatiquement, montrant des scores de Fidélité et de Pertinence.
- **CA-3** : Les traces Phoenix montrent la fusion des deux retrievers (Vector + BM25).
- **CA-4** : Aucun ralentissement majeur n'est constaté (< 5s pour une réponse complète hybride + rerank).

---
**STATUT : SPRINT DE QUALITÉ - PRÊT POUR EXÉCUTION**
