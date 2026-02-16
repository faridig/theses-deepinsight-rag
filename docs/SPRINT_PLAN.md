# SPRINT PLAN N°15 : "Connexion Totale & Intelligence Multi-Domaines"

**Sprint Goal** : Connecter l'interface utilisateur à la base de données Qdrant pour permettre l'exploration dynamique des thèmes indexés et supprimer les dépendances aux données de test.

**Statut** : VALIDÉ (PO)

---

## [PBI-035] Mapping Dynamique Qdrant
**Priorité** : Haute | **Estimation** : S

**User Story** : "En tant qu'utilisateur, je veux que l'interface détecte automatiquement les thèmes (collections) disponibles dans la base de données, afin de ne pas avoir à configurer manuellement les domaines de recherche."

**Critères d'Acceptation** :
- [ ] Ajout d'une méthode `list_collections()` dans `VectorService`.
- [ ] Filtrage des collections techniques (ex: ne garder que celles préfixées ou identifiées comme thèses).
- [ ] Exposition de cette liste au moteur `RAGEngine`.

---

## [PBI-036] Sélecteur de Domaine UI (Chainlit)
**Priorité** : Haute | **Estimation** : M

**User Story** : "En tant qu'étudiant, je veux sélectionner mon domaine d'étude (IA, Agriculture, etc.) dans la barre latérale, afin que mes questions soient traitées par les thèses pertinentes uniquement."

**Critères d'Acceptation** :
- [ ] Intégration d'un `cl.Select` dans la sidebar de Chainlit.
- [ ] Mise à jour dynamique de la liste des domaines au lancement de l'app.
- [ ] Routage de la requête `engine.aask(question, theme=selected_theme)`.
- [ ] Persistance du choix du domaine pendant la session utilisateur.

---

## [PBI-037] Indicateurs de Volume & Nettoyage (PBI-038)
**Priorité** : Moyenne | **Estimation** : S

**User Story** : "En tant qu'utilisateur, je veux voir combien de documents sont analysés pour le thème choisi, afin d'évaluer la profondeur de la base documentaire."

**Critères d'Acceptation** :
- [ ] Affichage du compteur de documents/nodes pour la collection active.
- [ ] **Action PBI-038** : Suppression complète du code chargeant `sample.pdf` ou pointant vers `data/test`.
- [ ] Message d'erreur explicite si une collection est vide.

---

## 🏛️ JOURNAL DES DÉCISIONS (Sprint 15)
- **DÉCISION 15.1** : L'interface Chainlit devient l'unique point d'entrée pour l'exploration multi-collections.
- **DÉCISION 15.2** : Abandon définitif des fichiers de test locaux au profit du stockage S3/MinIO et Qdrant pour garantir la cohérence des données.

---
**PLANNING VALIDÉ. À TOI LEAD-DEV.**
