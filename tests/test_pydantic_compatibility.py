#!/usr/bin/env python3
"""
Test suite for pydantic compatibility across versions 2.0.3, 2.5.3, 2.10.6, 2.12.3

This test module ensures pytidb works correctly across all supported pydantic versions.
"""

import warnings
import pytest
from typing import Optional, Any, Dict, List
from unittest.mock import Mock

# DO NOT suppress pydantic warnings globally - we need to detect them to ensure our fix works!


class TestPydanticBasicCompatibility:
    """Test basic pydantic functionality used by pytidb"""

    def test_pydantic_imports(self):
        """Test that all required pydantic imports work"""
        from pydantic import BaseModel, Field, PrivateAttr
        from pydantic import AnyUrl, UrlConstraints, ConfigDict

        # All imports should work without error
        assert BaseModel is not None
        assert Field is not None
        assert PrivateAttr is not None
        assert AnyUrl is not None
        assert UrlConstraints is not None
        assert ConfigDict is not None

    def test_base_model_functionality(self):
        """Test BaseModel functionality as used in pytidb"""
        from pydantic import BaseModel, Field, ConfigDict

        class TestModel(BaseModel):
            model_config = ConfigDict(protected_namespaces=())

            provider: str = Field("openai", description="Test provider")
            model_name: str = Field(None, description="Test model name")
            dimensions: Optional[int] = Field(None, description="Test dimensions")
            use_server: bool = Field(False, description="Test bool field")
            additional_json_options: Optional[Dict[str, Any]] = Field(None, description="Test dict field")

        # Test default instantiation
        model = TestModel()
        assert model.provider == "openai"
        assert model.model_name is None
        assert model.dimensions is None
        assert model.use_server is False
        assert model.additional_json_options is None

        # Test with values
        model2 = TestModel(
            provider="test",
            model_name="test-model",
            dimensions=768,
            use_server=True,
            additional_json_options={"key": "value"}
        )
        assert model2.provider == "test"
        assert model2.model_name == "test-model"
        assert model2.dimensions == 768
        assert model2.use_server is True
        assert model2.additional_json_options == {"key": "value"}

        # Test serialization (model_dump vs dict for older versions)
        if hasattr(model, 'model_dump'):
            data = model.model_dump()
        else:
            data = model.dict()

        assert isinstance(data, dict)
        assert data["provider"] == "openai"

    def test_url_constraints(self):
        """Test URL constraints functionality"""
        from pydantic import AnyUrl, UrlConstraints

        class TestURL(AnyUrl):
            _constraints = UrlConstraints(
                allowed_schemes=["mysql", "mysql+pymysql"],
                default_port=4000,
                host_required=True,
            )

        # Test URL building
        url = TestURL.build(
            scheme="mysql+pymysql",
            host="localhost",
            port=4000,
            username="root",
            path="test"
        )

        assert str(url).startswith("mysql+pymysql://")
        assert "localhost" in str(url)
        assert "test" in str(url)

    def test_private_attr(self):
        """Test PrivateAttr functionality"""
        from pydantic import BaseModel, PrivateAttr

        class TestPrivateModel(BaseModel):
            public_field: str = "public"
            _private_field: str = PrivateAttr(default="private")

        model = TestPrivateModel()
        assert model.public_field == "public"
        assert model._private_field == "private"

        # Private field should not be in serialized data
        if hasattr(model, 'model_dump'):
            data = model.model_dump()
        else:
            data = model.dict()

        assert "public_field" in data
        assert "_private_field" not in data


class TestPyTiDBPydanticIntegration:
    """Test pytidb's actual pydantic usage patterns"""

    def test_embedding_function_base(self):
        """Test BaseEmbeddingFunction model compatibility"""
        from pytidb.embeddings.base import BaseEmbeddingFunction

        # Test class definition and instantiation without warnings
        # NOTE: The warning occurs during class definition, not instantiation
        with warnings.catch_warnings(record=True) as w:
            warnings.resetwarnings()  # Clear any existing filters
            warnings.simplefilter("always")

            class TestEmbedding(BaseEmbeddingFunction):
                def get_query_embedding(self, query, source_type="text", **kwargs):
                    return [0.1, 0.2, 0.3]

                def get_source_embedding(self, source, source_type="text", **kwargs):
                    return [0.1, 0.2, 0.3]

                def get_source_embeddings(self, sources, source_type="text", **kwargs):
                    return [[0.1, 0.2, 0.3] for _ in sources]

            embed_fn = TestEmbedding(provider="test", model_name="test-model")

            # Check that no protected namespace warnings were raised
            pydantic_warnings = [warning for warning in w
                               if "protected namespace" in str(warning.message)]
            assert len(pydantic_warnings) == 0, f"Found pydantic warnings: {pydantic_warnings}"

        assert embed_fn.provider == "test"
        assert embed_fn.model_name == "test-model"
        assert embed_fn.dimensions is None
        assert embed_fn.use_server is False

        # Test methods work
        assert embed_fn.get_query_embedding("test") == [0.1, 0.2, 0.3]
        assert embed_fn.get_source_embedding("test") == [0.1, 0.2, 0.3]
        assert embed_fn.get_source_embeddings(["test1", "test2"]) == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]

    def test_search_models(self):
        """Test search-related pydantic models"""
        from pytidb.search import SearchResult

        # Test that SearchResult can be imported and used
        # (We'll create a minimal test since it depends on database results)
        assert SearchResult is not None

    def test_schema_models(self):
        """Test schema-related pydantic models"""
        from pytidb.schema import VectorField

        # Test basic VectorField functionality
        # Note: VectorField is more complex and depends on database types,
        # so we're just testing that it can be imported and basic functionality works
        assert VectorField is not None

    def test_result_models(self):
        """Test result-related pydantic models"""
        from pytidb.result import QueryResult, Result, SQLExecuteResult

        # Test that result models can be imported
        assert QueryResult is not None
        assert Result is not None
        assert SQLExecuteResult is not None

    def test_utils_url_functionality(self):
        """Test TiDBConnectionURL functionality"""
        from pytidb.utils import TiDBConnectionURL, build_tidb_connection_url

        # Test URL building
        url_str = build_tidb_connection_url(
            host="localhost",
            port=4000,
            username="root",
            password="",
            database="test"
        )

        assert isinstance(url_str, str)
        assert "mysql+pymysql://" in url_str
        assert "localhost" in url_str
        assert "4000" in url_str

        # Test URL validation
        url = TiDBConnectionURL(url_str)
        assert str(url) == url_str


class TestPydanticVersionSpecificFeatures:
    """Test features that might vary across pydantic versions"""

    def test_model_serialization_methods(self):
        """Test that both model_dump and dict methods are handled"""
        from pydantic import BaseModel, Field, ConfigDict

        class TestModel(BaseModel):
            model_config = ConfigDict(protected_namespaces=())
            test_field: str = Field("default", description="Test field")

        model = TestModel(test_field="test_value")

        # Test both serialization methods
        if hasattr(model, 'model_dump'):
            data1 = model.model_dump()
            assert data1["test_field"] == "test_value"

        if hasattr(model, 'dict'):
            data2 = model.dict()
            assert data2["test_field"] == "test_value"

        # At least one method should be available
        assert hasattr(model, 'model_dump') or hasattr(model, 'dict')

    def test_field_validation(self):
        """Test field validation works consistently"""
        from pydantic import BaseModel, Field, ValidationError, ConfigDict

        class TestModel(BaseModel):
            model_config = ConfigDict(protected_namespaces=())
            required_field: str = Field(..., description="Required field")
            optional_field: Optional[str] = Field(None, description="Optional field")

        # Test valid model
        model = TestModel(required_field="test")
        assert model.required_field == "test"
        assert model.optional_field is None

        # Test validation error
        with pytest.raises(ValidationError):
            TestModel()  # Missing required field

    def test_config_compatibility(self):
        """Test that ConfigDict works across versions"""
        from pydantic import BaseModel, ConfigDict

        class TestModel(BaseModel):
            model_config = ConfigDict(
                protected_namespaces=(),
                str_strip_whitespace=True,
            )
            test_field: str = "default"

        # Test that config is applied
        model = TestModel(test_field="  test  ")
        assert model.test_field == "test"  # Should be stripped


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])