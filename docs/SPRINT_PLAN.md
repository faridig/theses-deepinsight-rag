# SPRINT PLAN N°24 : "Robustness & Local Intelligence"

**Sprint Goal** : Résoudre l'incident de "Réponse Vide" (Empty Response) et intégrer Ollama comme moteur de génération alternatif pour la souveraineté.

**Statut** : VALIDÉ (Validé par le Chef d'Orchestre)

---

## 🏛️ VOLET 1 : DIAGNOSTIC & RÉPARATION (RAG ENGINE)

### [PBI-100] Debug & Fix Empty Response
**Priorité** : Critique | **Estimation** : M
**User Story** : "En tant qu'Utilisateur, je veux recevoir une réponse claire même si le système ne trouve rien, afin de ne pas rester face à un écran vide."
**Justification context7** : Utilisation de `default_response` dans `get_response_synthesizer()` ou vérification des scores post-reranking avant synthèse.
**Critères d'Acceptation** :
- [ ] Identification de la cause de l'absence de réponse (Seuil `CohereThresholdPostprocessor` à 0.6 ou retrieval vide).
- [ ] Ajout de logs détaillés sur le nombre de nœuds post-processing.
- [ ] Implémentation d'une réponse par défaut "Je ne trouve pas d'information pertinente dans les thèses de ce domaine." au lieu de rien.
- [ ] Test de régression : simuler une question hors-sujet et vérifier le message.

### [PBI-102] Robustesse & Feedback "No Sources"
**Priorité** : Moyenne | **Estimation** : S
**User Story** : "En tant qu'Utilisateur, je veux que l'UI m'informe explicitement si la recherche n'a retourné aucun document."
**Critères d'Acceptation** :
- [ ] Modification de `main_ui.py` pour gérer le cas `response.source_nodes` vide.
- [ ] Envoi d'un `cl.Message` spécifique expliquant qu'aucune source n'est disponible.

---

## ⚙️ VOLET 2 : SOUVERAINETÉ (HYBRID LLM)

### [PBI-101] Moteur LLM Hybride (OpenAI/Ollama)
**Priorité** : Haute | **Estimation** : M
**User Story** : "En tant que PO, je veux pouvoir basculer sur un LLM local (Ollama) si OpenAI est indisponible ou pour des raisons de coût/confidentialité."
**Justification context7** : Utilisation du module `llama_index.llms.ollama` configuré via `src/config.py`.
**Critères d'Acceptation** :
- [ ] Ajout d'une variable `USE_LOCAL_LLM=1` dans `.env`.
- [ ] Mise à jour de `src/config.py` pour initialiser `Settings.llm` avec `Ollama(model="llama3.2:3b")` si activé.
- [ ] Vérification que les prompts de rigueur scientifique (Strict Context Adherence) sont supportés par le modèle local.
- [ ] Monitoring Phoenix : vérifier que les traces indiquent bien l'usage d'Ollama.

---

## 🏛️ JOURNAL DES DÉCISIONS (Sprint 24)
- **DÉCISION 24.1** : Le seuil de reranking de 0.6 (Cohere) sera assoupli à 0.4 en cas de "réponse vide" récurrente si la qualité reste acceptable.
- **DÉCISION 24.2** : Ollama (Llama 3.2:3b) devient le modèle de fallback recommandé pour l'usage local.

---
**PLANNING VALIDÉ. À TOI LEAD-DEV.**
