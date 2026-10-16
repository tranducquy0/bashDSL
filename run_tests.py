import subprocess
import os
import sys


# The Test Runner
class TestRunner:
    def __init__(self, tests_dir="tests"):
        self.tests_dir = tests_dir
        self.python_path = sys.executable

    def run_all(self):
        print("Running bashDSL Test Suite")
        print("-" * 60)

        passed, failed = 0, 0
        for filename in sorted(os.listdir(self.tests_dir)):
            if filename.endswith(".shtm"):
                if self.run_test(filename):
                    passed += 1
                else:
                    failed += 1

        print("-" * 60)
        print(f"Test Suite Results: Passed: {passed}, Failed: {failed}")

        # Run REPL Integration Test
        print("\nRunning REPL Integration Check...")
        repl_result = subprocess.run(
            [self.python_path, "tests/test_repl.py"], capture_output=True, text=True
        )
        if repl_result.returncode == 0:
            print("PASS: REPL Session Test")
        else:
            print(
                f"FAIL: REPL Session Test\n{repl_result.stdout}\n{repl_result.stderr}"
            )
            failed += 1

        if failed > 0:
            sys.exit(1)

    def run_test(self, filename):
        filepath = os.path.join(self.tests_dir, filename)
        should_fail = filename.startswith("fail_")

        cmd = [self.python_path, "-m", "modules.cli.main", filepath]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if should_fail:
            if result.returncode != 0:
                print(f"PASS: {filename} (Failed as expected)")
                return True
            else:
                print(f"FAIL: {filename} (Expected failure, but it passed)")
                return False
        else:
            if result.returncode == 0:
                print(f"PASS: {filename}")
                return True
            else:
                print(f"FAIL: {filename} (Unexpected error: {result.stdout.strip()})")
                return False


if __name__ == "__main__":
    runner = TestRunner()
    runner.run_all()
