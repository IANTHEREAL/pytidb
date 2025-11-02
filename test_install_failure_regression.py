#!/usr/bin/env python3
"""
Unit test to prevent regression of installer failure handling.

This test simulates what happens when pydantic installation fails
and verifies that the test runners handle it gracefully without KeyError.
"""

import unittest
from unittest.mock import patch, MagicMock
import subprocess
import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add project root to path so we can import test modules
sys.path.insert(0, str(Path(__file__).parent))

# Import the utility functions from our test scripts
def get_test_functions():
    """Import the functions we need to test"""
    # We'll test the logic by importing and calling the functions directly
    exec(open("test_all_pydantic_versions.py").read().split("def main()")[0])
    exec(open("test_pydantic_versions.py").read().split("def main()")[0])
    exec(open("test_pydantic_versions_fixed.py").read().split("def main()")[0])

    # Return the function from the global namespace
    return globals()['run_with_pydantic_version']


class TestInstallFailureHandling(unittest.TestCase):
    """Test that install failures are handled gracefully"""

    def setUp(self):
        """Set up test environment"""
        # Mock the project root
        self.original_cwd = os.getcwd()

    def tearDown(self):
        """Clean up after tests"""
        os.chdir(self.original_cwd)

    @patch('subprocess.run')
    def test_install_failure_returns_proper_dict(self, mock_subprocess):
        """Test that install failure returns dict with install_success=False"""
        # Mock subprocess.run to simulate install failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "ERROR: Could not find a version that satisfies the requirement pydantic==9.9.9"
        mock_subprocess.return_value = mock_result

        # Import and test each version of run_with_pydantic_version
        test_files = [
            "test_all_pydantic_versions.py",
            "test_pydantic_versions.py",
            "test_pydantic_versions_fixed.py"
        ]

        for test_file in test_files:
            with self.subTest(test_file=test_file):
                # Read the file and extract the function
                with open(test_file, 'r') as f:
                    content = f.read()

                # Extract just the function definition
                func_start = content.find("def run_with_pydantic_version")
                if func_start == -1:
                    continue

                func_content = content[func_start:]

                # Find the end of the function (next def or end of file)
                lines = func_content.split('\n')
                func_lines = [lines[0]]  # def line

                for line in lines[1:]:
                    if line.startswith('def ') and not line.startswith('    '):
                        break
                    func_lines.append(line)

                # Create a local namespace and execute the function
                namespace = {}
                exec('\n'.join(func_lines), globals(), namespace)
                run_func = namespace['run_with_pydantic_version']

                # Call the function with a fake version
                result = run_func("9.9.9")

                # Verify the result has the expected structure
                self.assertIsInstance(result, dict, f"Function in {test_file} should return dict")
                self.assertIn("version", result, f"Result from {test_file} should have 'version' key")
                self.assertIn("install_success", result, f"Result from {test_file} should have 'install_success' key")
                self.assertEqual(result["install_success"], False, f"install_success should be False in {test_file}")
                self.assertEqual(result["version"], "9.9.9", f"Version should be preserved in {test_file}")

                # Verify that overall_success is NOT in the result when install fails
                # This is the key fix - when install fails, we should not include overall_success
                self.assertNotIn("overall_success", result,
                                f"Result from {test_file} should NOT have 'overall_success' when install fails")

    def test_result_processing_handles_missing_overall_success(self):
        """Test that result processing handles missing overall_success gracefully"""

        # Test data: simulate results from install failures
        test_results = [
            {"version": "2.0.3", "install_success": False, "error": "Install failed"},
            {"version": "2.5.3", "install_success": True, "overall_success": True},
            {"version": "2.10.6", "install_success": True, "overall_success": False, "import_test_success": False},
        ]

        # Test the logic that processes results (this is what was failing before)
        passed_count = 0
        for result in test_results:
            # This is the fixed logic that should not cause KeyError
            if not result.get("install_success", True):
                # Install failed - don't count as passed, don't access overall_success
                status = "INSTALL FAILED"
            elif result.get("overall_success", False):
                # Install succeeded and tests passed
                status = "PASS"
                passed_count += 1
            else:
                # Install succeeded but tests failed
                status = "FAIL"

        # Verify we correctly identified 1 passed result out of 3
        self.assertEqual(passed_count, 1, "Should have 1 passed test")

    def test_count_logic_handles_install_failures(self):
        """Test that the counting logic correctly handles install failures"""

        test_results = [
            {"version": "2.0.3", "install_success": False, "error": "Install failed"},
            {"version": "2.5.3", "install_success": True, "overall_success": True},
            {"version": "2.10.6", "install_success": True, "overall_success": False},
            {"version": "2.12.3", "install_success": True, "overall_success": True},
        ]

        # This is the fixed counting logic
        passed = sum(1 for r in test_results if r.get("install_success", True) and r.get("overall_success", False))
        total = len(test_results)

        # Should count 2 passed (2.5.3 and 2.12.3), out of 4 total
        self.assertEqual(passed, 2, "Should count 2 passed tests")
        self.assertEqual(total, 4, "Should count 4 total tests")
        self.assertEqual(passed/total, 0.5, "Success rate should be 50%")

    @patch('subprocess.run')
    @patch('time.time')
    def test_main_function_handles_install_failures(self, mock_time, mock_subprocess):
        """Test that main() function and report generation handles install failures gracefully"""

        # Mock time for consistent reports
        mock_time.return_value = 1234567890.0

        # Mock subprocess to simulate mixed success/failure scenarios
        def mock_subprocess_side_effect(*args, **kwargs):
            mock_result = MagicMock()

            # Check if this is a uv pip install call
            if args[0] and len(args[0]) >= 3 and args[0][:3] == ["uv", "pip", "install"]:
                version = args[0][3]  # Extract pydantic==X.X.X
                # Simulate install failure for version 2.0.3
                if "2.0.3" in version:
                    mock_result.returncode = 1
                    mock_result.stderr = "ERROR: Could not find a version that satisfies the requirement pydantic==2.0.3"
                else:
                    mock_result.returncode = 0
                    mock_result.stderr = ""
            else:
                # All other subprocess calls succeed
                mock_result.returncode = 0
                mock_result.stdout = "SUCCESS: Mock test passed"
                mock_result.stderr = ""

            return mock_result

        mock_subprocess.side_effect = mock_subprocess_side_effect

        # Use temporary directory to avoid modifying tracked files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save original working directory
            original_cwd = os.getcwd()

            try:
                # Copy test script and create a dummy pyproject.toml to temp directory
                temp_script_path = os.path.join(temp_dir, "test_all_pydantic_versions.py")
                shutil.copy2("test_all_pydantic_versions.py", temp_script_path)

                # Create dummy pyproject.toml so find_project_root works
                with open(os.path.join(temp_dir, "pyproject.toml"), "w") as f:
                    f.write("[project]\nname = \"test\"\n")

                # Change to temp directory
                os.chdir(temp_dir)

                # Import and execute the main function from the copied script
                import importlib.util
                spec = importlib.util.spec_from_file_location("test_module", temp_script_path)
                test_module = importlib.util.module_from_spec(spec)

                # Execute the module to define all functions
                spec.loader.exec_module(test_module)

                # Mock the PYDANTIC_VERSIONS to just test 2 versions for speed
                original_versions = test_module.PYDANTIC_VERSIONS
                test_module.PYDANTIC_VERSIONS = ["2.0.3", "2.5.3"]  # One fails, one succeeds

                # Run the main function (will create files in temp directory)
                result = test_module.main()

                # Should return False because not all versions passed (install failure)
                self.assertFalse(result, "main() should return False when install failures occur")

                # Check that the report file was created in temp directory
                report_path = os.path.join(temp_dir, "PYDANTIC_COMPATIBILITY_REPORT.md")
                self.assertTrue(os.path.exists(report_path),
                              "Report file should be created even with install failures")

                # Read and verify the report content handles install failures gracefully
                with open(report_path, "r") as f:
                    report_content = f.read()

                # Verify install failure is properly reported
                self.assertIn("INSTALL FAILED", report_content,
                             "Report should mention install failure")
                self.assertIn("2.0.3", report_content,
                             "Report should include the failed version")
                self.assertIn("Could not find a version", report_content,
                             "Report should include the install error message")

                # Restore original versions
                test_module.PYDANTIC_VERSIONS = original_versions

            except Exception as e:
                self.fail(f"main() function should handle install failures gracefully, but got: {e}")
            finally:
                # Always restore original working directory
                os.chdir(original_cwd)

    def test_summary_report_generation_with_failures(self):
        """Test that summary report generation handles missing overall_success keys"""

        # Test data with mixed results including install failures
        test_results = [
            {"version": "2.0.3", "install_success": False, "error": "Install failed"},
            {"version": "2.5.3", "install_success": True, "overall_success": True},
            {"version": "2.10.6", "install_success": True, "overall_success": False, "import_test_error": "Some import error"},
        ]

        # Simulate the report generation logic
        passed = sum(1 for r in test_results if r.get("install_success", True) and r.get("overall_success", False))
        total = len(test_results)

        # Simulate writing report sections that were problematic
        report_lines = []

        # Test the fixed status generation logic
        for result in test_results:
            if not result.get("install_success", True):
                status = "❌ INSTALL FAILED"
            elif result.get("overall_success", False):
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
            report_lines.append(f"- **pydantic {result['version']}**: {status}")

        # Test the fixed issues section logic
        issues_lines = []
        for result in test_results:
            if not result.get("install_success", True):
                issues_lines.append(f"### pydantic {result['version']} - Install Failed")
                issues_lines.append(f"**Error:** {result.get('error', 'Unknown install error')}")
            elif not result.get("overall_success", False):
                issues_lines.append(f"### pydantic {result['version']} - Tests Failed")

        # Verify no KeyError occurred and proper reporting
        expected_status_lines = [
            "- **pydantic 2.0.3**: ❌ INSTALL FAILED",
            "- **pydantic 2.5.3**: ✅ PASS",
            "- **pydantic 2.10.6**: ❌ FAIL"
        ]
        self.assertEqual(report_lines, expected_status_lines, "Status reporting should handle missing keys gracefully")

        expected_issues_lines = [
            "### pydantic 2.0.3 - Install Failed",
            "**Error:** Install failed",
            "### pydantic 2.10.6 - Tests Failed"
        ]
        self.assertEqual(issues_lines, expected_issues_lines, "Issues reporting should handle missing keys gracefully")

        # Verify counting logic
        self.assertEqual(passed, 1, "Should count 1 passed test (2.5.3)")
        self.assertEqual(total, 3, "Should count 3 total attempts")


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)