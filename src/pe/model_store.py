"""Transport-free scenario-registry I/O, shared by every app tier (T5).

``ets.web.api`` (``POST /api/graph/save-model``, ``GET /api/templates``),
``ets.mcp.tools`` (``list_models``, ``new_graph``, ``save_model`` — the
composer, which authors models), and ``ets.mcp.models_tools``
(``list_models``, ``describe_model``, ``run_model``, ``rename_model``,
``delete_model``, ... — the governor, which operates the already-saved
registry) all need to turn a composer :class:`~ets.blocks.graph.Graph` into
a validated, runnable scenario config, persist it under
``USER_SCENARIOS_DIR`` alongside its source graph, and enumerate/rename/
delete the example/registry models already there. That logic used to live
only in ``ets.web.api._handle_graph_save_model``; this module is the one
place it's implemented, so a model saved through any app appears
immediately in the others (they share one registry directory on disk) and
no app duplicates the validate-compile-persist(-rename/delete) sequence.

Design choice — a small top-level module, not ``ets.blocks``: this package
does real file I/O (``USER_SCENARIOS_DIR.mkdir``, reading/writing
``<slug>.json``/``<slug>.graph.json``), which is exactly what
``ets.blocks``'s own dependency law forbids it ("imports only ``config_io``
and stdlib — never ...") — ``ets.blocks`` is metadata plus a pure compiler,
deliberately I/O-free (``docs/blocks-graph-plan.md`` §3). A bare top-level
module is also the natural home for something both ``ets.web`` and
``ets.mcp`` need without either importing the other (the end-state
dependency diagram, ``docs/blocks-graph-plan.md`` §6, already says "nothing
imports web" — routing this shared logic through ``ets.web`` would break
that). ``tests/test_module_isolation.py`` classifies it ``LEGACY``
(no enforced import contract beyond clause (h)'s underscore-boundary rule) —
consistent with the file living beside, not inside, one of the five tiers.

Engineering constants (max output size caps, etc.) that don't correspond to
an economic/model parameter are colocated here as named module constants
rather than routed through a ``.env`` loader: this repo's actual
``src/<pkg>/config.py`` convention (``ets.core.paths``) covers filesystem
locations, and every existing numeric default of this kind (solver
tolerances, MSR/CCR defaults, ...) already lives next to the code that uses
it (``ets.config_io.templates``, ``ets.core.defaults``) rather than in an
env file — this module follows that established precedent.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .blocks import Graph, compile_graph, graph_from_config, validate_graph
from .config_io import load_config, save_config
from .core.paths import EXAMPLES_DIR, USER_SCENARIOS_DIR


class ModelStoreError(ValueError):
    """Raised when a graph/model id cannot be resolved, compiled, or saved.

    A ``ValueError`` subclass so existing callers that catch bare
    ``Exception``/``ValueError`` (``ets.web.server``'s WSGI 400 handler) need
    no changes.
    """


@dataclass(frozen=True)
class SavedModel:
    """The result of :func:`save_graph_as_model`.

    Args:
        id: Registry id, ``"user_<slug>"`` — the same id
            ``GET /api/templates`` and ``ets.mcp``'s ``list_models`` use.
        name: The display name the caller passed in (untrimmed of nothing —
            already ``.strip()``-ed).
        config: The compiled scenario config, re-read from disk (so it has
            gone through ``config_io.normalize_config`` exactly once, the
            same as every other registry read).
        config_path: Where the scenario config was written
            (``<registry_dir>/<slug>.json``).
        graph_path: Where the source composer graph was written verbatim
            (``<registry_dir>/<slug>.graph.json``).
    """

    id: str
    name: str
    config: dict[str, Any]
    config_path: Path
    graph_path: Path


def slugify_filename(value: str) -> str:
    """Turn a display name into a filesystem-safe, collision-tolerant stem.

    Args:
        value: Any string (typically a model's display name).

    Returns:
        Lowercase, ``[a-z0-9_]``-only, no repeated/edge underscores;
        ``"scenario"`` if ``value`` has no alphanumeric characters at all.
    """
    slug = "".join(char.lower() if char.isalnum() else "_" for char in str(value)).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "scenario"


def compile_graph_or_raise(graph: Graph) -> dict[str, Any]:
    """Validate then compile a graph, summarising every ERROR issue on failure.

    Args:
        graph: The drawn block graph.

    Returns:
        The compiled, normalized scenario-config dict
        (``ets.blocks.compile_graph`` output).

    Raises:
        ModelStoreError: At least one ERROR-level
            :class:`~ets.blocks.validate.ValidationIssue` — the message lists
            every one, ``"[<rule>] <text>"``, semicolon-separated.
    """
    issues = validate_graph(graph)
    errors = [issue for issue in issues if issue.level == "error"]
    if errors:
        summary = "; ".join(f"[{issue.rule}] {issue.message}" for issue in errors)
        raise ModelStoreError(f"Graph validation failed: {summary}")
    return compile_graph(graph)


def save_graph_as_model(
    graph: Graph, name: str, *, registry_dir: Path | None = None
) -> SavedModel:
    """Validate, compile, and persist a graph as a registry model.

    Writes two files under ``registry_dir`` (default ``USER_SCENARIOS_DIR``):

    * ``<slug>.json`` — the compiled scenario config
      (``config_io.save_config``), so it is picked up by every existing
      "list runnable models" path (``_predefined_templates``,
      ``ets.mcp.tools.list_models``) and runs unmodified through
      ``run_simulation_from_config``.
    * ``<slug>.graph.json`` — the source composer graph verbatim, so the
      model reopens exactly as drawn (see :func:`resolve_model_graph`).

    Args:
        graph: The drawn block graph.
        name: Display name; also the basis for the ``<slug>`` (via
            :func:`slugify_filename`) and thus the registry id.
        registry_dir: Where to write the two files. Defaults to
            ``ets.core.paths.USER_SCENARIOS_DIR``.

    Returns:
        The :class:`SavedModel`.

    Raises:
        ModelStoreError: Empty ``name``, or graph validation/compile failure
            (:func:`compile_graph_or_raise`).
    """
    display_name = name.strip()
    if not display_name:
        raise ModelStoreError("A model needs a non-empty name.")
    config = compile_graph_or_raise(graph)

    directory = registry_dir if registry_dir is not None else USER_SCENARIOS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    stem = slugify_filename(display_name)
    config_path = directory / f"{stem}.json"
    graph_path = directory / f"{stem}.graph.json"
    save_config(config, config_path)
    graph_path.write_text(json.dumps(graph.to_dict(), indent=2), encoding="utf-8")

    return SavedModel(
        id=f"user_{stem}",
        name=display_name,
        config=load_config(config_path),
        config_path=config_path,
        graph_path=graph_path,
    )


def _require_registry_model_id(model_id: str) -> str:
    """Validate ``model_id`` is a registry (``"user_<slug>"``) id; return its slug.

    Shared guard for :func:`rename_registry_model` and
    :func:`delete_registry_model` — both are registry-only mutations, per
    ``ets.mcp.models_tools``'s role split (the governor operates the
    registry but never touches a bundled example).

    Args:
        model_id: A model id, as accepted by :func:`resolve_model_config`.

    Returns:
        The slug (``model_id`` with its ``"user_"`` prefix stripped).

    Raises:
        ModelStoreError: ``model_id`` doesn't start with ``"user_"`` (an
            example id, or empty/malformed) — examples are immutable.
    """
    slug = model_id.removeprefix("user_")
    if not model_id.startswith("user_") or not slug:
        raise ModelStoreError(
            f"'{model_id}' is not a registry model id — only models saved to the "
            "registry (ids starting with 'user_') can be renamed or deleted; "
            "bundled examples are immutable."
        )
    return slug


def rename_registry_model(
    model_id: str, new_name: str, *, registry_dir: Path | None = None
) -> SavedModel:
    """Rename a registry model by re-slugging its on-disk files to ``new_name``.

    A registry model's display name (see :func:`resolve_model_config`'s
    sibling ``ets.mcp.compact.describe_model_entry``) is derived from its
    id/slug, not stored inside the config — so "renaming" means moving
    ``<old_slug>.json`` (and its ``<old_slug>.graph.json`` sidecar, if
    present) to the new slug's filenames, exactly mirroring how
    :func:`save_graph_as_model` derives a slug from a display name.

    Args:
        model_id: The registry model's current ``"user_<slug>"`` id.
        new_name: The new display name; also the basis of the new slug (via
            :func:`slugify_filename`).
        registry_dir: Defaults to ``ets.core.paths.USER_SCENARIOS_DIR``.

    Returns:
        The renamed model's :class:`SavedModel` (``id`` is the new
        ``"user_<slug>"``).

    Raises:
        ModelStoreError: ``model_id`` isn't a registry id (see
            :func:`_require_registry_model_id`), doesn't exist, ``new_name``
            is empty, or the new slug collides with a different existing
            registry model.
    """
    slug = _require_registry_model_id(model_id)
    display_name = new_name.strip()
    if not display_name:
        raise ModelStoreError("A model needs a non-empty name.")

    directory = registry_dir if registry_dir is not None else USER_SCENARIOS_DIR
    config_path = directory / f"{slug}.json"
    graph_path = directory / f"{slug}.graph.json"
    if not config_path.exists():
        raise ModelStoreError(f"Unknown model id '{model_id}'.")

    new_slug = slugify_filename(display_name)
    new_config_path = directory / f"{new_slug}.json"
    new_graph_path = directory / f"{new_slug}.graph.json"
    if new_slug != slug and new_config_path.exists():
        raise ModelStoreError(
            f"A registry model named '{display_name}' already exists (id 'user_{new_slug}')."
        )

    config_path.rename(new_config_path)
    if graph_path.exists():
        graph_path.rename(new_graph_path)

    return SavedModel(
        id=f"user_{new_slug}",
        name=display_name,
        config=load_config(new_config_path),
        config_path=new_config_path,
        graph_path=new_graph_path,
    )


def delete_registry_model(model_id: str, *, registry_dir: Path | None = None) -> None:
    """Delete a registry model's config and (if present) its graph sidecar.

    Args:
        model_id: The registry model's ``"user_<slug>"`` id.
        registry_dir: Defaults to ``ets.core.paths.USER_SCENARIOS_DIR``.

    Raises:
        ModelStoreError: ``model_id`` isn't a registry id (see
            :func:`_require_registry_model_id`), or doesn't exist.
    """
    slug = _require_registry_model_id(model_id)
    directory = registry_dir if registry_dir is not None else USER_SCENARIOS_DIR
    config_path = directory / f"{slug}.json"
    graph_path = directory / f"{slug}.graph.json"
    if not config_path.exists():
        raise ModelStoreError(f"Unknown model id '{model_id}'.")
    config_path.unlink()
    if graph_path.exists():
        graph_path.unlink()


def iter_examples(*, examples_dir: Path | None = None) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(id, config)`` for every loadable ``examples/*.json`` file.

    Args:
        examples_dir: Defaults to ``ets.core.paths.EXAMPLES_DIR``.

    Yields:
        ``(path.stem, config)`` in sorted filename order. Files that fail to
        load as a scenario config (the repo's generator scripts and API
        request-payload fixtures also live under ``examples/``) are silently
        skipped, same tolerance as the pre-refactor
        ``ets.web.api._predefined_templates`` loop.
    """
    directory = examples_dir if examples_dir is not None else EXAMPLES_DIR
    for path in sorted(directory.glob("*.json")):
        try:
            yield path.stem, load_config(path)
        except Exception:
            continue


def iter_registry_models(
    *, registry_dir: Path | None = None
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``("user_<slug>", config)`` for every saved registry model.

    Args:
        registry_dir: Defaults to ``ets.core.paths.USER_SCENARIOS_DIR``.
            Created if it doesn't exist yet.

    Yields:
        ``(f"user_{path.stem}", config)`` in sorted filename order.
        ``*.graph.json`` composer-graph sidecars (:func:`save_graph_as_model`)
        are skipped, as is any file that fails to load.
    """
    directory = registry_dir if registry_dir is not None else USER_SCENARIOS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    for path in sorted(directory.glob("*.json")):
        if path.name.endswith(".graph.json"):
            continue
        try:
            yield f"user_{path.stem}", load_config(path)
        except Exception:
            continue


def resolve_model_config(
    model_id: str, *, examples_dir: Path | None = None, registry_dir: Path | None = None
) -> dict[str, Any]:
    """Resolve a model id (example stem or ``"user_<slug>"``) to its config.

    Args:
        model_id: An example's ``examples/<id>.json`` stem, or a registry
            model's ``"user_<slug>"`` id.
        examples_dir: Defaults to ``ets.core.paths.EXAMPLES_DIR``.
        registry_dir: Defaults to ``ets.core.paths.USER_SCENARIOS_DIR``.

    Returns:
        The scenario-config dict (``config_io.load_config`` output).

    Raises:
        ModelStoreError: ``model_id`` is empty or matches no known model.
    """
    if not model_id:
        raise ModelStoreError("A model id is required.")
    if model_id.startswith("user_"):
        directory = registry_dir if registry_dir is not None else USER_SCENARIOS_DIR
        path = directory / f"{model_id.removeprefix('user_')}.json"
    else:
        directory = examples_dir if examples_dir is not None else EXAMPLES_DIR
        path = directory / f"{model_id}.json"
    if not path.exists():
        raise ModelStoreError(f"Unknown model id '{model_id}'.")
    return load_config(path)


def resolve_model_graph(
    model_id: str, *, examples_dir: Path | None = None, registry_dir: Path | None = None
) -> Graph:
    """Resolve a model id to its composer graph, preferring a saved sidecar.

    For a registry model (``"user_<slug>"``) saved through
    :func:`save_graph_as_model`, the original composer graph is returned
    verbatim from its ``<slug>.graph.json`` sidecar when present — an exact
    round trip of what was drawn, including canvas metadata. Every other
    case (an example, or a registry model saved through the older
    ``/api/save-scenario`` flow with no sidecar) falls back to decompiling
    the resolved config (:func:`ets.blocks.decompile.graph_from_config`).

    Args:
        model_id: An example stem or a registry ``"user_<slug>"`` id.
        examples_dir: Defaults to ``ets.core.paths.EXAMPLES_DIR``.
        registry_dir: Defaults to ``ets.core.paths.USER_SCENARIOS_DIR``.

    Returns:
        The resolved :class:`~ets.blocks.graph.Graph`.

    Raises:
        ModelStoreError: ``model_id`` matches no known model.
    """
    if model_id.startswith("user_"):
        directory = registry_dir if registry_dir is not None else USER_SCENARIOS_DIR
        graph_path = directory / f"{model_id.removeprefix('user_')}.graph.json"
        if graph_path.exists():
            return Graph.from_dict(json.loads(graph_path.read_text(encoding="utf-8")))
    config = resolve_model_config(model_id, examples_dir=examples_dir, registry_dir=registry_dir)
    return graph_from_config(config)
