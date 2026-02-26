import sys
try:
    import httpx
    print(f"httpx version: {httpx.__version__}")
except ImportError:
    print("httpx not installed")

try:
    import brotlicffi
    print(f"brotlicffi version: {brotlicffi.__version__ if hasattr(brotlicffi, '__version__') else 'installed (unknown version)'}")
except ImportError:
    print("brotlicffi not installed")

try:
    import brotli
    print(f"brotli version: {brotli.__version__ if hasattr(brotli, '__version__') else 'installed (unknown version)'}")
except ImportError:
    print("brotli not installed")
