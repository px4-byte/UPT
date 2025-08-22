import requests
import json
import argparse

class UPTQueryClient:
    def __init__(self, server_url="http://localhost:8888"):
        self.server_url = server_url
    
    def translate_packet(self, packet_data: bytes, target_protocol: str) -> bytes:
        """Send translation request to UPT server"""
        try:
            request_data = {
                'packet_data': packet_data.hex(),
                'target_protocol': target_protocol
            }
            response = requests.post(
                f"{self.server_url}/translate",
                json=request_data,
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                if result['success']:
                    return bytes.fromhex(result['translated_data'])
                else:
                    raise Exception(f"Translation failed: {result.get('error', 'Unknown error')}")
            else:
                raise Exception(f"Server error: {response.status_code}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Connection error: {e}")
    
    def get_translation_stats(self):
        """Get translation statistics from server"""
        try:
            response = requests.get(f"{self.server_url}/stats", timeout=5)
            return response.json()
        except:
            return {"error": "Could not connect to server"}
    
    def list_supported_protocols(self):
        """Get list of supported target protocols"""
        try:
            response = requests.get(f"{self.server_url}/protocols", timeout=5)
            return response.json()
        except:
            return ["HTTP", "MQTT", "JSON", "Generic"]  # Updated fallback

def main():
    parser = argparse.ArgumentParser(description="UPT Query Client")
    parser.add_argument("--server", default="http://localhost:8888", help="UPT server URL")
    subparsers = parser.add_subparsers(dest="command")
    translate_parser = subparsers.add_parser("translate", help="Translate a packet")
    translate_parser.add_argument("--input", required=True, help="Input file or hex string")
    translate_parser.add_argument("--target", required=True, help="Target protocol")
    translate_parser.add_argument("--output", help="Output file")
    subparsers.add_parser("stats", help="Get translation statistics")
    subparsers.add_parser("protocols", help="List supported protocols")
    args = parser.parse_args()
    client = UPTQueryClient(args.server)
    if args.command == "translate":
        if args.input.startswith("0x") or len(args.input) % 2 == 0:
            packet_data = bytes.fromhex(args.input.replace("0x", ""))
        else:
            with open(args.input, 'rb') as f:
                packet_data = f.read()
        try:
            result = client.translate_packet(packet_data, args.target)
            if args.output:
                with open(args.output, 'wb') as f:
                    f.write(result)
                print(f"✅ Translation saved to {args.output}")
            else:
                print(f"📦 Translated data (hex): 0x{result.hex()}")
                print(f"📊 Original: {len(packet_data)} bytes, Translated: {len(result)} bytes")
        except Exception as e:
            print(f"❌ Translation error: {e}")
    elif args.command == "stats":
        stats = client.get_translation_stats()
        print("📈 Translation Statistics:")
        print(json.dumps(stats, indent=2))
    elif args.command == "protocols":
        protocols = client.list_supported_protocols()
        print("🎯 Supported Target Protocols:")
        for proto in protocols:
            print(f"  - {proto}")

if __name__ == "__main__":
    main()