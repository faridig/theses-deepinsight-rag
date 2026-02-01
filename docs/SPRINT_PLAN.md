# Sprint Plan 5 - Observabilité, Intelligence HyDE & Multimodalité

**ID :** PBI-005, PBI-006 & PBI-007  
**Objectif :** Déployer une infrastructure d'observabilité pour piloter l'optimisation du RAG (HyDE) et débloquer l'analyse multimodale des documents complexes.

## Tâches à réaliser (Lead-Dev)

### 1. Observabilité Critique (PBI-005 - PRIORITÉ 1)
- [ ] Installer `arize-phoenix` et `openinference-instrumentation-llama-index`.
- [ ] Initialiser le serveur Phoenix au démarrage de l'application (`px.launch_app()`).
- [ ] Configurer l'instrumentation globale via `set_global_handler("arize_phoenix")`.
- [ ] **CA-O :** Vérifier que chaque requête RAG génère une trace complète visible sur l'interface (Retriever -> Post-Processor -> LLM).

### 2. Optimisation HyDE (PBI-006 - PRIORITÉ 2)
- [ ] Implémenter `HyDEQueryTransform` dans le module `src/generation/rag_engine.py`.
- [ ] Envelopper le moteur de réponse dans un `TransformQueryEngine`.
- [ ] **Validation visuelle :** Utiliser Phoenix pour comparer la requête originale et la réponse hypothétique générée par HyDE.

### 3. Ingestion Multimodale Premium (PBI-007 - PRIORITÉ 3)
- [ ] Mettre à jour `src/ingestion/parser.py` pour configurer `LlamaParse` en mode Premium.
- [ ] Activer les options : `result_type="markdown"`, `use_vendor_multimodal_model=True`, `vendor_multimodal_model_name="gpt-4o"`.
- [ ] Ré-indexer une thèse contenant des tableaux denses et des schémas pour valider l'extraction de données structurées.

## Critères d'Acceptation (CA)
- **CA-1 (Phoenix)** : Toutes les étapes de la chaîne RAG (notamment la transformation HyDE) sont traçables visuellement dans Phoenix.
- **CA-2 (HyDE)** : Le système démontre une meilleure robustesse face aux questions floues grâce à la génération du document hypothétique.
- **CA-3 (Multimodal)** : Le parser identifie et transcrit les tableaux complexes en format Markdown exploitable par le LLM.
- **CA-4 (Sources)** : Les citations de sources restent précises et incluent le contexte étendu (Sentence Window).

---
**STATUT : PRIORITÉ ÉLEVÉE - PRÊT POUR EXÉCUTION**
