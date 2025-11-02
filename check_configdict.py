#!/usr/bin/env python3
"""Check ConfigDict availability across pydantic versions"""

import subprocess
import sys
import os

VERSIONS = ["2.0.3", "2.5.3", "2.10.6", "2.12.3"]

for version in VERSIONS:
    print(f"Testing pydantic {version}...")

    # Install version
    subprocess.run([
        "uv", "pip", "install", f"pydantic=={version}"
    ], capture_output=True, env={**os.environ, "PATH": f"{os.environ['HOME']}/.local/bin:{os.environ['PATH']}"})

    # Test ConfigDict
    result = subprocess.run([
        ".venv/bin/python", "-c",
        """
import pydantic
print(f'Version: {pydantic.__version__}')
try:
    from pydantic import ConfigDict
    print('ConfigDict: AVAILABLE')
except ImportError:
    print('ConfigDict: NOT AVAILABLE')
try:
    # Test alternative approach
    from pydantic import BaseConfig
    print('BaseConfig: AVAILABLE')
except ImportError:
    print('BaseConfig: NOT AVAILABLE')
        """
    ], capture_output=True, text=True)

    print(result.stdout.strip())
    print("-" * 30)