# Sprint Plan 8 - Redressement Technique & Intégrité de l'Indexation

**Sprint Goal** : Garantir une indexation exhaustive et transparente de l'intégralité des PDF (notamment les conclusions) et prouver l'origine textuelle des réponses pour restaurer la confiance client.
**Statut** : PLANNING

---

### [PBI-011] Indexation Exhaustive & Intègre
**Priorité** : Critique | **Estimation** : L

**User Story** : "En tant que Product Owner, je veux que le système parse l'intégralité des thèses (corps du texte et conclusions) sans limitation de page, afin de garantir l'honnêteté scientifique des réponses."
**Dépendances** : Aucune (Refonte structurelle)
**Critères d'Acceptation (Gherkin)** :
- [ ] **Scenario 0** : Assainissement Total (Data & Index)
  - **GIVEN** Un dossier `data/` pollué par des fichiers `.json` de test et une base vectorielle corrompue.
  - **WHEN** Le sprint de redressement démarre.
  - **THEN** :
      1. Suppression de tous les fichiers `.json` suspects dans `data/` (ex: `test_dataset.json`, `golden_dataset.json` corrompus).
      2. Suppression/Réinitialisation de la collection ChromaDB.
      3. Seuls les fichiers PDFs originaux doivent être conservés comme source de vérité.
- [ ] **Scenario 1** : Parsing intégral
  - **GIVEN** Un document PDF de plus de 100 pages
  - **WHEN** Le processus d'ingestion est lancé
  - **THEN** Le nombre de fragments (Nodes) créés correspond à la totalité du texte, conclusions incluses.
- [ ] **Scenario 2** : Suppression des "Shadow Metadata"
  - **GIVEN** Le pipeline de parsing
  - **WHEN** Les métadonnées sont générées
  - **THEN** Aucune donnée factuelle (ex: résumé, conclusion) ne doit être injectée manuellement si elle n'est pas extraite dynamiquement du texte source.

---

### [PBI-012] Preuve d'Extraction (Transparence)
**Priorité** : Haute | **Estimation** : M

**User Story** : "En tant que Client, je veux voir la source exacte (citation et numéro de page) utilisée pour chaque réponse, afin de m'assurer qu'il ne s'agit pas d'hallucinations basées sur des métadonnées."
**Dépendances** : [PBI-011]
**Critères d'Acceptation (Gherkin)** :
- [ ] **Scenario 1** : Citation de source
  - **GIVEN** Une réponse générée par le RAG
  - **WHEN** L'utilisateur consulte la réponse
  - **THEN** Le système affiche un bloc "Sources" avec le texte exact extrait et la référence à la page du PDF original.

---

### [PBI-010] Recherche Hybride (Reprise)
**Priorité** : Haute | **Estimation** : S

**User Story** : "En tant qu'utilisateur, je veux que la recherche hybride (BM25 + Vectoriel) s'applique sur l'intégralité du corpus indexé, afin de retrouver des termes techniques même en fin de document."
**Dépendances** : [PBI-011]
**Critères d'Acceptation (Gherkin)** :
- [ ] **Scenario 1** : Recherche sur l'index global
  - **GIVEN** Un terme technique présent uniquement dans la conclusion d'une thèse
  - **WHEN** Je lance une recherche hybride
  - **THEN** Le document est correctement remonté et classé par le Reranker.

---

**CONSIGNES POUR LE LEAD-DEV** :
1. Interdiction d'utiliser des limites de pages arbitraires.
2. Utiliser LlamaParse en mode `full_parse` ou implémenter un `RecursiveRetriever` si nécessaire pour gérer les longs documents.
3. La transparence est la priorité : toute métadonnée injectée doit être traçable vers une portion du document original.
