"""Exact-identity rule registry with inspectable canonical descriptors."""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import textwrap
from dataclasses import dataclass
from typing import Any, Callable

from .errors import InvariantError


RuleEvaluator = Callable[..., Any]


@dataclass(frozen=True)
class RuleDescriptor:
    """Canonical public description of one exact rule implementation."""

    rule_id: str
    rule_version: str
    inputs: tuple[str, ...]
    output_contract: str
    policy_constants: tuple[tuple[str, Any], ...]
    predicate: str
    evaluator_digest: str

    @property
    def identity(self) -> tuple[str, str]:
        return self.rule_id, self.rule_version

    def canonical_document(self) -> dict[str, Any]:
        return {
            "evaluatorDigest": self.evaluator_digest,
            "inputs": list(self.inputs),
            "outputContract": self.output_contract,
            "policyConstants": dict(self.policy_constants),
            "predicate": self.predicate,
            "ruleId": self.rule_id,
            "ruleVersion": self.rule_version,
        }


@dataclass(frozen=True)
class RegisteredRule:
    descriptor: RuleDescriptor
    evaluator: RuleEvaluator


def canonical_semantic_representation(evaluator: RuleEvaluator) -> bytes:
    """Return stable evaluator semantics excluding presentation-only source details."""
    try:
        source = textwrap.dedent(inspect.getsource(evaluator))
        tree = ast.parse(source)
    except (OSError, TypeError, SyntaxError) as exc:
        raise InvariantError(
            f"cannot canonicalize rule evaluator {evaluator!r}"
        ) from exc

    for node in ast.walk(tree):
        for attribute in ("lineno", "col_offset", "end_lineno", "end_col_offset"):
            if hasattr(node, attribute):
                setattr(node, attribute, None)

    return ast.dump(
        tree,
        annotate_fields=True,
        include_attributes=False,
    ).encode("utf-8")


def semantic_implementation_digest(evaluator: RuleEvaluator) -> str:
    """Hash the canonical semantic evaluator representation."""
    return hashlib.sha256(canonical_semantic_representation(evaluator)).hexdigest()


def _scope_drift(scope: tuple[str, ...], changes: tuple[Any, ...]) -> tuple[str, ...]:
    """Return non-deletion destinations outside the component-prefix scope."""
    return tuple(
        sorted(
            change.path
            for change in changes
            if not change.is_deletion
            and not any(
                change.path == prefix or change.path.startswith(f"{prefix}/")
                for prefix in scope
            )
        )
    )


def _descriptor(
    *,
    rule_id: str,
    rule_version: str,
    inputs: tuple[str, ...],
    output_contract: str,
    policy_constants: tuple[tuple[str, Any], ...],
    predicate: str,
    evaluator: RuleEvaluator,
) -> RuleDescriptor:
    return RuleDescriptor(
        rule_id=rule_id,
        rule_version=rule_version,
        inputs=inputs,
        output_contract=output_contract,
        policy_constants=policy_constants,
        predicate=predicate,
        evaluator_digest=semantic_implementation_digest(evaluator),
    )


_SCOPE_DRIFT = RegisteredRule(
    descriptor=_descriptor(
        rule_id="scope-drift",
        rule_version="1.0",
        inputs=("scope", "changes"),
        output_contract="sorted tuple of non-deletion changed paths outside scope",
        policy_constants=(
            ("deletionOutsideScopeCreatesDrift", False),
            ("pathRelation", "equal-or-descendant-component-prefix"),
        ),
        predicate=(
            "A non-deletion change is drift when its destination path is not equal "
            "to or beneath any declared scope path."
        ),
        evaluator=_scope_drift,
    ),
    evaluator=_scope_drift,
)

_REGISTRY: dict[tuple[str, str], RegisteredRule] = {
    _SCOPE_DRIFT.descriptor.identity: _SCOPE_DRIFT,
}


def resolve_rule(rule_id: str, rule_version: str) -> RegisteredRule:
    """Resolve only an exact registered rule identity."""
    identity = (rule_id, rule_version)
    try:
        return _REGISTRY[identity]
    except KeyError as exc:
        raise InvariantError(
            f"unregistered rule identity: {rule_id}@{rule_version}"
        ) from exc


def registered_rules() -> tuple[RegisteredRule, ...]:
    """Return registered rules in deterministic exact-identity order."""
    return tuple(_REGISTRY[identity] for identity in sorted(_REGISTRY))


def canonical_descriptor_bytes(descriptor: RuleDescriptor) -> bytes:
    """Serialize one descriptor canonically."""
    return (
        json.dumps(
            descriptor.canonical_document(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
