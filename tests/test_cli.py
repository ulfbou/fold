"""Contract tests for the Fold command-line interface."""
from __future__ import annotations

from pathlib import Path

import pytest

from fold.cli import run
from fold.errors import InvariantError, SourceUnavailableError
from fold.model import DerivedRef, FieldNode
from fold.task import TaskDeclaration

from support import run_fold


def test_cli_contracts_and_version_short_circuit(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run(["explain", "missing"], repository) == 2
    assert run(["explain", "status", "--json"], repository) == 2

    def fail_if_called(_: Path) -> object:
        raise AssertionError("evaluate must not run for --version")

    monkeypatch.setattr("fold.cli.evaluate", fail_if_called)
    assert run(["--version"], repository) == 0


def test_canonical_outputs_are_cross_process_deterministic(
    repository: Path,
) -> None:
    for arguments in (("task",), ("explain", "status"), ("explain", "--json")):
        first = run_fold(repository, *arguments)
        second = run_fold(repository, *arguments)
        assert first.returncode == second.returncode == 0
        assert first.stdout == second.stdout


def test_drift_warns_and_check_fails(repository: Path) -> None:
    (repository / "outside.txt").write_text("drift\n", encoding="utf-8")
    plain = run_fold(repository, "task")
    checked = run_fold(repository, "task", "--check")
    assert plain.returncode == 0
    assert checked.returncode == 1
    assert plain.stdout == checked.stdout
    assert b"STATUS: DRIFTED" in plain.stdout
    assert b"outside.txt" in plain.stdout


def test_task_check_exit_zero_when_aligned(repository: Path) -> None:
    result = run_fold(repository, "task", "--check")
    assert result.returncode == 0
    assert b"STATUS: ALIGNED" in result.stdout


def test_exit_codes_two_through_five_have_focused_evidence(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run(["explain", "missing"], repository) == 2

    (repository / ".fold" / "task.json").write_text(
        "not json\n", encoding="utf-8"
    )
    assert run(["task"], repository) == 3

    def source_failure(_: Path) -> object:
        raise SourceUnavailableError("source unavailable")

    monkeypatch.setattr("fold.cli.evaluate", source_failure)
    assert run(["task"], repository) == 4

    def invariant_failure(_: Path) -> object:
        raise InvariantError("invariant failure")

    monkeypatch.setattr("fold.cli.evaluate", invariant_failure)
    assert run(["task"], repository) == 5


@pytest.mark.parametrize(
    "arguments",
    (
        ("task", "--check"),
        ("explain", "broken"),
    ),
)
def test_invalid_graph_fails_before_renderer_or_gate_consumption(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    arguments: tuple[str, ...],
) -> None:
    invalid = (
        FieldNode(
            name="broken",
            value=(),
            classification="derived",
            provenance=DerivedRef(
                kind="derived",
                rule_id="scope-drift",
                rule_version="1.0",
                inputs=("missing",),
            ),
        ),
    )

    def invalid_nodes(
        task: TaskDeclaration,
        git_state: object,
    ) -> tuple[FieldNode, ...]:
        return invalid

    monkeypatch.setattr("fold.graph.build_nodes", invalid_nodes)

    assert run(list(arguments), repository) == 5
