"""Shared pytest configuration for the ETS test suite."""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "slow: long-running golden-baseline replay scenarios (>= 25 s each). "
        "ON by default; deselect with -m 'not slow' for quick local loops — "
        "the equivalence gate always runs the full set.",
    )
