# Technical Debt - Theses-DeepInsight RAG

## Fallback Synchrone dans AsyncIngestor
**Date** : 2026-02-12
**Contexte** : Le pipeline d'ingestion LlamaIndex (`arun`) exige un client asynchrone pour le vector store. Or, Qdrant ne supporte pas d'accès asynchrone en mode stockage local (path).
**Dette** : Pour éviter un crash en mode local, `AsyncIngestor` bascule sur `pipeline.run` (synchrone) via `asyncio.to_thread`. 
**Impact** : Performance réduite en mode local par rapport au mode serveur Qdrant.
**Action corrective** : Recommander l'usage du serveur Qdrant (`QDRANT_URL`) pour les déploiements de production nécessitant une ingestion massive.
