"""Canonical human and JSON renderers for the evaluated Fold graph."""
from __future__ import annotations

import json
from typing import Any

from .model import ChangeRecord, Envelope, FieldNode, ProvenanceGraph, SourceRef
from .rules import resolve_rule

RENDER_CONSUMES: dict[str, frozenset[str]] = {
    "task": frozenset(
        {
            "branch",
            "changes",
            "drift_paths",
            "head",
            "repository_root",
            "scope",
            "status",
            "tests",
            "title",
        }
    ),
    "explain_json": frozenset({"schema_version"}),
}


def value_to_json(value: Any) -> Any:
    if isinstance(value, ChangeRecord):
        document: dict[str, Any] = {
            "path": value.path,
            "indexKind": value.index_kind.value,
            "worktreeKind": value.worktree_kind.value,
        }
        if value.original_path is not None:
            document["originalPath"] = value.original_path
        if value.unmerged:
            document["unmerged"] = True
        return document
    if isinstance(value, tuple):
        return [value_to_json(item) for item in value]
    return value


def node_to_json(node: FieldNode) -> dict[str, Any]:
    provenance = node.provenance
    if isinstance(provenance, SourceRef):
        detail = {
            "kind": "source",
            "provider": provenance.provider,
            "locator": provenance.locator,
        }
    else:
        detail = {
            "kind": "derived",
            "ruleId": provenance.rule_id,
            "ruleVersion": provenance.rule_version,
            "inputs": list(provenance.inputs),
        }
    return {
        "name": node.name,
        "value": value_to_json(node.value),
        "classification": node.classification,
        "provenance": detail,
    }



def explanation_to_json(
    name: str,
    nodes: dict[str, FieldNode],
) -> dict[str, Any]:
    """Build one recursive explanation from the evaluated graph."""
    node = nodes[name]
    provenance = node.provenance
    document: dict[str, Any] = {
        "classification": node.classification,
        "name": node.name,
        "value": value_to_json(node.value),
    }

    if isinstance(provenance, SourceRef):
        document["provenance"] = {
            "kind": "source",
            "locator": provenance.locator,
            "provider": provenance.provider,
        }
        return document

    rule = resolve_rule(provenance.rule_id, provenance.rule_version)
    inputs = [
        explanation_to_json(input_name, nodes)
        for input_name in provenance.inputs
    ]
    document["provenance"] = {
        "descriptor": rule.descriptor.canonical_document(),
        "evaluatedInputs": [
            {
                "name": input_name,
                "value": value_to_json(nodes[input_name].value),
            }
            for input_name in provenance.inputs
        ],
        "inputs": inputs,
        "kind": "derived",
        "output": value_to_json(node.value),
        "ruleId": provenance.rule_id,
        "ruleVersion": provenance.rule_version,
    }
    return document


def envelope_to_json(envelope: Envelope) -> dict[str, Any]:
    return {
        "schemaVersion": envelope.schema_version,
        "toolVersion": envelope.tool_version,
        "declaredFieldCount": envelope.declared_field_count,
        "recoveredFieldCount": envelope.recovered_field_count,
        "derivedFieldCount": envelope.derived_field_count,
        "verifiedFieldCount": envelope.verified_field_count,
        "compressionRatio": envelope.compression_ratio,
        "derivationCount": envelope.derivation_count,
        "declarativeBurden": envelope.declarative_burden,
        "unconsumedRecoveries": list(envelope.unconsumed_recoveries),
        "referencedRules": [
            {"ruleId": rule_id, "ruleVersion": version}
            for rule_id, version in envelope.referenced_rules
        ],
    }


def canonical_envelope_bytes(envelope: Envelope) -> bytes:
    """Serialize an envelope canonically for recomputation comparison."""
    return (
        json.dumps(
            envelope_to_json(envelope),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")



def graph_json(
    graph: ProvenanceGraph,
    envelope: Envelope,
) -> dict[str, Any]:
    nodes = graph.by_name()
    return {
        "schemaVersion": "1.0",
        "envelope": envelope_to_json(envelope),
        "fields": [node_to_json(node) for node in graph.nodes],
        "explanations": [
            explanation_to_json(node.name, nodes)
            for node in graph.nodes
        ],
    }
def render_explain_json(graph: ProvenanceGraph, envelope: Envelope) -> str:
    return (
        json.dumps(
            graph_json(graph, envelope),
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    )


def indented(values: list[str]) -> list[str]:
    return [f"  {value}" for value in values] if values else ["  (none)"]


def render_task(graph: ProvenanceGraph, envelope: Envelope) -> str:
    """Render the accepted human task surface from the graph and envelope."""
    nodes = graph.by_name()
    changes = [change.path for change in nodes["changes"].value]
    ratio = (
        "n/a"
        if envelope.compression_ratio is None
        else f"{envelope.compression_ratio:.3f}"
    )
    lines = [
        "FOLD TASK",
        "",
        f"STATUS: {nodes['status'].value}",
        "",
        "TITLE",
        f"  {nodes['title'].value}",
        "",
        "REPOSITORY",
        f"  root: {nodes['repository_root'].value}",
        f"  branch: {nodes['branch'].value}",
        f"  head: {nodes['head'].value}",
        "",
        "DECLARED SCOPE",
        *indented(list(nodes["scope"].value)),
        "",
        "ACTUAL CHANGES",
        *indented(changes),
        "",
        "DRIFT",
        *indented(list(nodes["drift_paths"].value)),
        "",
        "VERIFICATION",
        *indented(list(nodes["tests"].value)),
        "",
        "METRICS",
        f"  compression_ratio: {ratio}",
        f"  derivation_count: {envelope.derivation_count}",
        f"  declarative_burden: {envelope.declarative_burden}",
    ]
    return "\n".join(lines) + "\n"



def _walk(
    name: str,
    nodes: dict[str, FieldNode],
    depth: int,
) -> list[str]:
    node = nodes[name]
    padding = "  " * depth
    value = json.dumps(
        value_to_json(node.value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    lines = [
        f"{padding}{node.name}",
        f"{padding}  classification: {node.classification}",
        f"{padding}  value: {value}",
    ]
    provenance = node.provenance

    if isinstance(provenance, SourceRef):
        lines.extend(
            (
                f"{padding}  source: {provenance.provider}",
                f"{padding}  locator: {provenance.locator}",
            )
        )
        return lines

    rule = resolve_rule(provenance.rule_id, provenance.rule_version)
    descriptor = json.dumps(
        rule.descriptor.canonical_document(),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    lines.extend(
        (
            f"{padding}  rule: "
            f"{provenance.rule_id}@{provenance.rule_version}",
            f"{padding}  evaluator_digest: "
            f"{rule.descriptor.evaluator_digest}",
            f"{padding}  descriptor: {descriptor}",
            f"{padding}  evaluated_inputs:",
        )
    )

    for input_name in provenance.inputs:
        input_value = json.dumps(
            value_to_json(nodes[input_name].value),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        lines.append(f"{padding}    {input_name}: {input_value}")

    lines.append(f"{padding}  inputs:")
    for input_name in provenance.inputs:
        lines.extend(_walk(input_name, nodes, depth + 2))

    lines.append(f"{padding}  output: {value}")
    return lines

def render_explain(
    graph: ProvenanceGraph,
    field: str | None = None,
) -> str:
    """Render recursive provenance from the validated evaluated graph."""
    nodes = graph.by_name()
    names = [field] if field else [node.name for node in graph.nodes]
    blocks: list[str] = []

    for name in names:
        graph.get_for_explanation(name)
        blocks.append("\n".join(_walk(name, nodes, 0)))

    return "\n\n".join(blocks) + "\n"
