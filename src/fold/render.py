from __future__ import annotations

import json
from typing import Any

from .model import DerivedRef, FieldNode, ProvenanceGraph, SourceRef


def _lines(value: Any) -> list[str]:
    if isinstance(value, (tuple, list)):
        return [str(item) for item in value] or ["(none)"]
    if isinstance(value, float):
        return [f"{value:.3f}"]
    return [str(value)]


def render_task(graph: ProvenanceGraph) -> str:
    nodes = graph.by_name()
    sections = [
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
        *[f"  {item}" for item in _lines(nodes['scope'].value)],
        "",
        "ACTUAL CHANGES",
        *[f"  {item}" for item in _lines(nodes['changed_paths'].value)],
        "",
        "DRIFT",
        *[f"  {item}" for item in _lines(nodes['drift_paths'].value)],
        "",
        "VERIFICATION",
        *[f"  {item}" for item in _lines(nodes['tests'].value)],
        "",
        "METRICS",
        f"  compression_ratio: {nodes['compression_ratio'].value:.3f}",
        f"  derivation_count: {nodes['derivation_count'].value}",
        f"  declarative_backlog: {nodes['declarative_backlog'].value}",
    ]
    return "\n".join(sections) + "\n"


def _node_json(node: FieldNode) -> dict[str, Any]:
    provenance = node.provenance
    if isinstance(provenance, SourceRef):
        prov = {"kind": "source", "provider": provenance.provider, "locator": provenance.locator}
    else:
        prov = {"kind": "derived", "ruleId": provenance.rule_id, "ruleVersion": provenance.rule_version, "inputs": list(provenance.inputs)}
    value = list(node.value) if isinstance(node.value, tuple) else node.value
    return {"name": node.name, "value": value, "classification": node.classification, "provenance": prov}


def graph_json(graph: ProvenanceGraph) -> dict[str, Any]:
    return {"schemaVersion": "1.0", "fields": [_node_json(node) for node in graph.nodes]}


def render_explain_json(graph: ProvenanceGraph) -> str:
    return json.dumps(graph_json(graph), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _walk(name: str, nodes: dict[str, FieldNode], depth: int, seen: set[str]) -> list[str]:
    node = nodes[name]
    pad = "  " * depth
    lines = [f"{pad}{node.name}", f"{pad}  classification: {node.classification}"]
    provenance = node.provenance
    if isinstance(provenance, SourceRef):
        lines.extend((f"{pad}  source: {provenance.provider}", f"{pad}  locator: {provenance.locator}"))
    else:
        lines.extend((f"{pad}  rule: {provenance.rule_id}@{provenance.rule_version}", f"{pad}  inputs:"))
        if name in seen:
            lines.append(f"{pad}    (cycle suppressed)")
        else:
            next_seen = set(seen) | {name}
            for input_name in provenance.inputs:
                lines.extend(_walk(input_name, nodes, depth + 2, next_seen))
    return lines


def render_explain(graph: ProvenanceGraph, field: str | None = None) -> str:
    nodes = graph.by_name()
    names = [field] if field else [node.name for node in graph.nodes]
    unknown = [name for name in names if name not in nodes]
    if unknown:
        raise KeyError(unknown[0])
    blocks = ["\n".join(_walk(name, nodes, 0, set())) for name in names]
    return "\n\n".join(blocks) + "\n"
