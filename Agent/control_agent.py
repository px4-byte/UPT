import requests
import json
import argparse

class AgentController:
    def __init__(self, agent_url="http://localhost:9999"):
        self.agent_url = agent_url
    
    def get_status(self):
        try:
            response = requests.get(f"{self.agent_url}/status", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to get status: {e}"}
    
    def get_decisions(self):
        try:
            response = requests.get(f"{self.agent_url}/decisions", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to get decisions: {e}"}
    
    def get_knowledge(self):
        try:
            response = requests.get(f"{self.agent_url}/knowledge", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to get knowledge: {e}"}
    
    def make_decision(self, packet_hex: str):
        try:
            response = requests.post(
                f"{self.agent_url}/decide",
                json={'packet_hex': packet_hex, 'source_info': {}},
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to make decision: {e}"}
    
    def provide_feedback(self, decision_id: str, success: bool, latency_ms: float):
        try:
            response = requests.post(
                f"{self.agent_url}/learn",
                json={'decision_id': decision_id, 'success': success, 'latency_ms': latency_ms},
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to provide feedback: {e}"}

def main():
    parser = argparse.ArgumentParser(description="UPT Agent Controller")
    parser.add_argument("--agent", default="http://localhost:9999", help="Agent API URL")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("status", help="Get agent status")
    subparsers.add_parser("decisions", help="Get recent decisions")
    subparsers.add_parser("knowledge", help="Get knowledge base")
    decide_parser = subparsers.add_parser("decide", help="Make a decision")
    decide_parser.add_argument("packet", help="Packet data in hex")
    learn_parser = subparsers.add_parser("learn", help="Provide learning feedback")
    learn_parser.add_argument("--decision", required=True, help="Decision ID")
    learn_parser.add_argument("--success", type=bool, required=True, help="Success status")
    learn_parser.add_argument("--latency", type=float, required=True, help="Latency in ms")
    args = parser.parse_args()
    controller = AgentController(args.agent)
    if args.command == "status":
        print(json.dumps(controller.get_status(), indent=2))
    elif args.command == "decisions":
        print(json.dumps(controller.get_decisions(), indent=2))
    elif args.command == "knowledge":
        print(json.dumps(controller.get_knowledge(), indent=2))
    elif args.command == "decide":
        result = controller.make_decision(args.packet)
        print("🤖 Agent Decision:")
        print(json.dumps(result, indent=2))
    elif args.command == "learn":
        result = controller.provide_feedback(args.decision, args.success, args.latency)
        print("📚 Learning Feedback Applied:")
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()