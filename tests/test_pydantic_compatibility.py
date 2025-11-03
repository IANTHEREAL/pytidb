"""
Comprehensive Pydantic compatibility tests for pytidb.

This test module validates that pytidb works correctly across different
Pydantic versions (2.0.3, 2.5.3, 2.10.6, 2.12.3) by testing key integration
points and ensuring no warnings are generated.
"""

import pytest
import warnings
from typing import Optional, Any
from unittest.mock import Mock

from pytidb.embeddings.base import BaseEmbeddingFunction, EmbeddingSourceType
from pytidb.search import SearchResult
from pytidb.result import SQLExecuteResult


class MockEmbeddingFunction(BaseEmbeddingFunction):
    """Concrete implementation for testing BaseEmbeddingFunction."""

    def get_query_embedding(
        self, query: Any, source_type: Optional[EmbeddingSourceType] = "text", **kwargs
    ) -> list[float]:
        return [0.1, 0.2, 0.3]

    def get_source_embedding(
        self, source: Any, source_type: Optional[EmbeddingSourceType] = "text", **kwargs
    ) -> list[float]:
        return [0.1, 0.2, 0.3]

    def get_source_embeddings(
        self,
        sources: list[Any],
        source_type: Optional[EmbeddingSourceType] = "text",
        **kwargs,
    ) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in sources]


class MockHit:
    """Mock hit object for testing SearchResult."""

    def __init__(self, id: int, content: str):
        self.id = id
        self.content = content

    def __eq__(self, other):
        return isinstance(other, MockHit) and self.id == other.id and self.content == other.content


class TestPydanticCompatibility:
    """Test Pydantic compatibility across versions."""

    def test_base_embedding_function_instantiation(self):
        """Test BaseEmbeddingFunction can be instantiated without warnings."""

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            embed_func = MockEmbeddingFunction(
                model_name="test-model",
                provider="test-provider",
                dimensions=384
            )

            # Check no protected namespace warnings
            protected_warnings = [
                warning for warning in w
                if "protected" in str(warning.message).lower() and "model_name" in str(warning.message)
            ]

            assert len(protected_warnings) == 0, f"Protected namespace warnings: {protected_warnings}"

            # Verify attributes are set correctly
            assert embed_func.model_name == "test-model"
            assert embed_func.provider == "test-provider"
            assert embed_func.dimensions == 384

    def test_base_embedding_function_serialization(self):
        """Test BaseEmbeddingFunction serialization methods."""

        embed_func = MockEmbeddingFunction(
            model_name="test-model",
            provider="openai"
        )

        # Test model_dump (Pydantic v2)
        data = embed_func.model_dump()
        assert isinstance(data, dict)
        assert data["model_name"] == "test-model"
        assert data["provider"] == "openai"

        # Test model_validate (Pydantic v2)
        test_data = {
            "model_name": "another-model",
            "provider": "test-provider",
            "dimensions": 512
        }

        new_func = MockEmbeddingFunction.model_validate(test_data)
        assert new_func.model_name == "another-model"
        assert new_func.provider == "test-provider"
        assert new_func.dimensions == 512

    def test_search_result_with_generic_types(self):
        """Test SearchResult works with generic types without warnings."""

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            hit = MockHit(id=1, content="test content")
            result = SearchResult[MockHit](
                hit=hit,
                distance=0.5,
                match_score=0.8,
                score=0.9
            )

            # Check no arbitrary types warnings
            arbitrary_warnings = [
                warning for warning in w
                if "arbitrary" in str(warning.message).lower()
            ]

            assert len(arbitrary_warnings) == 0, f"Arbitrary types warnings: {arbitrary_warnings}"

            # Verify attributes
            assert result.hit == hit
            assert result.distance == 0.5
            assert result.match_score == 0.8
            assert result.score == 0.9

    def test_search_result_serialization(self):
        """Test SearchResult serialization with generic types."""

        hit = MockHit(id=1, content="test content")
        result = SearchResult[MockHit](
            hit=hit,
            distance=0.5
        )

        # Test model_dump
        data = result.model_dump()
        assert isinstance(data, dict)
        assert data["distance"] == 0.5
        assert "hit" in data

    def test_search_result_similarity_score(self):
        """Test SearchResult similarity_score property."""

        hit = MockHit(id=1, content="test")

        # Test with distance
        result_with_distance = SearchResult[MockHit](
            hit=hit,
            distance=0.2
        )
        assert result_with_distance.similarity_score == 0.8  # 1 - 0.2

        # Test without distance
        result_without_distance = SearchResult[MockHit](
            hit=hit
        )
        assert result_without_distance.similarity_score is None

    def test_search_result_attribute_delegation(self):
        """Test SearchResult delegates attributes to hit object."""

        hit = MockHit(id=42, content="delegate test")
        result = SearchResult[MockHit](hit=hit)

        # Test attribute delegation
        assert result.id == 42
        assert result.content == "delegate test"

        # Test AttributeError for non-existent attributes
        with pytest.raises(AttributeError):
            _ = result.non_existent_attribute

    def test_sql_execute_result(self):
        """Test SQLExecuteResult model."""

        # Test default values
        result = SQLExecuteResult()
        assert result.rowcount == 0
        assert result.success is False
        assert result.message is None

        # Test with values
        result = SQLExecuteResult(
            rowcount=5,
            success=True,
            message="Operation completed"
        )

        assert result.rowcount == 5
        assert result.success is True
        assert result.message == "Operation completed"

        # Test serialization
        data = result.model_dump()
        assert data["rowcount"] == 5
        assert data["success"] is True
        assert data["message"] == "Operation completed"

    def test_config_dict_settings(self):
        """Test that ConfigDict settings are properly applied."""

        # Test BaseEmbeddingFunction has protected_namespaces config
        embed_func = MockEmbeddingFunction(model_name="test")
        config = embed_func.model_config

        # Check that protected_namespaces is set to empty tuple
        assert hasattr(config, "get") or hasattr(config, "__getitem__")

        # For ConfigDict, check the protected_namespaces setting
        if hasattr(config, "get"):
            protected_ns = config.get("protected_namespaces", None)
        else:
            protected_ns = getattr(config, "protected_namespaces", None)

        assert protected_ns == (), f"Expected empty tuple for protected_namespaces, got {protected_ns}"

        # Test SearchResult has arbitrary_types_allowed config
        hit = MockHit(id=1, content="test")
        result = SearchResult[MockHit](hit=hit)
        config = result.model_config

        if hasattr(config, "get"):
            arbitrary_types = config.get("arbitrary_types_allowed", None)
        else:
            arbitrary_types = getattr(config, "arbitrary_types_allowed", None)

        assert arbitrary_types is True, f"Expected True for arbitrary_types_allowed, got {arbitrary_types}"

    def test_no_pydantic_warnings(self):
        """Comprehensive test to ensure no Pydantic warnings are generated."""

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Test various operations that could trigger warnings
            embed_func = MockEmbeddingFunction(
                model_name="test-model",
                provider="test"
            )

            hit = MockHit(id=1, content="test")
            result = SearchResult[MockHit](hit=hit, distance=0.3)

            sql_result = SQLExecuteResult(rowcount=1, success=True)

            # Test serialization
            embed_data = embed_func.model_dump()
            result_data = result.model_dump()
            sql_data = sql_result.model_dump()

            # Test validation
            MockEmbeddingFunction.model_validate(embed_data)
            SQLExecuteResult.model_validate(sql_data)

            # Filter out unrelated warnings and check for Pydantic-specific warnings
            pydantic_warnings = [
                warning for warning in w
                if any(keyword in str(warning.message).lower()
                      for keyword in ["pydantic", "protected", "arbitrary", "model_name"])
            ]

            assert len(pydantic_warnings) == 0, f"Unexpected Pydantic warnings: {pydantic_warnings}"


# Pytest markers for different test scenarios
class TestPydanticVersionSpecific:
    """Version-specific tests that may behave differently across Pydantic versions."""

    @pytest.mark.parametrize("field_name,field_value", [
        ("model_name", "test-model"),
        ("provider", "openai"),
        ("dimensions", 384),
    ])
    def test_field_validation(self, field_name, field_value):
        """Test field validation works consistently across versions."""

        kwargs = {field_name: field_value}
        embed_func = MockEmbeddingFunction(**kwargs)

        assert getattr(embed_func, field_name) == field_value

    def test_model_config_compatibility(self):
        """Test model_config is compatible across Pydantic versions."""

        # Test that model_config exists and has expected structure
        embed_func = MockEmbeddingFunction(model_name="test")
        assert hasattr(embed_func, "model_config")

        result = SearchResult[MockHit](hit=MockHit(1, "test"))
        assert hasattr(result, "model_config")

        # Both should be ConfigDict instances or compatible
        embed_config = embed_func.model_config
        result_config = result.model_config

        # Basic sanity check - configs should be objects with attributes
        assert embed_config is not None
        assert result_config is not None