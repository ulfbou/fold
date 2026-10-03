from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from fold.cli import run
from fold.errors import InvariantError, SourceUnavailableError
from fold.git import parse_porcelain_v2
from fold.graph import build_envelope, evaluate
from fold.model import ChangeKind, FieldNode, ProvenanceGraph, SourceRef


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
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


def run_fold(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    return subprocess.run(
        [sys.executable, "-m", "fold", *args],
        cwd=root,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_porcelain_v2_preserves_semantic_records_and_spaces() -> None:
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


def test_envelope_is_computed_outside_the_field_graph(tmp_path: Path) -> None:
    graph, envelope = evaluate(repository(tmp_path))

    assert "envelope" not in graph.by_name()
    assert "declarative_backlog" not in graph.by_name()
    assert envelope.declared_field_count == sum(
        node.classification == "declared" for node in graph.nodes
    )
    assert envelope.recovered_field_count == sum(
        node.classification == "recovered" for node in graph.nodes
    )
    assert envelope.derived_field_count == sum(
        node.classification == "derived" for node in graph.nodes
    )
    assert envelope.derivation_count == envelope.derived_field_count
    assert envelope.compression_ratio == (
        envelope.recovered_field_count / envelope.declared_field_count
    )


def test_duplicate_and_unconsumed_fields_are_invariant_failures() -> None:
    node = FieldNode(
        name="unused",
        value=1,
        classification="recovered",
        provenance=SourceRef(kind="source", provider="test", locator="fixture"),
    )

    with pytest.raises(InvariantError, match="unconsumed"):
        build_envelope(ProvenanceGraph((node,)))
    with pytest.raises(InvariantError, match="duplicate"):
        build_envelope(ProvenanceGraph((node, node)))


def test_deletion_outside_scope_does_not_drift(tmp_path: Path) -> None:
    root = repository(tmp_path)
    (root / "outside.txt").write_text("tracked\n", encoding="utf-8")
    git(root, "add", "outside.txt")
    git(root, "commit", "-qm", "add outside path")
    (root / "outside.txt").unlink()
    (root / "src2.txt").write_text("drift\n", encoding="utf-8")

    graph, _ = evaluate(root)

    assert graph.require("drift_paths").value == ("src2.txt",)
    assert any(
        record.path == "outside.txt" and record.is_deletion
        for record in graph.require("changes").value
    )


def test_cli_exit_codes_and_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = repository(tmp_path)
    assert run(["task"], root) == 0
    assert run(["task", "--check"], root) == 0
    assert run(["explain", "missing"], root) == 2
    assert run([], root) == 2
    assert run(["--version"], root) == 0

    (root / "outside.txt").write_text("drift\n", encoding="utf-8")
    assert run(["task", "--check"], root) == 1

    (root / ".fold" / "task.json").write_text("{}", encoding="utf-8")
    assert run(["task"], root) == 3

    def unavailable(_: Path) -> object:
        raise SourceUnavailableError("unavailable")

    monkeypatch.setattr("fold.graph.recover_git_state", unavailable)
    assert run(["task"], root) == 4

    def invalid(_: Path) -> object:
        raise InvariantError("invalid")

    monkeypatch.setattr("fold.cli.evaluate", invalid)
    assert run(["task"], root) == 5


def test_canonical_outputs_are_cross_process_deterministic(tmp_path: Path) -> None:
    root = repository(tmp_path)
    for arguments in (("task",), ("explain", "status"), ("explain", "--json")):
        first = run_fold(root, *arguments)
        second = run_fold(root, *arguments)
        assert first.returncode == second.returncode == 0
        assert first.stdout == second.stdout


def test_renderer_consumer_contract_matches_named_task_reads() -> None:
    """The declared task consumers must match direct renderer field reads."""
    import ast
    import inspect

    from fold import render

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


def test_unconsumed_recoveries_are_a_valid_envelope_sentinel(
    tmp_path: Path,
) -> None:
    _, envelope = evaluate(repository(tmp_path))

    assert envelope.unconsumed_recoveries == ()


def test_fold_compression_ratio_handles_zero_declared_fields() -> None:
    from fold.graph import compression_ratio

    assert compression_ratio(recovered_count=0, declared_count=0) is None


@pytest.mark.parametrize(
    ("original_path", "destination_path", "expected_drift"),
    [
        ("outside/old.py", "src/new.py", ()),
        ("src/old.py", "outside/new.py", ("outside/new.py",)),
        ("outside/old.py", "other/new.py", ("other/new.py",)),
        ("src/old.py", "src/new.py", ()),
    ],
)
def test_rename_drift_uses_destination_and_deletion_semantics(
    original_path: str,
    destination_path: str,
    expected_drift: tuple[str, ...],
) -> None:
    from fold.graph import drift_paths
    from fold.model import ChangeRecord
    from fold.task import TaskDeclaration

    task = TaskDeclaration(
        schema_version="1.0",
        title="Rename fixture",
        scope=("src",),
        tests=("python -m pytest",),
    )
    change = ChangeRecord(
        path=destination_path,
        index_kind=ChangeKind.RENAMED,
        worktree_kind=ChangeKind.UNCHANGED,
        original_path=original_path,
    )

    assert drift_paths(task, (change,)) == expected_drift


def test_task_loader_rejects_unknown_fields(tmp_path: Path) -> None:
    from fold.errors import TaskDeclarationError
    from fold.task import load_task

    root = repository(tmp_path)
    task_path = root / ".fold" / "task.json"
    document = json.loads(task_path.read_text(encoding="utf-8"))
    document["unknown"] = True
    task_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(TaskDeclarationError, match="task fields differ"):
        load_task(root)


def test_task_loader_deduplicates_normalized_scope_and_tests(
    tmp_path: Path,
) -> None:
    from fold.task import load_task

    root = repository(tmp_path)
    task_path = root / ".fold" / "task.json"
    document = {
        "schemaVersion": "1.0",
        "title": "Duplicates",
        "scope": ["src/", "src"],
        "tests": ["python -m pytest", "python -m pytest"],
    }
    task_path.write_text(json.dumps(document), encoding="utf-8")

    task = load_task(root)

    assert task.scope == ("src",)
    assert task.tests == ("python -m pytest",)


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        b'{"schemaVersion":"2.0","title":"T","scope":["src"],'
        b'"tests":["python -m pytest"]}',
        b'{"schemaVersion":"1.0","title":"T","scope":["../src"],'
        b'"tests":["python -m pytest"]}',
        b"\xff",
    ],
)
def test_task_loader_rejects_invalid_contracts(
    tmp_path: Path,
    payload: bytes,
) -> None:
    from fold.errors import TaskDeclarationError
    from fold.task import load_task

    root = repository(tmp_path)
    (root / ".fold" / "task.json").write_bytes(payload)

    with pytest.raises(TaskDeclarationError):
        load_task(root)


def test_task_loader_rejects_missing_file(tmp_path: Path) -> None:
    from fold.errors import TaskDeclarationError
    from fold.task import load_task

    root = repository(tmp_path)
    (root / ".fold" / "task.json").unlink()

    with pytest.raises(TaskDeclarationError, match="missing or unsafe"):
        load_task(root)


def test_explain_field_and_json_are_mutually_exclusive(tmp_path: Path) -> None:
    root = repository(tmp_path)

    assert run(["explain", "status", "--json"], root) == 2


def test_version_does_not_evaluate_repository_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail_if_called(_: Path) -> object:
        raise AssertionError("evaluate must not run for --version")

    monkeypatch.setattr("fold.cli.evaluate", fail_if_called)

    assert run(["--version"], tmp_path) == 0
