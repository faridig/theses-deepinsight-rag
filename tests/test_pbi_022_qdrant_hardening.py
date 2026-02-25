import pytest
import os
import asyncio
from src.indexing.vector_service import VectorService
from qdrant_client.http import models as rest

@pytest.mark.asyncio
async def test_qdrant_hardening_configuration():
    """
    Test que la configuration de durcissement (gRPC, Quantification, On-disk) est bien appliquée.
    """
    collection_name = "test-hardening-collection"
    # On utilise le serveur Qdrant réel si disponible, sinon on saute le test
    qdrant_url = os.getenv("QDRANT_URL")
    if not qdrant_url or "localhost" not in qdrant_url:
        pytest.skip("Serveur Qdrant local non disponible pour le test de durcissement")

    service = VectorService(collection_name=collection_name)
    
    # 1. Vérifier gRPC (difficile à vérifier directement sur l'objet client sans introspection complexe, 
    # mais on peut vérifier que ça ne crash pas et que prefer_grpc est bien passé si on pouvait accéder aux internes)
    # On va surtout vérifier la création de collection avec les bons paramètres.
    
    try:
        # Nettoyage préalable
        if service.aclient:
            try:
                await service.aclient.delete_collection(collection_name)
            except Exception:
                pass
        
        # Création de la collection
        await service.create_collection_if_not_exists(collection_name, vector_size=1536)
        
        # Vérification des paramètres de la collection
        info = await service.aclient.get_collection(collection_name)
        
        # Vérification on_disk
        assert info.config.params.vectors.on_disk is True
        
        # Vérification quantification
        assert info.config.quantization_config is not None
        assert info.config.quantization_config.scalar.type == rest.ScalarType.INT8
        
        print(f"\n[OK] Collection {collection_name} configurée avec succès (On-disk: True, Quantization: INT8)")

    finally:
        # Nettoyage rigoureux (PBI-Review: Hygiène Qdrant)
        # On essaie via aclient d'abord, puis client sync par sécurité
        try:
            if service.aclient:
                await service.aclient.delete_collection(collection_name)
            elif service.client:
                service.client.delete_collection(collection_name)
            print(f"[CLEANUP] Collection {collection_name} supprimée.")
        except Exception as e:
            print(f"[WARNING] Échec du nettoyage de la collection : {e}")
        
        service.close()

if __name__ == "__main__":
    asyncio.run(test_qdrant_hardening_configuration())
