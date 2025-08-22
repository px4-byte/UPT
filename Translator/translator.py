import sqlite3
import json
import logging
from typing import Dict, Optional, Tuple
try:
    from UPT.Translator.http_to_mqtt import HTTPToMQTTTranslator
    from UPT.Translator.http_to_btc import HTTPToBTCTranslator
    from UPT.Translator.tcp_to_json import TCPToJSONTranslator
except ImportError as e:
    logging.error(f"Failed to import translators: {e}")
    raise

class UPTTranslator:
    def __init__(self, dna_file: str = "../Sniffer/upt_protocol_dna.json"):
        self.protocol_dna = self.load_protocol_dna(dna_file)
        self.translators = {
            'MQTT': HTTPToMQTTTranslator(),
            'BTC': HTTPToBTCTranslator(),
            'JSON': TCPToJSONTranslator()
        }
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='translator.log',
            filemode='a'
        )
        self.logger = logging.getLogger("UPTTranslator")
        self.logger.info("Initialized UPT Translator")

    def load_protocol_dna(self, dna_file: str) -> list:
        """Load protocol fingerprints from analysis"""
        import os
        if not os.path.exists(dna_file):
            self.logger.warning("Protocol DNA file not found, using empty fingerprints")
            return []
        try:
            with open(dna_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load protocol DNA: {e}")
            return []

    def identify_protocol(self, packet_data: bytes) -> str:
        """Identify protocol using fingerprint method"""
        if not packet_data:
            return 'UNKNOWN'
        header_rhythm = packet_data[:4].hex() if len(packet_data) >= 4 else "0000"
        payload_breathing = len(packet_data) % 8
        response_tells = packet_data[-1] & 0b00001111 if packet_data else 0
        for protocol in self.protocol_dna:
            fingerprint = protocol.get('fingerprint', {})
            if (fingerprint.get('header_rhythm') == header_rhythm and
                fingerprint.get('payload_breathing') == payload_breathing and
                fingerprint.get('response_tells') == response_tells):
                return protocol.get('protocol_name', 'UNKNOWN')
        return 'UNKNOWN'

    def translate_packet(self, packet_data: bytes, target_protocol: str) -> Tuple[bytes, bool]:
        """Translate packet to target protocol"""
        try:
            source_protocol = self.identify_protocol(packet_data)
            if target_protocol not in self.translators:
                self.logger.error(f"Unsupported target protocol: {target_protocol}")
                return b"", False
            translated_data = self.translators[target_protocol].translate(packet_data)
            self.logger.info(f"Translated {source_protocol} to {target_protocol}")
            return translated_data, True
        except Exception as e:
            self.logger.error(f"Translation error: {e}")
            return b"", False