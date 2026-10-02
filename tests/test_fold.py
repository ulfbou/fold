from __future__ import annotations

import json
import subprocess
from pathlib import Path

from fold.cli import run
from fold.graph import build_graph
from fold.render import render_explain_json, render_task


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return result.stdout.strip()


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.invalid")
    (root / ".fold").mkdir()
    (root / ".fold" / "task.json").write_text(json.dumps({
        "schemaVersion": "1.0",
        "title": "Test task",
        "scope": ["src"],
        "tests": ["python -m pytest"],
    }, indent=2) + "\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "baseline")
    return root


def test_graph_has_declared_recovered_and_derived_nodes(tmp_path: Path):
    root = repository(tmp_path)
    (root / "src" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    graph = build_graph(root)
    nodes = graph.by_name()
    assert nodes["title"].classification == "declared"
    assert nodes["head"].classification == "recovered"
    assert nodes["status"].classification == "derived"
    assert nodes["status"].value == "ALIGNED"


def test_drift_warns_and_check_fails(tmp_path: Path, capsys):
    root = repository(tmp_path)
    (root / "outside.txt").write_text("drift\n", encoding="utf-8")
    assert run(["task"], root) == 0
    plain = capsys.readouterr().out
    assert "STATUS: DRIFTED" in plain
    assert "outside.txt" in plain
    assert run(["task", "--check"], root) == 1
    checked = capsys.readouterr().out
    assert checked == plain


def test_staged_unstaged_and_untracked_are_recovered(tmp_path: Path):
    root = repository(tmp_path)
    (root / "src" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    git(root, "add", "src/app.py")
    (root / "src" / "other.py").write_text("VALUE = 3\n", encoding="utf-8")
    changed = build_graph(root).require("changed_paths").value
    assert changed == ("src/app.py", "src/other.py")


def test_explain_json_is_same_graph_and_deterministic(tmp_path: Path):
    root = repository(tmp_path)
    graph = build_graph(root)
    first = render_explain_json(graph)
    second = render_explain_json(build_graph(root))
    assert first == second
    document = json.loads(first)
    fields = {item["name"]: item for item in document["fields"]}
    assert fields["head"]["provenance"]["provider"] == "git.head"
    assert fields["status"]["provenance"]["ruleId"] == "scope-drift"


def test_task_output_is_deterministic(tmp_path: Path):
    root = repository(tmp_path)
    assert render_task(build_graph(root)) == render_task(build_graph(root))
