import logging
import networkx as nx
from typing import Dict, List

class ProtocolKnowledgeGraph:
    def __init__(self):
        self.logger = logging.getLogger("UPTKnowledgeGraph")
        self.graph = nx.DiGraph()
        self._build_initial_knowledge()

    def _build_initial_knowledge(self):
        """Initialize graph with known protocols"""
        try:
            protocols = [
                {"name": "HTTP", "features": {"header": "HTTP/1", "port": 80}},
                {"name": "MQTT", "features": {"header": "\x30", "port": 1883}},
                {"name": "BTC", "features": {"header": "\x02", "port": 8333}},
                {"name": "TCP", "features": {"header": "\x45", "port": 0}}
            ]
            for proto in protocols:
                self.graph.add_node(proto["name"], **proto["features"])
                if proto["name"] != "TCP":
                    self.graph.add_edge("TCP", proto["name"], cost=1.0)
            self.logger.info("Initialized protocol knowledge graph")
        except Exception as e:
            self.logger.error(f"Knowledge graph initialization error: {e}")

    def infer_unknown_protocol(self, observed_behavior: Dict) -> Dict:
        """Infer protocol from observed behavior"""
        try:
            similar_protocols = []
            for node, attrs in self.graph.nodes(data=True):
                similarity = self._calculate_similarity(observed_behavior, attrs)
                if similarity > 0.5:
                    similar_protocols.append((node, similarity))
            similar_protocols.sort(key=lambda x: x[1], reverse=True)
            return {
                "likely_protocols": [p[0] for p in similar_protocols[:3]],
                "confidence_scores": [p[1] for p in similar_protocols[:3]],
                "recommended_actions": ["translate" if p[1] > 0.8 else "log" for p in similar_protocols[:3]]
            }
        except Exception as e:
            self.logger.error(f"Protocol inference error: {e}")
            return {"likely_protocols": [], "confidence_scores": [], "recommended_actions": []}

    def _calculate_similarity(self, behavior: Dict, node_attrs: Dict) -> float:
        """Calculate similarity between observed behavior and known protocol"""
        entropy_match = 1 - abs(behavior.get("syntactic_analysis", {}).get("entropy", 0) - node_attrs.get("entropy", 0)) / max(1, behavior.get("syntactic_analysis", {}).get("entropy", 1))
        return entropy_match

    def add_protocol(self, protocol: Dict):
        """Add a new protocol to the graph"""
        try:
            self.graph.add_node(protocol["name"], **protocol["features"])
            self.graph.add_edge("TCP", protocol["name"], cost=1.5)
            self.logger.info(f"Added new protocol: {protocol['name']}")
        except Exception as e:
            self.logger.error(f"Add protocol error: {e}")

    def suggest_translation_path(self, source: str, target: str) -> List[Dict]:
        """Find optimal translation path"""
        try:
            paths = list(nx.all_shortest_paths(self.graph, source, target, weight="cost"))
            return [{"path": path, "cost": sum(self.graph[path[i]][path[i+1]].get("cost", 1.0) for i in range(len(path)-1))} for path in paths]
        except Exception as e:
            self.logger.error(f"Translation path error: {e}")
            return []