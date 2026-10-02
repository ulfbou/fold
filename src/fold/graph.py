from __future__ import annotations

from pathlib import Path

from .git import GitState, recover_git_state
from .model import DerivedRef, FieldNode, ProvenanceGraph, SourceRef
from .task import TaskDeclaration, load_task

DRIFT_RULE_ID = "scope-drift"
DRIFT_RULE_VERSION = "1.0"
METRICS_RULE_ID = "fold-metrics"
METRICS_RULE_VERSION = "1.0"


def _inside(path: str, scope: str) -> bool:
    return path == scope or path.startswith(scope + "/")


def drift_paths(task: TaskDeclaration, git: GitState) -> tuple[str, ...]:
    outside = [path for path in git.changed_paths if not any(_inside(path, scope) for scope in task.scope)]
    return tuple(sorted(outside))


def build_graph(start: Path) -> ProvenanceGraph:
    git = recover_git_state(start)
    task = load_task(git.root)
    outside = drift_paths(task, git)
    declared = 3
    recovered = 4
    nodes = (
        FieldNode("schema_version", task.schema_version, "declared", SourceRef("source", "task", ".fold/task.json#/schemaVersion")),
        FieldNode("title", task.title, "declared", SourceRef("source", "task", ".fold/task.json#/title")),
        FieldNode("scope", task.scope, "declared", SourceRef("source", "task", ".fold/task.json#/scope")),
        FieldNode("tests", task.tests, "declared", SourceRef("source", "task", ".fold/task.json#/tests")),
        FieldNode("repository_root", git.root.as_posix(), "recovered", SourceRef("source", "git.repository_root", "git.repository_root")),
        FieldNode("head", git.head, "recovered", SourceRef("source", "git.head", "git.head")),
        FieldNode("branch", git.branch, "recovered", SourceRef("source", "git.branch", "git.branch")),
        FieldNode("changed_paths", git.changed_paths, "recovered", SourceRef("source", "git.changed_paths", "git.changed_paths")),
        FieldNode("deleted_paths", git.deleted_paths, "recovered", SourceRef("source", "git.changed_paths", "git.deleted_paths")),
        FieldNode("drift_paths", outside, "derived", DerivedRef("derived", DRIFT_RULE_ID, DRIFT_RULE_VERSION, ("scope", "changed_paths"))),
        FieldNode("status", "DRIFTED" if outside else "ALIGNED", "derived", DerivedRef("derived", DRIFT_RULE_ID, DRIFT_RULE_VERSION, ("drift_paths",))),
        FieldNode("compression_ratio", recovered / declared, "derived", DerivedRef("derived", METRICS_RULE_ID, METRICS_RULE_VERSION, ("title", "scope", "tests", "repository_root", "head", "branch", "changed_paths"))),
        FieldNode("derivation_count", 4, "derived", DerivedRef("derived", METRICS_RULE_ID, METRICS_RULE_VERSION, ("drift_paths", "status", "compression_ratio", "declarative_backlog"))),
        FieldNode("declarative_backlog", 0, "derived", DerivedRef("derived", METRICS_RULE_ID, METRICS_RULE_VERSION, ())),
    )
    return ProvenanceGraph(tuple(sorted(nodes, key=lambda node: node.name)))
