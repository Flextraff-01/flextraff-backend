#!/usr/bin/env python3
"""
Comprehensive test runner for FlexTraff API
Runs all test suites with proper organization and reporting
"""

import json
import os
import re
import subprocess
import sys
import time
from typing import Dict, List


class TestRunner:
    """Organizes and runs different test suites"""

    def __init__(self):
        self.python_path = self._get_python_path()
        self.test_results = {}
        self.marker_categories = {
            "unit": "Unit tests with mocked dependencies",
            "integration": "Integration tests with real database",
            "performance": "Performance and load tests",
            "slow": "Slow-running tests",
            "api": "API endpoint tests",
            "algorithm": "Algorithm-specific tests",
            "database": "Database-related tests",
        }

    def _get_python_path(self) -> str:
        """Get the correct Python executable path"""
        venv_python = "/Users/ajaypsk2722/flextraff-backend/.venv/bin/python"
        if os.path.exists(venv_python):
            return venv_python
        return sys.executable

    def _analyze_test_markers(
        self, test_output: str, command: List[str]
    ) -> Dict[str, int]:
        """Analyze pytest output to categorize tests by markers"""
        marker_counts = {marker: 0 for marker in self.marker_categories.keys()}

        # Count total passed tests
        passed_matches = re.findall(r"(\d+) passed", test_output)
        total_passed = int(passed_matches[-1]) if passed_matches else 0

        # Check command to determine test type
        command_str = " ".join(command)

        # Look for test names and try to infer categories
        if "test_traffic_algorithm.py" in command_str:
            marker_counts["algorithm"] += total_passed
            marker_counts[
                "unit"
            ] += total_passed  # Algorithm tests are unit tests with mocks

        if "test_api_endpoints.py" in command_str:
            marker_counts["api"] += total_passed
            # Check if it's unit tests (with "not integration" marker) or integration tests
            if "not integration" in command_str or "-m not integration" in command_str:
                marker_counts["unit"] += total_passed
            else:
                marker_counts["integration"] += total_passed

        if "test_performance.py" in command_str:
            marker_counts["performance"] += total_passed
            marker_counts["slow"] += total_passed
            marker_counts["api"] += total_passed  # Performance tests are also API tests

        if "test_api_integration.py" in command_str:
            marker_counts["integration"] += total_passed
            marker_counts["api"] += total_passed

        if (
            "test_database_integration.py" in command_str
            or "database" in command_str.lower()
        ):
            marker_counts["database"] += total_passed
            marker_counts["integration"] += total_passed

        return marker_counts

    def _get_detailed_test_info(self, command: List[str]) -> Dict:
        """Get detailed test information with JSON output"""
        # Add JSON reporting to get detailed test info
        json_command = command + [
            "--json-report",
            "--json-report-file=/tmp/pytest_report.json",
        ]

        try:
            result = subprocess.run(
                json_command,
                capture_output=True,
                text=True,
                cwd="/Users/ajaypsk2722/flextraff-backend",
            )

            # Try to read JSON report
            try:
                with open("/tmp/pytest_report.json", "r") as f:
                    json_data = json.load(f)
                    return json_data
            except (FileNotFoundError, json.JSONDecodeError):
                pass
        except Exception:
            pass

        return {}

    def run_command(self, command: List[str], test_name: str) -> Dict:
        """Run a command and capture results"""
        print(f"\n{'='*60}")
        print(f"🧪 Running {test_name}")
        print(f"{'='*60}")

        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd="/Users/ajaypsk2722/flextraff-backend",
            )

            end_time = time.time()
            duration = end_time - start_time

            success = result.returncode == 0

            print(f"Command: {' '.join(command)}")
            print(f"Duration: {duration:.2f} seconds")
            print(f"Exit Code: {result.returncode}")

            if result.stdout:
                print("\nSTDOUT:")
                print(result.stdout)

            if result.stderr:
                print("\nSTDERR:")
                print(result.stderr)

            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"\nResult: {status}")

            # Analyze markers from output
            marker_counts = self._analyze_test_markers(result.stdout, command)

            # Extract test count information
            test_count = 0
            passed_count = 0
            failed_count = 0

            if success and result.stdout:
                # Look for pytest summary line like "31 passed in 0.17s"
                summary_match = re.search(r"(\d+) passed", result.stdout)
                if summary_match:
                    passed_count = int(summary_match.group(1))
                    test_count = passed_count

                failed_match = re.search(r"(\d+) failed", result.stdout)
                if failed_match:
                    failed_count = int(failed_match.group(1))
                    test_count += failed_count

            return {
                "name": test_name,
                "success": success,
                "duration": duration,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "test_count": test_count,
                "passed_count": passed_count,
                "failed_count": failed_count,
                "marker_counts": marker_counts,
            }

        except Exception as e:
            print(f"❌ Error running {test_name}: {str(e)}")
            return {
                "name": test_name,
                "success": False,
                "duration": 0,
                "error": str(e),
                "test_count": 0,
                "passed_count": 0,
                "failed_count": 0,
                "marker_counts": {},
            }

    def run_unit_tests(self):
        """Run unit tests with mocked dependencies"""
        command = [
            self.python_path,
            "-m",
            "pytest",
            "tests/test_api_endpoints.py",
            "-m",
            "not integration",
            "--tb=short",
            "-v",
        ]
        return self.run_command(command, "Unit Tests (API Endpoints)")

    def run_algorithm_tests(self):
        """Run algorithm-specific tests"""
        command = [
            self.python_path,
            "-m",
            "pytest",
            "tests/test_traffic_algorithm.py",
            "-v",
        ]
        return self.run_command(command, "Algorithm Tests")

    def run_integration_tests(self):
        """Run integration tests with real API"""
        print("\n⚠️  Note: Make sure the API server is running on http://127.0.0.1:8001")

        command = [
            self.python_path,
            "-m",
            "pytest",
            "tests/test_api_integration.py",
            "-v",
            "--tb=short",
        ]
        return self.run_command(command, "Integration Tests (Live API)")

    def run_performance_tests(self):
        """Run performance and load tests"""
        print("\n⚠️  Note: Make sure the API server is running on http://127.0.0.1:8001")

        command = [
            self.python_path,
            "-m",
            "pytest",
            "tests/test_performance.py",
            "-v",
            "--tb=short",
            "-s",  # Show print statements for performance metrics
        ]
        return self.run_command(command, "Performance Tests")

    def run_database_integration_test(self):
        """Run the comprehensive database integration test"""
        command = [self.python_path, "test_database_integration.py"]
        return self.run_command(command, "Database Integration Test")

    def run_database_tests(self):
        """Run database-specific tests using pytest markers"""
        command = [
            self.python_path,
            "-m",
            "pytest",
            "-m",
            "database",
            "-v",
            "--tb=short",
        ]
        return self.run_command(command, "Database Tests")

    def run_slow_tests(self):
        """Run slow-running tests using pytest markers"""
        command = [
            self.python_path,
            "-m",
            "pytest",
            "-m",
            "slow",
            "-v",
            "--tb=short",
            "-s",
        ]
        return self.run_command(command, "Slow Tests")

    def run_all_integration_tests(self):
        """Run all integration tests using pytest markers"""
        command = [
            self.python_path,
            "-m",
            "pytest",
            "-m",
            "integration",
            "-v",
            "--tb=short",
        ]
        return self.run_command(command, "All Integration Tests")

    def run_api_basic_test(self):
        """Run basic API functionality test"""
        command = [self.python_path, "simple_api_test.py"]
        return self.run_command(command, "Basic API Test")

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 FlexTraff Comprehensive Test Suite")
        print("=" * 60)

        # Test suites in order of complexity
        test_suites = [
            ("Algorithm Tests", self.run_algorithm_tests),
            ("Unit Tests", self.run_unit_tests),
            ("Database Integration", self.run_database_integration_test),
            ("Basic API Test", self.run_api_basic_test),
            ("Integration Tests", self.run_integration_tests),
            ("Performance Tests", self.run_performance_tests),
        ]

        results = []

        for suite_name, suite_func in test_suites:
            try:
                result = suite_func()
                results.append(result)
                self.test_results[suite_name] = result

                # Stop on critical failures
                if not result["success"] and suite_name in [
                    "Algorithm Tests",
                    "Database Integration",
                ]:
                    print(f"\n💥 Critical test suite failed: {suite_name}")
                    print("Stopping test execution due to critical failure.")
                    break

            except KeyboardInterrupt:
                print("\n🛑 Test execution interrupted by user")
                break
            except Exception as e:
                print(f"\n💥 Error in test suite {suite_name}: {str(e)}")
                results.append({"name": suite_name, "success": False, "error": str(e)})

        # Print summary
        self.print_summary(results)

        return results

    def run_comprehensive_tests(self):
        """Run comprehensive test suite including all marker categories"""
        print("🚀 FlexTraff COMPREHENSIVE Test Suite - All Categories")
        print("=" * 70)

        # Comprehensive test suites covering all markers
        test_suites = [
            # Core functionality
            ("Algorithm Tests", self.run_algorithm_tests),
            ("Unit Tests (API Endpoints)", self.run_unit_tests),
            # Integration and database
            ("Database Integration Test", self.run_database_integration_test),
            ("Database Tests (Markers)", self.run_database_tests),
            ("Integration Tests (API)", self.run_integration_tests),
            ("All Integration Tests (Markers)", self.run_all_integration_tests),
            # Performance and slow tests
            ("Performance Tests", self.run_performance_tests),
            ("Slow Tests (Markers)", self.run_slow_tests),
            # Basic functionality
            ("Basic API Test", self.run_api_basic_test),
        ]

        results = []

        for suite_name, suite_func in test_suites:
            try:
                print(f"\n🔄 Starting: {suite_name}")
                result = suite_func()
                results.append(result)
                self.test_results[suite_name] = result

                # Log result immediately
                status = "✅ PASSED" if result["success"] else "❌ FAILED"
                print(f"📊 {suite_name}: {status}")

                # Continue even on failures for comprehensive testing
                if not result["success"]:
                    print(f"⚠️ {suite_name} failed but continuing with other tests...")

            except KeyboardInterrupt:
                print("\n🛑 Test execution interrupted by user")
                break
            except Exception as e:
                print(f"\n💥 Error in test suite {suite_name}: {str(e)}")
                results.append(
                    {
                        "name": suite_name,
                        "success": False,
                        "error": str(e),
                        "test_count": 0,
                        "passed_count": 0,
                        "failed_count": 0,
                        "marker_counts": {},
                    }
                )

        # Print comprehensive summary
        self.print_summary(results)

        return results

    def print_summary(self, results: List[Dict]):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("📊 TEST EXECUTION SUMMARY")
        print("=" * 80)

        total_tests = len(results)
        passed_tests = len([r for r in results if r["success"]])
        failed_tests = total_tests - passed_tests

        # Calculate total individual test counts
        total_test_count = sum(r.get("test_count", 0) for r in results)
        total_passed_count = sum(r.get("passed_count", 0) for r in results)
        total_failed_count = sum(r.get("failed_count", 0) for r in results)

        print(f"Total Test Suites: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(
            f"Success Rate: {(passed_tests/total_tests)*100:.1f}%"
            if total_tests > 0
            else "N/A"
        )

        print(f"\nIndividual Tests: {total_test_count}")
        print(f"Passed: {total_passed_count} ✅")
        print(f"Failed: {total_failed_count} ❌")

        total_duration = sum(r.get("duration", 0) for r in results)
        print(f"Total Duration: {total_duration:.2f} seconds")

        print("\nDetailed Results:")
        print("-" * 60)

        for result in results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            duration = result.get("duration", 0)
            name = result["name"]
            test_count = result.get("test_count", 0)

            print(f"{status:<8} {name:<30} ({duration:.2f}s)")
            if test_count > 0:
                print(
                    f"         {test_count} tests - {result.get('passed_count', 0)} passed, {result.get('failed_count', 0)} failed"
                )

            if not result["success"] and "error" in result:
                print(f"         Error: {result['error']}")

        # Aggregate marker metrics
        print("\n" + "=" * 80)
        print("📊 TEST METRICS BY CATEGORY")
        print("=" * 80)

        aggregated_markers = {marker: 0 for marker in self.marker_categories.keys()}

        for result in results:
            marker_counts = result.get("marker_counts", {})
            for marker, count in marker_counts.items():
                aggregated_markers[marker] += count

        # Display marker metrics
        for marker, count in aggregated_markers.items():
            if count > 0:
                description = self.marker_categories[marker]
                print(f"{marker:>12}: {count:>3} tests - {description}")

        # Show empty categories
        empty_categories = [
            marker for marker, count in aggregated_markers.items() if count == 0
        ]
        if empty_categories:
            print(f"\nEmpty Categories:")
            for marker in empty_categories:
                description = self.marker_categories[marker]
                print(f"{marker:>12}: {0:>3} tests - {description}")

        print("\n" + "=" * 80)

        if failed_tests == 0:
            print("🎉 ALL TESTS PASSED! FlexTraff API is working perfectly!")
            print("🚀 System is ready for production deployment!")
        else:
            print(f"⚠️  {failed_tests} test suite(s) failed. Review the errors above.")
            print("🔧 Fix the issues before proceeding to production.")

        print("=" * 80)

    def run_quick_tests(self):
        """Run only quick tests (unit + algorithm)"""
        print("⚡ Running Quick Test Suite")

        results = []

        # Run critical tests only
        quick_suites = [
            ("Algorithm Tests", self.run_algorithm_tests),
            ("Unit Tests", self.run_unit_tests),
        ]

        for suite_name, suite_func in quick_suites:
            result = suite_func()
            results.append(result)

        self.print_summary(results)
        return results

    def run_ci_tests(self):
        """Run tests suitable for CI/CD pipeline"""
        print("🤖 Running CI/CD Test Suite")

        results = []

        # CI tests (no live API required)
        ci_suites = [
            ("Algorithm Tests", self.run_algorithm_tests),
            ("Unit Tests", self.run_unit_tests),
            ("Database Integration", self.run_database_integration_test),
        ]

        for suite_name, suite_func in ci_suites:
            result = suite_func()
            results.append(result)

            if not result["success"]:
                print(f"💥 CI test failed: {suite_name}")
                break

        self.print_summary(results)
        return results


def main():
    """Main test runner entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="FlexTraff API Test Runner")
    parser.add_argument(
        "suite",
        nargs="?",
        default="all",
        choices=[
            "all",
            "comprehensive",
            "unit",
            "integration",
            "performance",
            "algorithm",
            "database",
            "slow",
            "quick",
            "ci",
        ],
        help="Test suite to run",
    )

    args = parser.parse_args()

    runner = TestRunner()

    if args.suite == "all":
        runner.run_all_tests()
    elif args.suite == "comprehensive":
        runner.run_comprehensive_tests()
    elif args.suite == "unit":
        runner.run_unit_tests()
    elif args.suite == "integration":
        runner.run_integration_tests()
    elif args.suite == "performance":
        runner.run_performance_tests()
    elif args.suite == "algorithm":
        runner.run_algorithm_tests()
    elif args.suite == "database":
        runner.run_database_tests()
    elif args.suite == "slow":
        runner.run_slow_tests()
    elif args.suite == "quick":
        runner.run_quick_tests()
    elif args.suite == "ci":
        runner.run_ci_tests()


if __name__ == "__main__":
    main()
