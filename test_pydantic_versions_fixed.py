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
    result = subprocess.run([
        ".venv/bin/python", "test_pydantic_compat.py"
    ], capture_output=True, text=True)

    test_success = result.returncode == 0
    test_output = result.stdout
    test_error = result.stderr

    # Try to import pytidb core modules with correct names
    print("Testing pytidb imports...")
    import_result = subprocess.run([
        ".venv/bin/python", "-c",
        """
import warnings
warnings.filterwarnings('ignore', category=UserWarning, message='.*Field.*model_.*')

try:
    from pytidb import TiDBClient, Session, Table
    from pytidb.embeddings import EmbeddingFunction
    from pytidb.search import Search, SearchResult
    from pytidb.schema import VectorField
    from pytidb.utils import TiDBConnectionURL
    from pytidb.result import SearchResult as ResultSearchResult
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
        ".venv/bin/python", "-c",
        """
import warnings
warnings.filterwarnings('ignore', category=UserWarning, message='.*Field.*model_.*')

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

    # Change to the correct directory
    os.chdir("/home/pan/workspace/pytidb")

    results = []

    for version in PYDANTIC_VERSIONS:
        result = run_with_pydantic_version(version)
        results.append(result)

        if result["overall_success"]:
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

    passed = sum(1 for r in results if r["overall_success"])
    total = len(results)

    print(f"Versions tested: {total}")
    print(f"Versions passed: {passed}")
    print(f"Success rate: {passed/total*100:.1f}%")

    print("\nDetailed results:")
    for result in results:
        status = "✅ PASS" if result["overall_success"] else "❌ FAIL"
        print(f"  pydantic=={result['version']}: {status}")
        if not result["overall_success"]:
            if not result.get("compatibility_test_success", False):
                print(f"    Compatibility error: {result.get('compatibility_test_error', 'Unknown')[:100]}...")
            if not result.get("import_test_success", False):
                print(f"    Import error: {result.get('import_test_error', 'Unknown')[:100]}...")
            if not result.get("model_test_success", False):
                print(f"    Model error: {result.get('model_test_error', 'Unknown')[:100]}...")

    # Save detailed results
    with open("pydantic_compatibility_results_fixed.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nDetailed results saved to: pydantic_compatibility_results_fixed.json")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)