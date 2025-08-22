import subprocess
import time as time_module
import logging
import os
from typing import Dict

class UPTDaemon:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.running = False
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='upt_daemon.log',
            filemode='a'
        )
        self.logger = logging.getLogger("UPTDaemon")
        # Set PYTHONPATH for subprocesses
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = os.path.abspath(os.path.join(os.getcwd(), ".."))

    def start_process(self, name: str, command: list, cwd: str) -> bool:
        """Start a process and track it"""
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.env
            )
            self.processes[name] = process
            self.logger.info(f"{name.upper()} started (PID: {process.pid})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start {name}: {e}")
            return False

    def monitor_processes(self):
        """Monitor and restart crashed processes"""
        while self.running:
            for name, process in list(self.processes.items()):
                if process.poll() is not None:  # Process has terminated
                    exit_code = process.poll()
                    self.logger.warning(f"{name.upper()} crashed (exit code: {exit_code}), restarting...")
                    command = process.args
                    cwd = process.cwd
                    self.start_process(name, command, cwd)
            time_module.sleep(5)

    def start(self):
        """Start all UPT components"""
        self.running = True
        self.logger.info("Starting Universal Protocol Translator System...")
        
        # Start Sniffer
        self.start_process(
            "sniffer",
            ["python", "sniffer.py", "-i", "Wi-Fi", "-f", "tcp"],
            os.path.join(os.getcwd(), "../Sniffer")
        )
        
        # Start Translator
        self.start_process(
            "translator",
            ["python", "translator_server.py"],
            os.path.join(os.getcwd(), "../Translator")
        )
        
        # Start Agent
        self.start_process(
            "agent",
            ["python", "agent.py"],
            os.path.join(os.getcwd(), "../Agent")
        )
        
        self.logger.info("UPT System fully operational!")
        self.monitor_processes()

    def stop(self):
        """Stop all processes"""
        self.running = False
        for name, process in self.processes.items():
            process.terminate()
            try:
                process.wait(timeout=5)
                self.logger.info(f"{name.upper()} stopped")
            except subprocess.TimeoutExpired:
                process.kill()
                self.logger.warning(f"{name.upper()} forcibly terminated")

def main():
    daemon = UPTDaemon()
    try:
        daemon.start()
    except KeyboardInterrupt:
        daemon.stop()

if __name__ == "__main__":
    main()