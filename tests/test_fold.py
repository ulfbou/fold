from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from fold import render
from fold.cli import run
from fold.errors import InvariantError, SourceUnavailableError, TaskDeclarationError
from fold.git import parse_porcelain_v2, recover_git_state
from fold.graph import build_envelope, compression_ratio, drift_paths, evaluate
from fold.model import ChangeKind, ChangeRecord, FieldNode, ProvenanceGraph, SourceRef
from fold.task import TaskDeclaration, load_task


def git(root: Path, *arguments: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )
    return result.stdout.strip()


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.invalid")
    (root / ".fold").mkdir()
    task = {
        "schemaVersion": "1.0",
        "title": "Test task",
        "scope": ["src"],
        "tests": ["python -m pytest"],
    }
    (root / ".fold" / "task.json").write_text(
        json.dumps(task, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "baseline")
    return root


def run_fold(root: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    return subprocess.run(
        [sys.executable, "-m", "fold", *arguments],
        cwd=root,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_porcelain_v2_preserves_all_semantic_record_kinds() -> None:
    data = (
        b"? z space.txt\0"
        b"1 MM N... 100644 100644 100644 a b src/both space.py\0"
        b"1 D. N... 100644 000000 000000 a b gone\0"
        b"2 R. N... 100644 100644 100644 a b R100 new name\0old name\0"
        b"u UU N... 100644 100644 100644 100644 a b c conflict file\0"
    )

    records = parse_porcelain_v2(data)
    by_path = {record.path: record for record in records}

    assert [record.path for record in records] == sorted(by_path)
    assert by_path["src/both space.py"].status_pair == "MM"
    assert by_path["new name"].original_path == "old name"
    assert by_path["gone"].is_deletion
    assert by_path["conflict file"].unmerged
    assert by_path["z space.txt"].index_kind is ChangeKind.UNTRACKED


@pytest.mark.parametrize("data", [b"1 bad\0", b"2 R. x\0", b"! nope\0", b"?\0"])
def test_porcelain_v2_rejects_malformed_records(data: bytes) -> None:
    with pytest.raises(SourceUnavailableError):
        parse_porcelain_v2(data)


def test_renderer_consumer_contract_matches_named_reads() -> None:
    """Direct reads must stay in render_task for this AST contract."""
    tree = ast.parse(inspect.getsource(render.render_task))
    direct_reads = {
        node.slice.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "nodes"
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    }

    assert direct_reads == set(render.RENDER_CONSUMES["task"])


def test_envelope_is_graph_derived_and_rejects_unconsumed_fields(
    tmp_path: Path,
) -> None:
    graph, envelope = evaluate(repository(tmp_path))
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


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        b'{"schemaVersion":"2.0","title":"T","scope":["src"],"tests":[]}',
        b'{"schemaVersion":"1.0","title":"T","scope":["../src"],"tests":[]}',
        b"\xff",
    ],
)
def test_task_loader_rejects_invalid_artifacts(
    tmp_path: Path,
    payload: bytes,
) -> None:
    root = repository(tmp_path)
    (root / ".fold" / "task.json").write_bytes(payload)
    with pytest.raises(TaskDeclarationError):
        load_task(root)


def test_task_loader_preserves_commands_and_rejects_unknown_fields(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    path = root / ".fold" / "task.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["tests"] = ['pytest -k "unit"']
    path.write_text(json.dumps(document), encoding="utf-8")
    assert load_task(root).tests == ('pytest -k "unit"',)

    document["unknown"] = True
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(TaskDeclarationError, match="task fields differ"):
        load_task(root)


def test_empty_repository_has_targeted_head_error(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    git(root, "init", "-q")
    with pytest.raises(SourceUnavailableError, match="HEAD is unavailable"):
        recover_git_state(root)


def test_cli_contracts_and_version_short_circuit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = repository(tmp_path)
    assert run(["explain", "missing"], root) == 2
    assert run(["explain", "status", "--json"], root) == 2

    def fail_if_called(_: Path) -> object:
        raise AssertionError("evaluate must not run for --version")

    monkeypatch.setattr("fold.cli.evaluate", fail_if_called)
    assert run(["--version"], tmp_path) == 0


def test_canonical_outputs_are_cross_process_deterministic(tmp_path: Path) -> None:
    root = repository(tmp_path)
    for arguments in (("task",), ("explain", "status"), ("explain", "--json")):
        first = run_fold(root, *arguments)
        second = run_fold(root, *arguments)
        assert first.returncode == second.returncode == 0
        assert first.stdout == second.stdout


def test_graph_has_declared_recovered_and_derived_nodes(tmp_path: Path) -> None:
    root = repository(tmp_path)
    (root / "src" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    graph, _ = evaluate(root)
    nodes = graph.by_name()
    assert nodes["title"].classification == "declared"
    assert nodes["head"].classification == "recovered"
    assert nodes["status"].classification == "derived"
    assert nodes["status"].value == "ALIGNED"


def test_drift_warns_and_check_fails(tmp_path: Path) -> None:
    root = repository(tmp_path)
    (root / "outside.txt").write_text("drift\n", encoding="utf-8")
    plain = run_fold(root, "task")
    checked = run_fold(root, "task", "--check")
    assert plain.returncode == 0
    assert checked.returncode == 1
    assert plain.stdout == checked.stdout
    assert b"STATUS: DRIFTED" in plain.stdout
    assert b"outside.txt" in plain.stdout


def test_staged_unstaged_and_untracked_are_recovered(tmp_path: Path) -> None:
    root = repository(tmp_path)
    (root / "src" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    git(root, "add", "src/app.py")
    (root / "src" / "other.py").write_text("VALUE = 3\n", encoding="utf-8")
    changes = evaluate(root)[0].require("changes").value
    assert tuple(change.path for change in changes) == (
        "src/app.py",
        "src/other.py",
    )
    assert changes[0].index_kind is ChangeKind.MODIFIED
    assert changes[0].worktree_kind is ChangeKind.UNCHANGED
    assert changes[1].index_kind is ChangeKind.UNTRACKED
    assert changes[1].worktree_kind is ChangeKind.UNTRACKED


def test_explain_json_is_same_graph_and_deterministic(tmp_path: Path) -> None:
    root = repository(tmp_path)
    graph, envelope = evaluate(root)
    first = render.render_explain_json(graph, envelope)
    second_graph, second_envelope = evaluate(root)
    second = render.render_explain_json(second_graph, second_envelope)
    assert first == second
    document = json.loads(first)
    fields = {item["name"]: item for item in document["fields"]}
    assert fields["head"]["provenance"]["provider"] == "git.head"
    assert fields["status"]["provenance"] == {
        "inputs": ["drift_paths"],
        "kind": "derived",
        "ruleId": "scope-drift",
        "ruleVersion": "1.0",
    }


def test_task_output_is_deterministic(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    (root / "src" / "other.py").write_text("VALUE = 3\n", encoding="utf-8")
    first_graph, first_envelope = evaluate(root)
    second_graph, second_envelope = evaluate(root)
    first = render.render_task(first_graph, first_envelope)
    second = render.render_task(second_graph, second_envelope)
    assert first == second
    assert "ACTUAL CHANGES\n  src/other.py\n" in first
    assert "?? src/other.py" not in first
    assert all(
        heading in first
        for heading in (
            "TITLE",
            "REPOSITORY",
            "DECLARED SCOPE",
            "ACTUAL CHANGES",
            "DRIFT",
            "VERIFICATION",
            "METRICS",
        )
    )


def test_explain_field_recursively_reaches_source_leaves(tmp_path: Path) -> None:
    graph, _ = evaluate(repository(tmp_path))
    explanation = render.render_explain(graph, "status")
    assert explanation == (
        "status\n"
        "  classification: derived\n"
        "  rule: scope-drift@1.0\n"
        "  inputs:\n"
        "    drift_paths\n"
        "      classification: derived\n"
        "      rule: scope-drift@1.0\n"
        "      inputs:\n"
        "        scope\n"
        "          classification: declared\n"
        "          source: task\n"
        "          locator: .fold/task.json#/scope\n"
        "        changes\n"
        "          classification: recovered\n"
        "          source: git.changed_paths\n"
        "          locator: working tree and index\n"
    )


def test_envelope_recomputation_is_byte_identical_and_mismatch_fails(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    from fold.graph import verify_envelope

    graph, envelope = evaluate(repository(tmp_path))
    first = render.canonical_envelope_bytes(build_envelope(graph))
    second = render.canonical_envelope_bytes(build_envelope(graph))
    assert first == second
    assert envelope.derived_field_count == 2
    assert envelope.derivation_count == 2
    mismatched = replace(envelope, derivation_count=3)
    with pytest.raises(InvariantError, match="envelope differs"):
        verify_envelope(graph, mismatched)


def test_task_check_exit_zero_when_aligned(tmp_path: Path) -> None:
    result = run_fold(repository(tmp_path), "task", "--check")
    assert result.returncode == 0
    assert b"STATUS: ALIGNED" in result.stdout


def test_exit_codes_two_through_five_have_focused_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = repository(tmp_path)
    assert run(["explain", "missing"], root) == 2

    (root / ".fold" / "task.json").write_text("not json\n", encoding="utf-8")
    assert run(["task"], root) == 3

    def source_failure(_: Path) -> object:
        raise SourceUnavailableError("source unavailable")

    monkeypatch.setattr("fold.cli.evaluate", source_failure)
    assert run(["task"], root) == 4

    def invariant_failure(_: Path) -> object:
        raise InvariantError("invariant failure")

    monkeypatch.setattr("fold.cli.evaluate", invariant_failure)
    assert run(["task"], root) == 5


def test_rule_registry_resolves_only_exact_identity() -> None:
    from fold.rules import resolve_rule

    rule = resolve_rule("scope-drift", "1.0")

    assert rule.descriptor.rule_id == "scope-drift"
    assert rule.descriptor.rule_version == "1.0"
    assert rule.descriptor.inputs == ("scope", "changes")

    with pytest.raises(InvariantError, match="scope-drift@2.0"):
        resolve_rule("scope-drift", "2.0")

    with pytest.raises(InvariantError, match="unknown@1.0"):
        resolve_rule("unknown", "1.0")


def test_scope_drift_descriptor_is_canonical_and_digest_bound() -> None:
    from fold.rules import (
        canonical_descriptor_bytes,
        registered_rules,
        semantic_implementation_digest,
    )

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
    from fold.rules import resolve_rule

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


def test_graph_validation_rejects_duplicate_names() -> None:
    from fold.graph import validate_graph

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
    from fold.graph import validate_graph
    from fold.model import DerivedRef

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
    from fold.graph import validate_graph
    from fold.model import DerivedRef

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
    from fold.graph import validate_graph
    from fold.model import DerivedRef

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
