import pytest
import tempfile
import os
from pytidb.utils import build_tidb_connection_url, merge_ca_path_into_url


def test_build_tidb_conn_url():
    # For TiDB Serverless
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="xxxxxxxx.root",
        password="$password$",
    )
    assert (
        url
        == "mysql+pymysql://xxxxxxxx.root:%24password%24@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true"
    )

    # For TiDB Cluster on local.
    url = build_tidb_connection_url(
        host="localhost", username="root", password="password"
    )
    assert url == "mysql+pymysql://root:password@localhost:4000/test"

    # Defaults
    url = build_tidb_connection_url()
    assert url == "mysql+pymysql://root@localhost:4000/test"


def test_build_tidb_conn_url_invalid():
    # Unacceptable schema
    with pytest.raises(ValueError):
        build_tidb_connection_url(schema="invalid_schema")

    # Missing host
    with pytest.raises(ValueError):
        build_tidb_connection_url(host="")


def test_build_tidb_conn_url_with_ca_path():
    """Test build_tidb_connection_url with CA certificate path."""
    # Create a temporary CA file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as ca_file:
        ca_file.write("-----BEGIN CERTIFICATE-----\ntest certificate\n-----END CERTIFICATE-----")
        ca_file_path = ca_file.name

    try:
        # Test TiDB Serverless with CA path
        url = build_tidb_connection_url(
            host="gateway01.us-west-2.prod.aws.tidbcloud.com",
            username="test.root",
            password="password",
            ca_path=ca_file_path
        )
        # Check that ssl_ca parameter is present with the correct path
        assert "ssl_verify_cert=true" in url
        assert "ssl_verify_identity=true" in url
        assert f"ssl_ca={ca_file_path}" in url

        # Test local TiDB with CA path and explicit SSL enabled
        url = build_tidb_connection_url(
            host="localhost",
            username="root",
            password="password",
            enable_ssl=True,
            ca_path=ca_file_path
        )
        assert "ssl_verify_cert=true" in url
        assert "ssl_verify_identity=true" in url
        assert f"ssl_ca={ca_file_path}" in url

        # Test local TiDB with CA path but SSL disabled (CA path should be ignored)
        url = build_tidb_connection_url(
            host="localhost",
            username="root",
            password="password",
            enable_ssl=False,
            ca_path=ca_file_path
        )
        assert "ssl_verify_cert" not in url
        assert "ssl_verify_identity" not in url
        assert "ssl_ca" not in url

    finally:
        # Clean up temporary file
        os.unlink(ca_file_path)


def test_build_tidb_conn_url_ca_path_edge_cases():
    """Test edge cases for CA path parameter."""
    # Test with None ca_path (should work normally)
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        ca_path=None
    )
    assert "ssl_verify_cert=true" in url
    assert "ssl_verify_identity=true" in url
    assert "ssl_ca" not in url

    # Test with empty string ca_path (should be ignored)
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        ca_path=""
    )
    assert "ssl_verify_cert=true" in url
    assert "ssl_verify_identity=true" in url
    assert "ssl_ca" not in url

    # Test CA path with special characters that need URL encoding
    special_path = "/path/with spaces/ca-cert.pem"
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        ca_path=special_path
    )
    # Check that spaces are properly encoded
    assert "ssl_ca=/path/with%20spaces/ca-cert.pem" in url


def test_build_tidb_conn_url_ca_path_backward_compatibility():
    """Test that existing behavior is preserved when ca_path is not used."""
    # TiDB Serverless without ca_path should work exactly as before
    url_without_ca = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="test.root",
        password="password"
    )

    url_with_none_ca = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="test.root",
        password="password",
        ca_path=None
    )

    # Should produce identical URLs
    assert url_without_ca == url_with_none_ca

    # Local TiDB without ca_path should work as before
    url_local = build_tidb_connection_url(host="localhost")
    assert "ssl_" not in url_local


def test_merge_ca_path_into_url():
    """Test merging CA path into database URLs."""
    ca_path = "/test/ca-cert.pem"

    # Test URL without query parameters
    url1 = "mysql+pymysql://user:pass@host:3306/db"
    result1 = merge_ca_path_into_url(url1, ca_path)
    assert "ssl_ca=%2Ftest%2Fca-cert.pem" in result1
    assert result1 == "mysql+pymysql://user:pass@host:3306/db?ssl_ca=%2Ftest%2Fca-cert.pem"

    # Test URL with existing query parameters
    url2 = "mysql+pymysql://user:pass@host:3306/db?ssl_verify_cert=true&ssl_verify_identity=true"
    result2 = merge_ca_path_into_url(url2, ca_path)
    assert "ssl_ca=%2Ftest%2Fca-cert.pem" in result2
    assert "ssl_verify_cert=true" in result2
    assert "ssl_verify_identity=true" in result2

    # Test URL that already has ssl_ca (P0 FIX: should override with new ca_path)
    url3 = "mysql+pymysql://user:pass@host:3306/db?ssl_ca=%2Fexisting%2Fca.pem"
    result3 = merge_ca_path_into_url(url3, ca_path)
    assert "ssl_ca=%2Ftest%2Fca-cert.pem" in result3  # Should use new ca_path
    assert "ssl_ca=%2Fexisting%2Fca.pem" not in result3  # Should not contain old ca_path

    # Test with None ca_path (should not modify)
    url4 = "mysql+pymysql://user:pass@host:3306/db"
    result4 = merge_ca_path_into_url(url4, None)
    assert result4 == url4  # Should be unchanged

    # Test with empty ca_path (should not modify)
    url5 = "mysql+pymysql://user:pass@host:3306/db"
    result5 = merge_ca_path_into_url(url5, "")
    assert result5 == url5  # Should be unchanged


def test_merge_ca_path_into_url_special_characters():
    """Test merging CA path with special characters."""
    ca_path = "/path/with spaces/ca-cert.pem"
    url = "mysql+pymysql://user:pass@host:3306/db"

    result = merge_ca_path_into_url(url, ca_path)
    # Spaces can be encoded as either %20 or + in URLs
    assert ("ssl_ca=%2Fpath%2Fwith%20spaces%2Fca-cert.pem" in result or
            "ssl_ca=%2Fpath%2Fwith+spaces%2Fca-cert.pem" in result)


def test_merge_ca_path_into_url_complex_scenarios():
    """Test complex URL scenarios."""
    ca_path = "/test/ca.pem"

    # Test URL with multiple existing parameters
    url1 = "mysql+pymysql://user:pass@host:3306/db?charset=utf8&autocommit=true&ssl_verify_cert=true"
    result1 = merge_ca_path_into_url(url1, ca_path)
    assert "ssl_ca=%2Ftest%2Fca.pem" in result1
    assert "charset=utf8" in result1
    assert "autocommit=true" in result1
    assert "ssl_verify_cert=true" in result1

    # Test URL with ssl_ca already present mixed with other params (P0 FIX: should override)
    url2 = "mysql+pymysql://user:pass@host:3306/db?charset=utf8&ssl_ca=%2Fother%2Fca.pem&ssl_verify_cert=true"
    result2 = merge_ca_path_into_url(url2, ca_path)
    assert "ssl_ca=%2Ftest%2Fca.pem" in result2  # Should use new ca_path
    assert "ssl_ca=%2Fother%2Fca.pem" not in result2  # Should not contain old ca_path
    assert "charset=utf8" in result2  # Other params should be preserved
    assert "ssl_verify_cert=true" in result2  # Other params should be preserved


def test_extract_ca_path_from_url():
    """Test extracting CA certificate path from database URLs."""
    from pytidb.utils import extract_ca_path_from_url

    # Test URL with ssl_ca parameter
    url1 = "mysql+pymysql://user:pass@host:3306/db?ssl_ca=%2Ftest%2Fca-cert.pem&ssl_verify_cert=true"
    result1 = extract_ca_path_from_url(url1)
    assert result1 == "/test/ca-cert.pem"

    # Test URL without ssl_ca parameter
    url2 = "mysql+pymysql://user:pass@host:3306/db?ssl_verify_cert=true"
    result2 = extract_ca_path_from_url(url2)
    assert result2 is None

    # Test URL with no query parameters
    url3 = "mysql+pymysql://user:pass@host:3306/db"
    result3 = extract_ca_path_from_url(url3)
    assert result3 is None

    # Test with None/empty URL
    result4 = extract_ca_path_from_url(None)
    assert result4 is None

    result5 = extract_ca_path_from_url("")
    assert result5 is None


def test_extract_ca_path_from_url_special_characters():
    """Test extracting CA path with special characters from URLs."""
    from pytidb.utils import extract_ca_path_from_url

    # Test URL with spaces (encoded as %20)
    url1 = "mysql+pymysql://user:pass@host:3306/db?ssl_ca=%2Fpath%2Fwith%20spaces%2Fca-cert.pem"
    result1 = extract_ca_path_from_url(url1)
    assert result1 == "/path/with spaces/ca-cert.pem"

    # Test URL with spaces (encoded as +)
    url2 = "mysql+pymysql://user:pass@host:3306/db?ssl_ca=%2Fpath%2Fwith+spaces%2Fca-cert.pem"
    result2 = extract_ca_path_from_url(url2)
    assert result2 == "/path/with spaces/ca-cert.pem"

    # Test Windows-style path with backslashes (encoded)
    url3 = "mysql+pymysql://user:pass@host:3306/db?ssl_ca=C%3A%5CProgram%20Files%5Cca-cert.pem"
    result3 = extract_ca_path_from_url(url3)
    assert result3 == "C:\\Program Files\\ca-cert.pem"


def test_extract_ca_path_from_url_multiple_values():
    """Test extracting CA path when ssl_ca appears multiple times in URL."""
    from pytidb.utils import extract_ca_path_from_url

    # Test URL with multiple ssl_ca parameters (should return first one)
    url = "mysql+pymysql://user:pass@host:3306/db?ssl_ca=%2Ffirst%2Fca.pem&ssl_ca=%2Fsecond%2Fca.pem"
    result = extract_ca_path_from_url(url)
    assert result == "/first/ca.pem"


def test_merge_ca_path_override_behavior():
    """P0 FIX TEST: Verify that explicit ca_path overrides existing ssl_ca in URLs."""
    from pytidb.utils import merge_ca_path_into_url

    # Test case for Windows users overriding Linux paths
    linux_ca_path = "/usr/share/ca-certificates/ca-cert.pem"
    windows_ca_path = "C:\\Program Files\\ca-cert.pem"

    # Original URL has Linux-style path (common in TIDB_DATABASE_URL)
    original_url = f"mysql+pymysql://user:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/db?ssl_ca=%2Fusr%2Fshare%2Fca-certificates%2Fca-cert.pem&ssl_verify_cert=true"

    # Explicit ca_path should override URL ssl_ca (key use case for TIDB_CA_PATH)
    result_url = merge_ca_path_into_url(original_url, windows_ca_path)

    # Verify override occurred
    assert "ssl_ca=C%3A%5CProgram%20Files%5Cca-cert.pem" in result_url
    assert "ssl_ca=%2Fusr%2Fshare%2Fca-certificates%2Fca-cert.pem" not in result_url

    # Verify other parameters preserved
    assert "ssl_verify_cert=true" in result_url
    assert "gateway01.us-west-2.prod.aws.tidbcloud.com:4000" in result_url

    # Test edge case: override empty/invalid paths
    invalid_url = "mysql+pymysql://user:pass@host:3306/db?ssl_ca=&ssl_verify_cert=true"
    valid_ca_path = "/valid/ca.pem"

    result_invalid = merge_ca_path_into_url(invalid_url, valid_ca_path)
    assert "ssl_ca=%2Fvalid%2Fca.pem" in result_invalid
    assert "ssl_ca=" not in result_invalid or "ssl_ca=%2Fvalid%2Fca.pem" in result_invalid

    # Test multiple override scenarios with special characters
    special_chars_url = "mysql+pymysql://user:pass@host:3306/db?ssl_ca=%2Fold%2Fpath%20with%20spaces%2Fca.pem"
    new_special_path = "/new/path with spaces/ca.pem"

    result_special = merge_ca_path_into_url(special_chars_url, new_special_path)
    assert ("%2Fnew%2Fpath%20with%20spaces%2Fca.pem" in result_special or
            "%2Fnew%2Fpath+with+spaces%2Fca.pem" in result_special)
    assert "%2Fold%2Fpath%20with%20spaces%2Fca.pem" not in result_special


def test_build_tidb_conn_url_ca_path_enables_ssl():
    """P0 REGRESSION TEST: ca_path should enable SSL for non-serverless hosts."""
    from pytidb.utils import build_tidb_connection_url

    # Non-serverless host (localhost) with ca_path should enable SSL
    url1 = build_tidb_connection_url(
        host="localhost",
        port=4000,
        username="root",
        password="password",
        database="test",
        enable_ssl=None,  # Explicitly None - this is the P0 issue scenario
        ca_path="/test/ca-cert.pem"
    )

    # Should contain SSL parameters including ssl_ca
    assert "ssl_verify_cert=true" in url1
    assert "ssl_verify_identity=true" in url1
    assert "ssl_ca=/test/ca-cert.pem" in url1

    # Custom IP host with Windows CA path should enable SSL
    url2 = build_tidb_connection_url(
        host="192.168.1.100",
        port=4000,
        username="user",
        password="pass",
        database="mydb",
        enable_ssl=None,
        ca_path="C:\\certs\\ca-cert.pem"
    )

    # Should contain SSL parameters with encoded Windows path
    assert "ssl_verify_cert=true" in url2
    assert "ssl_verify_identity=true" in url2
    assert "ssl_ca=C%3A%5Ccerts%5Cca-cert.pem" in url2

    # Same hosts without ca_path should NOT enable SSL
    url3 = build_tidb_connection_url(
        host="localhost",
        port=4000,
        username="root",
        password="password",
        database="test",
        enable_ssl=None,
        ca_path=None
    )

    # Should NOT contain any SSL parameters
    assert "ssl_" not in url3

    # Serverless host should still work with ca_path
    url4 = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        port=4000,
        username="test.root",
        password="password",
        database="test",
        enable_ssl=None,
        ca_path="/test/ca-cert.pem"
    )

    # Should contain SSL parameters for serverless
    assert "ssl_verify_cert=true" in url4
    assert "ssl_verify_identity=true" in url4
    assert "ssl_ca=/test/ca-cert.pem" in url4


def test_build_tidb_conn_url_explicit_enable_ssl_precedence():
    """Test that explicit enable_ssl parameter takes precedence over ca_path detection."""
    from pytidb.utils import build_tidb_connection_url

    # Explicit enable_ssl=False should disable SSL even with ca_path
    url1 = build_tidb_connection_url(
        host="localhost",
        port=4000,
        username="root",
        password="password",
        database="test",
        enable_ssl=False,  # Explicitly disabled
        ca_path="/test/ca-cert.pem"
    )

    # Should NOT contain SSL parameters when explicitly disabled
    assert "ssl_" not in url1

    # Explicit enable_ssl=True should enable SSL without ca_path
    url2 = build_tidb_connection_url(
        host="localhost",
        port=4000,
        username="root",
        password="password",
        database="test",
        enable_ssl=True,  # Explicitly enabled
        ca_path=None
    )

    # Should contain SSL parameters but no ssl_ca
    assert "ssl_verify_cert=true" in url2
    assert "ssl_verify_identity=true" in url2
    assert "ssl_ca=" not in url2
