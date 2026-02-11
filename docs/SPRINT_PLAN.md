# SPRINT PLAN N°10

**Sprint Goal** : Industrialiser l'infrastructure (Docker, MinIO, Qdrant) et optimiser la réactivité du système pour supporter un volume massif de thèses multi-domaines.
**Statut** : PLANNING

---

## 🚀 PBI-019 : Optimisation Latence via Parallélisme (Async)
**Priorité** : Haute | **Estimation** : S

**User Story** : "En tant que Lead-Dev, je veux paralléliser les appels au retriever afin de diviser la latence de récupération par 3."

**Guide Technique (Lead-Dev)** :
- Utiliser `asyncio.gather` pour exécuter simultanément les appels `aretrieve` dans le `MultiQueryRetriever`.
- Remplacer les boucles séquentielles par une collection de tâches asynchrones.
- **Référence MCP context7** :
  ```python
  import asyncio
  tasks = [retriever.aretrieve(q) for q in generated_queries]
  results = await asyncio.gather(*tasks)
  ```

**Critères d'Acceptation (CA)** :
- [ ] La latence totale pour 3 requêtes simultanées est < 3.5s.
- [ ] Les traces Arize Phoenix montrent des barres de progression parallèles pour les retrievers.

---

## 🐳 PBI-020 : Infrastructure Cloud-Native (Docker Compose)
**Priorité** : Haute | **Estimation** : M

**User Story** : "En tant que DevOps, je veux déployer MinIO et Qdrant via Docker pour garantir la portabilité, la gratuité et la performance."

**Guide Technique (Lead-Dev)** :
- Créer un fichier `docker-compose.yml` incluant :
  - **Qdrant** : Port 6333 (API) et 6334 (gRPC).
  - **MinIO** : Port 9000 (API S3) et 9001 (Console).
- Configurer les volumes persistants pour éviter toute perte de données.
- Utiliser les images officielles `qdrant/qdrant` et `minio/minio`.

**Critères d'Acceptation (CA)** :
- [ ] `docker compose up -d` lance tous les services sans erreur.
- [ ] La console MinIO est accessible sur `localhost:9001`.
- [ ] L'API Qdrant répond sur `localhost:6333/dashboard`.

---

## ☁️ PBI-021 : Abstraction Stockage S3 (MinIO)
**Priorité** : Haute | **Estimation** : M

**User Story** : "En tant que Lead-Dev, je veux migrer le stockage des PDFs du système de fichiers local vers l'API S3 pour permettre une migration Cloud transparente."

**Guide Technique (Lead-Dev)** :
- Installer `s3fs`.
- Configurer `s3fs.S3FileSystem` avec l'endpoint local de MinIO (`http://localhost:9000`).
- Refactorer le `ThesesClient` pour uploader les PDFs dans un bucket MinIO au lieu de `data/`.
- Mettre à jour `SimpleDirectoryReader` pour lire depuis S3 via le paramètre `fs`.
- **Référence MCP context7** :
  ```python
  import s3fs
  fs = s3fs.S3FileSystem(endpoint_url="http://localhost:9000", key="minioadmin", secret="minioadmin")
  documents = SimpleDirectoryReader(input_dir="bucket_name/ia", fs=fs).load_data()
  ```

**Critères d'Acceptation (CA)** :
- [ ] Les nouveaux PDFs téléchargés apparaissent dans l'interface MinIO.
- [ ] Le pipeline RAG charge les documents depuis MinIO sans erreur.
- [ ] Aucune dépendance sur des chemins de fichiers locaux absolus.

---

## 🏁 PASSAGE DE RELAIS
1. L'infrastructure Docker est la priorité absolue pour permettre les autres développements.
2. Le refactoring S3 doit être fait avec précaution pour ne pas casser l'ingestion actuelle.

**PLANNING VALIDÉ. À TOI LEAD-DEV.**
