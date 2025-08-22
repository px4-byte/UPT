import scapy.all as scapy
import sys

def list_interfaces():
    """List available scapy network interfaces"""
    try:
        ifaces = scapy.get_if_list()
        if not ifaces:
            print("No network interfaces found")
            return
        print("Available network interfaces:")
        for iface in ifaces:
            print(f" - {iface}")
    except Exception as e:
        print(f"Error listing interfaces: {e}")

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("Error: Run this script as Administrator")
            sys.exit(1)
    list_interfaces()