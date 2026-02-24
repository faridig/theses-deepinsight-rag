# SPRINT PLAN N°22 : "Local Edge & Quality Boost"

**Sprint Goal** : Réduire les coûts d'ingestion via un SLM local (Ollama) et restaurer l'excellence scientifique en redressant la Fidélité (>0.85) et la Pertinence (>0.70).

**Statut** : EN COURS

---

## 🏗️ VOLET 1 : SOUVERAINETÉ & PERFORMANCE (SLM)

### [PBI-079] Infra SLM Local (Ollama)
**Priorité** : Haute | **Estimation** : M
**User Story** : "En tant que Lead-Dev, je veux un service Ollama tournant en local dans le Docker Compose, afin de traiter les métadonnées sans dépendre du cloud."
**Critères d'Acceptation** :
- [ ] Ajout du service `ollama` dans `docker-compose.yml`.
- [ ] Téléchargement automatisé du modèle `llama3.2:3b` au démarrage.
- [ ] Vérification de l'accès via API REST depuis le conteneur Ingestion.

### [PBI-080] Handoff Métadonnées vers SLM
**Priorité** : Haute | **Estimation** : S
**User Story** : "En tant qu'Administrateur, je veux que l'extraction du titre et du résumé soit faite par le LLM local, afin de rendre l'ingestion massive gratuite."
**Critères d'Acceptation** :
- [ ] Remplacement de `OpenAI` par `Ollama` dans les classes `TitleExtractor` et `SummaryExtractor`.
- [ ] Filtrage intelligent : Exclusion des sections "Remerciements/Dédicaces" via Docling.
- [ ] Ciblage prioritaire des sections "Abstract/Résumé" (début ou fin de document) et "Conclusion".
- [ ] Validation de la qualité des résumés produits (comparaison vs GPT-4o).

---

## 🔬 VOLET 2 : EXCELLENCE RAG (FIABILITÉ & PERTINENCE)

### [PBI-081] Durcissement Prompt & Anti-Hallucination
**Priorité** : Critique | **Estimation** : S
**User Story** : "En tant que Chef d'Orchestre, je veux que le système refuse de répondre s'il n'a pas de sources, afin de remonter la Fidélité (actuellement 0.59) à >0.85."
**Critères d'Acceptation** :
- [ ] GIVEN une question hors-sujet.
- [ ] WHEN le système cherche dans les sources.
- [ ] THEN il répond "Je ne sais pas" au lieu d'inventer (Strict Context Adherence).
- [ ] Obligation de citation formatée pour chaque affirmation.

### [PBI-082] Optimisation du Retrieval Hybride & Reranking
**Priorité** : Critique | **Estimation** : M
**User Story** : "En tant qu'Utilisateur, je veux que les documents remontés soient plus proches de ma question, afin de remonter la Pertinence (actuellement 0.37) à >0.70."
**Critères d'Acceptation** :
- [ ] **Hybrid Tuning** : Implémentation de `relative_score_fusion` dans `QdrantVectorStore` pour une meilleure pondération.
- [ ] **Alpha Calibration** : Fixation de `alpha=0.7` (priorité sémantique) comme base de benchmark.
- [ ] **Cohere Thresholding** : Implémentation d'un filtre post-rerank éjectant tout nœud avec un `rank_score < 0.6`.
- [ ] **Multi-Query Safety** : Réduction de la température à `0.1` pour le `QueryTransform` et durcissement du prompt de réécriture pour éviter le "Semantic Drift".
- [ ] **Small-to-Big Retrieval** : Activation de la substitution de fenêtre (Window Substitution) uniquement si le score de rerank est élevé.

---

## 🏛️ JOURNAL DES DÉCISIONS (Sprint 22)
- **DÉCISION 22.1** : Adoption de `llama3.2:3b` comme SLM de référence pour les tâches d'extraction structurée (Title/Summary).
- **DÉCISION 22.2** : Priorité absolue à la Fidélité sur la loquacité : le système doit préférer une réponse courte et sourcée à une synthèse longue potentiellement hallucinogène.

---
**PLANNING VALIDÉ. À TOI LEAD-DEV.**
