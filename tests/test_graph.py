"""Contract tests for graph construction, validation, and envelope."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from fold import render
from fold.errors import InvariantError
from fold.graph import (
    build_envelope,
    compression_ratio,
    evaluate,
    validate_graph,
    verify_envelope,
)
from fold.model import DerivedRef, FieldNode, ProvenanceGraph, SourceRef


def test_envelope_is_graph_derived_and_rejects_unconsumed_fields(
    repository: Path,
) -> None:
    graph, envelope = evaluate(repository)
    assert envelope.declared_field_count == sum(
        node.classification == "declared" for node in graph.nodes
    )
    derived_nodes = tuple(
        node for node in graph.nodes if node.classification == "derived"
    )
    consumed_derivations = tuple(
        node for node in graph.nodes if node.name in {"drift_paths", "status"}
    )
    assert envelope.derived_field_count == len(derived_nodes)
    assert envelope.derivation_count == len(consumed_derivations)
    assert envelope.unconsumed_recoveries == ()

    unused = FieldNode(
        name="unused",
        value=1,
        classification="recovered",
        provenance=SourceRef(kind="source", provider="test", locator="fixture"),
    )
    with pytest.raises(InvariantError, match="unconsumed"):
        build_envelope(ProvenanceGraph(nodes=(unused,)))


def test_compression_ratio_has_zero_denominator_contract() -> None:
    assert compression_ratio(recovered_count=0, declared_count=0) is None


def test_graph_has_declared_recovered_and_derived_nodes(
    repository: Path,
) -> None:
    (repository / "src" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    graph, _ = evaluate(repository)
    nodes = graph.by_name()
    assert nodes["title"].classification == "declared"
    assert nodes["head"].classification == "recovered"
    assert nodes["status"].classification == "derived"
    assert nodes["status"].value == "ALIGNED"


def test_envelope_recomputation_is_byte_identical_and_mismatch_fails(
    repository: Path,
) -> None:
    graph, envelope = evaluate(repository)
    first = render.canonical_envelope_bytes(build_envelope(graph))
    second = render.canonical_envelope_bytes(build_envelope(graph))
    assert first == second
    assert envelope.derived_field_count == 2
    assert envelope.derivation_count == 2
    mismatched = replace(envelope, derivation_count=3)
    with pytest.raises(InvariantError, match="envelope differs"):
        verify_envelope(graph, mismatched)


def test_graph_validation_rejects_duplicate_names() -> None:
    source = SourceRef(kind="source", provider="test", locator="fixture")
    graph = ProvenanceGraph(
        nodes=(
            FieldNode("same", 1, "declared", source),
            FieldNode("same", 2, "recovered", source),
        )
    )

    with pytest.raises(InvariantError, match="duplicate field names"):
        validate_graph(graph)


def test_graph_validation_rejects_missing_derivation_input() -> None:
    graph = ProvenanceGraph(
        nodes=(
            FieldNode(
                name="derived",
                value=False,
                classification="derived",
                provenance=DerivedRef(
                    kind="derived",
                    rule_id="scope-drift",
                    rule_version="1.0",
                    inputs=("missing",),
                ),
            ),
        )
    )

    with pytest.raises(InvariantError, match="missing input"):
        validate_graph(graph)


def test_graph_validation_rejects_cycles() -> None:
    graph = ProvenanceGraph(
        nodes=(
            FieldNode(
                "left",
                (),
                "derived",
                DerivedRef("derived", "scope-drift", "1.0", ("right",)),
            ),
            FieldNode(
                "right",
                (),
                "derived",
                DerivedRef("derived", "scope-drift", "1.0", ("left",)),
            ),
        )
    )

    with pytest.raises(InvariantError, match="graph cycle detected"):
        validate_graph(graph)


def test_graph_validation_rejects_unregistered_rule_identity() -> None:
    source = FieldNode(
        "source",
        (),
        "declared",
        SourceRef(kind="source", provider="test", locator="fixture"),
    )
    derived = FieldNode(
        "derived",
        (),
        "derived",
        DerivedRef("derived", "scope-drift", "999.0", ("source",)),
    )

    with pytest.raises(InvariantError, match="scope-drift@999.0"):
        validate_graph(ProvenanceGraph(nodes=(source, derived)))


def test_graph_validation_requires_recursive_source_leaf_termination() -> None:
    invalid_leaf = FieldNode(
        name="invalid_leaf",
        value=(),
        classification="derived",
        provenance=SourceRef(
            kind="source",
            provider="test",
            locator="fixture",
        ),
    )
    root = FieldNode(
        name="root",
        value=(),
        classification="derived",
        provenance=DerivedRef(
            kind="derived",
            rule_id="scope-drift",
            rule_version="1.0",
            inputs=("invalid_leaf",),
        ),
    )

    graph = ProvenanceGraph(nodes=(invalid_leaf, root))

    with pytest.raises(
        InvariantError,
        match="derived field.*lacks derived provenance",
    ):
        validate_graph(graph)
