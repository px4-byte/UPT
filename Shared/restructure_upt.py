import os
import shutil

def restructure_upt():
    base_dir = r"C:\Users\PX3 pro Machine\UPT"
    os.chdir(base_dir)

    # Create directories
    directories = ["Agent", "Sniffer", "Translator", "Shared"]
    for d in directories:
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "__init__.py"), 'w') as f:
            f.write("# Package init file\n")

    # Move files
    agent_files = ["agent.py", "agent_config.yaml", "control_agent.py", "query_translator.py"]
    sniffer_files = ["sniffer.py", "generate_protocol_dna.py", "list_interface.py", "query_packets.py", "packets.db", "upt_protocol_dna.json"]
    translator_files = ["translator.py", "translator_server.py", "http_to_btc.py", "http_to_mqtt.py", "tcp_to_json.py"]
    shared_files = ["check_dependencies.py", "dashboard.py", "dashboard.html", "deamon.py", "integration.py", "load_balancer.py", "priority_engine.py", "requirements.txt"]

    for f in agent_files:
        if os.path.exists(f):
            shutil.move(f, os.path.join("Agent", f))
    for f in sniffer_files:
        if os.path.exists(f):
            shutil.move(f, os.path.join("Sniffer", f))
    for f in translator_files:
        if os.path.exists(f):
            shutil.move(f, os.path.join("Translator", f))
    if os.path.exists("translation_db.py"):
        shutil.move("translation_db.py", os.path.join("Translator", "init_translation_db.py"))
    for f in shared_files:
        if os.path.exists(f):
            shutil.move(f, os.path.join("Shared", f))

    # Remove incorrect __init__ file
    if os.path.exists("__init_translator_.py"):
        os.remove("__init_translator_.py")

    print("Directory structure updated successfully!")

if __name__ == "__main__":
    restructure_upt()