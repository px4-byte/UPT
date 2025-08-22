import importlib
import sys
import pkg_resources

def check_module(module_name: str, pip_name: str = None, required_version: str = None) -> bool:
    """Check if a module is installed with optional version check"""
    try:
        module = importlib.import_module(module_name)
        installed_version = pkg_resources.get_distribution(module_name).version
        if required_version and installed_version != required_version:
            print(f"⚠️ {module_name} (installed: {installed_version}, required: {required_version})")
            return False
        print(f"✅ {module_name} (v{installed_version})")
        return True
    except ImportError:
        pip_name = pip_name or module_name
        print(f"❌ {module_name} - Install with: pip install {pip_name}")
        return False

required_modules = [
    ("scapy", "scapy", "2.5.0"),
    ("numpy", "numpy", "1.24.3"),
    ("pandas", "pandas", "2.0.3"),
    ("sklearn", "scikit-learn", "1.3.0"),
    ("requests", "requests", "2.31.0"),
    ("flask", "Flask", "2.3.3"),
    ("werkzeug", "Werkzeug", "2.3.7"),
    ("yaml", "pyyaml", "6.0"),
]

optional_modules = [
    ("matplotlib", "matplotlib", "3.7.2"),
    ("seaborn", "seaborn", "0.12.2"),
    ("netifaces", "netifaces", "0.11.0"),
    ("psutil", "psutil", "5.9.5"),
    ("tqdm", "tqdm", "4.65.0"),
]

print("🔍 Checking required dependencies...")
all_required_ok = True
for module, pip_name, version in required_modules:
    if not check_module(module, pip_name, version):
        all_required_ok = False

print("\n🔍 Checking optional dependencies...")
for module, pip_name, version in optional_modules:
    check_module(module, pip_name, version)

if all_required_ok:
    print("\n🎉 All required dependencies are installed! You can run the UPT Agent.")
else:
    print("\n❌ Some required dependencies are missing or incorrect version. Please install them first.")
    sys.exit(1)