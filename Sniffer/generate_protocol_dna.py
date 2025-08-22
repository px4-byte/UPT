import sqlite3
import json
import logging

def generate_protocol_dna(db_path: str = "packets.db", output_file: str = "upt_protocol_dna.json"):
    """Generate protocol DNA from packets.db"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='sniffer.log',
        filemode='a'
    )
    logger = logging.getLogger("GenerateProtocolDNA")
    
    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT protocol, raw_packet FROM fingerprints WHERE cluster_id != -1 LIMIT 100")
        packets = cursor.fetchall()
        protocol_dna = []
        for protocol, raw in packets:
            protocol_dna.append({
                'protocol_name': protocol,
                'packet_count': 1,
                'fingerprint': {
                    'header_rhythm': raw[:4].hex() if len(raw) >= 4 else "0000",
                    'payload_breathing': len(raw) % 8,
                    'response_tells': raw[-1] & 0b00001111 if raw else 0
                }
            })
        conn.close()
        with open(output_file, 'w') as f:
            json.dump(protocol_dna, f, indent=2)
        logger.info(f"Generated {output_file} with {len(protocol_dna)} protocols")
    except Exception as e:
        logger.error(f"Error generating protocol DNA: {e}")

if __name__ == "__main__":
    generate_protocol_dna()