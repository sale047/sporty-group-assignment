from typing import Any


class SoftAssertions:
    """Collects failed checks and raises once, so a single E2E run reports every broken expectation."""

    def __init__(self) -> None:
        self._failures: list[str] = []

    def equal(self, actual: Any, expected: Any, description: str) -> None:
        if actual != expected:
            self._failures.append(f"{description}: expected {expected}, got {actual}")

    def true(self, condition: bool, description: str) -> None:
        if not condition:
            self._failures.append(description)

    def assert_all(self) -> None:
        if self._failures:
            details = "\n".join(f"  - {failure}" for failure in self._failures)
            raise AssertionError(f"{len(self._failures)} check(s) failed:\n{details}")
