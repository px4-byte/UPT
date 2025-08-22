import sqlite3
from collections import Counter
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
import json
import os
from pathlib import Path
import logging

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='query_packets.log',
    filemode='a'
)
logger = logging.getLogger("UPTQueryPackets")

def get_db_connection(db_path):
    try:
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        # Check write permissions
        if not os.access(Path(db_path).parent, os.W_OK):
            logger.error(f"❌ No write permission for {Path(db_path).parent}")
            raise PermissionError(f"No write permission for {Path(db_path).parent}")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        return conn
    except (sqlite3.Error, PermissionError) as e:
        logger.error(f"❌ Database error for {db_path}: {e}")
        print(f"❌ Database error: {e}")
        return None

def analyze_protocol_patterns():
    db_path = os.getenv("UPT_PACKETS_DB", r"C:\Users\PX3 pro Machine\UPT\Sniffer\packets.db")
    conn = get_db_connection(db_path)
    if not conn:
        print("❌ Failed to connect to packets.db")
        return
    
    cursor = conn.cursor()
    
    # 1. Basic Statistics
    try:
        cursor.execute("SELECT COUNT(*) FROM fingerprints")
        total_packets = cursor.fetchone()[0]
        print(f"📊 Total packets captured: {total_packets}")
        
        cursor.execute("SELECT COUNT(DISTINCT protocol_hash) FROM fingerprints")
        unique_hashes = cursor.fetchone()[0]
        print(f"🔑 Unique protocol fingerprints: {unique_hashes}")
        
        cursor.execute("SELECT COUNT(*) FROM fingerprints WHERE is_unknown = 1")
        unknown_packets = cursor.fetchone()[0]
        print(f"🔍 Unknown protocols detected: {unknown_packets}")
        
        # 2. Protocol Frequency with cluster info
        cursor.execute("""
            SELECT f.protocol, c.protocol_name, COUNT(*) as count
            FROM fingerprints f
            LEFT JOIN protocol_clusters c ON f.cluster_id = c.cluster_id
            GROUP BY f.protocol, c.protocol_name
            ORDER BY count DESC
            LIMIT 15
        """)
        print("\n🏆 Top 15 Protocol Patterns:")
        for protocol, cluster_name, count in cursor.fetchall():
            cluster_info = f"({cluster_name})" if cluster_name else "[UNCLUSTERED]"
            print(f"  {protocol} {cluster_info}: {count} packets")
        
        # 3. Header Rhythm Patterns
        cursor.execute("""
            SELECT header_rhythm, COUNT(*) as count 
            FROM fingerprints 
            GROUP BY header_rhythm 
            HAVING count > 1
            ORDER BY count DESC 
            LIMIT 10
        """)
        print("\n🎵 Top 10 Header Rhythms:")
        for rhythm, count in cursor.fetchall():
            print(f"  {rhythm}: {count} packets")
        
        # 4. Breathing Pattern Analysis
        cursor.execute("""
            SELECT payload_breathing, COUNT(*) as count 
            FROM fingerprints 
            GROUP BY payload_breathing 
            ORDER BY payload_breathing
        """)
        print("\n🌬️ Payload Breathing Patterns (mod 8):")
        breathing_data = []
        for breathing, count in cursor.fetchall():
            breathing_data.append((breathing, count))
            print(f"  {breathing}: {count} packets")
        
        # 5. Most Active Conversations
        cursor.execute("""
            SELECT source_ip, dest_ip, COUNT(*) as conversation_count 
            FROM fingerprints 
            WHERE source_ip != 'unknown' AND dest_ip != 'unknown'
            GROUP BY source_ip, dest_ip 
            ORDER BY conversation_count DESC 
            LIMIT 8
        """)
        print("\n💬 Top 8 Conversations:")
        for src_ip, dst_ip, count in cursor.fetchall():
            print(f"  {src_ip} ↔ {dst_ip}: {count} packets")
        
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"❌ Query error: {e}")
        print(f"❌ Query error: {e}")
        conn.close()

def export_protocol_dna():
    db_path = os.getenv("UPT_PACKETS_DB", r"C:\Users\PX3 pro Machine\UPT\Sniffer\packets.db")
    output_path = os.path.join(os.path.dirname(db_path), "upt_protocol_dna.json")
    
    conn = get_db_connection(db_path)
    if not conn:
        print("❌ Failed to connect to packets.db")
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT protocol, header_rhythm, payload_breathing, response_tells, cluster_id
            FROM fingerprints 
            WHERE cluster_id != -1
        """)
        protocols = [
            {
                "protocol_name": row[0],
                "fingerprint": {
                    "header_rhythm": row[1],
                    "payload_breathing": row[2],
                    "response_tells": row[3]
                },
                "cluster_id": row[4]
            }
            for row in cursor.fetchall()
        ]
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(protocols, f, indent=2)
        logger.info(f"✅ Generated {output_path} with {len(protocols)} protocols")
        print(f"✅ Generated {output_path} with {len(protocols)} protocols")
        
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"❌ Query error: {e}")
        print(f"❌ Query error: {e}")
        conn.close()
    except Exception as e:
        logger.error(f"❌ Error writing protocol DNA: {e}")
        print(f"❌ Error writing protocol DNA: {e}")

def generate_upt_config():
    db_path = os.getenv("UPT_PACKETS_DB", r"C:\Users\PX3 pro Machine\UPT\Sniffer\packets.db")
    conn = get_db_connection(db_path)
    if not conn:
        print("❌ Failed to connect to packets.db")
        return
    
    config = {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "protocols": [],
        "translation_rules": []
    }
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT source_proto, dest_proto, COUNT(*) as count
            FROM (
                SELECT 
                    (SELECT protocol FROM fingerprints f1 WHERE f1.id = f.id - 1) as source_proto,
                    protocol as dest_proto
                FROM fingerprints f
                WHERE id > 1
            )
            WHERE source_proto IS NOT NULL AND dest_proto IS NOT NULL
            GROUP BY source_proto, dest_proto
            HAVING count > 5
            ORDER BY count DESC
            LIMIT 10
        """)
        
        for src, dst, count in cursor.fetchall():
            config["translation_rules"].append({
                "from": src,
                "to": dst,
                "confidence": min(100, count / 2),
                "samples": count
            })
        
        Path(r"C:\Users\PX3 pro Machine\UPT").mkdir(parents=True, exist_ok=True)
        with open(r"C:\Users\PX3 pro Machine\UPT\upt_translator_config.json", 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"⚙️ Generated UPT translator configuration with {len(config['translation_rules'])} rules")
        print(f"\n⚙️ Generated UPT translator configuration with {len(config['translation_rules'])} rules")
        print("💡 Configuration saved to 'upt_translator_config.json'")
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"❌ Query error: {e}")
        print(f"❌ Query error: {e}")
        conn.close()

if __name__ == "__main__":
    logger.info("🚀 Starting UPT Protocol Analysis Toolkit")
    print("🤖 UPT Protocol Analysis Toolkit")
    print("=" * 50)
    
    db_path = os.getenv("UPT_PACKETS_DB", r"C:\Users\PX3 pro Machine\UPT\Sniffer\packets.db")
    conn = get_db_connection(db_path)
    if not conn:
        print("❌ Failed to connect to packets.db")
    else:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            logger.info("📦 Database Tables: %s", [table[0] for table in tables])
            print("📦 Database Tables:", [table[0] for table in tables])
            
            cursor.execute("SELECT COUNT(*) FROM fingerprints")
            total = cursor.fetchone()[0]
            print(f"📊 Total packets: {total}")
            
            if total == 0:
                print("❌ No packets found. Run the sniffer first!")
            else:
                analyze_protocol_patterns()
                export_protocol_dna()
                generate_upt_config()
                
                print("\n🎉 Analysis complete! Next steps:")
                print("  1. Review protocol_dna.json for learned patterns")
                print("  2. Use translator_config.json for UPT setup")
                print("  3. Run sniffer longer to improve learning")
        finally:
            conn.close()