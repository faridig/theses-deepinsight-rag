import os
import logging
import json
import asyncio
from typing import Optional, Sequence, Any
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.http import models as rest
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.schema import BaseNode, TextNode

logger = logging.getLogger(__name__)

class VectorService:
    """
    Service for managing vector indexing and retrieval using Qdrant and LlamaIndex.
    Optimisé pour l'isolation des domaines (PBI-023).
    """
    def __init__(self, storage_path: str = "./storage/qdrant", collection_name: str = "theses-default", client: Optional[QdrantClient] = None, aclient: Optional[Any] = None):
        self.storage_path = storage_path
        self.collection_name = collection_name
        
        # Initialisation des clients Qdrant
        if client:
            self.client = client
            self.aclient = aclient
        else:
            qdrant_url = os.getenv("QDRANT_URL")
            if qdrant_url:
                logger.info(f"Utilisation du serveur Qdrant à {qdrant_url}")
                # Migration gRPC (PBI-022)
                # Si l'URL contient un port (ex: :6333), on tente de passer en gRPC sur 6334
                # Sinon on utilise prefer_grpc=True
                self.client = QdrantClient(url=qdrant_url, prefer_grpc=True)
                self.aclient = AsyncQdrantClient(url=qdrant_url, prefer_grpc=True)
            elif self.storage_path == ":memory:":
                logger.info("Utilisation de Qdrant en mémoire")
                self.client = QdrantClient(":memory:")
                self.aclient = None # L'async est désactivé en local pour éviter les verrous
            else:
                logger.info(f"Utilisation du stockage local Qdrant : {self.storage_path}")
                os.makedirs(self.storage_path, exist_ok=True)
                self.client = QdrantClient(path=self.storage_path)
                self.aclient = None 
        
        # Initialisation du Vector Store Qdrant
        self.vector_store = QdrantVectorStore(
            collection_name=self.collection_name, 
            client=self.client, 
            aclient=self.aclient
        )
        
        # Initialisation du StorageContext
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        
        self._index: Optional[VectorStoreIndex] = None

    @property
    def index(self) -> VectorStoreIndex:
        """Retourne l'index actuel, en le chargeant depuis le vector store si nécessaire."""
        if self._index is None:
            self._index = VectorStoreIndex.from_vector_store(
                self.vector_store,
                storage_context=self.storage_context
            )
        return self._index

    async def create_collection_if_not_exists(self, collection_name: str, vector_size: int = 1536):
        """
        Crée une collection Qdrant de manière asynchrone si elle n'existe pas (PBI-023).
        """
        if self.aclient:
            try:
                collections = await self.aclient.get_collections()
                collection_names = [c.name for c in collections.collections]
                if collection_name not in collection_names:
                    # Durcissement Qdrant (PBI-022)
                    # - scalar_quantization: Int8
                    # - on_disk: true pour les vecteurs
                    await self.aclient.create_collection(
                        collection_name=collection_name,
                        vectors_config=rest.VectorParams(
                            size=vector_size, 
                            distance=rest.Distance.COSINE,
                            on_disk=True
                        ),
                        quantization_config=rest.ScalarQuantization(
                            scalar=rest.ScalarQuantizationConfig(
                                type=rest.ScalarType.INT8,
                                always_ram=False,
                            ),
                        ),
                    )
            except Exception as e:
                logger.error(f"Erreur async lors de la création de collection : {e}")
        else:
            try:
                def _create():
                    collections = self.client.get_collections()
                    collection_names = [c.name for c in collections.collections]
                    if collection_name not in collection_names:
                        # Durcissement Qdrant (PBI-022)
                        self.client.create_collection(
                            collection_name=collection_name,
                            vectors_config=rest.VectorParams(
                                size=vector_size, 
                                distance=rest.Distance.COSINE,
                                on_disk=True
                            ),
                            quantization_config=rest.ScalarQuantization(
                                scalar=rest.ScalarQuantizationConfig(
                                    type=rest.ScalarType.INT8,
                                    always_ram=False,
                                ),
                            ),
                        )
                await asyncio.to_thread(_create)
            except Exception as e:
                logger.error(f"Erreur sync lors de la création de collection : {e}")

    def index_nodes(self, nodes: Sequence[BaseNode]) -> VectorStoreIndex:
        """
        Indexe les nœuds dans la collection actuelle.
        """
        if self._index is None:
            self._index = VectorStoreIndex(
                nodes, 
                storage_context=self.storage_context
            )
        else:
            self._index.insert_nodes(nodes)
            
        return self._index

    def get_all_nodes(self) -> Sequence[BaseNode]:
        """
        Récupère tous les nœuds de la collection Qdrant.
        """
        points, _ = self.client.scroll(
            collection_name=self.collection_name,
            with_payload=True,
            with_vectors=False,
        )
        
        nodes = []
        for point in points:
            payload = point.payload or {}
            if "_node_content" in payload:
                node_data = json.loads(payload["_node_content"])
                nodes.append(TextNode.from_dict(node_data))
            else:
                nodes.append(TextNode(
                    text=payload.get("text", ""),
                    id_=str(point.id),
                    metadata=payload.get("metadata", {})
                ))
        return nodes

    def list_collections(self) -> list[str]:
        """
        Liste toutes les collections disponibles dans Qdrant,
        filtrées pour ne garder que les thèmes de thèses (PBI-035).
        Optimisé pour le nettoyage de la pollution (PBI-Review).
        """
        try:
            collections_response = self.client.get_collections()
            all_names = [c.name for c in collections_response.collections]
            
            # Filtrage rigoureux (PBI-Review)
            # On exclut les collections de test, par défaut ou techniques
            # On ne garde que celles commençant par 'theses-'
            filtered = [
                name for name in all_names 
                if name.startswith("theses-") 
                and not any(x in name.lower() for x in ["test", "default", "tmp", "persist"])
            ]
            
            # Si aucune collection filtrée n'existe, on peut autoriser theses-default par sécurité
            if not filtered and "theses-default" in all_names:
                filtered = ["theses-default"]
                
            return sorted(filtered)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des collections : {e}")
            return []

    def get_collection_stats(self, collection_name: Optional[str] = None) -> dict[str, Any]:
        """
        Récupère des statistiques sur une collection (PBI-037).
        """
        target = collection_name or self.collection_name
        try:
            info = self.client.get_collection(collection_name=target)
            # Utilisation de getattr pour la robustesse selon la version de qdrant-client
            points_count = getattr(info, "points_count", 0)
            if points_count is None:
                points_count = 0
            
            return {
                "points_count": points_count,
                "status": str(info.status),
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stats de {target} : {e}")
            return {"points_count": 0, "status": "error"}

    def get_retriever(self, similarity_top_k: int = 5):
        """
        Retourne un retriever pour l'index actuel.
        """
        return self.index.as_retriever(similarity_top_k=similarity_top_k)

    def query(self, query_text: str, similarity_top_k: int = 5):
        """
        Exécute une requête et retourne les meilleurs résultats.
        """
        retriever = self.get_retriever(similarity_top_k=similarity_top_k)
        return retriever.retrieve(query_text)

    def close(self):
        """Ferme les clients Qdrant."""
        self.client.close()
        if self.aclient:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.aclient.close())
                else:
                    asyncio.run(self.aclient.close())
            except Exception:
                pass
