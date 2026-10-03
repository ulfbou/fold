"""Contract tests for canonical human and JSON renderers."""
from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

from fold import render
from fold.graph import evaluate


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


def test_explain_json_is_same_graph_and_deterministic(
    repository: Path,
) -> None:
    graph, envelope = evaluate(repository)
    first = render.render_explain_json(graph, envelope)
    second_graph, second_envelope = evaluate(repository)
    second = render.render_explain_json(second_graph, second_envelope)

    assert first == second

    document = json.loads(first)
    fields = {item["name"]: item for item in document["fields"]}
    explanations = {
        item["name"]: item for item in document["explanations"]
    }

    assert fields["head"]["provenance"]["provider"] == "git.head"

    status = explanations["status"]
    provenance = status["provenance"]
    descriptor = provenance["descriptor"]

    assert status["value"] == "ALIGNED"
    assert provenance["ruleId"] == "scope-drift"
    assert provenance["ruleVersion"] == "1.0"
    assert provenance["output"] == "ALIGNED"
    assert provenance["evaluatedInputs"] == [
        {"name": "drift_paths", "value": []},
    ]
    assert descriptor["ruleId"] == "scope-drift"
    assert descriptor["ruleVersion"] == "1.0"
    assert len(descriptor["evaluatorDigest"]) == 64

    drift_paths = provenance["inputs"][0]
    assert drift_paths["name"] == "drift_paths"
    leaf_names = {
        item["name"]
        for item in drift_paths["provenance"]["inputs"]
    }
    assert leaf_names == {"scope", "changes"}


def test_task_output_is_deterministic(repository: Path) -> None:
    (repository / "src" / "other.py").write_text("VALUE = 3\n", encoding="utf-8")
    first_graph, first_envelope = evaluate(repository)
    second_graph, second_envelope = evaluate(repository)
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


def test_explain_field_recursively_reaches_source_leaves(
    repository: Path,
) -> None:
    graph, _ = evaluate(repository)
    explanation = render.render_explain(graph, "status")

    assert explanation.startswith(
        "status\n"
        "  classification: derived\n"
        "  value: \"ALIGNED\"\n"
        "  rule: scope-drift@1.0\n"
    )
    assert "  evaluator_digest: " in explanation
    assert "  descriptor: {" in explanation
    assert "  evaluated_inputs:" in explanation
    assert "    drift_paths: []" in explanation
    assert "    drift_paths\n" in explanation
    assert "        scope\n" in explanation
    assert "          source: task\n" in explanation
    assert "        changes\n" in explanation
    assert "          source: git.changed_paths\n" in explanation
    assert explanation.endswith('  output: "ALIGNED"\n')


def test_human_and_json_explanations_share_recursive_semantics(
    repository: Path,
) -> None:
    graph, envelope = evaluate(repository)

    human = render.render_explain(graph, "drift_paths")
    document = json.loads(render.render_explain_json(graph, envelope))
    explanations = {item["name"]: item for item in document["explanations"]}
    recursive = explanations["drift_paths"]

    assert recursive["classification"] == "derived"
    assert recursive["value"] == []
    assert [item["name"] for item in recursive["provenance"]["inputs"]] == [
        "scope",
        "changes",
    ]

    assert "drift_paths\n" in human
    assert "  classification: derived\n" in human
    assert "  value: []\n" in human
    assert "    scope: [\"src\"]\n" in human
    assert "    changes: []\n" in human
    assert "    scope\n" in human
    assert "    changes\n" in human
