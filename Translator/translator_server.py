import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import sqlite3
import json
import logging
import time as time_module
from typing import Dict
try:
    from UPT.Translator.translator import UPTTranslator
    from UPT.Shared.load_balancer import LoadBalancer
    from UPT.Shared.priority_engine import PriorityEngine
except ImportError as e:
    logging.error(f"Failed to import modules in {__file__}: {e}")
    raise
import http.server
import socketserver

class NetworkTranslationServer:
    def __init__(self, host: str = "localhost", port: int = 8888, db_path: str = "translation_sessions.db"):
        self.host = host
        self.port = port
        self.db_path = db_path
        self.running = False
        self.connection_db = None
        self.translator = UPTTranslator()
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s - %(pathname)s',
            filename='translator.log',
            filemode='a'
        )
        self.logger = logging.getLogger("NetworkTranslationServer")
    
    def connect_to_db(self, retries: int = 5, delay: float = 2.0) -> bool:
        """Connect to translation_sessions.db with retries and table verification"""
        try:
            db_dir = os.path.dirname(self.db_path) or '.'
            if not os.access(db_dir, os.W_OK):
                self.logger.error(f"Directory {db_dir} is not writable")
                return False

            for attempt in range(retries):
                try:
                    self.connection_db = sqlite3.connect(self.db_path, check_same_thread=False)
                    cursor = self.connection_db.cursor()
                    # Verify table exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='translation_sessions'")
                    if not cursor.fetchone():
                        self.logger.warning(f"translation_sessions table not found in {self.db_path}, creating")
                        cursor.execute("""
                            CREATE TABLE translation_sessions (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                source_protocol TEXT,
                                target_protocol TEXT,
                                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                                success BOOLEAN,
                                original_length INTEGER,
                                translated_length INTEGER
                            )
                        """)
                        self.connection_db.commit()
                    self.logger.info(f"Connected to {self.db_path} with translation_sessions table")
                    return True
                except sqlite3.Error as e:
                    self.logger.error(f"DB connection attempt {attempt + 1} failed: {e}")
                    if attempt < retries - 1:
                        time_module.sleep(delay)
                finally:
                    if self.connection_db:
                        self.connection_db.close()
                        self.connection_db = None
            self.logger.error(f"Failed to connect to {self.db_path} after {retries} retries")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error in connect_to_db: {e}")
            return False
    
    def process_translation_request(self, source_data: bytes, target_protocol: str) -> bytes:
        """Process a translation request"""
        try:
            translated_data, success = self.translator.translate_packet(source_data, target_protocol)
            if self.connection_db:
                self.connection_db.execute(
                    "INSERT INTO translation_sessions (source_protocol, target_protocol, success, original_length, translated_length) VALUES (?, ?, ?, ?, ?)",
                    (self.translator.identify_protocol(source_data), target_protocol, success, len(source_data), len(translated_data))
                )
                self.connection_db.commit()
            return translated_data
        except Exception as e:
            self.logger.error(f"Translation error: {e}")
            if self.connection_db:
                self.connection_db.execute(
                    "INSERT INTO translation_sessions (source_protocol, target_protocol, success, original_length, translated_length) VALUES (?, ?, ?, ?, ?)",
                    (self.translator.identify_protocol(source_data), target_protocol, False, len(source_data), 0)
                )
                self.connection_db.commit()
            raise
    
    def start_server(self):
        """Start the translation server"""
        if not self.connect_to_db():
            self.logger.error("Cannot start server without DB connection")
            return
        
        class TranslationHTTPHandler(http.server.BaseHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                self.server_instance = self.server.server_instance
                super().__init__(*args, **kwargs)
            
            def do_GET(self):
                if self.path == '/stats':
                    try:
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        response = {
                            'status': 'running' if self.server_instance.running else 'stopped',
                            'sessions': self.server_instance.connection_db.execute(
                                "SELECT COUNT(*) FROM translation_sessions"
                            ).fetchone()[0] if self.server_instance.connection_db else 0
                        }
                        self.wfile.write(json.dumps(response).encode())
                    except Exception as e:
                        self.server_instance.logger.error(f"Stats endpoint error: {e}")
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': str(e)}).encode())
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def do_POST(self):
                if self.path == '/translate':
                    try:
                        content_length = int(self.headers['Content-Length'])
                        data = self.rfile.read(content_length)
                        request = json.loads(data.decode())
                        source_data = bytes.fromhex(request['packet_data'])
                        target_protocol = request['target_protocol']
                        translated_data = self.server_instance.process_translation_request(
                            source_data, target_protocol
                        )
                        response = {
                            'success': True,
                            'translated_data': translated_data.hex(),
                            'original_length': len(source_data),
                            'translated_length': len(translated_data)
                        }
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(response).encode())
                    except Exception as e:
                        self.server_instance.logger.error(f"Translate endpoint error: {e}")
                        response = {'success': False, 'error': str(e)}
                        self.send_response(400)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(response).encode())
                else:
                    self.send_response(404)
                    self.end_headers()
        
        self.running = True
        server = socketserver.TCPServer((self.host, self.port), TranslationHTTPHandler)
        server.server_instance = self
        self.logger.info(f"UPT Translation Server running on {self.host}:{self.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.server_close()
            self.stop_server()
    
    def stop_server(self):
        """Stop the server"""
        self.running = False
        if self.connection_db:
            self.connection_db.close()
        self.logger.info("Translation Server stopped")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="UPT Translation Server")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8888, help="Server port")
    args = parser.parse_args()
    server = NetworkTranslationServer(args.host, args.port)
    server.start_server()

if __name__ == "__main__":
    main()