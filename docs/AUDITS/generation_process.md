# Processus de Génération de Données Synthétiques

Ce document décrit le processus utilisé pour générer automatiquement des datasets d'évaluation pour le système DeepInsight RAG.

## Outils Utilisés
- **LlamaIndex `RagDatasetGenerator`** : Utilise un LLM (GPT-4o-mini par défaut) pour extraire des questions et des réponses de référence à partir de documents PDF.
- **Source de données** : Thèses réelles téléchargées via `ThesesClient` ou chargées depuis MinIO.

## Procédure
1. **Préparation des documents** : Les documents sont chargés depuis le stockage S3 (MinIO) ou localement via `SimpleDirectoryReader`.
2. **Génération** : Le script `scripts/generate_synthetic_data.py` découpe les documents en nœuds et génère 2 questions par nœud.
3. **Format de sortie** : Un fichier JSON (`data/synthetic_dataset.json`) contenant une liste d'objets avec les clés suivantes :
    - `question` : La question générée.
    - `ground_truth` : La réponse de référence attendue.
    - `contexts` : Le contexte extrait du document original ayant servi à la génération.

## Utilisation pour l'Audit
Le dataset généré peut être utilisé pour mesurer :
- **Faithfulness** : Si la réponse du RAG est fidèle au contexte.
- **Answer Relevancy** : Si la réponse répond bien à la question.
- **Context Recall** : Si le RAG retrouve bien le contexte de référence.

## Commande
```bash
python scripts/generate_synthetic_data.py
```
