import unittest
import requests
import time
import subprocess
import os
from query_translator import UPTQueryClient
import logging

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='integration.log',
    filemode='a'
)
logger = logging.getLogger("UPTIntegration")

class TestUPTIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Start the full UPT system for testing"""
        daemon_path = os.getenv("UPT_DAEMON_PATH", r"C:\Users\PX3 pro Machine\UPT\daemon.py")
        os.environ["UPT_PACKETS_DB"] = r"C:\Users\PX3 pro Machine\UPT\Sniffer\packets.db"
        os.environ["UPT_TRANSLATIONS_DB"] = r"C:\Users\PX3 pro Machine\UPT\Translator\translation_sessions.db"
        
        if not os.path.exists(daemon_path):
            logger.error(f"❌ Daemon file not found: {daemon_path}")
            cls.fail(f"Daemon file not found: {daemon_path}")
        
        max_retries = 3
        retry_delay = 5
        for attempt in range(max_retries):
            try:
                cls.daemon = subprocess.Popen(["python", daemon_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                time.sleep(10)
                response = requests.get("http://localhost:8888/stats", timeout=2)
                if response.status_code < 500:
                    cls.client = UPTQueryClient()
                    logger.info("✅ Daemon started successfully")
                    return
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} to start daemon failed: {e}")
                if cls.daemon:
                    cls.daemon.terminate()
                    cls.daemon.wait()
                time.sleep(retry_delay)
        cls.fail(f"Failed to start daemon after {max_retries} attempts")
    
    def test_1_system_health(self):
        """Test that all components are running"""
        try:
            response = requests.get("http://localhost:8888/stats", timeout=2)
            self.assertTrue(response.status_code < 500, f"Translator server not responding: {response.status_code}")
            logger.info("✅ Translator server is running")
        except Exception as e:
            logger.error(f"❌ Translator server not responding: {e}")
            self.fail(f"Translator server not responding: {e}")
        
        try:
            response = requests.get("http://localhost:9999/status", timeout=2)
            self.assertEqual(response.status_code, 200, f"Agent API not responding: {response.status_code}")
            logger.info("✅ Agent API is running")
        except Exception as e:
            logger.error(f"❌ Agent API not responding: {e}")
            self.fail(f"Agent API not responding: {e}")
    
    def test_2_protocol_translation(self):
        """Test end-to-end protocol translation"""
        http_packet = b"GET /api/data HTTP/1.1\r\nHost: example.com\r\n\r\n"
        try:
            result = self.client.translate_packet(http_packet, "MQTT")
            self.assertIsNotNone(result, "Translation result is None")
            self.assertGreater(len(result), len(http_packet), "Translated packet is not larger")
            self.assertTrue(result.startswith(b'\x30'), "Invalid MQTT packet")
            logger.info("✅ Protocol translation successful")
        except Exception as e:
            logger.error(f"❌ Translation failed: {e}")
            self.fail(f"Translation failed: {e}")
    
    def test_3_agent_decision_making(self):
        """Test agent decision capabilities"""
        try:
            agent_status = requests.get("http://localhost:9999/status").json()
            self.assertGreater(agent_status['protocols_known'], 0, "No protocols known")
            self.assertGreaterEqual(agent_status['translation_patterns'], 0, "Invalid translation patterns")
            logger.info("✅ Agent decision-making successful")
        except Exception as e:
            logger.error(f"❌ Agent decision test failed: {e}")
            self.fail(f"Agent decision test failed: {e}")
    
    def test_4_load_balancer(self):
        """Test load balancer node selection"""
        from load_balancer import LoadBalancer
        from priority_engine import PriorityEngine
        lb = LoadBalancer()
        pe = PriorityEngine()
        packet = b"GET /api/data HTTP/1.1\r\nHost: example.com\r\n\r\n"
        try:
            priority = pe.calculate_priority(packet, {'internal': True})
            node = lb.select_translator(priority)
            self.assertIn(node, lb.translator_nodes, "Invalid translator node selected")
            logger.info(f"✅ Load balancer selected node: {node}")
        except Exception as e:
            logger.error(f"❌ Load balancer test failed: {e}")
            self.fail(f"Load balancer test failed: {e}")
    
    @classmethod
    def tearDownClass(cls):
        """Stop the UPT system"""
        if cls.daemon:
            cls.daemon.terminate()
            cls.daemon.wait()
            logger.info("🛑 Daemon stopped")

if __name__ == "__main__":
    logger.info("🚀 Starting integration tests")
    unittest.main()