from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import FoldError, UsageError
from .graph import build_graph
from .render import render_explain, render_explain_json, render_task


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UsageError(message)


def parser() -> Parser:
    top = Parser(prog="fold")
    sub = top.add_subparsers(dest="command", required=True)
    task = sub.add_parser("task", help="render the merged working surface")
    task.add_argument("--check", action="store_true", help="exit 1 when drift is present")
    explain = sub.add_parser("explain", help="render provenance from the same graph")
    explain.add_argument("field", nargs="?", help="explain one field recursively")
    explain.add_argument("--json", action="store_true", help="render the complete graph as JSON")
    return top


def run(argv: list[str] | None = None, start: Path | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        graph = build_graph(start or Path.cwd())
        if args.command == "task":
            sys.stdout.write(render_task(graph))
            if args.check and graph.require("status").value == "DRIFTED":
                return 1
            return 0
        if args.json and args.field:
            raise UsageError("FIELD and --json are mutually exclusive")
        sys.stdout.write(render_explain_json(graph) if args.json else render_explain(graph, args.field))
        return 0
    except KeyError as exc:
        print(f"ERROR: unknown field: {exc.args[0]}", file=sys.stderr)
        return 2
    except FoldError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return exc.exit_code


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
