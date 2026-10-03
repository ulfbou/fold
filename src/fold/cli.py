"""Fold command-line interface."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .errors import FoldError, UsageError
from .graph import evaluate
from .render import render_explain, render_explain_json, render_task


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UsageError(message)


def build_parser() -> Parser:
    parser = Parser(prog="fold")
    parser.add_argument("--version", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    task = subparsers.add_parser("task", help="render the working surface")
    task.add_argument("--check", action="store_true", help="exit 1 on drift")

    explain = subparsers.add_parser("explain", help="render direct provenance")
    explain.add_argument("field", nargs="?", help="field to explain")
    explain.add_argument("--json", action="store_true", help="render graph JSON")
    return parser


def run(argv: list[str] | None = None, start: Path | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
        if arguments.version:
            sys.stdout.write(f"fold {__version__}\n")
            return 0
        if arguments.command is None:
            raise UsageError("a command is required")

        graph, envelope = evaluate(start or Path.cwd())
        if arguments.command == "task":
            sys.stdout.write(render_task(graph, envelope))
            if arguments.check and graph.require("status").value == "DRIFTED":
                return 1
            return 0

        if arguments.json and arguments.field:
            raise UsageError("FIELD and --json are mutually exclusive")
        output = (
            render_explain_json(graph, envelope)
            if arguments.json
            else render_explain(graph, arguments.field)
        )
        sys.stdout.write(output)
        return 0
    except FoldError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return exc.exit_code


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
