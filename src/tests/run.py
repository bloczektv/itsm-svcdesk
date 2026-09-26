# ai-generated: 85% - Claude Code drafted, reviewed by the author

"""Entry point for the compose `tests` profile (Stretch S3): runs the pytest suite in this package
and prints the summary line the checker parses. Retries /health first, since a cold container can
otherwise race the healthcheck (docker-compose.yml comment)."""

import sys
import time
import urllib.error
import urllib.request

import pytest

from ._client import BASE_URL


def _wait_for_health(timeout_seconds: float = 30.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/health", timeout=3) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1)


class _Counter:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def pytest_runtest_logreport(self, report):
        if report.when != "call":
            return
        if report.passed:
            self.passed += 1
        elif report.failed:
            self.failed += 1


def main() -> int:
    _wait_for_health()
    counter = _Counter()
    pytest.main(["-q", "--tb=short", "tests"], plugins=[counter])
    print(f"ITSMLAB-TESTS: passed={counter.passed} failed={counter.failed}")
    return 0 if counter.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
