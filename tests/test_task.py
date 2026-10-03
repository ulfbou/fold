"""Contract tests for the repository task declaration loader."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from fold.errors import TaskDeclarationError
from fold.task import load_task


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
    repository: Path,
    payload: bytes,
) -> None:
    (repository / ".fold" / "task.json").write_bytes(payload)
    with pytest.raises(TaskDeclarationError):
        load_task(repository)


def test_task_loader_preserves_commands_and_rejects_unknown_fields(
    repository: Path,
) -> None:
    path = repository / ".fold" / "task.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["tests"] = ['pytest -k "unit"']
    path.write_text(json.dumps(document), encoding="utf-8")
    assert load_task(repository).tests == ('pytest -k "unit"',)

    document["unknown"] = True
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(TaskDeclarationError, match="task fields differ"):
        load_task(repository)
