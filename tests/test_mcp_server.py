"""
Tests for MCP server CA path functionality.
"""
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from pytidb.ext.mcp.server import TiDBConnector


def test_tidb_connector_with_ca_path():
    """Test TiDBConnector accepts and passes ca_path parameter."""
    ca_file_path = "/test/path/ca.pem"

    # Mock TiDBClient.connect to verify ca_path is passed
    with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.connect.return_value = mock_client

        # Create TiDBConnector with ca_path
        connector = TiDBConnector(
            host="localhost",
            port=4000,
            username="root",
            password="test",
            database="testdb",
            ca_path=ca_file_path
        )

        # Verify TiDBClient.connect was called with ca_path
        mock_client_class.connect.assert_called_once_with(
            url=None,
            host="localhost",
            port=4000,
            username="root",
            password="test",
            database="testdb",
            ca_path=ca_file_path
        )


def test_tidb_connector_without_ca_path():
    """Test TiDBConnector works without ca_path (backward compatibility)."""
    with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.connect.return_value = mock_client

        # Create TiDBConnector without ca_path
        connector = TiDBConnector(
            host="localhost",
            port=4000,
            username="root",
            password="test",
            database="testdb"
        )

        # Verify TiDBClient.connect was called with ca_path=None
        mock_client_class.connect.assert_called_once_with(
            url=None,
            host="localhost",
            port=4000,
            username="root",
            password="test",
            database="testdb",
            ca_path=None
        )


def test_tidb_connector_with_database_url():
    """Test TiDBConnector with database URL (ca_path should be ignored)."""
    database_url = "mysql+pymysql://user:pass@host:3306/db?ssl_verify_cert=true"
    ca_file_path = "/test/path/ca.pem"

    with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.connect.return_value = mock_client

        # Create TiDBConnector with database_url and ca_path
        connector = TiDBConnector(
            database_url=database_url,
            ca_path=ca_file_path
        )

        # When database_url is provided, individual parameters are ignored
        # but ca_path should still be passed to connect()
        mock_client_class.connect.assert_called_once_with(
            url=database_url,
            host=None,
            port=None,
            username=None,
            password=None,
            database=None,
            ca_path=ca_file_path
        )


@patch.dict(os.environ, {}, clear=True)
def test_mcp_server_ca_path_env_var():
    """Test MCP server reads TIDB_CA_PATH environment variable."""
    ca_file_path = "/test/ca-cert.pem"

    # Set environment variables
    test_env = {
        'TIDB_HOST': 'test-host',
        'TIDB_PORT': '3306',
        'TIDB_USERNAME': 'testuser',
        'TIDB_PASSWORD': 'testpass',
        'TIDB_DATABASE': 'testdb',
        'TIDB_CA_PATH': ca_file_path
    }

    with patch.dict(os.environ, test_env):
        with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.connect.return_value = mock_client

            # Create TiDBConnector (simulating MCP server initialization)
            connector = TiDBConnector(
                database_url=os.getenv("TIDB_DATABASE_URL", None),
                host=os.getenv("TIDB_HOST", "127.0.0.1"),
                port=int(os.getenv("TIDB_PORT", "4000")),
                username=os.getenv("TIDB_USERNAME", "root"),
                password=os.getenv("TIDB_PASSWORD", ""),
                database=os.getenv("TIDB_DATABASE", "test"),
                ca_path=os.getenv("TIDB_CA_PATH", None),
            )

            # Verify the correct values were read from environment
            mock_client_class.connect.assert_called_once_with(
                url=None,
                host='test-host',
                port=3306,
                username='testuser',
                password='testpass',
                database='testdb',
                ca_path=ca_file_path
            )


@patch.dict(os.environ, {}, clear=True)
def test_mcp_server_without_ca_path_env_var():
    """Test MCP server works without TIDB_CA_PATH environment variable."""
    test_env = {
        'TIDB_HOST': 'test-host',
        'TIDB_PORT': '3306',
        'TIDB_USERNAME': 'testuser',
        'TIDB_PASSWORD': 'testpass',
        'TIDB_DATABASE': 'testdb'
        # TIDB_CA_PATH is not set
    }

    with patch.dict(os.environ, test_env):
        with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.connect.return_value = mock_client

            # Create TiDBConnector (simulating MCP server initialization)
            connector = TiDBConnector(
                database_url=os.getenv("TIDB_DATABASE_URL", None),
                host=os.getenv("TIDB_HOST", "127.0.0.1"),
                port=int(os.getenv("TIDB_PORT", "4000")),
                username=os.getenv("TIDB_USERNAME", "root"),
                password=os.getenv("TIDB_PASSWORD", ""),
                database=os.getenv("TIDB_DATABASE", "test"),
                ca_path=os.getenv("TIDB_CA_PATH", None),
            )

            # Verify ca_path is None when environment variable is not set
            mock_client_class.connect.assert_called_once_with(
                url=None,
                host='test-host',
                port=3306,
                username='testuser',
                password='testpass',
                database='testdb',
                ca_path=None
            )


def test_tidb_client_connect_with_ca_path():
    """Test TiDBClient.connect() properly handles ca_path parameter."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as ca_file:
        ca_file.write("-----BEGIN CERTIFICATE-----\ntest certificate\n-----END CERTIFICATE-----")
        ca_file_path = ca_file.name

    try:
        # Mock build_tidb_connection_url to verify it receives ca_path
        with patch('pytidb.client.build_tidb_connection_url') as mock_build_url:
            mock_build_url.return_value = "mysql+pymysql://test@host/db?ssl_ca=" + ca_file_path

            # Mock create_engine to avoid actual database connection
            with patch('pytidb.client.create_engine') as mock_create_engine:
                mock_engine = MagicMock()
                # Mock the engine's url.host attribute
                mock_engine.url.host = "gateway01.us-west-2.prod.aws.tidbcloud.com"
                mock_create_engine.return_value = mock_engine

                from pytidb.client import TiDBClient

                # Test TiDBClient.connect with ca_path
                client = TiDBClient.connect(
                    host="gateway01.us-west-2.prod.aws.tidbcloud.com",
                    username="test.root",
                    password="password",
                    database="testdb",
                    ca_path=ca_file_path
                )

                # Verify build_tidb_connection_url was called with ca_path
                mock_build_url.assert_called_once_with(
                    host="gateway01.us-west-2.prod.aws.tidbcloud.com",
                    port=4000,
                    username="test.root",
                    password="password",
                    database="testdb",
                    enable_ssl=None,
                    ca_path=ca_file_path
                )

    finally:
        os.unlink(ca_file_path)


def test_tidb_client_connect_backward_compatibility():
    """Test TiDBClient.connect() maintains backward compatibility without ca_path."""
    with patch('pytidb.client.build_tidb_connection_url') as mock_build_url:
        mock_build_url.return_value = "mysql+pymysql://test@host/db"

        with patch('pytidb.client.create_engine') as mock_create_engine:
            mock_engine = MagicMock()
            # Mock the engine's url.host attribute
            mock_engine.url.host = "localhost"
            mock_create_engine.return_value = mock_engine

            from pytidb.client import TiDBClient

            # Test TiDBClient.connect without ca_path
            client = TiDBClient.connect(
                host="localhost",
                username="root",
                password="password",
                database="testdb"
            )

            # Verify build_tidb_connection_url was called with ca_path=None
            mock_build_url.assert_called_once_with(
                host="localhost",
                port=4000,
                username="root",
                password="password",
                database="testdb",
                enable_ssl=None,
                ca_path=None
            )


def test_tidb_connector_switch_database_preserves_ca_path():
    """Test that TiDBConnector.switch_database() preserves CA path configuration."""
    ca_file_path = "/test/path/ca.pem"

    with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.connect.return_value = mock_client

        # Create TiDBConnector with ca_path
        connector = TiDBConnector(
            host="gateway01.us-west-2.prod.aws.tidbcloud.com",
            port=4000,
            username="test.root",
            password="testpass",
            database="original_db",
            ca_path=ca_file_path
        )

        # Verify initial connection was made with ca_path
        assert mock_client_class.connect.call_count == 1
        initial_call = mock_client_class.connect.call_args
        assert initial_call.kwargs['ca_path'] == ca_file_path

        # Reset mock to track switch_database call
        mock_client_class.connect.reset_mock()

        # Switch to a different database
        connector.switch_database("new_database")

        # Verify switch_database call preserves ca_path
        mock_client_class.connect.assert_called_once_with(
            host="gateway01.us-west-2.prod.aws.tidbcloud.com",
            port=4000,
            username="test.root",
            password="testpass",
            database="new_database",
            ca_path=ca_file_path  # THIS IS THE CRITICAL ASSERTION
        )


def test_tidb_connector_switch_database_with_custom_credentials():
    """Test switch_database with custom credentials still preserves ca_path."""
    ca_file_path = "/test/path/ca.pem"

    with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.connect.return_value = mock_client

        # Create TiDBConnector with ca_path
        connector = TiDBConnector(
            host="gateway01.us-west-2.prod.aws.tidbcloud.com",
            port=4000,
            username="original_user",
            password="original_pass",
            database="original_db",
            ca_path=ca_file_path
        )

        # Reset mock to track switch_database call
        mock_client_class.connect.reset_mock()

        # Switch database with different credentials
        connector.switch_database(
            db_name="new_database",
            username="new_user",
            password="new_pass"
        )

        # Verify switch_database call preserves ca_path with new credentials
        mock_client_class.connect.assert_called_once_with(
            host="gateway01.us-west-2.prod.aws.tidbcloud.com",
            port=4000,
            username="new_user",
            password="new_pass",
            database="new_database",
            ca_path=ca_file_path  # CA path should still be preserved
        )


def test_tidb_connector_switch_database_without_ca_path():
    """Test switch_database works correctly when no ca_path was originally configured."""
    with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.connect.return_value = mock_client

        # Create TiDBConnector without ca_path
        connector = TiDBConnector(
            host="localhost",
            port=4000,
            username="root",
            password="password",
            database="original_db"
            # ca_path not specified - should be None
        )

        # Reset mock to track switch_database call
        mock_client_class.connect.reset_mock()

        # Switch database
        connector.switch_database("new_database")

        # Verify switch_database call has ca_path=None
        mock_client_class.connect.assert_called_once_with(
            host="localhost",
            port=4000,
            username="root",
            password="password",
            database="new_database",
            ca_path=None  # Should be None when not originally configured
        )


def test_tidb_connector_switch_database_with_database_url():
    """Test switch_database preserves ca_path even when original connection used database_url."""
    database_url = "mysql+pymysql://user:pass@host:3306/db?ssl_verify_cert=true"
    ca_file_path = "/test/path/ca.pem"

    with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.connect.return_value = mock_client

        # Create TiDBConnector with database_url and ca_path
        connector = TiDBConnector(
            database_url=database_url,
            ca_path=ca_file_path
        )

        # Verify ca_path is stored correctly
        assert connector.ca_path == ca_file_path

        # Reset mock to track switch_database call
        mock_client_class.connect.reset_mock()

        # Switch database
        connector.switch_database("new_database")

        # Verify switch_database call preserves ca_path
        # Note: when database_url was used, individual connection params are extracted
        mock_client_class.connect.assert_called_once_with(
            host="host",
            port=3306,
            username="user",
            password="pass",
            database="new_database",
            ca_path=ca_file_path  # CA path should be preserved
        )


def test_tidb_client_connect_with_database_url_and_ca_path():
    """P1 REGRESSION TEST: TiDBClient.connect with both database_url and ca_path."""
    database_url = "mysql+pymysql://user:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/testdb?ssl_verify_cert=true&ssl_verify_identity=true"
    ca_file_path = "/test/path/ca.pem"

    # Mock create_engine to capture the final URL passed to SQLAlchemy
    with patch('pytidb.client.create_engine') as mock_create_engine:
        mock_engine = MagicMock()
        mock_engine.url.host = "gateway01.us-west-2.prod.aws.tidbcloud.com"
        mock_create_engine.return_value = mock_engine

        from pytidb.client import TiDBClient

        # THE P1 CRITICAL TEST: Both database_url and ca_path provided
        client = TiDBClient.connect(
            url=database_url,
            ca_path=ca_file_path
        )

        # Verify create_engine was called with URL that includes ssl_ca
        mock_create_engine.assert_called_once()
        actual_url = mock_create_engine.call_args[0][0]  # First positional argument

        # CRITICAL ASSERTIONS for P1 fix
        assert "ssl_ca=%2Ftest%2Fpath%2Fca.pem" in actual_url, f"ssl_ca missing in URL: {actual_url}"
        assert "ssl_verify_cert=true" in actual_url, f"Original SSL params missing: {actual_url}"
        assert "ssl_verify_identity=true" in actual_url, f"Original SSL params missing: {actual_url}"

        print(f"P1 Fix verified - Final URL: {actual_url}")


def test_tidb_client_connect_database_url_with_existing_ssl_ca():
    """Test TiDBClient.connect with database_url that already has ssl_ca - explicit ca_path should override."""
    existing_ca_path = "/existing/ca.pem"
    new_ca_path = "/new/ca.pem"
    database_url = f"mysql+pymysql://user:pass@host:3306/db?ssl_ca=%2F{existing_ca_path.replace('/', '%2F')[3:]}"

    with patch('pytidb.client.create_engine') as mock_create_engine:
        mock_engine = MagicMock()
        mock_engine.url.host = "host"
        mock_create_engine.return_value = mock_engine

        from pytidb.client import TiDBClient

        # P0 FIX: Explicit ca_path should override existing ssl_ca in URL
        client = TiDBClient.connect(
            url=database_url,
            ca_path=new_ca_path  # This should override the URL ssl_ca
        )

        actual_url = mock_create_engine.call_args[0][0]

        # Should use new ca_path, overriding existing ssl_ca from URL
        assert new_ca_path.replace('/', '%2F') in actual_url
        assert existing_ca_path.replace('/', '%2F') not in actual_url


def test_tidb_client_connect_database_url_without_ca_path():
    """Test TiDBClient.connect with database_url but no ca_path (backward compatibility)."""
    database_url = "mysql+pymysql://user:pass@host:3306/db?ssl_verify_cert=true"

    with patch('pytidb.client.create_engine') as mock_create_engine:
        mock_engine = MagicMock()
        mock_engine.url.host = "host"
        mock_create_engine.return_value = mock_engine

        from pytidb.client import TiDBClient

        # Should use URL unchanged when no ca_path provided
        client = TiDBClient.connect(url=database_url)

        actual_url = mock_create_engine.call_args[0][0]

        # URL should be unchanged
        assert actual_url == database_url
        assert "ssl_ca=" not in actual_url


def test_mcp_server_with_database_url_and_ca_path():
    """Test MCP server scenario with both TIDB_DATABASE_URL and TIDB_CA_PATH."""
    database_url = "mysql+pymysql://user:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/testdb"
    ca_file_path = "/windows/ca-cert.pem"

    with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.connect.return_value = mock_client

        # Simulate MCP server configuration with both URL and CA path
        connector = TiDBConnector(
            database_url=database_url,
            ca_path=ca_file_path
        )

        # Verify TiDBClient.connect was called with both parameters
        mock_client_class.connect.assert_called_once_with(
            url=database_url,
            host=None,
            port=None,
            username=None,
            password=None,
            database=None,
            ca_path=ca_file_path  # P1 fix: ca_path should be passed along
        )


def test_tidb_connector_ca_from_database_url_only():
    """P0 REGRESSION TEST: TiDBConnector preserves CA from database_url during switch_database."""
    # URL with ssl_ca embedded (no explicit ca_path parameter)
    ca_file_path = "/embedded/ca-cert.pem"
    database_url = f"mysql+pymysql://user:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/testdb?ssl_ca=%2Fembedded%2Fca-cert.pem&ssl_verify_cert=true"

    with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.connect.return_value = mock_client

        # Create TiDBConnector with database_url containing ssl_ca (no explicit ca_path)
        connector = TiDBConnector(
            database_url=database_url
            # ca_path=None (not provided)
        )

        # Verify CA path was extracted and stored from URL
        assert connector.ca_path == ca_file_path

        # Reset mock to track switch_database call
        mock_client_class.connect.reset_mock()

        # Switch database - this should preserve CA from original URL
        connector.switch_database("new_database")

        # CRITICAL P0 ASSERTION: CA path from URL should be preserved
        mock_client_class.connect.assert_called_once_with(
            host="gateway01.us-west-2.prod.aws.tidbcloud.com",
            port=4000,
            username="user",
            password="pass",
            database="new_database",
            ca_path=ca_file_path  # P0 fix: CA from URL should be preserved
        )


def test_tidb_connector_explicit_ca_path_overrides_url_ca():
    """Test that explicit ca_path takes precedence over ssl_ca in database_url."""
    url_ca_path = "/url/ca-cert.pem"
    explicit_ca_path = "/explicit/ca-cert.pem"
    database_url = f"mysql+pymysql://user:pass@host:3306/db?ssl_ca=%2Furl%2Fca-cert.pem"

    with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.connect.return_value = mock_client

        # Create TiDBConnector with both URL ssl_ca and explicit ca_path
        connector = TiDBConnector(
            database_url=database_url,
            ca_path=explicit_ca_path  # Should take precedence
        )

        # Verify explicit ca_path takes precedence
        assert connector.ca_path == explicit_ca_path

        # Reset mock and test switch_database
        mock_client_class.connect.reset_mock()
        connector.switch_database("new_database")

        # Should use explicit ca_path, not URL ca_path
        mock_client_class.connect.assert_called_once_with(
            host="host",
            port=3306,
            username="user",
            password="pass",
            database="new_database",
            ca_path=explicit_ca_path  # Explicit path should win
        )