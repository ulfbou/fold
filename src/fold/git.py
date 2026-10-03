"""Deterministic recovery of semantic Git change records."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .errors import SourceUnavailableError
from .model import ChangeKind, ChangeRecord

PORCELAIN_V2_ARGS = ("status", "--porcelain=v2", "-z", "--untracked-files=all")
_RECORD_FIELD_LIMITS = {b"1": 8, b"2": 9, b"u": 10}


@dataclass(frozen=True)
class GitState:
    root: Path
    head: str
    branch: str
    changes: tuple[ChangeRecord, ...]


def run_git(root: Path, *args: str) -> bytes:
    """Run Git and map execution failures to the source error contract."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SourceUnavailableError("git executable is unavailable") from exc

    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise SourceUnavailableError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def repository_root(start: Path) -> Path:
    output = run_git(start, "rev-parse", "--show-toplevel")
    return Path(output.decode("utf-8", "strict").strip()).resolve()


def normalize_path(raw_path: bytes) -> str:
    """Decode and validate one repository-relative path from Git."""
    try:
        text = raw_path.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise SourceUnavailableError(f"git returned a non-UTF-8 path: {exc}") from exc

    path = PurePosixPath(text.replace("\\", "/"))
    invalid = path.is_absolute() or any(
        part in {"", ".", ".."} for part in path.parts
    )
    if invalid:
        raise SourceUnavailableError(f"git returned an unsafe path: {text!r}")
    return path.as_posix()


def parse_status(raw_status: bytes) -> tuple[ChangeKind, ChangeKind]:
    """Parse the two-character porcelain-v2 XY status field."""
    if len(raw_status) != 2:
        raise SourceUnavailableError(
            f"malformed porcelain-v2 status field: {raw_status!r}"
        )
    try:
        return ChangeKind(chr(raw_status[0])), ChangeKind(chr(raw_status[1]))
    except ValueError as exc:
        raise SourceUnavailableError(
            f"unknown porcelain-v2 status: {raw_status!r}"
        ) from exc


def parse_porcelain_v2(data: bytes) -> tuple[ChangeRecord, ...]:
    """Parse one NUL-delimited porcelain-v2 observation."""
    segments = data.split(b"\0")
    records: list[ChangeRecord] = []
    index = 0

    while index < len(segments):
        segment = segments[index]
        index += 1
        if not segment:
            continue

        tag = segment[:1]
        if tag == b"?":
            if segment[1:2] != b" " or len(segment) < 3:
                raise SourceUnavailableError(
                    "malformed porcelain-v2 untracked record"
                )
            records.append(
                ChangeRecord(
                    path=normalize_path(segment[2:]),
                    index_kind=ChangeKind.UNTRACKED,
                    worktree_kind=ChangeKind.UNTRACKED,
                )
            )
            continue

        field_limit = _RECORD_FIELD_LIMITS.get(tag)
        if field_limit is None:
            raise SourceUnavailableError(
                f"unsupported porcelain-v2 record: {tag!r}"
            )
        parts = segment.split(b" ", field_limit)
        if len(parts) != field_limit + 1:
            raise SourceUnavailableError(
                f"malformed porcelain-v2 record type {tag.decode()}"
            )

        index_kind, worktree_kind = parse_status(parts[1])
        original_path = None
        if tag == b"2":
            if index >= len(segments) or not segments[index]:
                raise SourceUnavailableError(
                    "rename record is missing its original path"
                )
            original_path = normalize_path(segments[index])
            index += 1

        records.append(
            ChangeRecord(
                path=normalize_path(parts[-1]),
                index_kind=index_kind,
                worktree_kind=worktree_kind,
                original_path=original_path,
                unmerged=tag == b"u",
            )
        )

    return tuple(sorted(records, key=ChangeRecord.sort_key))


def recover_git_state(start: Path) -> GitState:
    root = repository_root(start)
    try:
        head = run_git(root, "rev-parse", "HEAD").decode("ascii", "strict").strip()
    except SourceUnavailableError as exc:
        raise SourceUnavailableError(
            "Git HEAD is unavailable; the repository may have no commits"
        ) from exc

    branch = (
        run_git(root, "branch", "--show-current")
        .decode("utf-8", "strict")
        .strip()
        or "(detached)"
    )
    changes = parse_porcelain_v2(run_git(root, *PORCELAIN_V2_ARGS))
    return GitState(root=root, head=head, branch=branch, changes=changes)
