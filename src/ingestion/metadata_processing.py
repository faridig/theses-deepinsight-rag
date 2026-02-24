import logging
from typing import Sequence, List, Any
from llama_index.core.schema import BaseNode, TransformComponent
from llama_index.core.extractors import TitleExtractor, SummaryExtractor
from pydantic import Field, PrivateAttr
from src.config import get_ollama_llm

logger = logging.getLogger(__name__)

class ThesisMetadataProcessor(TransformComponent):
    """
    Composant de transformation pour le filtrage et l'extraction de métadonnées (PBI-080).
    Utilise Ollama pour le titre et le résumé.
    """
    ollama_model: str = Field(default="llama3.2:3b", description="Modèle Ollama à utiliser")
    exclude_keywords: List[str] = Field(
        default_factory=lambda: ["remerciements", "dédicaces", "acknowledgements", "dedications"]
    )
    priority_keywords: List[str] = Field(
        default_factory=lambda: ["abstract", "résumé", "conclusion", "introduction"]
    )
    
    _llm: Any = PrivateAttr()
    _title_extractor: Any = PrivateAttr()
    _summary_extractor: Any = PrivateAttr()
    
    def __init__(self, **data):
        super().__init__(**data)
        self._llm = get_ollama_llm(model=self.ollama_model)
        self._title_extractor = TitleExtractor(llm=self._llm, nodes=5)
        self._summary_extractor = SummaryExtractor(llm=self._llm, summaries=["self"])

    def _should_exclude(self, node: BaseNode) -> bool:
        """
        Détermine si un nœud doit être exclu du traitement des métadonnées (PBI-080).
        """
        text = node.get_content().lower()
        
        # Vérification des headings si présents (via Docling)
        headings = node.metadata.get("headings", "")
        if isinstance(headings, list):
            headings = " ".join(headings).lower()
        else:
            headings = str(headings).lower()
            
        for kw in self.exclude_keywords:
            if kw in headings or (len(text) < 500 and kw in text[:200]):
                return True
        return False

    def _is_priority(self, node: BaseNode) -> bool:
        """
        Détermine si un nœud est prioritaire pour l'extraction de métadonnées.
        """
        text = node.get_content().lower()
        headings = node.metadata.get("headings", "")
        if isinstance(headings, list):
            headings = " ".join(headings).lower()
        else:
            headings = str(headings).lower()
            
        for kw in self.priority_keywords:
            if kw in headings or kw in text[:300]:
                return True
        return False

    def __call__(self, nodes: Sequence[BaseNode], **kwargs) -> Sequence[BaseNode]:
        """
        Exécute le filtrage et l'extraction.
        """
        if not nodes:
            return nodes

        logger.info(f"Traitement des métadonnées via Ollama pour {len(nodes)} nœuds.")

        # 1. Filtrage pour l'extraction (on ne garde que les nœuds utiles pour le titre/résumé)
        filtered_nodes_for_metadata = [
            node for node in nodes 
            if not self._should_exclude(node) and (self._is_priority(node) or node.metadata.get("page_label") in ["1", "2", "3"])
        ]
        
        # Si aucun nœud filtré, on prend les premiers par défaut
        if not filtered_nodes_for_metadata:
            filtered_nodes_for_metadata = nodes[:10]

        try:
            # 2. Extraction du titre (sur les 5 premiers nœuds filtrés)
            title_nodes = filtered_nodes_for_metadata[:5]
            # TitleExtractor.extract() attend une liste de nodes et retourne une liste de dicts de métadonnées
            # On va le faire manuellement pour avoir plus de contrôle si besoin, 
            # mais on peut utiliser l'interface standard.
            titles_meta = self._title_extractor.extract(title_nodes)
            
            # 3. Extraction du résumé
            # On prend un échantillon représentatif (début, milieu, fin des nœuds filtrés)
            summary_sample = list(filtered_nodes_for_metadata)
            if len(summary_sample) > 10:
                summary_sample = summary_sample[:5] + summary_sample[-5:]
                
            summaries_meta = self._summary_extractor.extract(summary_sample)

            # 4. Propagation des métadonnées à TOUS les nœuds du document
            # (LlamaIndex le fait généralement si on passe par IngestionPipeline, 
            # mais ici on assure la cohérence).
            
            # On récupère le titre le plus fréquent ou le premier trouvé
            final_title = "Titre non extrait"
            for m in titles_meta:
                if "document_title" in m:
                    final_title = m["document_title"]
                    break
            
            # On combine les résumés si nécessaire (ici on en prend un seul global)
            final_summary = "Résumé non extrait"
            for m in summaries_meta:
                if "section_summary" in m: # SummaryExtractor utilise souvent section_summary
                    final_summary = m["section_summary"]
                    break

            for node in nodes:
                node.metadata["extracted_title"] = final_title
                node.metadata["ollama_summary"] = final_summary
                
            logger.info(f"Métadonnées extraites avec succès : {final_title[:50]}...")

        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de métadonnées via Ollama : {e}")
            # On continue sans bloquer l'ingestion
            
        return nodes
