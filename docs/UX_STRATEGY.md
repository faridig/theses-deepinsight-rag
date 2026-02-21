# 🧠 STRATÉGIE UX : DeepInsight (Inspiré par HubSpot)

## 🌟 1. Vision Produit
L'interface doit respirer la **confiance**, la **clarté** et l'**efficacité**. L'objectif est de transformer des données complexes (Theses & RAG) en insights actionnables, à l'image du dashboard HubSpot qui centralise le flux de travail CRM.

**Ambiance Visuelle (Moodboard) :**
- **SaaS Moderne** : Fond blanc cassé/gris très clair pour réduire la fatigue visuelle.
- **Data-Centric** : Utilisation de cartes structurées avec des ombres légères.
- **Propreté** : Espacement (Gutter) généreux de 24px entre les éléments.

---

## 🎨 2. Design System (Tokens)

### Palette de Couleurs
Pour se différencier tout en gardant l'aspect pro de HubSpot :
- **Primary (Insight Blue)** : `#2563EB` (Bleu vibrant au lieu de l'orange HubSpot)
- **Secondary (Action Orange)** : `#FF7A59` (Clin d'œil à HubSpot pour les CTAs secondaires)
- **Background** : `#F9FAFB`
- **Surface (Cards)** : `#FFFFFF`
- **Text (Dark)** : `#111827` (Presque noir pour un contraste maximal)

### Typographie
- **Font** : `Geist` ou `Inter` (Standard moderne, hautement lisible).
- **H1** : 24px, Bold, Tracking -0.02em.
- **Body** : 14px, Regular, Line-height 1.5.

### Snippet Tailwind (Config Ready)
```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#2563EB',
          foreground: '#FFFFFF',
        },
        secondary: '#FF7A59',
        background: '#F9FAFB',
        surface: '#FFFFFF',
        muted: '#6B7280',
      },
      borderRadius: {
        lg: '8px',
        md: '6px',
        sm: '4px',
      },
      boxShadow: {
        card: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
      }
    },
  },
}
```

---

## 🏗️ 3. Architecture des Pages (Atomic Design)

### ⚛️ Atomes (Buttons, Inputs)
- **Bouton Primaire** : Angles arrondis (8px), fond bleu, texte blanc. Effet de hover subtil (assombrissement).
- **Search Bar Input** : Toujours visible en haut, avec un raccourci clavier affiché `⌘K`.

### 🧬 Molécules (Formulaires, KPI Cards)
- **KPI Card** : Une valeur numérique forte, un label, et un indicateur de tendance (ex: +12% flèche verte).
- **Navigation Item** : Icône Lucide + Texte, état actif avec une bordure gauche de 3px en bleu primaire.

### 🏢 Organismes (Navbar, Sidebar)
- **Sidebar (Collapsible)** : Menu à gauche avec icônes (Dashboard, Analyses, Thèses, Settings).
- **Global Header** : Profil utilisateur à droite, Notifications, et Barre de recherche centrale.

---

## 📊 4. Recommandations Keep/Drop/Custom

| Élément | Action | Raison |
| :--- | :--- | :--- |
| **Navigation Latérale** | **KEEP** | Standard d'ergonomie SaaS pour la gestion multi-objets. |
| **Filtres Avancés** | **KEEP** | Essentiel pour trier les thèses et les sources RAG. |
| **Menu Paramètres Trop Dense** | **DROP** | Trop complexe pour une V1. Préférer un menu contextuel simple. |
| **Couleur Orange HubSpot** | **CUSTOMIZE** | Remplacer par un Bleu Insight pour marquer l'identité "DeepInsight". |
| **Border Radius** | **CUSTOMIZE** | Passer de 4px (HubSpot standard) à 8px pour un look plus "Soft-UI". |

---

## 🛠️ 5. Stack UI Recommandée
Via analyse Context7, voici la stack optimale pour la fidélité et la vitesse de dev :
- **Framework** : Next.js 14+ (App Router).
- **UI Library** : `shadcn/ui` (Basé sur Radix UI pour l'accessibilité).
- **Icons** : `Lucide-react`.
- **Charts** : `Tremor` ou `Recharts` (Pour les analytics DeepInsight).

---

## ♿ Accessibilité (A11y)
- **Contraste** : Ratio minimum de 4.5:1 pour tous les textes.
- **Focus States** : Outline visible de 2px lors de la navigation au clavier.
- **ARIA** : Utiliser `aria-expanded` sur les sous-menus de la sidebar.

---

**STRATÉGIE UX VALIDÉE. À TOI PRODUCT OWNER POUR L'INTÉGRATION AU BACKLOG.**
