"""Immutable domain models for Fold state, provenance, and metadata."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, TypeAlias

from .errors import InvariantError, UnknownFieldError


class ChangeKind(str, Enum):
    """One character from a Git porcelain-v2 XY status pair."""

    UNCHANGED = "."
    MODIFIED = "M"
    ADDED = "A"
    DELETED = "D"
    RENAMED = "R"
    COPIED = "C"
    TYPE_CHANGED = "T"
    UNMERGED = "U"
    UNTRACKED = "?"


@dataclass(frozen=True)
class ChangeRecord:
    """A deterministic semantic representation of one Git change."""

    path: str
    index_kind: ChangeKind
    worktree_kind: ChangeKind
    original_path: str | None = None
    unmerged: bool = False

    @property
    def status_pair(self) -> str:
        return f"{self.index_kind.value}{self.worktree_kind.value}"

    @property
    def is_deletion(self) -> bool:
        return (
            self.index_kind is ChangeKind.DELETED
            or self.worktree_kind is ChangeKind.DELETED
        )

    def sort_key(self) -> tuple[str, str, str, str]:
        return (
            self.path,
            self.index_kind.value,
            self.worktree_kind.value,
            self.original_path or "",
        )


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

    def get_for_explanation(self, name: str) -> FieldNode:
        try:
            return self.by_name()[name]
        except KeyError as exc:
            raise UnknownFieldError(f"unknown field: {name}") from exc

    def require(self, name: str) -> FieldNode:
        try:
            return self.by_name()[name]
        except KeyError as exc:
            raise InvariantError(
                f"evaluated graph is missing required field: {name}"
            ) from exc


@dataclass(frozen=True)
class Envelope:
    """Metadata computed from, but never counted as, graph fields."""

    schema_version: str
    tool_version: str
    declared_field_count: int
    recovered_field_count: int
    derived_field_count: int
    verified_field_count: int
    compression_ratio: float | None
    derivation_count: int
    declarative_burden: int
    unconsumed_recoveries: tuple[str, ...]
    referenced_rules: tuple[tuple[str, str], ...]
