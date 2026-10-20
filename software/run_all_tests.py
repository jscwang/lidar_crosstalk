#!/usr/bin/env python3
"""Runs every automated check: firmware core unit tests (native C++), the
ESP32-S3 firmware build, and the host test suite.

    python run_all_tests.py            all three
    python run_all_tests.py --no-build skip the firmware build (no toolchain)

Needs: pip install platformio ziglang pytest pyserial numpy scipy pandas matplotlib

Author: Jessica
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def step(name: str, cmd: list[str], cwd: Path) -> bool:
    print(f"\n=== {name} ===", flush=True)
    ok = subprocess.run(cmd, cwd=cwd).returncode == 0
    print(f"--- {name}: {'PASS' if ok else 'FAIL'}", flush=True)
    return ok


def main() -> int:
    results = [step("firmware core unit tests (native)", [sys.executable, "test_native/run_native_tests.py"],
                    ROOT / "firmware")]
    if "--no-build" not in sys.argv:
        results.append(step("firmware build, both ESP32-S3 boards", [sys.executable, "-m", "platformio", "run", "-e", "esp32s3_n16r8", "-e", "esp32s3_wroom2"],
                            ROOT / "firmware"))
    results.append(step("host tests", [sys.executable, "-m", "pytest", "-q"], ROOT / "host"))
    print("\nALL PASSED" if all(results) else "\nSOME CHECKS FAILED")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
