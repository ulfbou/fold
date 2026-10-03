# Fold

Fold compresses declared collaboration state into a minimal working surface and reconstructs every rendered field from its declared source or a named, versioned derivation.

No hidden inference. No hidden state. No unrecoverable decisions.

## Milestone 0

Fold combines a versioned task declaration with Git repository state, builds one provenance graph, and renders that graph as a working view or an explanation. The same graph drives the drift gate.

```bash
python -m fold task
python -m fold explain
python -m fold explain --json
python -m fold task --check
```

## Architecture

1. **Schema**: `.fold/task.json` declares remembered state. Its silences are deliberate.
2. **Renderer**: `fold task` and `fold explain` render the same provenance graph.
3. **Gate**: `fold task --check` fails when an actual changed path is outside declared scope.

Fields are classified as:

- **Declared**: read from `.fold/task.json`.
- **Recovered**: deterministically read from an authoritative source such as Git.
- **Derived**: computed by a named, versioned rule from graph inputs.

## Drift contract

Declared scope is an allowed-prefix set. Staged, unstaged, untracked, renamed, and deleted paths reported by `git status --porcelain=v2 -z` are actual changes. A deletion outside declared scope is ignored. Every other actual changed path must equal a declared scope path or be beneath one. Declared scope may be broader than actual changes.

Plain `fold task` renders `DRIFTED` and continues. `fold task --check` renders the same deterministic view and exits `1` when drift exists.

## Explanation contract

`fold explain FIELD` reports the field classification and its direct source or
direct derivation inputs. Recursive traversal and equivalent recursive human
and JSON explanations remain M1B scope. `fold explain --json` serializes the
complete current graph and envelope deterministically.

## Exit codes

- `0`: success
- `1`: drift detected under `task --check`
- `2`: usage error
- `3`: missing or invalid task declaration
- `4`: authoritative source unavailable or invalid
- `5`: internal graph, envelope, or invariant failure

## Graph envelope

Declared, recovered, and derived remain the only field kinds. Counts, compression ratio, derivation count, declarative burden, and consumed-recovery checks are computed in a separate immutable envelope, so metadata cannot count itself. No declarative-backlog value is rendered because no authoritative backlog artifact exists.

Git changes are recovered through the stable `git.changed_paths` provider as deterministic semantic records preserving index, worktree, rename, deletion, untracked, and unmerged state.

Outputs are deterministic for identical task and Git inputs: fields and paths are ordered, timestamps are absent, and locale-dependent formatting is not used.

## Contributing

Repository contributions follow [Contributing to Fold](CONTRIBUTING.md), the
[Coding Standards](docs/coding-standards.md), and the
[Documentation Standards](docs/documentation-standards.md).
