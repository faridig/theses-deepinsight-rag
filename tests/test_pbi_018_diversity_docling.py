
from llama_index.core.schema import TextNode, NodeWithScore
from src.generation.rag_engine import DiversityPostprocessor

class TestDiversityDocling:

    def test_diversity_with_file_name(self):
        """
        Vérifie que le post-processeur utilise file_name si titre est absent (Cas Docling).
        """
        # Nodes avec file_name au lieu de titre
        node1 = TextNode(text="Frag 1 Doc A", metadata={"file_name": "these_a.pdf"})
        node2 = TextNode(text="Frag 2 Doc A", metadata={"file_name": "these_a.pdf"})
        node3 = TextNode(text="Frag 3 Doc A", metadata={"file_name": "these_a.pdf"})  # Troisième fragment
        node4 = TextNode(text="Frag 1 Doc B", metadata={"file_name": "these_b.pdf"})
        
        nodes = [
            NodeWithScore(node=node1, score=0.9),
            NodeWithScore(node=node2, score=0.85),
            NodeWithScore(node=node3, score=0.8),
            NodeWithScore(node=node4, score=0.7),
        ]
        
        # On veut jusqu'à 2 extraits par document
        processor = DiversityPostprocessor(target_top_n=4)  # On veut voir tous les nodes possibles
        filtered_nodes = processor._postprocess_nodes(nodes)
        
        # Avec max_per_doc=2 et target_top_n=4, on devrait avoir:
        # - 2 extraits de these_a.pdf (les 2 meilleurs: 0.9 et 0.85)
        # - 1 extrait de these_b.pdf (0.7)
        # Total: 3 nodes (le troisième A est rejeté)
        assert len(filtered_nodes) == 3
        
        file_names = [n.node.metadata["file_name"] for n in filtered_nodes]
        assert file_names.count("these_a.pdf") == 2  # 2 extraits de these_a.pdf
        assert "these_b.pdf" in file_names
        
        # Vérifier que les 2 meilleurs de A sont inclus
        a_nodes = [n for n in filtered_nodes if n.node.metadata["file_name"] == "these_a.pdf"]
        assert len(a_nodes) == 2
        a_scores = [n.score for n in a_nodes]
        assert 0.9 in a_scores  # Meilleur score de A
        assert 0.85 in a_scores  # Deuxième meilleur score de A

    def test_diversity_mixed_metadata(self):
        """
        Vérifie la priorité entre titre et file_name.
        """
        # Un node avec titre (ancien format/LlamaParse)
        node1 = TextNode(text="A", metadata={"titre": "Thèse A", "file_name": "a.pdf"})
        # Un node avec seulement file_name (nouveau format/Docling)
        node2 = TextNode(text="B", metadata={"file_name": "a.pdf"})
        
        nodes = [
            NodeWithScore(node=node1, score=0.9),
            NodeWithScore(node=node2, score=0.8),
        ]
        
        # Si on considère que a.pdf et Thèse A sont le même doc (via file_name), 
        # on ne devrait en avoir qu'un.
        # MAIS si on utilise le titre d'abord, on risque d'en avoir deux si l'autre n'a pas de titre.
        # L'objectif du PBI est d'éviter le monopole.
        
        processor = DiversityPostprocessor(target_top_n=2)
        filtered_nodes = processor._postprocess_nodes(nodes)
        
        # Actuellement, il en renvoie 2 car "Thèse A" != "a.pdf"
        # C'est le comportement attendu pour l'instant pour éviter les faux positifs de déduplication
        assert len(filtered_nodes) == 2

    def test_node_cleaning_preserves_file_name_if_no_titre(self):
        """
        Vérifie que NodeCleaningProcessor permet au LLM de voir file_name si titre absent.
        """
        from src.generation.rag_engine import NodeCleaningProcessor
        
        node_no_title = TextNode(text="Content", metadata={"file_name": "test.pdf"})
        node_with_title = TextNode(text="Content", metadata={"titre": "Title", "file_name": "test.pdf"})
        
        nodes = [
            NodeWithScore(node=node_no_title, score=1.0),
            NodeWithScore(node=node_with_title, score=1.0)
        ]
        
        processor = NodeCleaningProcessor()
        processed_nodes = processor._postprocess_nodes(nodes)
        
        # Node sans titre : file_name ne doit pas être dans excluded_llm_metadata_keys
        assert "file_name" not in processed_nodes[0].node.excluded_llm_metadata_keys
        # Node avec titre : file_name doit être dans excluded_llm_metadata_keys
        assert "file_name" in processed_nodes[1].node.excluded_llm_metadata_keys
