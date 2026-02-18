## Rate Limiting APIs Externes (Cohere/OpenAI)
**Date** : 2026-02-18
**Contexte** : Lors de la simulation de trafic massive (Sprint 16), des erreurs 429 (Too Many Requests) ont été observées sur les clés de test/trial (Cohere Rerank et OpenAI Embeddings).
**Dette** : Le code n'implémente pas encore de file d'attente robuste ou de backoff exponentiel personnalisé au-delà des mécanismes natifs des SDK.
**Impact** : Échec partiel des requêtes lors de pics de charge ou d'audits massifs.
**Action corrective** : Implémenter un système de rate-limiting côté client ou passer à des clés de production avec des quotas plus élevés.
