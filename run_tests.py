"""Automated Test Runner for Multi-Agent Financial Research System.

Executes all unit, integration, and end-to-end tests across the test suite.
"""

import os
import sys
import unittest
from pathlib import Path

# Ensure offline operation so cached models load immediately
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def run_all_tests() -> bool:
    print("=" * 70)
    print("Multi-Agent Financial Research System — Automated Test Suite")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir="tests", pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print(f"Total Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
