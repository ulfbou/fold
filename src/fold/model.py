from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias


@dataclass(frozen=True)
class SourceRef:
    kind: Literal["source"]
    provider: str
    locator: str


@dataclass(frozen=True)
class DerivedRef:
    kind: Literal["derived"]
    rule_id: str
    rule_version: str
    inputs: tuple[str, ...]


Provenance: TypeAlias = SourceRef | DerivedRef


@dataclass(frozen=True)
class FieldNode:
    name: str
    value: Any
    classification: Literal["declared", "recovered", "derived"]
    provenance: Provenance


@dataclass(frozen=True)
class ProvenanceGraph:
    nodes: tuple[FieldNode, ...]

    def by_name(self) -> dict[str, FieldNode]:
        return {node.name: node for node in self.nodes}

    def require(self, name: str) -> FieldNode:
        try:
            return self.by_name()[name]
        except KeyError as exc:
            raise KeyError(f"unknown field: {name}") from exc
