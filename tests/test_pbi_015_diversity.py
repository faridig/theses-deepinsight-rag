
from llama_index.core.schema import TextNode, NodeWithScore
from src.generation.rag_engine import DiversityPostprocessor

class TestDiversityPostprocessor:

    def test_diversity_filtering(self):
        """
        Vérifie que le post-processeur ne garde qu'un fragment par document.
        """
        # Création de nodes fictifs
        node1 = TextNode(text="Fragment 1 Doc A", metadata={"titre": "Thèse A"})
        node2 = TextNode(text="Fragment 2 Doc A", metadata={"titre": "Thèse A"})
        node3 = TextNode(text="Fragment 1 Doc B", metadata={"titre": "Thèse B"})
        node4 = TextNode(text="Fragment 1 Doc C", metadata={"titre": "Thèse C"})
        
        nodes = [
            NodeWithScore(node=node1, score=0.9),
            NodeWithScore(node=node2, score=0.85),
            NodeWithScore(node=node3, score=0.8),
            NodeWithScore(node=node4, score=0.7),
        ]
        
        processor = DiversityPostprocessor(target_top_n=3)
        filtered_nodes = processor._postprocess_nodes(nodes)
        
        # On doit avoir 3 nodes au total (A, B, C)
        assert len(filtered_nodes) == 3
        
        # On doit avoir le meilleur de A (score 0.9)
        assert filtered_nodes[0].node.get_content() == "Fragment 1 Doc A"
        assert filtered_nodes[0].score == 0.9
        
        # On doit avoir B et C
        titles = [n.node.metadata["titre"] for n in filtered_nodes]
        assert "Thèse A" in titles
        assert "Thèse B" in titles
        assert "Thèse C" in titles
        assert titles.count("Thèse A") == 1

    def test_diversity_limit(self):
        """
        Vérifie que la limite target_top_n est respectée.
        """
        node1 = TextNode(text="A", metadata={"titre": "A"})
        node2 = TextNode(text="B", metadata={"titre": "B"})
        node3 = TextNode(text="C", metadata={"titre": "C"})
        node4 = TextNode(text="D", metadata={"titre": "D"})
        
        nodes = [
            NodeWithScore(node=node1, score=0.9),
            NodeWithScore(node=node2, score=0.8),
            NodeWithScore(node=node3, score=0.7),
            NodeWithScore(node=node4, score=0.6),
        ]
        
        processor = DiversityPostprocessor(target_top_n=2)
        filtered_nodes = processor._postprocess_nodes(nodes)
        
        assert len(filtered_nodes) == 2
        assert filtered_nodes[0].node.metadata["titre"] == "A"
        assert filtered_nodes[1].node.metadata["titre"] == "B"

    def test_diversity_fallback_to_node_id(self):
        """
        Vérifie que si le titre est absent, on utilise le node_id (pas de filtrage excessif).
        """
        node1 = TextNode(text="A", id_="id1")
        node2 = TextNode(text="B", id_="id2")
        
        nodes = [
            NodeWithScore(node=node1, score=0.9),
            NodeWithScore(node=node2, score=0.8),
        ]
        
        processor = DiversityPostprocessor(target_top_n=3)
        filtered_nodes = processor._postprocess_nodes(nodes)
        
        assert len(filtered_nodes) == 2
