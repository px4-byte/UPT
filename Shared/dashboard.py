import os
import sqlite3
import logging
from flask import Flask, render_template, Response
from typing import Dict, List

app = Flask(__name__, template_folder="templates")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s - %(pathname)s',
    filename='dashboard.log',
    filemode='a'
)
logger = logging.getLogger("UPTDashboard")

def get_db_data(db_path: str, query: str) -> List:
    """Fetch data from SQLite database with error handling"""
    try:
        if not os.path.exists(db_path):
            logger.error(f"Database not found: {db_path}")
            return []
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        conn.close()
        return data
    except sqlite3.Error as e:
        logger.error(f"Database error in {db_path}: {e}")
        return []

@app.route('/')
def dashboard():
    """Render the main dashboard with enhanced error handling"""
    try:
        # Verify template exists
        template_path = os.path.join(app.template_folder, 'dashboard.html')
        if not os.path.exists(template_path):
            logger.error(f"Template not found: {template_path}")
            return Response("Error: dashboard.html not found", status=500)

        # Fetch packet stats
        packets_db = os.path.join(os.path.dirname(__file__), "../Sniffer/packets.db")
        packet_stats = get_db_data(packets_db, """
            SELECT protocol, COUNT(*) as count, AVG(packet_length) as avg_length 
            FROM fingerprints 
            GROUP BY protocol
        """)

        # Fetch translation stats
        translations_db = os.path.join(os.path.dirname(__file__), "../Translator/translation_sessions.db")
        translation_stats = get_db_data(translations_db, """
            SELECT source_protocol, target_protocol, COUNT(*) as count, AVG(translated_length) as avg_length 
            FROM translation_sessions 
            GROUP BY source_protocol, target_protocol
        """)

        # Fetch agent knowledge
        agent_knowledge = {}
        try:
            import requests
            response = requests.get("http://localhost:9999/knowledge", timeout=5)
            response.raise_for_status()
            agent_knowledge = response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch agent knowledge: {e}")

        return render_template(
            'dashboard.html',
            packet_stats=packet_stats,
            translation_stats=translation_stats,
            agent_knowledge=agent_knowledge
        )
    except Exception as e:
        logger.error(f"Dashboard rendering error: {e}")
        return Response(f"Error: {str(e)}", status=500)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return {"status": "running", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    try:
        logger.info("Starting UPT Dashboard on http://0.0.0.0:5000")
        app.config['TEMPLATES_AUTO_RELOAD'] = False  # Optimize for Core i3
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")