# DeepInsight Theses RAG

Système de recherche conversationnelle sur le **corpus national des thèses françaises**. Pipeline RAG de production avec recherche hybride, reclassement neuronal et évaluation automatique de la qualité.

## Demo

> *"Quelles thèses traitent de la détection de fake news via le deep learning ?"*
> *"Quels sont les impacts de l'IA sur le système scientifique ?"*

L'assistant répond en langage naturel, cite ses sources avec liens vers les PDFs originaux, et affiche ses scores de fiabilité en temps réel.

## Architecture

```
PDF → Docling (GPU) → Markdown structuré
                           ↓
                  SLM local (métadonnées)
                           ↓
              ┌────────────┴────────────┐
          Qdrant (Int8)             BM25s
        text-embedding-3         lexical
              └────────────┬────────────┘
                    RRF Fusion
                           ↓
                  Cohere Rerank v3
                           ↓
               Diversity Filter → GPT-4o-mini
                           ↓
                  Réponse sourcée + scores
```

**Pourquoi cette stack ?**
- **Docling (IBM)** : parsing layout-aware pour tableaux et multi-colonnes vs. extraction linéaire classique
- **Qdrant Int8** : quantification scalaire → 4x moins de mémoire, 99%+ de précision conservée
- **RRF Fusion** : combine recherche sémantique (sens) + lexicale (acronymes, noms propres)
- **Cohere Rerank v3** : reclassement neuronal post-retrieval pour maximiser la pertinence

## Stack

| Composant | Technologie |
|-----------|-------------|
| UI conversationnelle | Chainlit |
| Parsing PDF | IBM Docling (GPU) |
| Embeddings | OpenAI text-embedding-3 |
| Vector DB | Qdrant (quantification Int8) |
| Recherche lexicale | BM25s |
| Reranking | Cohere Rerank v3 |
| LLM | GPT-4o-mini |
| Stockage | MinIO S3 |
| Tracing / Eval | Arize Phoenix |
| Déploiement | Docker Compose |
| CI/CD | GitHub Actions |

## Lancement

```bash
# Variables d'environnement
cp .env.example .env

# Démarrage complet
docker compose up -d

# Interface Chainlit
python main_ui.py
# → http://localhost:8000

# Dashboard qualité (Streamlit)
python cockpit_streamlit.py
# → http://localhost:8501
```

## Évaluation

Chaque réponse expose des scores **Faithfulness** et **Relevancy** calculés en temps réel via Arize Phoenix. Les rapports d'audit sont générés automatiquement dans `docs/AUDITS/`.

## Structure

```
src/
├── ingestion/      # Téléchargement & parsing PDFs
├── processing/     # Enrichissement SLM + métadonnées
├── indexing/       # Embeddings + index Qdrant/BM25
├── generation/     # Pipeline RAG + LLM
├── evaluation/     # Métriques Faithfulness/Relevancy
└── utils/
```
