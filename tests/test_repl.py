import subprocess
import sys
import os


def test_repl_session():
    print("Testing REPL interactive session...")

    main_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

    process = subprocess.Popen(
        [sys.executable, "-m", "modules.cli.main"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=main_path,
    )

    commands = [
        "var x = 42;",
        "out x;",
        'func hello() { out "hi"; }',
        "hello();",
        "exit",
    ]

    full_input = "\n".join(commands) + "\n"
    stdout, stderr = process.communicate(input=full_input, timeout=10)

    expected_outputs = ["42", "hi"]
    for expected in expected_outputs:
        if expected not in stdout:
            print(f"FAILED: Expected '{expected}' in output, but it was missing.")
            print(f"STDOUT: {stdout}")
            return False

    print("REPL session test PASSED")
    return True


if __name__ == "__main__":
    if test_repl_session():
        sys.exit(0)
    else:
        sys.exit(1)
