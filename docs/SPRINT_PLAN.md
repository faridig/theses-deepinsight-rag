# SPRINT PLAN N°21 : "Clean Slate & Gold Standard"

**Sprint Goal** : Assurer l'intégrité totale du système par un nettoyage profond de l'infrastructure S3, la synchronisation des suppressions et la restauration de la métrique "Context Precision" via le référentiel de vérité.

**Statut** : EN ATTENTE DE VALIDATION

---

## 🧹 VOLET 1 : INFRASTRUCTURE & HYGIÈNE

### [PBI-071] Grand Nettoyage S3 (Housekeeping)
**Priorité** : Haute | **Estimation** : S
**User Story** : "En tant qu'Administrateur, je veux que les buckets inutiles soient supprimés et les fichiers orphelins (racine) soient nettoyés, afin de maintenir une source de vérité propre."
**Critères d'Acceptation** :
- [ ] Suppression de tous les buckets MinIO sauf `theses-data`.
- [ ] Migration du fichier PDF orphelin à la racine vers un dossier de secours ou thématique.
- [ ] Suppression du dossier `agriculture` vide/orphelin à la racine.

### [PBI-072] Réorganisation Thématique Physique
**Priorité** : Moyenne | **Estimation** : M
**User Story** : "En tant qu'Administrateur, je veux que les PDFs soient rangés physiquement par thèmes dans MinIO, afin de pouvoir naviguer visuellement dans mes documents."
**Critères d'Acceptation** :
- [ ] Migration des fichiers : `theses-data/pdfs/{hash}.pdf` -> `theses-data/themes/{theme}/docs/{filename}.pdf`.
- [ ] Mise à jour du `ThemeIngestor` pour pointer vers ces nouveaux chemins.

### [PBI-073] Synchronisation Totale de la Purge
**Priorité** : Critique | **Estimation** : S
**User Story** : "En tant qu'Administrateur, je veux que la suppression d'une collection dans le Cockpit efface aussi les fichiers dans MinIO, afin d'éviter les collections fantômes."
**Critères d'Acceptation** :
- [ ] GIVEN une collection "animaux-zoologie" existante dans Qdrant et MinIO.
- [ ] WHEN je clique sur "Supprimer" dans le Cockpit.
- [ ] THEN la collection Qdrant est supprimée ET le dossier `themes/animaux-zoologie/` est purgé de MinIO.

---

## 🔬 VOLET 2 : FIABILITÉ SCIENTIFIQUE (RAGAS)

### [PBI-076] Restauration de la Context Precision (Gold Standard)
**Priorité** : Critique | **Estimation** : M
**User Story** : "En tant qu'Administrateur, je veux utiliser le fichier `ground_truth.json` pour calculer une précision réelle, afin de ne plus avoir de valeurs 'NaN' dans mes rapports."
**Critères d'Acceptation** :
- [ ] Branchement du script d'audit sur `data/ground_truth.json`.
- [ ] Affichage de la métrique "Context Precision" dans le Cockpit Streamlit.
- [ ] Export automatique de tous les scores Ragas vers Arize Phoenix.

---

## 📖 VOLET 3 : EXPÉRIENCE ADMIN & PÉDAGOGIE

### [PBI-075] Guide des Metrics & Aide à la Décision
**Priorité** : Moyenne | **Estimation** : XS
**User Story** : "En tant qu'Administrateur, je veux comprendre chaque score et savoir comment réagir, afin de piloter la qualité de mon RAG de manière experte."
**Critères d'Acceptation** :
- [ ] Ajout d'une section "Aide" dans le Dashboard Qualité.
- [ ] Dictionnaire des metrics (Fidélité, Pertinence, Précision) avec seuils d'alerte et solutions.

### [PBI-077] Sourcing Check (Prévisualisation theses.fr)
**Priorité** : Moyenne | **Estimation** : S
**User Story** : "En tant qu'Administrateur, je veux voir la liste des thèses trouvées avant de lancer l'ingestion, afin d'éviter d'indexer des documents hors-sujet."
**Critères d'Acceptation** :
- [ ] Affichage d'un tableau récapitulatif (Titres/Années) après la recherche theses.fr.
- [ ] Bouton de confirmation pour déclencher l'ingestion effective.

### [PBI-078] Visualisation du Flux (Architecture View)
**Priorité** : Moyenne | **Estimation** : XS
**User Story** : "En tant qu'Administrateur, je veux visualiser le schéma technique du pipeline dans le Cockpit, afin de comprendre l'enchaînement des étapes (parsing, métadonnées locales, génération)."
**Critères d'Acceptation** :
- [ ] Nouvel onglet "Architecture" dans le Cockpit Streamlit.
- [ ] Schéma Mermaid ou SVG détaillant :
    - PDF -> Docling (Local) -> Markdown.
    - Markdown -> SLM Metadata (Local) -> Metadata.
    - Text+Metadata -> Embedding (Local) -> Qdrant.
    - Question -> GPT-4o (Cloud) -> Réponse.

---

## 🏛️ JOURNAL DES DÉCISIONS (Sprint 21)
- **DÉCISION 21.1** : Abandon du dossier central unique `pdfs/` au profit d'une structure thématique `themes/{nom}/docs/` pour satisfaire le besoin de lisibilité de l'utilisateur.
- **DÉCISION 21.2** : Utilisation du fichier `ground_truth.json` comme benchmark de référence (Gold Standard) pour stabiliser les mesures de précision.

---
**"PLANNING VALIDÉ. À TOI LEAD-DEV."**
