# Contributing to Fold

Fold treats inspectability as a product property. Contributions must therefore
be understandable, deterministic, and mechanically verifiable.

## Before changing code

1. Identify the roadmap milestone or internal gate served by the change.
2. State one falsifiable proof target.
3. Declare in-scope and out-of-scope behavior.
4. Update `.fold/task.json` before editing paths outside its declared scope.
5. Preserve earlier accepted contracts unless an explicit versioned decision
   authorizes a semantic change.

## Required standards

- Follow [Coding Standards](docs/coding-standards.md).
- Follow [Documentation Standards](docs/documentation-standards.md).
- Keep public documentation, CLI help, schemas, tests, and implementation in
  agreement.
- Use Conventional Commits.
- Change `master` only through a pull request after repository bootstrap.
- Associate implementation pull requests with their public roadmap milestone.
- Use `gate: M1A` and `gate: M1B` only for their corresponding internal gates.
- Do not claim checks, acceptance evidence, or behavior that did not run or is
  not implemented.

## Pull request content

Every implementation pull request must include:

- proof target;
- scope and explicit non-goals;
- affected public contracts;
- acceptance criteria and evidence;
- validation commands and results;
- earlier guarantees covered by regression tests;
- intentional deferrals;
- relevant milestone and gate metadata.

## Local validation

Run the repository checks from the repository root:

```bash
python -m pytest
python tools/fold-changelog verify
python -m compileall -q src tests
git diff --check
```

Run affected public commands as part of feature validation. For M1A this
includes:

```bash
python -m fold --version
python -m fold task
python -m fold explain status
python -m fold explain --json
python -m fold task --check
```

A nonzero result is acceptable only when the test explicitly proves that exit
contract. Do not suppress or reinterpret a failing mandatory check.
