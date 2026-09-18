import unittest
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.test_fixes import TestLocalPilotFixes

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLocalPilotFixes)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        for failure in result.failures:
            print(f"\n--- FAILURE in {failure[0]} ---")
            print(failure[1])
        for error in result.errors:
            print(f"\n--- ERROR in {error[0]} ---")
            print(error[1])
        sys.exit(1)
    else:
        print("\nALL 5 TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
