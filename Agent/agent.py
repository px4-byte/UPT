import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import sqlite3
import json
import time as time_module
import threading
import socket
import struct
import hashlib
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging
from typing import Dict, List, Optional, Tuple
import argparse
import yaml
import requests

class MulticastKnowledgeSharing:
    def __init__(self, multicast_group: str = "239.255.0.1", port: int = 5000, ttl: int = 2):
        self.multicast_group = multicast_group
        self.port = port
        self.ttl = ttl
        self.logger = logging.getLogger("UPTAgent")
        self.running = False
        self.sock = None
        self.node_id = hashlib.md5(socket.gethostname().encode()).hexdigest()[:8]  # Unique node identifier

    def start(self, protocol_knowledge: Dict, update_callback: callable):
        """Start multicast sender and receiver threads"""
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, self.ttl)
        # Bind to receive multicast
        self.sock.bind(("", self.port))
        mreq = struct.pack("4sl", socket.inet_aton(self.multicast_group), socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        # Start sender and receiver threads
        sender_thread = threading.Thread(target=self._send_knowledge, args=(protocol_knowledge,), daemon=True)
        receiver_thread = threading.Thread(target=self._receive_knowledge, args=(protocol_knowledge, update_callback), daemon=True)
        sender_thread.start()
        receiver_thread.start()
        self.logger.info(f"Started multicast knowledge sharing on {self.multicast_group}:{self.port}")

    def _send_knowledge(self, protocol_knowledge: Dict):
        """Periodically send protocol knowledge to multicast group"""
        while self.running:
            try:
                knowledge = {
                    "node_id": self.node_id,
                    "timestamp": datetime.now().isoformat(),
                    "protocols": protocol_knowledge["protocols"],
                    "translation_patterns": protocol_knowledge["translation_patterns"],
                    "signature": self._sign_knowledge(protocol_knowledge)
                }
                data = json.dumps(knowledge).encode("utf-8")
                self.sock.sendto(data, (self.multicast_group, self.port))
                self.logger.debug(f"Sent knowledge to {self.multicast_group}:{self.port}")
                time_module.sleep(60)  # Send every 60 seconds
            except Exception as e:
                self.logger.error(f"Multicast send error: {e}")
                time_module.sleep(10)

    def _receive_knowledge(self, protocol_knowledge: Dict, update_callback: callable):
        """Receive and merge knowledge from other nodes"""
        while self.running:
            try:
                data, _ = self.sock.recvfrom(4096)
                knowledge = json.loads(data.decode("utf-8"))
                if knowledge["node_id"] == self.node_id:
                    continue  # Ignore own messages
                if not self._verify_signature(knowledge):
                    self.logger.warning(f"Invalid signature from {knowledge['node_id']}")
                    continue
                update_callback(knowledge["protocols"], knowledge["translation_patterns"])
                self.logger.info(f"Received and merged knowledge from {knowledge['node_id']}")
            except Exception as e:
                self.logger.error(f"Multicast receive error: {e}")
                time_module.sleep(1)

    def _sign_knowledge(self, knowledge: Dict) -> str:
        """Generate a simple signature for knowledge data"""
        data = json.dumps({
            "protocols": knowledge["protocols"],
            "translation_patterns": knowledge["translation_patterns"]
        })
        return hashlib.sha256(data.encode()).hexdigest()

    def _verify_signature(self, knowledge: Dict) -> bool:
        """Verify the signature of received knowledge"""
        expected_signature = self._sign_knowledge(knowledge)
        return knowledge["signature"] == expected_signature

    def stop(self):
        """Stop multicast operations"""
        self.running = False
        if self.sock:
            self.sock.close()
        self.logger.info("Stopped multicast knowledge sharing")

class UPTAgent:
    def __init__(self, sniffer_db: str = "../Sniffer/packets.db", translator_url: str = "http://localhost:8888"):
        self.sniffer_db = sniffer_db
        self.translator_url = translator_url
        self.decision_memory = deque(maxlen=1000)
        self.routing_table = {}
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s - %(pathname)s',
            filename='upt_agent.log',
            filemode='a'
        )
        self.logger = logging.getLogger("UPTAgent")
        try:
            with open("agent_config.yaml", 'r') as f:
                config = yaml.safe_load(f)
            self.learning_rate = config['learning']['rate']
            self.throughput_baseline = config['decision_making'].get('max_throughput', 10)
            self.max_sources = config['security']['max_connections_per_second']
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            self.learning_rate = 0.1
            self.throughput_baseline = 10
            self.max_sources = 100
        self.protocol_knowledge = self.load_knowledge_base()
        self.running = False
        self.multicast_sharing = MulticastKnowledgeSharing()
        self.logger.info("Initialized UPT Agent - Ready to learn and decide!")

    def load_knowledge_base(self) -> Dict:
        """Load learned protocol knowledge from database"""
        try:
            conn = sqlite3.connect(self.sniffer_db, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS protocol_clusters (
                    cluster_id INTEGER PRIMARY KEY,
                    protocol_name TEXT,
                    packet_count INTEGER
                )
            """)
            conn.commit()
            cursor.execute("SELECT cluster_id, protocol_name, packet_count FROM protocol_clusters")
            protocols = {}
            for row in cursor.fetchall():
                protocols[row[0]] = {'name': row[1], 'count': row[2]}
            if not protocols:
                cursor.execute("SELECT protocol, COUNT(*) as count FROM fingerprints GROUP BY protocol")
                for i, (protocol, count) in enumerate(cursor.fetchall()):
                    protocols[i] = {'name': protocol, 'count': count}
            translation_patterns = {}
            try:
                translations_db = os.path.join(os.path.dirname(self.sniffer_db), "../Translator/translation_sessions.db")
                trans_conn = sqlite3.connect(translations_db, check_same_thread=False)
                trans_cursor = trans_conn.cursor()
                trans_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='translation_sessions'")
                if not trans_cursor.fetchone():
                    self.logger.warning(f"translation_sessions table not found in {translations_db} - starting fresh")
                else:
                    trans_cursor.execute("""
                        SELECT source_protocol, target_protocol, COUNT(*) as count 
                        FROM translation_sessions 
                        GROUP BY source_protocol, target_protocol
                    """)
                    for src, tgt, count in trans_cursor.fetchall():
                        if src not in translation_patterns:
                            translation_patterns[src] = {}
                        translation_patterns[src][tgt] = count
                trans_conn.close()
            except sqlite3.Error as e:
                self.logger.warning(f"Error accessing translation_sessions.db: {e} - starting fresh")
            conn.close()
            return {
                'protocols': protocols,
                'translation_patterns': translation_patterns,
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Failed to load knowledge base: {e}")
            return {'protocols': {}, 'translation_patterns': {}, 'last_updated': datetime.now().isoformat()}

    def merge_knowledge(self, protocols: Dict, translation_patterns: Dict):
        """Merge knowledge received from other nodes"""
        try:
            # Merge protocols
            for cluster_id, proto_data in protocols.items():
                if cluster_id not in self.protocol_knowledge['protocols']:
                    self.protocol_knowledge['protocols'][cluster_id] = proto_data
                else:
                    self.protocol_knowledge['protocols'][cluster_id]['count'] += proto_data['count']
            # Merge translation patterns
            for src_proto, targets in translation_patterns.items():
                if src_proto not in self.protocol_knowledge['translation_patterns']:
                    self.protocol_knowledge['translation_patterns'][src_proto] = {}
                for tgt_proto, count in targets.items():
                    if tgt_proto not in self.protocol_knowledge['translation_patterns'][src_proto]:
                        self.protocol_knowledge['translation_patterns'][src_proto][tgt_proto] = count
                    else:
                        self.protocol_knowledge['translation_patterns'][src_proto][tgt_proto] += count
            self.protocol_knowledge['last_updated'] = datetime.now().isoformat()
            self.logger.info("Merged knowledge from multicast")
        except Exception as e:
            self.logger.error(f"Error merging knowledge: {e}")

    def analyze_network_patterns(self):
        """Continuously analyze network traffic patterns"""
        while self.running:
            try:
                conn = sqlite3.connect(self.sniffer_db, check_same_thread=False)
                cursor = conn.cursor()
                five_min_ago = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    SELECT protocol, COUNT(*) as packet_count,
                           AVG(packet_length) as avg_size,
                           COUNT(DISTINCT source_ip) as unique_sources
                    FROM fingerprints 
                    WHERE timestamp > ? 
                    GROUP BY protocol
                    ORDER BY packet_count DESC
                """, (five_min_ago,))
                current_traffic = {}
                for row in cursor.fetchall():
                    protocol, count, avg_size, unique_sources = row
                    current_traffic[protocol] = {
                        'packet_count': count,
                        'avg_size': avg_size,
                        'unique_sources': unique_sources,
                        'throughput': count / 300
                    }
                self.detect_anomalies(current_traffic)
                self.optimize_routing_strategy(current_traffic)
                conn.close()
                time_module.sleep(30)
            except Exception as e:
                self.logger.error(f"Analysis error: {e}")
                time_module.sleep(60)

    def detect_anomalies(self, traffic_data: Dict):
        """Detect unusual network patterns"""
        for protocol, stats in traffic_data.items():
            if stats['throughput'] > self.throughput_baseline * 5:
                self.logger.warning(f"HIGH TRAFFIC ALERT: {protocol} - {stats['throughput']:.1f} pps")
                self.trigger_defensive_measures(protocol)
            if stats['unique_sources'] > self.max_sources:
                self.logger.warning(f"MULTI-SOURCE ALERT: {protocol} - {stats['unique_sources']} unique sources")

    def trigger_defensive_measures(self, protocol: str):
        """Take action against suspicious traffic"""
        defensive_actions = {
            'priority': 'medium',
            'action': 'rate_limit',
            'protocol': protocol,
            'max_throughput': 20,
            'duration_minutes': 5
        }
        self.logger.info(f"Defense triggered: {defensive_actions}")
        self.apply_routing_policy(defensive_actions)

    def apply_routing_policy(self, actions: Dict):
        """Apply routing policy (placeholder for future implementation)"""
        self.logger.info(f"Applying policy: {actions}")

    def optimize_routing_strategy(self, traffic_data: Dict):
        """Dynamically optimize translation routing based on current traffic"""
        optimal_paths = {}
        for protocol in traffic_data.keys():
            best_target = self.choose_best_translation_target(protocol)
            if best_target:
                optimal_paths[protocol] = {
                    'target': best_target,
                    'confidence': self.calculate_confidence(protocol, best_target),
                    'expected_latency': self.estimate_latency(protocol, best_target)
                }
        self.update_routing_table(optimal_paths)

    def choose_best_translation_target(self, source_protocol: str) -> Optional[str]:
        """Choose the best target protocol for translation"""
        if source_protocol in self.protocol_knowledge['translation_patterns']:
            targets = self.protocol_knowledge['translation_patterns'][source_protocol]
            if targets:
                return max(targets.items(), key=lambda x: x[1])[0]
        if 'HTTP' in source_protocol:
            return 'MQTT'
        elif 'MQTT' in source_protocol:
            return 'HTTP'
        elif 'BTC' in source_protocol:
            return 'HTTP'
        elif 'TCP' in source_protocol:
            return 'JSON'
        return None

    def calculate_confidence(self, source_protocol: str, target_protocol: str) -> float:
        """Calculate confidence score for translation"""
        if source_protocol in self.protocol_knowledge['translation_patterns']:
            if target_protocol in self.protocol_knowledge['translation_patterns'][source_protocol]:
                success_count = self.protocol_knowledge['translation_patterns'][source_protocol][target_protocol]
                return min(1.0, success_count / 10.0)
        return 0.6

    def estimate_latency(self, source_protocol: str, target_protocol: str) -> float:
        """Estimate translation latency (placeholder)"""
        return 10.0

    def update_routing_table(self, paths: Dict):
        """Update routing table with new paths"""
        self.routing_table.update(paths)

    def make_decision(self, packet_data: bytes, source_info: Dict) -> Dict:
        """Make intelligent translation decision for a packet"""
        source_protocol = self.identify_protocol_from_data(packet_data)
        target_info = self.routing_table.get(source_protocol, {})
        target_protocol = target_info.get('target', 'HTTP')
        decision = {
            'source_protocol': source_protocol,
            'target_protocol': target_protocol,
            'confidence': self.calculate_confidence(source_protocol, target_protocol),
            'estimated_latency_ms': self.estimate_latency(source_protocol, target_protocol),
            'timestamp': datetime.now().isoformat(),
            'decision_id': hash((source_protocol, target_protocol, time_module.time()))
        }
        self.decision_memory.append(decision)
        return decision

    def identify_protocol_from_data(self, packet_data: bytes) -> str:
        """Simple protocol identification from packet data"""
        if packet_data.startswith(b'HTTP'):
            return 'HTTP'
        elif packet_data.startswith(b'\x30'):
            return 'MQTT'
        elif len(packet_data) > 0 and packet_data[0] == 0x02:
            return 'BTC_Transaction'
        elif len(packet_data) > 0 and packet_data[0] == 0x45:
            return 'TCP'
        else:
            return 'Unknown'

    def learn_from_feedback(self, translation_result: Dict):
        """Reinforcement learning from translation outcomes"""
        success = translation_result.get('success', False)
        latency = translation_result.get('latency_ms', 0)
        source_proto = translation_result.get('source_protocol', '')
        target_proto = translation_result.get('target_protocol', '')
        if success and source_proto and target_proto:
            if source_proto not in self.protocol_knowledge['translation_patterns']:
                self.protocol_knowledge['translation_patterns'][source_proto] = {}
            if target_proto not in self.protocol_knowledge['translation_patterns'][source_proto]:
                self.protocol_knowledge['translation_patterns'][source_proto][target_proto] = 0
            self.protocol_knowledge['translation_patterns'][source_proto][target_proto] += 1
            self.logger.info(f"Learning: {source_proto}->{target_proto} success (+1)")
        else:
            self.logger.info(f"Learning: {source_proto}->{target_proto} failure (adjusting)")

    def process_pending_decisions(self):
        """Process pending translation decisions from packets.db"""
        try:
            from UPT.Shared.load_balancer import LoadBalancer
            from UPT.Shared.priority_engine import PriorityEngine
        except ImportError as e:
            self.logger.error(f"Failed to import shared modules in {__file__}: {e}")
            raise
        try:
            lb = LoadBalancer(self.translator_url)
            pe = PriorityEngine()
            conn = sqlite3.connect(self.sniffer_db, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("SELECT raw_packet, protocol FROM fingerprints WHERE cluster_id != -1 LIMIT 10")
            packets = cursor.fetchall()
            conn.close()
            for raw_packet, source_protocol in packets:
                priority = pe.calculate_priority(raw_packet, {'internal': '127.0.0.1' in source_protocol})
                translator_url = lb.select_translator(priority)
                decision = self.make_decision(raw_packet, {'protocol': source_protocol})
                retries = 3
                for attempt in range(retries):
                    try:
                        response = requests.post(
                            f"{translator_url}/translate",
                            json={'packet_data': raw_packet.hex(), 'target_protocol': decision['target_protocol']},
                            timeout=5
                        )
                        response.raise_for_status()
                        result = response.json()
                        lb.update_metrics(translator_url, result.get('success', False))
                        self.learn_from_feedback({
                            'success': result.get('success', False),
                            'latency_ms': result.get('translated_length', 0) * 0.1,
                            'source_protocol': source_protocol,
                            'target_protocol': decision['target_protocol']
                        })
                        break
                    except requests.exceptions.RequestException as e:
                        self.logger.error(f"Translation attempt {attempt + 1} failed with {translator_url}: {e}")
                        lb.update_metrics(translator_url, False)
                        if attempt == retries - 1:
                            self.logger.warning(f"Skipping packet after {retries} failed attempts")
            self.logger.info(f"Processed {len(packets)} pending decisions")
        except Exception as e:
            self.logger.error(f"Process pending decisions error: {e}")

    def start_autonomous_operation(self):
        """Start the agent's autonomous learning and decision-making"""
        self.running = True
        self.logger.info("Starting autonomous operation...")
        self.multicast_sharing.start(self.protocol_knowledge, self.merge_knowledge)
        analysis_thread = threading.Thread(target=self.analyze_network_patterns, daemon=True)
        analysis_thread.start()
        learning_thread = threading.Thread(target=self.continuous_learning, daemon=True)
        learning_thread.start()
        while self.running:
            try:
                self.process_pending_decisions()
                time_module.sleep(0.1)
            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                self.logger.error(f"Decision loop error: {e}")
                time_module.sleep(1)

    def continuous_learning(self):
        """Continuous learning and knowledge refinement"""
        while self.running:
            try:
                self.protocol_knowledge = self.load_knowledge_base()
                self.prune_old_patterns()
                time_module.sleep(60)
            except Exception as e:
                self.logger.error(f"Learning error: {e}")
                time_module.sleep(120)

    def prune_old_patterns(self):
        """Remove outdated translation patterns"""
        patterns = self.protocol_knowledge['translation_patterns']
        for src_proto in list(patterns.keys()):
            for tgt_proto, count in list(patterns[src_proto].items()):
                if count < 3:
                    del patterns[src_proto][tgt_proto]
            if not patterns[src_proto]:
                del patterns[src_proto]

    def stop(self):
        """Stop the agent"""
        self.running = False
        self.multicast_sharing.stop()
        self.logger.info("Agent stopped")

class SimpleAgentAPI:
    def __init__(self, agent: UPTAgent, host: str = 'localhost', port: int = 9999):
        self.agent = agent
        self.host = host
        self.port = port
        self.running = False

    def start(self):
        """Start a simple HTTP server"""
        import http.server
        import socketserver
        import json

        class AgentHTTPHandler(http.server.BaseHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                self.agent = self.server.agent
                super().__init__(*args, **kwargs)

            def do_GET(self):
                if self.path == '/status':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {
                        'status': 'running' if self.agent.running else 'stopped',
                        'decisions_made': len(self.agent.decision_memory),
                        'protocols_known': len(self.agent.protocol_knowledge['protocols']),
                        'translation_patterns': sum(len(targets) for targets in self.agent.protocol_knowledge['translation_patterns'].values())
                    }
                    self.wfile.write(json.dumps(response).encode())
                elif self.path == '/decisions':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {'decisions': list(self.agent.decision_memory)[-10:]}
                    self.wfile.write(json.dumps(response).encode())
                elif self.path == '/knowledge':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = self.agent.protocol_knowledge
                    self.wfile.write(json.dumps(response).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

        self.running = True
        server = socketserver.TCPServer((self.host, self.port), AgentHTTPHandler)
        server.agent = self.agent
        self.agent.logger.info(f"Starting Agent API on {self.host}:{self.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.server_close()
            self.agent.stop()

def main():
    """Main function to start the UPT Agent"""
    parser = argparse.ArgumentParser(description="UPT Autonomous Agent")
    parser.add_argument("--api", action="store_true", help="Start API server")
    parser.add_argument("--host", default="localhost", help="API host")
    parser.add_argument("--port", type=int, default=9999, help="API port")
    args = parser.parse_args()
    agent = UPTAgent()
    if args.api:
        api = SimpleAgentAPI(agent, args.host, args.port)
        try:
            api.start()
        except KeyboardInterrupt:
            agent.stop()
    else:
        try:
            agent.start_autonomous_operation()
        except KeyboardInterrupt:
            agent.stop()

if __name__ == "__main__":
    main()

