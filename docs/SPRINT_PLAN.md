# SPRINT PLAN N°23 : "Governance & Global Oversight"

**Sprint Goal** : Industrialiser le pilotage de la qualité par thématique et rendre les metrics actionnables pour l'opérateur via le Cockpit.

**Statut** : VALIDÉ

---

## 🏛️ VOLET 1 : GOUVERNANCE THÉMATIQUE (LAB & TERRAIN)

### [PBI-090] Datasets de Vérité Thématiques
**Priorité** : Haute | **Estimation** : M
**User Story** : "En tant qu'Administrateur, je veux des fichiers `ground_truth_{theme}.json` séparés, afin de mesurer la précision spécifique à chaque domaine sans pollution croisée."
**Justification context7** : Utilisation de `ragas.EvaluationDataset.from_list()` après chargement du JSON thématique pour une isolation stricte des benchs.
**Critères d'Acceptation** :
- [ ] Création d'un dossier `data/benchmarks/` pour stocker les datasets.
- [ ] Adaptation du script d'audit pour charger le dataset correspondant au thème sélectionné (`ground_truth_{theme}.json`).
- [ ] Mécanisme de fallback sur `ground_truth.json` si le fichier thématique est absent.
- [ ] Validation via `pytest` que le bon dataset est chargé selon l'argument `--theme`.

### [PBI-091] Moteur d'Audit Dual (Trigger Mixte)
**Priorité** : Haute | **Estimation** : M
**User Story** : "En tant qu'Opérateur, je veux déclencher un audit 'Lab' (sur dataset) ou 'Terrain' (sur traces réelles) depuis l'UI, afin de diagnostiquer rapidement une baisse de qualité."
**Justification context7** : Utilisation du container `st.status` de Streamlit pour encapsuler le `subprocess.Popen` et streamer les logs de l'audit en temps réel.
**Critères d'Acceptation** :
- [ ] Ajout d'une section "Audit Qualité" dans l'onglet Admin du Cockpit (Streamlit).
- [ ] Sélecteur de mode : "Dataset (Lab)" vs "Traces (Terrain)".
- [ ] Lancement asynchrone du script `audit_quality.py` via `subprocess.Popen`.
- [ ] Affichage d'une barre de progression (simulation ou logs parsés) et notification de fin.

---

## 📊 VOLET 2 : DASHBOARDING & INTERPRÉTATION

### [PBI-092] Vue Comparative & Benchmarking
**Priorité** : Critique | **Estimation** : M
**User Story** : "En tant que PO, je veux voir un tableau comparatif des scores (Fidélité/Pertinence) entre tous les thèmes, afin d'identifier les domaines nécessitant un réglage de prompt spécifique."
**Justification context7** : Bar Chart groupé via Plotly pour comparer Faithfulness, Relevancy, Precision et Recall par thématique.
**Critères d'Acceptation** :
- [ ] Implémentation d'une vue "Global Overview" dans le Cockpit.
- [ ] Graphique Plotly (Grouped Bar Chart) comparant les 4 metrics Ragas (Faithfulness, Relevancy, Context Precision, Context Recall) par thème.
- [ ] Tableau de bord récapitulatif montrant le "Thème le plus performant" et le "Thème en alerte".

### [PBI-093] Module d'Interprétation Intelligente
**Priorité** : Haute | **Estimation** : S
**User Story** : "En tant qu'Utilisateur non-technique, je veux une explication textuelle de ce que signifie un score de 0.6, afin de savoir si le système est prêt pour la production."
**Critères d'Acceptation** :
- [ ] Mapping des scores en labels :
    - < 0.4 : "CRITIQUE - Amélioration du prompt nécessaire"
    - 0.4 - 0.7 : "ACCEPTABLE - Vérifier la précision du parsing"
    - \> 0.7 : "EXCELLENT - Prêt pour la production"
- [ ] Affichage de ces conseils actionnables directement sous les graphiques de metrics dans Streamlit.
- [ ] Lexique interactif expliquant chaque métrique Ragas en français simple.

---

## 🏛️ JOURNAL DES DÉCISIONS (Sprint 23)
- **DÉCISION 23.1** : Adoption d'un stockage structuré par dossier `data/benchmarks/{theme}/` pour les référentiels de vérité.
- **DÉCISION 23.2** : Standardisation du mode d'audit dual (Lab vs Terrain) pour séparer l'évaluation "période de dev" (dataset fixe) de l'évaluation "vie réelle" (traces utilisateurs).

---
**PLANNING VALIDÉ. À TOI LEAD-DEV.**
