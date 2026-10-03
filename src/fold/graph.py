"""Construction and validation of the M1A provenance graph and envelope."""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from . import __version__
from .errors import InvariantError
from .git import GitState, recover_git_state
from .model import (
    ChangeRecord,
    DerivedRef,
    Envelope,
    FieldNode,
    ProvenanceGraph,
    SourceRef,
)
from .render import RENDER_CONSUMES
from .task import TaskDeclaration, load_task

DRIFT_RULE_ID = "scope-drift"
DRIFT_RULE_VERSION = "1.0"


def is_path_covered(path: str, scope: str) -> bool:
    """Return whether a path equals or descends from a scope component."""
    return path == scope or path.startswith(f"{scope}/")


def drift_paths(
    task: TaskDeclaration,
    changes: tuple[ChangeRecord, ...],
) -> tuple[str, ...]:
    """Return non-deletion destinations outside declared component prefixes."""
    outside: list[str] = []
    for change in changes:
        if change.is_deletion:
            continue
        if any(is_path_covered(change.path, scope) for scope in task.scope):
            continue
        outside.append(change.path)
    return tuple(sorted(outside))


def source_field(
    name: str,
    value: object,
    classification: Literal["declared", "recovered"],
    provider: str,
    locator: str,
) -> FieldNode:
    """Build a declared or recovered field with source provenance."""
    return FieldNode(
        name=name,
        value=value,
        classification=classification,
        provenance=SourceRef(
            kind="source",
            provider=provider,
            locator=locator,
        ),
    )


def build_nodes(
    task: TaskDeclaration,
    git: GitState,
) -> tuple[FieldNode, ...]:
    """Build M1A collaboration-state fields from authoritative inputs."""
    outside = drift_paths(task, git.changes)
    return (
        source_field(
            "schema_version",
            task.schema_version,
            "declared",
            "task",
            ".fold/task.json#/schemaVersion",
        ),
        source_field(
            "title",
            task.title,
            "declared",
            "task",
            ".fold/task.json#/title",
        ),
        source_field(
            "scope",
            task.scope,
            "declared",
            "task",
            ".fold/task.json#/scope",
        ),
        source_field(
            "tests",
            task.tests,
            "declared",
            "task",
            ".fold/task.json#/tests",
        ),
        source_field(
            "repository_root",
            git.root.as_posix(),
            "recovered",
            "git.repository_root",
            "repository root",
        ),
        source_field(
            "head",
            git.head,
            "recovered",
            "git.head",
            "HEAD",
        ),
        source_field(
            "branch",
            git.branch,
            "recovered",
            "git.branch",
            "current branch",
        ),
        source_field(
            "changes",
            git.changes,
            "recovered",
            "git.changed_paths",
            "working tree and index",
        ),
        FieldNode(
            name="drift_paths",
            value=outside,
            classification="derived",
            provenance=DerivedRef(
                kind="derived",
                rule_id=DRIFT_RULE_ID,
                rule_version=DRIFT_RULE_VERSION,
                inputs=("scope", "changes"),
            ),
        ),
        FieldNode(
            name="status",
            value="DRIFTED" if outside else "ALIGNED",
            classification="derived",
            provenance=DerivedRef(
                kind="derived",
                rule_id=DRIFT_RULE_ID,
                rule_version=DRIFT_RULE_VERSION,
                inputs=("drift_paths",),
            ),
        ),
    )


def consumer_names(graph: ProvenanceGraph) -> frozenset[str]:
    """Derive consumers from renderer contracts and derivation inputs."""
    names = set().union(*RENDER_CONSUMES.values())
    for node in graph.nodes:
        if isinstance(node.provenance, DerivedRef):
            names.update(node.provenance.inputs)
    return frozenset(names)


def classified(
    graph: ProvenanceGraph,
    kind: str,
) -> tuple[FieldNode, ...]:
    """Select graph nodes by collaboration-state classification."""
    return tuple(
        node for node in graph.nodes if node.classification == kind
    )


def rule_identities(
    nodes: Iterable[FieldNode],
) -> tuple[tuple[str, str], ...]:
    """Return canonical identities referenced by derived fields."""
    identities = {
        (node.provenance.rule_id, node.provenance.rule_version)
        for node in nodes
        if isinstance(node.provenance, DerivedRef)
    }
    return tuple(sorted(identities))


def compression_ratio(
    recovered_count: int,
    declared_count: int,
) -> float | None:
    """Return Fold's recovered-to-declared field ratio."""
    return None if declared_count == 0 else recovered_count / declared_count


def build_envelope(graph: ProvenanceGraph) -> Envelope:
    """Compute and validate metadata without adding graph fields."""
    names = [node.name for node in graph.nodes]
    if len(names) != len(set(names)):
        raise InvariantError("duplicate field names in evaluated graph")

    consumers = consumer_names(graph)
    unconsumed = tuple(sorted(set(names) - consumers))
    if unconsumed:
        recoveries = tuple(
            name
            for name in unconsumed
            if graph.require(name).classification == "recovered"
        )
        raise InvariantError(
            "unconsumed collaboration-state fields: "
            f"{unconsumed!r}; recoveries={recoveries!r}"
        )

    declared = classified(graph, "declared")
    recovered = classified(graph, "recovered")
    derived = classified(graph, "derived")
    consumed_derivations = tuple(
        node for node in derived if node.name in consumers
    )
    return Envelope(
        schema_version="1.0",
        tool_version=__version__,
        declared_field_count=len(declared),
        recovered_field_count=len(recovered),
        derived_field_count=len(derived),
        verified_field_count=0,
        compression_ratio=compression_ratio(len(recovered), len(declared)),
        derivation_count=len(consumed_derivations),
        declarative_burden=len(declared),
        unconsumed_recoveries=(),
        referenced_rules=rule_identities(derived),
    )


def evaluate(start: Path) -> tuple[ProvenanceGraph, Envelope]:
    """Recover sources once, build one graph, and compute one envelope."""
    git = recover_git_state(start)
    task = load_task(git.root)
    graph = ProvenanceGraph(
        tuple(sorted(build_nodes(task, git), key=lambda node: node.name))
    )
    return graph, build_envelope(graph)
