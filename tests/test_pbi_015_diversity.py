
from llama_index.core.schema import TextNode, NodeWithScore
from src.generation.rag_engine import DiversityPostprocessor

class TestDiversityPostprocessor:

    def test_diversity_filtering(self):
        """
        Vérifie que le post-processeur garde jusqu'à 2 fragments par document.
        """
        # Création de nodes fictifs
        node1 = TextNode(text="Fragment 1 Doc A", metadata={"titre": "Thèse A"})
        node2 = TextNode(text="Fragment 2 Doc A", metadata={"titre": "Thèse A"})
        node3 = TextNode(text="Fragment 3 Doc A", metadata={"titre": "Thèse A"})  # Troisième fragment de A
        node4 = TextNode(text="Fragment 1 Doc B", metadata={"titre": "Thèse B"})
        node5 = TextNode(text="Fragment 1 Doc C", metadata={"titre": "Thèse C"})
        
        nodes = [
            NodeWithScore(node=node1, score=0.9),
            NodeWithScore(node=node2, score=0.85),
            NodeWithScore(node=node3, score=0.8),
            NodeWithScore(node=node4, score=0.7),
            NodeWithScore(node=node5, score=0.6),
        ]
        
        processor = DiversityPostprocessor(target_top_n=5)  # On veut voir tous les nodes possibles
        filtered_nodes = processor._postprocess_nodes(nodes)
        
        # Avec max_per_doc=2 et target_top_n=5, on devrait avoir:
        # - 2 extraits de Thèse A (les 2 meilleurs: 0.9 et 0.85)
        # - 1 extrait de Thèse B (0.7)
        # - 1 extrait de Thèse C (0.6)
        # Total: 4 nodes (le troisième A est rejeté)
        assert len(filtered_nodes) == 4
        
        # Vérifier qu'on a bien 2 extraits de Thèse A
        titles = [n.node.metadata["titre"] for n in filtered_nodes]
        assert titles.count("Thèse A") == 2  # 2 extraits de Thèse A
        assert "Thèse B" in titles
        assert "Thèse C" in titles
        
        # Vérifier que les 2 meilleurs de A sont inclus
        a_nodes = [n for n in filtered_nodes if n.node.metadata["titre"] == "Thèse A"]
        assert len(a_nodes) == 2
        a_scores = [n.score for n in a_nodes]
        assert 0.9 in a_scores  # Meilleur score de A
        assert 0.85 in a_scores  # Deuxième meilleur score de A

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
