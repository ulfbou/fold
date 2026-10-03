"""Contract tests for Git recovery and porcelain-v2 parsing."""
from __future__ import annotations

from pathlib import Path

import pytest

from fold.errors import SourceUnavailableError
from fold.git import parse_porcelain_v2, recover_git_state
from fold.graph import evaluate
from fold.model import ChangeKind

from support import git


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


def test_empty_repository_has_targeted_head_error(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    git(root, "init", "-q")
    with pytest.raises(SourceUnavailableError, match="HEAD is unavailable"):
        recover_git_state(root)


def test_staged_unstaged_and_untracked_are_recovered(repository: Path) -> None:
    (repository / "src" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    git(repository, "add", "src/app.py")
    (repository / "src" / "other.py").write_text("VALUE = 3\n", encoding="utf-8")
    changes = evaluate(repository)[0].require("changes").value
    assert tuple(change.path for change in changes) == (
        "src/app.py",
        "src/other.py",
    )
    assert changes[0].index_kind is ChangeKind.MODIFIED
    assert changes[0].worktree_kind is ChangeKind.UNCHANGED
    assert changes[1].index_kind is ChangeKind.UNTRACKED
    assert changes[1].worktree_kind is ChangeKind.UNTRACKED
