#!/usr/bin/env python3
"""
Comprehensive pydantic compatibility test for pytidb across versions 2.0.3, 2.5.3, 2.10.6, 2.12.3
"""

import subprocess
import sys
import os
import json
import time
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

    # Run basic compatibility tests
    print("Running basic compatibility tests...")
    basic_result = subprocess.run([
        ".venv/bin/python", "test_pydantic_compat.py"
    ], capture_output=True, text=True)

    basic_success = basic_result.returncode == 0
    basic_output = basic_result.stdout
    basic_error = basic_result.stderr

    # Run comprehensive pytidb import tests
    print("Testing pytidb core imports...")
    import_result = subprocess.run([
        ".venv/bin/python", "-c",
        """
import warnings
warnings.filterwarnings('ignore', category=UserWarning, message='.*Field.*model_.*')

try:
    # Core imports
    from pytidb import TiDBClient, Session, Table
    print("✅ Core classes imported")

    # Embedding imports
    from pytidb.embeddings import EmbeddingFunction
    from pytidb.embeddings.base import BaseEmbeddingFunction
    print("✅ Embedding classes imported")

    # Search imports
    from pytidb.search import Search, SearchResult
    print("✅ Search classes imported")

    # Schema imports
    from pytidb.schema import VectorField
    print("✅ Schema classes imported")

    # Utils imports
    from pytidb.utils import TiDBConnectionURL, build_tidb_connection_url
    print("✅ Utils classes imported")

    # Result imports
    from pytidb.result import QueryResult, Result, SQLExecuteResult
    print("✅ Result classes imported")

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

    # Test embedding function instantiation (key use case)
    print("Testing embedding function instantiation...")
    embedding_result = subprocess.run([
        ".venv/bin/python", "-c",
        """
import warnings
warnings.filterwarnings('ignore', category=UserWarning, message='.*Field.*model_.*')

try:
    from pytidb.embeddings.base import BaseEmbeddingFunction

    class TestEmbedding(BaseEmbeddingFunction):
        def get_query_embedding(self, query, source_type="text", **kwargs):
            return [0.1, 0.2, 0.3]

        def get_source_embedding(self, source, source_type="text", **kwargs):
            return [0.1, 0.2, 0.3]

        def get_source_embeddings(self, sources, source_type="text", **kwargs):
            return [[0.1, 0.2, 0.3] for _ in sources]

    # Test instantiation with model_name (the problematic field)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        embed_fn = TestEmbedding(provider="test", model_name="test-model", dimensions=768)

        # Check for protected namespace warnings
        pydantic_warnings = [warning for warning in w
                           if "protected namespace" in str(warning.message)]
        if pydantic_warnings:
            print(f"WARNING: Found pydantic warnings: {[str(w.message) for w in pydantic_warnings]}")
        else:
            print("✅ No pydantic warnings found")

    # Test functionality
    assert embed_fn.provider == "test"
    assert embed_fn.model_name == "test-model"
    assert embed_fn.dimensions == 768
    assert embed_fn.get_query_embedding("test") == [0.1, 0.2, 0.3]

    # Test serialization
    if hasattr(embed_fn, 'model_dump'):
        data = embed_fn.model_dump()
    else:
        data = embed_fn.dict()

    assert data["provider"] == "test"
    assert data["model_name"] == "test-model"

    print("SUCCESS: Embedding function works correctly")
except Exception as e:
    print(f"ERROR: Embedding function test failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
        """
    ], capture_output=True, text=True)

    embedding_success = embedding_result.returncode == 0
    embedding_output = embedding_result.stdout
    embedding_error = embedding_result.stderr

    # Test URL functionality
    print("Testing URL functionality...")
    url_result = subprocess.run([
        ".venv/bin/python", "-c",
        """
try:
    from pytidb.utils import TiDBConnectionURL, build_tidb_connection_url

    # Test URL building
    url_str = build_tidb_connection_url(
        host="localhost",
        port=4000,
        username="root",
        password="testpass",
        database="test"
    )

    assert isinstance(url_str, str)
    assert "mysql+pymysql://" in url_str
    assert "localhost" in url_str

    # Test URL validation
    url = TiDBConnectionURL(url_str)
    assert str(url) == url_str

    print("SUCCESS: URL functionality works correctly")
except Exception as e:
    print(f"ERROR: URL functionality test failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
        """
    ], capture_output=True, text=True)

    url_success = url_result.returncode == 0
    url_output = url_result.stdout
    url_error = url_result.stderr

    # Run the dedicated pydantic compatibility tests
    print("Running dedicated pydantic compatibility test suite...")
    pytest_result = subprocess.run([
        ".venv/bin/python", "-m", "pytest", "tests/test_pydantic_compatibility.py", "-v", "--tb=short"
    ], capture_output=True, text=True)

    pytest_success = pytest_result.returncode == 0
    pytest_output = pytest_result.stdout
    pytest_error = pytest_result.stderr

    overall_success = (basic_success and import_success and embedding_success and
                      url_success and pytest_success)

    return {
        "version": version,
        "install_success": True,
        "basic_test_success": basic_success,
        "basic_test_output": basic_output,
        "basic_test_error": basic_error,
        "import_test_success": import_success,
        "import_test_output": import_output,
        "import_test_error": import_error,
        "embedding_test_success": embedding_success,
        "embedding_test_output": embedding_output,
        "embedding_test_error": embedding_error,
        "url_test_success": url_success,
        "url_test_output": url_output,
        "url_test_error": url_error,
        "pytest_success": pytest_success,
        "pytest_output": pytest_output,
        "pytest_error": pytest_error,
        "overall_success": overall_success
    }


def main():
    """Main test runner"""
    print("PyTiDB Pydantic Compatibility Test Suite - Comprehensive")
    print("Testing versions:", ", ".join(PYDANTIC_VERSIONS))
    print("Issue: https://github.com/pingcap/pytidb/issues/178")

    # Change to the correct directory
    os.chdir("/home/pan/workspace/pytidb")

    results = []
    start_time = time.time()

    for version in PYDANTIC_VERSIONS:
        result = run_with_pydantic_version(version)
        results.append(result)

        if result["overall_success"]:
            print(f"✅ pydantic=={version}: ALL TESTS PASSED")
        else:
            print(f"❌ pydantic=={version}: TESTS FAILED")
            failed_tests = []
            if not result.get("basic_test_success", False):
                failed_tests.append("basic")
            if not result.get("import_test_success", False):
                failed_tests.append("import")
            if not result.get("embedding_test_success", False):
                failed_tests.append("embedding")
            if not result.get("url_test_success", False):
                failed_tests.append("url")
            if not result.get("pytest_success", False):
                failed_tests.append("pytest")
            print(f"  Failed tests: {', '.join(failed_tests)}")

    # Summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for r in results if r["overall_success"])
    total = len(results)
    elapsed_time = time.time() - start_time

    print(f"Versions tested: {total}")
    print(f"Versions passed: {passed}")
    print(f"Success rate: {passed/total*100:.1f}%")
    print(f"Total time: {elapsed_time:.2f} seconds")

    print("\nDetailed results:")
    for result in results:
        status = "✅ PASS" if result["overall_success"] else "❌ FAIL"
        version = result["version"]
        print(f"  pydantic=={version}: {status}")

        if not result["overall_success"]:
            # Show first error for debugging
            if not result.get("import_test_success", False) and result.get("import_test_error"):
                error_lines = result["import_test_error"].split('\n')
                print(f"    Import error: {error_lines[-2] if len(error_lines) > 1 else error_lines[0]}")
            elif not result.get("embedding_test_success", False) and result.get("embedding_test_error"):
                error_lines = result["embedding_test_error"].split('\n')
                print(f"    Embedding error: {error_lines[-2] if len(error_lines) > 1 else error_lines[0]}")
            elif not result.get("pytest_success", False) and result.get("pytest_error"):
                error_lines = result["pytest_error"].split('\n')
                print(f"    Pytest error: {error_lines[-2] if len(error_lines) > 1 else error_lines[0]}")

    # Save detailed results
    results_file = "pydantic_compatibility_results_comprehensive.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nDetailed results saved to: {results_file}")

    # Create summary report
    summary_file = "PYDANTIC_COMPATIBILITY_REPORT.md"
    with open(summary_file, "w") as f:
        f.write("# PyTiDB Pydantic Compatibility Report\n\n")
        f.write(f"**Issue:** https://github.com/pingcap/pytidb/issues/178\n\n")
        f.write(f"**Test Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Versions Tested:** {', '.join(PYDANTIC_VERSIONS)}\n\n")
        f.write(f"**Success Rate:** {passed}/{total} ({passed/total*100:.1f}%)\n\n")

        f.write("## Test Results\n\n")
        for result in results:
            status = "✅ PASS" if result["overall_success"] else "❌ FAIL"
            f.write(f"- **pydantic {result['version']}**: {status}\n")

        f.write("\n## Test Coverage\n\n")
        f.write("The following functionality was tested across all pydantic versions:\n\n")
        f.write("1. Basic pydantic imports (BaseModel, Field, PrivateAttr, etc.)\n")
        f.write("2. Core pytidb module imports\n")
        f.write("3. BaseEmbeddingFunction instantiation (with model_name field)\n")
        f.write("4. TiDBConnectionURL functionality\n")
        f.write("5. Comprehensive test suite via pytest\n\n")

        if passed == total:
            f.write("## ✅ Conclusion\n\n")
            f.write("PyTiDB is fully compatible with all tested pydantic versions.\n")
        else:
            f.write("## ❌ Issues Found\n\n")
            for result in results:
                if not result["overall_success"]:
                    f.write(f"### pydantic {result['version']}\n\n")
                    # Add error details...

    print(f"Summary report saved to: {summary_file}")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)