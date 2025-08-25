import hmac
import hashlib
import json
import logging
from typing import Dict

class MulticastSecurity:
    def __init__(self, secret_key: str):
        self.logger = logging.getLogger("UPTMulticastSecurity")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s - %(pathname)s',
            filename='upt_intelligence.log',
            filemode='a'
        )
        self.secret_key = secret_key.encode()

    def sign_knowledge(self, knowledge: Dict) -> str:
        """Sign knowledge data with HMAC"""
        try:
            data = json.dumps(knowledge, sort_keys=True)
            return hmac.new(self.secret_key, data.encode(), hashlib.sha256).hexdigest()
        except Exception as e:
            self.logger.error(f"HMAC signing error: {e}")
            return ""

    def verify_knowledge(self, knowledge: Dict, signature: str) -> bool:
        """Verify knowledge data with HMAC"""
        try:
            expected_signature = self.sign_knowledge(knowledge)
            return hmac.compare_digest(expected_signature.encode(), signature.encode())
        except Exception as e:
            self.logger.error(f"HMAC verification error: {e}")
            return False