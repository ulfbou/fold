"""Construction and validation of the M1A graph and envelope."""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from . import __version__
from .errors import InvariantError
from .git import GitState, recover_git_state
from .model import ChangeRecord, DerivedRef, Envelope, FieldNode, ProvenanceGraph, SourceRef
from .render import RENDER_CONSUMES, canonical_envelope_bytes
from .rules import resolve_rule
from .task import TaskDeclaration, load_task

ENVELOPE_SCHEMA_VERSION = "1.0"
DRIFT_RULE_ID = "scope-drift"
DRIFT_RULE_VERSION = "1.0"
DRIFT_RULE_IDENTITY = "scope-drift@1.0"


def is_path_covered(path: str, scope: str) -> bool:
    return path == scope or path.startswith(f"{scope}/")


def drift_paths(
    task: TaskDeclaration,
    changes: tuple[ChangeRecord, ...],
) -> tuple[str, ...]:
    """Evaluate scope drift through the exact registered rule."""
    rule = resolve_rule(DRIFT_RULE_ID, DRIFT_RULE_VERSION)
    return rule.evaluator(task.scope, changes)

def source_field(
    name: str,
    value: object,
    classification: Literal["declared", "recovered"],
    provider: str,
    locator: str,
) -> FieldNode:
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
    declared = (
        source_field(
            "schema_version",
            task.schema_version,
            "declared",
            "task",
            ".fold/task.json#/schemaVersion",
        ),
        source_field("title", task.title, "declared", "task", ".fold/task.json#/title"),
        source_field("scope", task.scope, "declared", "task", ".fold/task.json#/scope"),
        source_field("tests", task.tests, "declared", "task", ".fold/task.json#/tests"),
    )
    recovered = (
        source_field(
            "repository_root",
            git.root.as_posix(),
            "recovered",
            "git.repository_root",
            "repository root",
        ),
        source_field("head", git.head, "recovered", "git.head", "HEAD"),
        source_field("branch", git.branch, "recovered", "git.branch", "current branch"),
        source_field(
            "changes",
            git.changes,
            "recovered",
            "git.changed_paths",
            "working tree and index",
        ),
    )
    derived = (
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
    return declared + recovered + derived


def validate_graph(graph: ProvenanceGraph) -> None:
    """Reject invalid provenance structure before any graph consumer runs."""
    names = [node.name for node in graph.nodes]
    if len(names) != len(set(names)):
        raise InvariantError("duplicate field names in evaluated graph")

    nodes = graph.by_name()
    state: dict[str, str] = {}

    def visit(name: str) -> None:
        status = state.get(name)
        if status == "visiting":
            raise InvariantError(f"graph cycle detected at field: {name}")
        if status == "visited":
            return

        state[name] = "visiting"
        node = nodes[name]

        if isinstance(node.provenance, DerivedRef):
            provenance = node.provenance
            resolve_rule(provenance.rule_id, provenance.rule_version)

            for input_name in provenance.inputs:
                if input_name not in nodes:
                    raise InvariantError(
                        f"derived field {name!r} has missing input {input_name!r}"
                    )
                visit(input_name)

        state[name] = "visited"

    for name in names:
        visit(name)


def consumer_names(graph: ProvenanceGraph) -> frozenset[str]:
    """Derive consumers from renderer contracts and derivation inputs."""
    names = set().union(*RENDER_CONSUMES.values())
    for node in graph.nodes:
        if isinstance(node.provenance, DerivedRef):
            names.update(node.provenance.inputs)
    return frozenset(names)


def classified(graph: ProvenanceGraph, kind: str) -> tuple[FieldNode, ...]:
    return tuple(node for node in graph.nodes if node.classification == kind)


def rule_identities(nodes: Iterable[FieldNode]) -> tuple[tuple[str, str], ...]:
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
    """Validate consumers and compute metadata outside the field graph."""

    names = [node.name for node in graph.nodes]
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
        schema_version=ENVELOPE_SCHEMA_VERSION,
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


def verify_envelope(graph: ProvenanceGraph, envelope: Envelope) -> None:
    """Reject an envelope that differs from canonical graph recomputation."""
    recomputed = build_envelope(graph)
    if canonical_envelope_bytes(envelope) != canonical_envelope_bytes(recomputed):
        raise InvariantError("envelope differs from canonical graph recomputation")


def evaluate(start: Path) -> tuple[ProvenanceGraph, Envelope]:
    """Recover sources once, build one graph, and compute one envelope."""
    git = recover_git_state(start)
    task = load_task(git.root)
    graph = ProvenanceGraph(
        tuple(sorted(build_nodes(task, git), key=lambda node: node.name))
    )
    validate_graph(graph)
    envelope = build_envelope(graph)
    verify_envelope(graph, envelope)
    return graph, envelope
