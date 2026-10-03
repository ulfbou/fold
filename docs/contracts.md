# Behavioral Contracts

## Task declaration

`.fold/task.json` schema version `1.0` contains exactly `schemaVersion`,
`title`, `scope`, and `tests`. Unknown properties are rejected.

`scope` is a non-empty array of safe repository-relative paths. Fold normalizes
path separators, removes trailing separators, rejects absolute paths and parent
traversal, sorts values, and removes duplicates.

`tests` is an array of non-empty command strings, not paths. Fold treats each
command as opaque text, sorts commands, and removes exact duplicates. Fold does
not execute these commands while loading the task declaration.

## Scope drift

Declared scope is an allowed-prefix set. An actual changed path is covered when it equals a declared scope path or is a descendant of that path on a path-component boundary.

The core relation is:

```text
actual relevant changes âŠ† declared scope
```

Declared scope may be broader than actual changes. That alone is not drift.

Actual changes include staged, unstaged, and untracked paths recovered by the single `git.changed_paths` provider. The provider must account for renames and must produce repository-relative normalized paths.

Deletion policy for `scope-drift@1.0`:

- deletion inside declared scope is a relevant change and is covered;
- deletion outside declared scope is reported separately but does not create scope drift;
- non-deletion changes outside declared scope create scope drift.

This deletion exception is explicit and versioned in the `scope-drift` rule. It must not be generalized silently.

Plain `fold task` renders the state and marks it `DRIFTED` when drift exists, but exits successfully if all sources and schema inputs are valid.

`fold task --check` renders the same state and exits with check failure when drift exists.

## Git change recovery

`git.changed_paths` is one recovery provider, even if its implementation parses multiple Git record types. The Git recovery provider uses one `git status --porcelain=v2` execution as its authoritative observation so staged, unstaged, untracked, renamed, and deleted paths are evaluated together.

The provider output is sorted deterministically after semantic parsing. Provenance names the provider, not its current shell implementation.

## Exit codes

```text
0  Successful rendering or successful check
1  Contract violation detected under an explicit check
2  CLI usage error
3  Missing, unreadable, or schema-invalid Fold artifact
4  Required authoritative source unavailable or invalid
5  Internal graph, rule, or invariant failure
```

A plain drift warning does not use exit code `1`; only an explicit check does.

## Determinism

For identical repository state, Fold artifacts, Fold version, command, and relevant environment-independent inputs, output must be byte-identical.

Therefore:

- field order is specified or canonically sorted;
- path collections are canonically sorted;
- JSON uses a stable serialization contract;
- timestamps are excluded from deterministic views;
- locale-dependent formatting is prohibited;
- colors and terminal capabilities cannot alter redirected canonical output;
- no random identifiers appear in task or explanation output.

## Rendering and evaluation

`fold task`, `fold explain`, `fold explain --json`, and `fold task --check` consume the same evaluated graph. A gate may add a status and exit code, but may not recompute fields through a separate interpretation.

## Failure policy

M1A fails rather than guessing when:

- the schema version is unsupported;
- a required task field is absent or invalid;
- Git state cannot be recovered;
- deterministic normalization cannot be completed;
- the recomputed graph envelope differs from the supplied envelope.

M1B will add rejection of missing derivation inputs, unknown rule identities or
versions, and graph cycles before rendering or gate evaluation.
