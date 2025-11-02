#!/usr/bin/env python3
"""
Pydantic compatibility test script for pytidb

Tests pydantic compatibility across versions 2.0.3, 2.5.3, 2.10.6, 2.12.3
"""

import sys
import importlib
import traceback
from typing import Optional, Any, Dict, List


def test_pydantic_imports():
    """Test basic pydantic imports used by pytidb"""
    try:
        from pydantic import BaseModel, Field, PrivateAttr
        from pydantic import AnyUrl, UrlConstraints

        # Test for MySQLDsn (might not be available in all versions)
        try:
            from pydantic import MySQLDsn
            mysql_dsn_available = True
        except ImportError:
            mysql_dsn_available = False

        return True, {"mysql_dsn_available": mysql_dsn_available}
    except Exception as e:
        return False, {"error": str(e)}


def test_base_model_functionality():
    """Test BaseModel functionality used in pytidb"""
    try:
        from pydantic import BaseModel, Field

        class TestModel(BaseModel):
            provider: str = Field("openai", description="Test provider")
            dimensions: Optional[int] = Field(None, description="Test dimensions")
            use_server: bool = Field(False, description="Test bool field")
            additional_json_options: Optional[Dict[str, Any]] = Field(None, description="Test dict field")

        # Test instantiation
        model = TestModel()
        assert model.provider == "openai"
        assert model.dimensions is None
        assert model.use_server is False

        # Test with values
        model2 = TestModel(provider="test", dimensions=768, use_server=True)
        assert model2.provider == "test"
        assert model2.dimensions == 768
        assert model2.use_server is True

        return True, {"model_dict": model.model_dump() if hasattr(model, 'model_dump') else model.dict()}
    except Exception as e:
        return False, {"error": str(e), "traceback": traceback.format_exc()}


def test_url_constraints():
    """Test URL constraints functionality"""
    try:
        from pydantic import AnyUrl, UrlConstraints

        class TestURL(AnyUrl):
            _constraints = UrlConstraints(
                allowed_schemes=["mysql", "mysql+pymysql"],
                default_port=4000,
                host_required=True,
            )

        # Try to build a URL
        url = TestURL.build(
            scheme="mysql+pymysql",
            host="localhost",
            port=4000,
            username="root",
            path="test"
        )

        return True, {"url": str(url)}
    except Exception as e:
        return False, {"error": str(e), "traceback": traceback.format_exc()}


def test_private_attr():
    """Test PrivateAttr functionality"""
    try:
        from pydantic import BaseModel, PrivateAttr

        class TestPrivateModel(BaseModel):
            public_field: str = "public"
            _private_field: str = PrivateAttr(default="private")

        model = TestPrivateModel()
        assert model.public_field == "public"
        assert model._private_field == "private"

        return True, {"model_created": True}
    except Exception as e:
        return False, {"error": str(e), "traceback": traceback.format_exc()}


def run_compatibility_tests():
    """Run all compatibility tests"""
    import pydantic
    print(f"Testing pydantic version: {pydantic.__version__}")
    print("=" * 50)

    tests = [
        ("Basic Imports", test_pydantic_imports),
        ("BaseModel Functionality", test_base_model_functionality),
        ("URL Constraints", test_url_constraints),
        ("PrivateAttr", test_private_attr),
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        try:
            success, data = test_func()
            if success:
                print(f"  ✅ PASSED")
                results[test_name] = {"status": "PASSED", "data": data}
            else:
                print(f"  ❌ FAILED: {data.get('error', 'Unknown error')}")
                results[test_name] = {"status": "FAILED", "data": data}
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            results[test_name] = {"status": "ERROR", "error": str(e)}
        print()

    return results


if __name__ == "__main__":
    results = run_compatibility_tests()

    # Print summary
    print("SUMMARY:")
    print("=" * 30)
    passed = sum(1 for r in results.values() if r["status"] == "PASSED")
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if passed != total:
        print("\nFailed tests:")
        for test_name, result in results.items():
            if result["status"] != "PASSED":
                print(f"  - {test_name}: {result['status']}")
                if "error" in result:
                    print(f"    Error: {result['error']}")
                elif "data" in result and "error" in result["data"]:
                    print(f"    Error: {result['data']['error']}")