# SPRINT PLAN N°12

**Sprint Goal** : Assainir l'infrastructure et peupler le système avec des données réelles multi-domaines pour valider l'isolation des collections.
**Statut** : PLANNING

---

## 🧹 PBI-026 : Hygiène de l'Infrastructure (Cleanup)
**Priorité** : Haute | **Estimation** : S

**User Story** : "En tant qu'administrateur, je veux supprimer les données temporaires et les buckets orphelins pour libérer de l'espace et éviter les confusions."

**Guide Technique (Lead-Dev)** :
- Créer un script de maintenance `scripts/cleanup_infra.py`.
- Supprimer tous les buckets MinIO sauf ceux explicitement définis dans la config (ex: `theses-ia`, `theses-agri`).
- Vider le dossier local `data/` après s'être assuré que les fichiers sont bien persistés dans MinIO.

**Critères d'Acceptation (CA)** :
- [x] Après exécution, `mc ls local` (MinIO CLI) ne montre que les buckets utiles.
- [x] Le dossier local `data/` est vide.

---

## 🚀 PBI-027 : Seeding & Validation Proactive
**Priorité** : Haute | **Estimation** : M

**User Story** : "En tant que chercheur, je veux m'assurer que seules les thèses valides et enrichies sont indexées pour garantir la qualité des réponses."

**Guide Technique (Lead-Dev)** :
- **Validation** : Implementer un `PDFValidator` (taille > 10Ko, test ouverture `PyMuPDF`).
- **Enrichissement** : Extraire systématiquement l'**année de soutenance** et l'**université** depuis les métadonnées theses.fr pour chaque `Document`.
- **Action sur Erreur** : Loguer les URLs corrompues, écarter les fichiers vides, et déplacer les suspects en bucket `quarantine`.

**Critères d'Acceptation (CA)** :
- [ ] 50 thèses valides par domaine (IA, Agri, Bio) indexées.
- [x] Les métadonnées `year` et `university` sont présentes sur chaque Node dans Qdrant.

---

## 🛡️ PBI-028 : Hygiène des Données & Dashboard
**Priorité** : Moyenne | **Estimation** : S

**User Story** : "En tant qu'administrateur, je veux éviter de stocker plusieurs fois la même thèse et avoir une vue claire sur l'état de mes données."

**Guide Technique (Lead-Dev)** :
- **Dédoublonnage** : Calculer un Hash SHA-256 pour chaque PDF. Utiliser ce Hash comme ID dans MinIO et comme métadonnée dans Qdrant. Si le Hash existe déjà, ignorer le téléchargement/indexation.
- **Dashboard de Santé** : Créer une commande `python manage.py health` affichant :
    - Volume par collection (Nb docs / Taille Mo).
    - État de la Quarantaine.
    - Top 5 des universités les plus représentées.

**Critères d'Acceptation (CA)** :
- [x] Une thèse téléchargée deux fois (via deux thèmes différents) n'est stockée qu'une seule fois.
- [x] La commande `health` retourne un tableau récapitulatif propre.

---

## 🏁 PASSAGE DE RELAIS
Le Lead-Dev doit commencer par le nettoyage (PBI-026) pour partir sur une base saine avant de lancer les téléchargements massifs.

**PLANNING VALIDÉ. À TOI LEAD-DEV.**
