"""Contract tests for the exact-identity rule registry."""
from __future__ import annotations

import json

import pytest

from fold.errors import InvariantError
from fold.graph import drift_paths
from fold.model import ChangeKind, ChangeRecord
from fold.rules import (
    canonical_descriptor_bytes,
    registered_rules,
    resolve_rule,
    semantic_implementation_digest,
)
from fold.task import TaskDeclaration


@pytest.mark.parametrize(
    ("original_path", "destination_path", "expected"),
    [
        ("outside/old.py", "src/new.py", ()),
        ("src/old.py", "outside/new.py", ("outside/new.py",)),
        ("outside/old.py", "other/new.py", ("other/new.py",)),
        ("src/old.py", "src/new.py", ()),
    ],
)
def test_rename_drift_uses_destination(
    original_path: str,
    destination_path: str,
    expected: tuple[str, ...],
) -> None:
    task = TaskDeclaration(
        schema_version="1.0",
        title="Rename",
        scope=("src",),
        tests=("python -m pytest",),
    )
    change = ChangeRecord(
        path=destination_path,
        index_kind=ChangeKind.RENAMED,
        worktree_kind=ChangeKind.UNCHANGED,
        original_path=original_path,
    )
    assert drift_paths(task, (change,)) == expected


def test_rule_registry_resolves_only_exact_identity() -> None:
    rule = resolve_rule("scope-drift", "1.0")

    assert rule.descriptor.rule_id == "scope-drift"
    assert rule.descriptor.rule_version == "1.0"
    assert rule.descriptor.inputs == ("scope", "changes")

    with pytest.raises(InvariantError, match="scope-drift@2.0"):
        resolve_rule("scope-drift", "2.0")

    with pytest.raises(InvariantError, match="unknown@1.0"):
        resolve_rule("unknown", "1.0")


def test_scope_drift_descriptor_is_canonical_and_digest_bound() -> None:
    rules = registered_rules()
    assert len(rules) == 1

    rule = rules[0]
    descriptor = rule.descriptor
    document = json.loads(canonical_descriptor_bytes(descriptor))

    assert document["ruleId"] == "scope-drift"
    assert document["ruleVersion"] == "1.0"
    assert document["inputs"] == ["scope", "changes"]
    assert document["policyConstants"] == {
        "deletionOutsideScopeCreatesDrift": False,
        "pathRelation": "equal-or-descendant-component-prefix",
    }
    assert descriptor.evaluator_digest == semantic_implementation_digest(
        rule.evaluator
    )
    assert len(descriptor.evaluator_digest) == 64


def test_registered_scope_drift_evaluator_preserves_existing_semantics() -> None:
    task = TaskDeclaration(
        schema_version="1.0",
        title="Registry",
        scope=("src",),
        tests=("python -m pytest",),
    )
    changes = (
        ChangeRecord(
            path="src/in.py",
            index_kind=ChangeKind.MODIFIED,
            worktree_kind=ChangeKind.UNCHANGED,
        ),
        ChangeRecord(
            path="outside/new.py",
            index_kind=ChangeKind.ADDED,
            worktree_kind=ChangeKind.UNCHANGED,
        ),
        ChangeRecord(
            path="outside/deleted.py",
            index_kind=ChangeKind.DELETED,
            worktree_kind=ChangeKind.UNCHANGED,
        ),
    )

    rule = resolve_rule("scope-drift", "1.0")

    assert rule.evaluator(task.scope, changes) == drift_paths(task, changes)
    assert rule.evaluator(task.scope, changes) == ("outside/new.py",)
