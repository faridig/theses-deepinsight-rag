# SPRINT PLAN N°13

**Sprint Goal** : Durcir l'infrastructure vectorielle et automatiser l'audit de qualité pour garantir un système haute performance et sans hallucinations.

**Statut** : EN COURS

---

## 🏗️ PBI-022 : Durcissement Qdrant (Migration Production)
**Priorité** : Haute | **Estimation** : M

**User Story** : "En tant qu'administrateur, je veux optimiser le stockage et la communication avec Qdrant pour garantir des performances constantes malgré l'augmentation du volume de thèses."

**Guide Technique (Lead-Dev)** :
- **Protocole** : Migrer la connexion client du mode REST (port 6333) vers **gRPC** (port 6334).
- **Quantification** : Activer la `scalar_quantization` (Int8) lors de la création ou de la mise à jour des collections pour réduire l'usage RAM.
- **Stockage** : Configurer `on_disk: true` pour les vecteurs afin de préserver la mémoire vive.
- **Vérification** : Comparer la latence d'une recherche Multi-Query avant/après.

**Critères d'Acceptation (CA)** :
- [ ] La communication s'effectue via gRPC (vérifiable dans les logs).
- [ ] L'usage RAM par point indexé est réduit d'au moins 50% (mesure via Dashboard Health).
- [ ] Les recherches vectorielles restent précises (pas de dégradation visible du Recall).

---

## 📊 PBI-013 : Nightly Audit Ragas (Qualité & Fiabilité)
**Priorité** : Haute | **Estimation** : L

**User Story** : "En tant qu'administrateur, je veux mesurer automatiquement la véracité des réponses pour identifier et corriger les potentielles hallucinations."

**Guide Technique (Lead-Dev)** :
- **Pipeline** : Créer un script `scripts/audit_quality.py` utilisant le framework **Ragas**.
- **Dataset** : Extraire un échantillon de 20 traces depuis Arize Phoenix (via l'API locale).
- **Métriques** : Calculer `faithfulness` (fidélité), `answer_relevancy` (pertinence) et `context_precision`.
- **Reporting** : 
    - Générer un rapport Markdown dans `docs/AUDITS/audit_YYYY-MM-DD.md`.
    - Envoyer les scores vers Arize Phoenix pour visualisation graphique.

**Critères d'Acceptation (CA)** :
- [ ] Un audit peut être lancé via une simple commande CLI.
- [ ] Un rapport Markdown détaillé est généré après chaque exécution.
- [ ] Les scores Ragas sont visibles dans l'interface locale de Phoenix (localhost:6006).

---

## 🏁 PASSAGE DE RELAIS
L'ordre recommandé est de traiter le **PBI-022** en premier pour s'assurer que l'audit (PBI-013) s'exécute sur l'infrastructure finale optimisée.

**PLANNING VALIDÉ. À TOI LEAD-DEV.**
