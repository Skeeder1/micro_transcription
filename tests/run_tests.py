#!/usr/bin/env python
"""Test runner for micro_transcription.

Usage:
    python tests/run_tests.py           # Run all tests
    python tests/run_tests.py -v        # Verbose mode
    python tests/run_tests.py -k voice  # Run only voice-related tests
    python tests/run_tests.py --quick   # Run quick tests only (no model loading)
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_tests():
    """Run all tests using pytest."""
    import pytest

    # Default arguments
    args = [
        str(PROJECT_ROOT / "tests"),
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
    ]

    # Add any command line arguments
    args.extend(sys.argv[1:])

    # Run pytest
    return pytest.main(args)


def run_quick_tests():
    """Run quick tests that don't require model loading."""
    import pytest

    args = [
        str(PROJECT_ROOT / "tests"),
        "-v",
        "--tb=short",
        "-k", "not (voice_detector or silero)",  # Skip slow tests
        "-x",
    ]

    return pytest.main(args)


def run_integration_tests():
    """Run integration tests only."""
    import pytest

    args = [
        str(PROJECT_ROOT / "tests" / "test_integration.py"),
        "-v",
        "--tb=short",
    ]

    return pytest.main(args)


def print_test_summary():
    """Print a summary of available test files."""
    tests_dir = PROJECT_ROOT / "tests"
    test_files = list(tests_dir.glob("test_*.py"))

    print("Available test files:")
    print("-" * 40)
    for tf in sorted(test_files):
        print(f"  - {tf.name}")
    print()
    print("Run options:")
    print("  python tests/run_tests.py           # All tests")
    print("  python tests/run_tests.py --quick   # Quick tests only")
    print("  python tests/run_tests.py -k voice  # Filter by keyword")


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print_test_summary()
        sys.exit(0)

    if "--quick" in sys.argv:
        sys.argv.remove("--quick")
        sys.exit(run_quick_tests())

    if "--integration" in sys.argv:
        sys.argv.remove("--integration")
        sys.exit(run_integration_tests())

    sys.exit(run_tests())
