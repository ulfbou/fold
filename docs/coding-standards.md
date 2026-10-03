# Coding Standards

These standards apply to Python source, tests, repository tools, and CI support
code in Fold. They turn Fold's inspectability thesis into reviewable coding
practice.

## Governing principles

1. **Readability is part of correctness.** Code that is difficult to inspect is
   not acceptance-ready even when tests pass.
2. **One behavior has one implementation path.** Renderers and gates consume
   the same evaluated graph rather than recovering or reinterpreting state.
3. **Contracts are explicit.** Public values, errors, ordering, normalization,
   and unavailable states are documented and tested.
4. **Determinism is designed in.** Canonical output must not depend on clocks,
   locale, process identity, terminal state, unordered collections, or random
   values.
5. **Dependencies require evidence.** Do not add a package, formatter, linter,
   plugin boundary, or compatibility layer without a repository need and an
   accepted scope decision.

## Python layout and naming

- Use four spaces for indentation and spaces around operators.
- Put one statement on each physical line. Do not use semicolons to compress
  logic.
- Prefer lines no longer than 100 characters. Break expressions using implicit
  continuation inside parentheses, brackets, or braces.
- Group imports as standard library, third party, then local imports, with one
  blank line between groups.
- Use `snake_case` for functions and variables, `PascalCase` for classes, and
  `UPPER_SNAKE_CASE` for module constants.
- Use descriptive names that expose domain meaning. Single-letter names are
  limited to conventional, very small mathematical or indexing contexts.
- Separate top-level functions and classes with two blank lines.
- Keep functions focused. Extract named helpers when parsing, validation,
  transformation, and rendering would otherwise be interleaved.

## Types and immutable models

- Type public functions and non-obvious internal functions.
- Use immutable domain values by default. Fold data records use
  `@dataclass(frozen=True)` unless mutation is the explicit contract.
- Prefer keyword arguments when constructing domain models with more than two
  fields.
- Use enums or literal types for closed vocabularies.
- Do not silence type ambiguity with broad `Any`, casts, or ignore comments when
  a precise domain type can express the contract.
- Keep graph metadata outside `FieldNode`; metadata must not count itself.

## Functions and errors

- Public functions and non-obvious protocol parsers require docstrings that
  describe their contract, not their implementation syntax.
- Catch only exceptions that can be handled or translated at that boundary.
- Do not catch `Exception` around product logic.
- User input failures and internal invariant failures are distinct:
  - invalid CLI usage and unknown requested fields use exit `2`;
  - invalid task artifacts use exit `3`;
  - unavailable authoritative sources use exit `4`;
  - graph, rule, envelope, and invariant failures use exit `5`.
- Internal required-field lookup must raise an invariant error. It must never be
  reported as an unknown user-requested field.
- Error messages identify the failed contract and relevant value without
  exposing secrets or unstable environment details.

## Git provider code

- Obtain changed state from one `git status --porcelain=v2 -z` observation.
- Parse bytes before decoding paths. Split fixed protocol headers with an exact
  maximum split so paths containing spaces remain intact.
- Preserve index and worktree status independently.
- Preserve rename destination and original path.
- Preserve deletion, untracked, and unmerged semantics.
- Reject malformed, unsupported, unsafe, absolute, or parent-traversing paths.
- Sort semantic records with an explicit stable key.
- Scope drift version 1 checks the rename destination. The original path has
  deletion semantics and does not independently cause drift.
- Ignored files are not observed unless a future contract explicitly adds them.
- M1A does not independently interpret submodule state beyond supported path
  records emitted by Git.
- A repository without `HEAD` is an unavailable authoritative source and must
  produce a targeted error.

## Graph, consumers, and envelope

- Every collaboration-state field is declared, recovered, or derived.
- Field names are unique.
- Every field must have a live consumer in a renderer, derivation input, or
  gate. Renderer consumption is declared by `RENDER_CONSUMES` beside the
  renderer implementation and is verified against the fields read by focused
  tests; derivation inputs and gate reads are added mechanically.
- Adding a field requires adding its consumer and focused tests in the same
  change.
- Envelope values are recomputed from the evaluated graph.
- Fold's compression ratio is recovered fields divided by declared fields.
  A zero declared-field denominator produces `None`, rendered as `null` in JSON
  and `n/a` in human output.
- Derived-field count and derivation count remain separate concepts even when
  their M1A values happen to match.
- `unconsumedRecoveries` is the recovered-field subset of the broader
  no-unconsumed-field validation surface. A valid envelope is emitted only
  after that broader invariant passes, so the field is empty in valid M1A
  output and remains present for envelope-schema continuity and diagnostics.
- No fabricated fallback value may stand in for an absent authoritative
  artifact.

## Rendering and serialization

- Human and JSON renderers consume the same graph and envelope.
- Ordering is explicit for fields, paths, change records, rules, and serialized
  collections.
- JSON uses stable key names and `sort_keys=True` for canonical output.
- Conversion to JSON is explicit for domain values; do not depend on `repr`,
  unordered containers, or implementation-specific serialization.
- Renderer helpers transform values only. They do not recover state, evaluate
  rules, suppress invalid graphs, or manufacture fields.

## Tests

- Tests are executable documentation and follow arrange, act, assert structure.
- Test names describe the contract and expected outcome.
- Helpers use descriptive names and type annotations where useful.
- Prefer controlled byte fixtures for protocol parsing and real repositories
  for end-to-end Git behavior.
- Cover normal, boundary, malformed, unavailable, deterministic, and
  non-regression behavior.
- Assert complete semantic values where practical, not only the presence of a
  substring.
- Canonical human and JSON output require separate-process byte comparisons.
- Every documented exit code requires a focused test.
- Do not weaken an assertion merely to make a failing implementation pass.

## Review gate

A Python change is not acceptance-ready if it contains compressed multi-action
lines, unexplained positional model construction, ambiguous names, hidden
ordering assumptions, broad exception masking, an unconsumed field, or a public
claim without executable evidence.
