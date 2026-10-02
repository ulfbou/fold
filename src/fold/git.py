from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .errors import SourceUnavailableError


@dataclass(frozen=True)
class GitState:
    root: Path
    head: str
    branch: str
    changed_paths: tuple[str, ...]
    deleted_paths: tuple[str, ...]


def _run(root: Path, *args: str) -> bytes:
    try:
        process = subprocess.run(
            ["git", *args], cwd=root, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False,
        )
    except FileNotFoundError as exc:
        raise SourceUnavailableError("git executable is unavailable") from exc
    if process.returncode:
        detail = process.stderr.decode("utf-8", "replace").strip()
        raise SourceUnavailableError(f"git {' '.join(args)} failed: {detail}")
    return process.stdout


def repository_root(start: Path) -> Path:
    value = _run(start, "rev-parse", "--show-toplevel").decode("utf-8", "strict").strip()
    return Path(value).resolve()


def _normalize(raw: bytes) -> str:
    text = raw.decode("utf-8", "strict")
    path = PurePosixPath(text.replace("\\", "/"))
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise SourceUnavailableError(f"git returned an unsafe path: {text!r}")
    return path.as_posix()


def _changed_paths(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    records = _run(root, "status", "--porcelain=v2", "-z", "--untracked-files=all").split(b"\0")
    changed: set[str] = set()
    deleted: set[str] = set()
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        tag = record[:1]
        if tag == b"?":
            changed.add(_normalize(record[2:]))
            continue
        fields = record.split(b" ")
        if tag == b"1" and len(fields) >= 9:
            status = fields[1].decode("ascii", "strict")
            path = _normalize(fields[8])
        elif tag == b"2" and len(fields) >= 10:
            status = fields[1].decode("ascii", "strict")
            path = _normalize(fields[9])
            if index < len(records):
                index += 1
        elif tag == b"u" and len(fields) >= 11:
            status = fields[1].decode("ascii", "strict")
            path = _normalize(fields[10])
        else:
            raise SourceUnavailableError("git status returned an unsupported porcelain-v2 record")
        if "D" in status:
            deleted.add(path)
        else:
            changed.add(path)
    return tuple(sorted(changed)), tuple(sorted(deleted))


def recover_git_state(start: Path) -> GitState:
    root = repository_root(start)
    head = _run(root, "rev-parse", "HEAD").decode("ascii", "strict").strip()
    branch = _run(root, "branch", "--show-current").decode("utf-8", "strict").strip() or "(detached)"
    changed, deleted = _changed_paths(root)
    return GitState(root, head, branch, changed, deleted)
