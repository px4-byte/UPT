import sqlite3
import logging
import os

def create_translation_sessions_db(db_path="translation_sessions.db"):
    """Create or repair translation_sessions.db with the required schema"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s - %(pathname)s',
        filename='translator.log',
        filemode='a'
    )
    logger = logging.getLogger("InitTranslationDB")

    try:
        db_dir = os.path.dirname(db_path) or '.'
        if not os.access(db_dir, os.W_OK):
            logger.error(f"Directory {db_dir} is not writable")
            raise PermissionError(f"Cannot write to {db_dir}")

        # Check if database file exists and is valid
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path, check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='translation_sessions'")
                if cursor.fetchone():
                    logger.info(f"Table translation_sessions already exists in {db_path}")
                    conn.close()
                    return
                logger.warning(f"Database {db_path} exists but missing translation_sessions table, recreating")
                conn.close()
                os.remove(db_path)  # Remove corrupted database
            except sqlite3.Error as e:
                logger.error(f"Error checking {db_path}: {e}, recreating database")
                os.remove(db_path)

        # Create new database
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()
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
        conn.commit()
        conn.close()
        logger.info(f"Created {db_path} with translation_sessions table")
    except Exception as e:
        logger.error(f"Failed to create {db_path}: {e}")
        raise

if __name__ == "__main__":
    create_translation_sessions_db()