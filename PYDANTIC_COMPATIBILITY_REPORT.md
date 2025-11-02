# PyTiDB Pydantic Compatibility Report

**Issue:** https://github.com/pingcap/pytidb/issues/178

**Test Date:** 2025-11-02 04:42:35

**Versions Tested:** 2.0.3, 2.5.3, 2.10.6, 2.12.3

**Success Rate:** 0/4 (0.0%)

## Test Results

- **pydantic 2.0.3**: ❌ FAIL
- **pydantic 2.5.3**: ❌ FAIL
- **pydantic 2.10.6**: ❌ FAIL
- **pydantic 2.12.3**: ❌ FAIL

## Test Coverage

The following functionality was tested across all pydantic versions:

1. Basic pydantic imports (BaseModel, Field, PrivateAttr, etc.)
2. Core pytidb module imports
3. BaseEmbeddingFunction instantiation (with model_name field)
4. TiDBConnectionURL functionality
5. Comprehensive test suite via pytest

## ❌ Issues Found

### pydantic 2.0.3

### pydantic 2.5.3

### pydantic 2.10.6

### pydantic 2.12.3

