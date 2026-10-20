#!/usr/bin/env python3
"""Build and run the firmware core's native unit tests on the PC.

Uses the C++ compiler shipped in the `ziglang` pip package, so no system
compiler is needed:  python -m pip install ziglang

Author: Jessica
"""
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
CORE = HERE.parent / "lib" / "rig_core" / "src"


def main() -> int:
    sources = [HERE / "test_core.cpp"] + sorted(CORE.glob("*.cpp"))
    with tempfile.TemporaryDirectory() as tmp:
        exe = pathlib.Path(tmp) / ("test_core.exe" if sys.platform == "win32" else "test_core")
        cmd = [sys.executable, "-m", "ziglang", "c++", "-std=c++17", "-O1", "-g",
               "-Wall", "-Wextra", "-Werror", "-fsanitize=undefined", "-fno-sanitize-recover=all",
               f"-I{CORE}", "-o", str(exe)] + [str(s) for s in sources]
        build = subprocess.run(cmd, capture_output=True, text=True)
        if build.returncode:
            print(build.stdout + build.stderr)
            return build.returncode
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        print(run.stdout + run.stderr, end="")
        return run.returncode


if __name__ == "__main__":
    sys.exit(main())
