import os
import sys
# Ensure UPT root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Advanced.upt_intelligence import ProtocolIntelligenceEngine
from Advanced.protocol_kernel import ProtocolKernel
from Advanced.multicast_security import MulticastSecurity

if __name__ == "__main__":
    engine = ProtocolIntelligenceEngine()
    kernel = ProtocolKernel()
    security = MulticastSecurity("upt_secure_2025")
    
    # Test protocol analysis
    packet = b"HTTP/1.1 200 OK\r\nHost: example.com\r\n\r\n"
    result = engine.deep_protocol_analysis(packet)
    print("Analysis:", result)
    
    # Test unknown protocol
    unknown_packet = b"\xFF\xFF\xFF\xFF"
    unknown_result = engine.handle_unknown_protocol(unknown_packet)
    print("Unknown Protocol:", unknown_result)
    
    # Test encrypted traffic
    encrypted_result = engine.analyze_encrypted_traffic([packet, b"\x45\x00\x00\x28"])
    print("Encrypted Analysis:", encrypted_result)
    
    # Test kernel
    decision = kernel.process_packet(packet, {"source": "192.168.1.1"})
    print("Kernel Decision:", decision)
    
    # Test HMAC
    knowledge = {"protocol": "HTTP", "patterns": ["48545450"]}
    signature = security.sign_knowledge(knowledge)
    print("HMAC Signature:", signature)
    print("HMAC Verification:", security.verify_knowledge(knowledge, signature))