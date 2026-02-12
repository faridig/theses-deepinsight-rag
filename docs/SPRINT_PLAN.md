# SPRINT PLAN N°11

**Sprint Goal** : Déployer une architecture multi-thèmes robuste permettant l'ingestion massive et isolée de thèses par domaine scientifique (IA, Agriculture, etc.).
**Statut** : PLANNING

---

## 🏗️ PBI-023 : Architecture Multi-Collections (Isolation des Domaines)
**Priorité** : Haute | **Estimation** : M

**User Story** : "En tant qu'utilisateur, je veux que mes recherches soient isolées par domaine afin d'éviter les interférences entre des sujets non liés."

**Guide Technique (Lead-Dev)** :
- Implémenter un `VectorService` capable de créer/gérer dynamiquement des collections Qdrant basées sur le "slug" du thème (ex: `theses-ia`, `theses-agri`).
- Utiliser le `AsyncQdrantClient` pour les opérations de création de collection.
- Mettre en place un sélecteur de collection dans le `RAGEngine` pour router la requête vers la bonne collection.
- **Référence MCP context7** :
  ```python
  from llama_index.vector_stores.qdrant import QdrantVectorStore
  vector_store = QdrantVectorStore(collection_name=dynamic_theme_name, client=client, aclient=aclient)
  ```

**Critères d'Acceptation (CA)** :
- [ ] Le système peut créer une nouvelle collection Qdrant à la volée lors de l'ingestion d'un nouveau thème.
- [ ] Une recherche lancée sur le thème "IA" ne retourne aucun résultat provenant de la collection "Agriculture".

---

## ⚡ PBI-024 : Async Ingestion Pipeline (Massive Loading)
**Priorité** : Haute | **Estimation** : M

**User Story** : "En tant que Data Engineer, je veux traiter des centaines de thèses simultanément sans bloquer le système."

**Guide Technique (Lead-Dev)** :
- Utiliser `llama_index.core.ingestion.IngestionPipeline` avec `vector_store` intégré.
- Configurer les transformations (SentenceSplitter, etc.) et lancer le pipeline via `arun` pour un traitement asynchrone total.
- Intégrer la gestion des erreurs pour ne pas stopper l'ingestion si un PDF est corrompu.
- **Référence MCP context7** :
  ```python
  pipeline = IngestionPipeline(transformations=[...], vector_store=vector_store)
  nodes = await pipeline.arun(documents=documents, show_progress=True)
  ```

**Critères d'Acceptation (CA)** :
- [ ] Le traitement de 50 documents simultanés n'entraîne pas de timeout ou de crash mémoire.
- [ ] Les traces Phoenix montrent l'exécution parallèle des étapes de parsing et d'embedding.

---

## 🌍 PBI-025 : Ingesteur Thématique Dynamique (Theses.fr)
**Priorité** : Moyenne | **Estimation** : S

**User Story** : "En tant que chercheur, je veux télécharger toutes les thèses d'une discipline spécifique via une simple commande."

**Guide Technique (Lead-Dev)** :
- Améliorer le `ThesesClient` pour supporter les filtres de recherche avancés de l'API (`discipline`, `sujet`).
- Implémenter une logique de pagination pour récupérer plus de 100 résultats par thème.
- S'assurer que chaque `Document` LlamaIndex porte les métadonnées du domaine (`theme`) pour le futur filtrage.

**Critères d'Acceptation (CA)** :
- [ ] Une commande `download_theme("intelligence artificielle", limit=100)` télécharge et indexe correctement les thèses correspondantes.
- [ ] Les métadonnées `discipline` et `theme` sont correctement injectées dans chaque Node.

---

## 🏁 PASSAGE DE RELAIS
Ce sprint est crucial pour la scalabilité. Le Lead-Dev doit commencer par l'isolation des collections (PBI-023) avant de lancer l'ingestion massive (PBI-024).

**PLANNING VALIDÉ. À TOI LEAD-DEV.**
