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

## 🧩 4. Zoom : Le Sélecteur de Thématique (Pattern Hybride)

### Vision Ergonomique
Pour les sections **"Ingestion theses.fr"** et **"Importation Directe (PDF)"**, nous utilisons le pattern **"Select or Create"**. Ce pattern minimise la charge cognitive tout en offrant une flexibilité totale.

#### Parcours Utilisateur :
1. **Exploration** : L'utilisateur ouvre le sélecteur (recherche intégrée).
2. **Sélection** : Il choisit une thématique existante (chargée dynamiquement depuis Qdrant).
3. **Création** : S'il ne trouve pas son bonheur, l'option `➕ Nouveau thème...` est sélectionnée.
4. **Saisie** : Un champ de texte apparaît immédiatement pour nommer le nouveau thème.

### Implémentation Streamlit Propre (Spécifications Lead-Dev)

```python
import streamlit as st

def theme_selector_component(existing_themes, key_prefix=""):
    """
    Composant réutilisable pour la sélection de thème avec option de création.
    Respecte les tokens : Radius 8px, Couleur #2563EB.
    """
    options = existing_themes + ["➕ Nouveau thème..."]
    
    selected_option = st.selectbox(
        "Thématique de recherche",
        options=options,
        index=0,
        key=f"{key_prefix}_select",
        help="Choisissez un thème existant ou créez-en un nouveau."
    )
    
    final_theme = selected_option
    
    if selected_option == "➕ Nouveau thème...":
        final_theme = st.text_input(
            "Nom du nouveau thème",
            placeholder="Ex: Intelligence Artificielle...",
            key=f"{key_prefix}_new",
            help="Ce nom servira de namespace dans la base vectorielle."
        )
        if final_theme:
            st.info(f"✨ Nouveau thème détecté : **{final_theme}**")
            
    return final_theme
```

### Style CSS Injecté (Design Tokens)
```python
st.markdown("""
    <style>
    /* Application du Radius 8px & Focus Bleu */
    .stSelectbox div[data-baseweb="select"], 
    div[data-testid="stTextInput"] input {
        border-radius: 8px !important;
    }
    .stSelectbox div[data-baseweb="select"]:focus-within {
        border-color: #2563EB !important;
    }
    </style>
    """, unsafe_allow_html=True)
```

---

## 📊 5. Recommandations Keep/Drop/Custom

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
