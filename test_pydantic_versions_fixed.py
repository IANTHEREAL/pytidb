#!/usr/bin/env python3
"""
Test pytidb compatibility across multiple pydantic versions - Fixed version
"""

import subprocess
import sys
import os
import json
from pathlib import Path

# Pydantic versions to test (as specified in the issue)
PYDANTIC_VERSIONS = ["2.0.3", "2.5.3", "2.10.6", "2.12.3"]


def find_project_root():
    """Find the project root directory by looking for pyproject.toml"""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    raise FileNotFoundError("Could not find project root (pyproject.toml not found)")


def get_python_executable():
    """Get the Python executable to use, with optional override"""
    return os.environ.get("PYTIDB_PYTHON", sys.executable)

def run_with_pydantic_version(version: str):
    """Test pytidb with a specific pydantic version"""
    print(f"\n{'='*60}")
    print(f"Testing with pydantic=={version}")
    print(f"{'='*60}")

    # Install specific pydantic version
    print(f"Installing pydantic=={version}...")
    result = subprocess.run([
        "uv", "pip", "install", f"pydantic=={version}"
    ], capture_output=True, text=True, env={**os.environ, "PATH": f"{os.environ['HOME']}/.local/bin:{os.environ['PATH']}"})

    if result.returncode != 0:
        print(f"❌ Failed to install pydantic=={version}")
        print(f"Error: {result.stderr}")
        return {"version": version, "install_success": False, "error": result.stderr}

    print(f"✅ Successfully installed pydantic=={version}")

    # Run compatibility tests
    print("Running compatibility tests...")
    python_exe = get_python_executable()
    result = subprocess.run([
        python_exe, "test_pydantic_compat.py"
    ], capture_output=True, text=True)

    test_success = result.returncode == 0
    test_output = result.stdout
    test_error = result.stderr

    # Try to import pytidb core modules with correct names
    print("Testing pytidb imports...")
    import_result = subprocess.run([
        python_exe, "-c",
        """
import warnings
# DO NOT suppress warnings globally - we need to detect them!

try:
    from pytidb import TiDBClient, Session, Table
    from pytidb.embeddings import EmbeddingFunction
    from pytidb.search import Search, SearchResult
    from pytidb.schema import VectorField
    from pytidb.utils import TiDBConnectionURL
    # Note: SearchResult is in pytidb.search, not pytidb.result
    from pytidb.result import QueryResult, Result, SQLExecuteResult
    print("SUCCESS: All core pytidb modules imported successfully")
except Exception as e:
    print(f"ERROR: Failed to import pytidb modules: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
        """
    ], capture_output=True, text=True)

    import_success = import_result.returncode == 0
    import_output = import_result.stdout
    import_error = import_result.stderr

    # Test creating a basic embedding function to check model compatibility
    print("Testing model instantiation...")
    model_result = subprocess.run([
        python_exe, "-c",
        """
import warnings
# DO NOT suppress warnings globally - we need to detect them!

try:
    from pytidb.embeddings.base import BaseEmbeddingFunction
    from pydantic import BaseModel, Field

    # Test creating a simple model like in pytidb
    class TestEmbedding(BaseEmbeddingFunction):
        def get_query_embedding(self, query, source_type="text", **kwargs):
            return [0.1, 0.2, 0.3]

        def get_source_embedding(self, source, source_type="text", **kwargs):
            return [0.1, 0.2, 0.3]

        def get_source_embeddings(self, sources, source_type="text", **kwargs):
            return [[0.1, 0.2, 0.3] for _ in sources]

    # Try to instantiate
    embed_fn = TestEmbedding(provider="test", model_name="test-model")
    print("SUCCESS: Model instantiation works")
    print(f"Model dump: {embed_fn.model_dump() if hasattr(embed_fn, 'model_dump') else embed_fn.dict()}")
except Exception as e:
    print(f"ERROR: Model instantiation failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
        """
    ], capture_output=True, text=True)

    model_success = model_result.returncode == 0
    model_output = model_result.stdout
    model_error = model_result.stderr

    return {
        "version": version,
        "install_success": True,
        "compatibility_test_success": test_success,
        "compatibility_test_output": test_output,
        "compatibility_test_error": test_error,
        "import_test_success": import_success,
        "import_test_output": import_output,
        "import_test_error": import_error,
        "model_test_success": model_success,
        "model_test_output": model_output,
        "model_test_error": model_error,
        "overall_success": test_success and import_success and model_success
    }


def main():
    """Main test runner"""
    print("PyTiDB Pydantic Compatibility Test Suite - Fixed")
    print("Testing versions:", ", ".join(PYDANTIC_VERSIONS))

    # Find and change to the project root directory
    project_root = find_project_root()
    print(f"Project root: {project_root}")
    os.chdir(project_root)

    results = []

    for version in PYDANTIC_VERSIONS:
        result = run_with_pydantic_version(version)
        results.append(result)

        # Check install success first, then overall success
        if not result.get("install_success", True):
            print(f"❌ pydantic=={version}: INSTALL FAILED")
            print(f"  - Install error: {result.get('error', 'Unknown error')}")
        elif result.get("overall_success", False):
            print(f"✅ pydantic=={version}: ALL TESTS PASSED")
        else:
            print(f"❌ pydantic=={version}: TESTS FAILED")
            if not result.get("compatibility_test_success", False):
                print("  - Compatibility tests failed")
            if not result.get("import_test_success", False):
                print("  - Import tests failed")
            if not result.get("model_test_success", False):
                print("  - Model tests failed")

    # Summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for r in results if r.get("install_success", True) and r.get("overall_success", False))
    total = len(results)

    print(f"Versions tested: {total}")
    print(f"Versions passed: {passed}")
    print(f"Success rate: {passed/total*100:.1f}%")

    print("\nDetailed results:")
    for result in results:
        if not result.get("install_success", True):
            status = "❌ INSTALL FAILED"
        elif result.get("overall_success", False):
            status = "✅ PASS"
        else:
            status = "❌ FAIL"

        print(f"  pydantic=={result['version']}: {status}")

        # Show errors for failed installs or failed tests
        if not result.get("install_success", True):
            print(f"    Install error: {result.get('error', 'Unknown')[:100]}...")
        elif not result.get("overall_success", False):
            if not result.get("compatibility_test_success", False):
                print(f"    Compatibility error: {result.get('compatibility_test_error', 'Unknown')[:100]}...")
            if not result.get("import_test_success", False):
                print(f"    Import error: {result.get('import_test_error', 'Unknown')[:100]}...")
            if not result.get("model_test_success", False):
                print(f"    Model error: {result.get('model_test_error', 'Unknown')[:100]}...")

    # Ensure .compat_reports directory exists
    os.makedirs(".compat_reports", exist_ok=True)

    # Save detailed results
    results_file = ".compat_reports/pydantic_compatibility_results_fixed.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nDetailed results saved to: {results_file}")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)