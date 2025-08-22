import scapy.all as scapy
import sqlite3
import argparse
import logging
import numpy as np
from datetime import datetime
import time as time_module
from threading import Thread
from typing import Dict, List
import json
import os

class UPTSniffer:
    def __init__(self, interface: str, filter: str = "tcp"):
        self.interface = interface
        self.filter = filter
        self.db_path = "packets.db"
        self.running = False
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='sniffer.log',
            filemode='a'
        )
        self.logger = logging.getLogger("UPTSniffer")
        self.setup_database()
        self.logger.info("Initialized UPT Sniffer")

    def setup_database(self):
        """Setup SQLite database for packet storage"""
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fingerprints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    source_ip TEXT,
                    protocol TEXT,
                    packet_length INTEGER,
                    raw_packet BLOB,
                    cluster_id INTEGER DEFAULT -1
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS protocol_clusters (
                    cluster_id INTEGER PRIMARY KEY,
                    protocol_name TEXT,
                    packet_count INTEGER
                )
            """)
            conn.commit()
            conn.close()
            self.logger.info("Database initialized")
        except Exception as e:
            self.logger.error(f"Database setup error: {e}")

    def extract_features(self, packet) -> Dict:
        """Extract features from a packet"""
        try:
            if 'IP' not in packet:
                return None
            ip_layer = packet['IP']
            protocol = packet.name
            packet_length = len(packet)
            raw_packet = bytes(packet)
            return {
                'timestamp': datetime.now().isoformat(),
                'source_ip': ip_layer.src,
                'protocol': protocol,
                'packet_length': packet_length,
                'raw_packet': raw_packet
            }
        except Exception as e:
            self.logger.error(f"Feature extraction error: {e}")
            return None

    def store_packet(self, packet_data: Dict):
        """Store packet data in SQLite"""
        if not packet_data:
            return
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO fingerprints (timestamp, source_ip, protocol, packet_length, raw_packet)
                VALUES (?, ?, ?, ?, ?)
            """, (
                packet_data['timestamp'],
                packet_data['source_ip'],
                packet_data['protocol'],
                packet_data['packet_length'],
                packet_data['raw_packet']
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Database storage error: {e}")

    def analyze_packets(self):
        """Analyze stored packets using clustering"""
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("SELECT id, packet_length, raw_packet FROM fingerprints WHERE cluster_id = -1")
            packets = cursor.fetchall()
            if not packets:
                conn.close()
                return

            features = []
            packet_ids = []
            for pkt_id, length, raw in packets:
                header_rhythm = raw[:4].hex() if len(raw) >= 4 else "0000"
                payload_breathing = len(raw) % 8
                response_tells = raw[-1] & 0b00001111 if raw else 0
                features.append([length, int(header_rhythm, 16), payload_breathing, response_tells])
                packet_ids.append(pkt_id)

            if features:
                clustering = DBSCAN(eps=0.5, min_samples=5).fit(features)
                labels = clustering.labels_
                for pkt_id, label in zip(packet_ids, labels):
                    protocol_name = f"Protocol_{label}" if label != -1 else "Unknown"
                    cursor.execute("UPDATE fingerprints SET cluster_id = ? WHERE id = ?", (label, pkt_id))
                    if label != -1:
                        cursor.execute("""
                            INSERT OR REPLACE INTO protocol_clusters (cluster_id, protocol_name, packet_count)
                            VALUES (?, ?, (SELECT COUNT(*) FROM fingerprints WHERE cluster_id = ?))
                        """, (label, protocol_name, label))
                conn.commit()

                protocol_dna = []
                cursor.execute("SELECT cluster_id, protocol_name, packet_count FROM protocol_clusters")
                for cluster_id, protocol_name, packet_count in cursor.fetchall():
                    if packet_count > 0:
                        cursor.execute("SELECT raw_packet FROM fingerprints WHERE cluster_id = ? LIMIT 1", (cluster_id,))
                        raw = cursor.fetchone()[0]
                        protocol_dna.append({
                            'cluster_id': cluster_id,
                            'protocol_name': protocol_name,
                            'packet_count': packet_count,
                            'fingerprint': {
                                'header_rhythm': raw[:4].hex() if len(raw) >= 4 else "0000",
                                'payload_breathing': len(raw) % 8,
                                'response_tells': raw[-1] & 0b00001111 if raw else 0
                            }
                        })
                dna_file = "upt_protocol_dna.json"
                with open(dna_file, 'w') as f:
                    json.dump(protocol_dna, f, indent=2)
                self.logger.info(f"Generated {dna_file} with {len(protocol_dna)} protocols")
            conn.close()
        except Exception as e:
            self.logger.error(f"Analysis error: {e}")

    def packet_callback(self, packet):
        """Callback for each captured packet"""
        packet_data = self.extract_features(packet)
        if packet_data:
            self.store_packet(packet_data)

    def start_sniffing(self):
        """Start packet sniffing"""
        self.running = True
        self.logger.info(f"Starting sniffer on {self.interface} with filter {self.filter}")
        try:
            scapy.sniff(
                iface=self.interface,
                filter=self.filter,
                prn=self.packet_callback,
                store=False,
                stop_filter=lambda x: not self.running
            )
        except Exception as e:
            self.logger.error(f"Sniffing error: {e}")

    def start_analysis(self):
        """Start continuous packet analysis"""
        while self.running:
            try:
                self.analyze_packets()
                time_module.sleep(10)
            except Exception as e:
                self.logger.error(f"Analysis loop error: {e}")
                time_module.sleep(30)

    def start(self):
        """Start sniffer and analyzer"""
        self.running = True
        self.logger.info("Starting sniffer and analyzer")
        sniff_thread = Thread(target=self.start_sniffing, daemon=True)
        analysis_thread = Thread(target=self.start_analysis, daemon=True)
        sniff_thread.start()
        analysis_thread.start()
        try:
            while self.running:
                time_module.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop sniffer and analyzer"""
        self.running = False
        self.logger.info("Sniffer stopped")

def main():
    parser = argparse.ArgumentParser(description="UPT Protocol Sniffer")
    parser.add_argument("-i", "--interface", default="Wi-Fi", help="Network interface to sniff")
    parser.add_argument("-f", "--filter", default="tcp", help="BPF filter")
    args = parser.parse_args()
    sniffer = UPTSniffer(args.interface, args.filter)
    sniffer.start()

if __name__ == "__main__":
    main()