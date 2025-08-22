import random
import requests
import time
from typing import Dict, List

class LoadBalancer:
    def __init__(self, agent_url: str = "http://localhost:9999"):
        self.agent_url = agent_url
        self.translator_nodes: List[str] = []
        self.node_metrics: Dict[str, Dict] = {}
        self.update_nodes()
    
    def update_nodes(self):
        """Dynamically discover translator nodes from Agent's knowledge base"""
        try:
            response = requests.get(f"{self.agent_url}/knowledge", timeout=5)
            knowledge = response.json()
            # Assume Agent provides known Translator nodes in translation_patterns
            nodes = []
            for src, targets in knowledge.get('translation_patterns', {}).items():
                for target in targets:
                    if target.startswith('http://'):
                        nodes.append(target)
            self.translator_nodes = nodes or ["http://localhost:8888"]  # Fallback
            self.node_metrics = {node: {'load': 0, 'success': 0, 'last_checked': 0} for node in self.translator_nodes}
            print(f"📡 Discovered {len(self.translator_nodes)} translator nodes: {self.translator_nodes}")
        except Exception as e:
            print(f"❌ Failed to discover nodes: {e}")
            self.translator_nodes = ["http://localhost:8888"]
            self.node_metrics = {node: {'load': 0, 'success': 0, 'last_checked': 0} for node in self.translator_nodes}
    
    def check_node_health(self, node: str) -> bool:
        """Check if a translator node is healthy"""
        try:
            response = requests.get(f"{node}/", timeout=2)
            return response.status_code < 500
        except:
            return False
    
    def update_metrics(self, node: str, success: bool, load_increment: float = 1.0):
        """Update node metrics based on translation outcome"""
        if node in self.node_metrics:
            self.node_metrics[node]['load'] = max(0, self.node_metrics[node]['load'] + load_increment - 0.1)  # Decay
            if success:
                self.node_metrics[node]['success'] += 1
            self.node_metrics[node]['last_checked'] = time.time()
    
    def select_translator(self, packet_priority: float) -> str:
        """Select best translator node based on load and priority"""
        # Update nodes periodically (every 60 seconds)
        if time.time() - max(m['last_checked'] for m in self.node_metrics.values()) > 60:
            self.update_nodes()
        
        # Filter healthy nodes
        healthy_nodes = [node for node in self.translator_nodes if self.check_node_health(node)]
        if not healthy_nodes:
            print("⚠️ No healthy translator nodes available, using default")
            return self.translator_nodes[0]
        
        # Adjust weights based on priority (higher priority prefers lower load)
        weights = [
            (1 / (self.node_metrics[node]['load'] + 0.1)) * (1 + packet_priority / 10)
            for node in healthy_nodes
        ]
        total = sum(weights)
        probabilities = [w / total for w in weights] if total > 0 else [1/len(healthy_nodes)] * len(healthy_nodes)
        
        selected_node = random.choices(healthy_nodes, weights=probabilities, k=1)[0]
        self.node_metrics[selected_node]['load'] += 1.0
        return selected_node