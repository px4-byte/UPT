import logging
import sqlite3
import os
from typing import Dict

class PriorityEngine:
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s - %(pathname)s',
            filename='priority_engine.log',
            filemode='a'
        )
        self.logger = logging.getLogger("PriorityEngine")
        self.patterns = self.load_patterns()
        self.logger.info(f"✅ Loaded {len(self.patterns)} protocol patterns")

    def load_patterns(self) -> Dict:
        """Load protocol patterns from translation_sessions.db"""
        patterns = {}
        try:
            db_path = os.path.join(os.path.dirname(__file__), "../Translator/translation_sessions.db")
            conn = sqlite3.connect(db_path, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='translation_sessions'")
            if not cursor.fetchone():
                self.logger.warning(f"translation_sessions table not found in {db_path} - starting with empty patterns")
                conn.close()
                return patterns
            cursor.execute("""
                SELECT source_protocol, target_protocol, COUNT(*) as count 
                FROM translation_sessions 
                GROUP BY source_protocol, target_protocol
            """)
            for src, tgt, count in cursor.fetchall():
                if src not in patterns:
                    patterns[src] = {}
                patterns[src][tgt] = count
            conn.close()
            return patterns
        except sqlite3.Error as e:
            self.logger.error(f"Error loading patterns from {db_path}: {e}")
            return patterns

    def calculate_priority(self, packet_data: bytes, metadata: Dict) -> str:
        """Calculate priority for a packet"""
        if not self.patterns:
            self.logger.warning("No protocol patterns available, defaulting to low priority")
            return "low"
        # Placeholder logic (adjust based on actual implementation)
        return "medium"