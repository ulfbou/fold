from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .errors import TaskDeclarationError


@dataclass(frozen=True)
class TaskDeclaration:
    schema_version: str
    title: str
    scope: tuple[str, ...]
    tests: tuple[str, ...]


def _path(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise TaskDeclarationError(f"{location} must be non-empty text")
    normalized = value.replace("\\", "/").rstrip("/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise TaskDeclarationError(f"{location} is not a safe repository-relative path: {value!r}")
    return path.as_posix()


def load_task(root: Path) -> TaskDeclaration:
    path = root / ".fold" / "task.json"
    if path.is_symlink() or not path.is_file():
        raise TaskDeclarationError(f"missing or unsafe task declaration: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TaskDeclarationError(f"invalid task declaration: {exc}") from exc
    if not isinstance(raw, dict):
        raise TaskDeclarationError("task declaration must be an object")
    expected = {"schemaVersion", "title", "scope", "tests"}
    if set(raw) != expected:
        raise TaskDeclarationError(f"task fields differ; expected {sorted(expected)}")
    if raw["schemaVersion"] != "1.0":
        raise TaskDeclarationError(f"unsupported task schema: {raw['schemaVersion']!r}")
    if not isinstance(raw["title"], str) or not raw["title"].strip():
        raise TaskDeclarationError("title must be non-empty text")
    if not isinstance(raw["scope"], list) or not raw["scope"]:
        raise TaskDeclarationError("scope must be a non-empty array")
    if not isinstance(raw["tests"], list) or any(not isinstance(item, str) or not item for item in raw["tests"]):
        raise TaskDeclarationError("tests must be an array of non-empty strings")
    scope = tuple(sorted(dict.fromkeys(_path(item, "scope item") for item in raw["scope"])))
    tests = tuple(sorted(dict.fromkeys(raw["tests"])))
    return TaskDeclaration("1.0", raw["title"].strip(), scope, tests)
