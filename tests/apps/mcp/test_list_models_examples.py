"""Regression: the governor's ``list_models`` must survive the WHOLE bundled
example library — including product-market / multi-commodity examples whose year
grids legitimately carry no ``total_cap`` (steel_carbon_joint, and any
nash/product model).

Guards the crash where the list/manifest path indexed ``year["total_cap"]``
unguarded and raised ``KeyError: 'total_cap'`` on a capless product year. This
test deliberately runs against the REAL ``model_store.EXAMPLES_DIR`` (no
fixture monkeypatch), so it exercises the actual shipped configs.
"""
from __future__ import annotations

from pe import model_store
from pe.mcp import tools
from pe.mcp.compact import describe_model_entry


def test_list_models_covers_full_example_library() -> None:
    result = tools.list_models()
    ids = {m["id"] for m in result["models"]}
    # The capless product/multi-commodity example that broke the manifest path.
    assert "steel_carbon_joint" in ids
    # Every entry is well-formed (no silent drop of a crashing model).
    for entry in result["models"]:
        assert entry["id"]
        assert "features" in entry and "approach" in entry


def _iter_year_grids(scenario: dict) -> "list[dict]":
    """Every year dict in a scenario — top-level (single-market) AND nested
    under ``markets[]`` (the joint/multi-market layout)."""
    years = list(scenario.get("years", []))
    for market in scenario.get("markets", []):
        years.extend(market.get("years", []))
    return years


def test_describe_entry_never_raises_on_any_example() -> None:
    saw_capless_year = False
    for model_id, config in model_store.iter_examples():
        # Must not raise for any bundled example, cap or no cap.
        describe_model_entry(model_id, "example", config)
        for scenario in config.get("scenarios", []):
            for year in _iter_year_grids(scenario):
                if "total_cap" not in year:
                    saw_capless_year = True
    # The regression is only meaningful if the library actually contains a
    # capless (product-market) year — the exact shape that broke the stale
    # manifest path (steel_carbon_joint's `product` market year).
    assert saw_capless_year, "expected at least one capless product-market year"
