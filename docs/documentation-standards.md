# Documentation Standards

Fold documentation is a public contract surface. It must be concise enough to
navigate and complete enough to implement, test, and review without relying on
conversation history.

## Document authority

Each behavior has one controlling document:

- `README.md` is the compact user entry point and describes only released or
  current verified behavior.
- `CONTRIBUTING.md` defines the contributor workflow and links to detailed
  standards.
- `docs/ROADMAP.md` controls invariants, milestone proofs, candidates, the
  horizon, and roadmap amendment governance.
- `docs/coding-standards.md` controls source and test conventions.
- `docs/documentation-standards.md` controls documentation conventions.
- Focused contract documents control detailed schemas, providers, rules, and
  operational behavior when the roadmap requires them.

Do not duplicate a controlling contract. Summaries link to it and must not
silently add or weaken obligations.

## Required qualities

Documentation must be:

- **Accurate:** describes implemented and tested behavior or clearly labels a
  proposal, candidate, limitation, or non-goal.
- **Evidence-linked:** behavioral claims identify the executable test, gate, or
  validation that proves them.
- **Deterministic:** examples avoid timestamps, random identifiers, local-only
  paths, and environment-dependent output unless those values are the subject.
- **Scoped:** separates current behavior, planned proof, candidate mechanism,
  and release horizon.
- **Navigable:** uses descriptive headings, relative Markdown links, and one
  clear continuation path.
- **Maintainable:** keeps one authority per contract and updates all affected
  summaries in the same change.

## Writing conventions

- Use concise, direct English and present tense for current behavior.
- Use normative words deliberately:
  - **must** for mandatory behavior;
  - **must not** for prohibited behavior;
  - **should** for a default that permits a documented exception;
  - **may** for an optional behavior.
- Name the actor and condition. Avoid vague pronouns such as "it" or phrases
  such as "when relevant" when they carry a requirement.
- Prefer concrete outcomes over abstractions such as "useful",
  "meaningful", or "sustained" unless the document defines a mechanical test.
- Define acronyms and repository-specific terms on first use.
- Keep paragraphs focused on one claim.
- Use sentence-style headings and fenced code blocks with a language marker.
- Do not use screenshots as the only representation of commands, values, or
  acceptance evidence.

## Code, commands, and paths

- Commands must be copyable in the shell named by the surrounding text.
- Use repository-relative paths in prose and examples.
- Do not use `/path/to` placeholders. Use named variables such as
  `$REPO_ROOT`, `$DX_FILE`, or `$OUTPUT_DIR` when a variable is required.
- Examples must not claim success unless the corresponding operation was run.
- Show expected exit behavior when nonzero exits are part of the contract.
- Keep examples minimal, but never omit required validation or error handling
  in a way that teaches an unsafe workflow.
- Use current DX v2.0 production carriers with `.dx.txt` filenames. ZIP files
  are distribution archives, not DX carriers.

## Behavioral and schema documentation

A public behavior description states:

- authoritative inputs;
- normalized value or output;
- ordering and determinism rules;
- unavailable and malformed behavior;
- exit code when applicable;
- version identity when semantics are versioned;
- focused evidence that proves the claim.

Schema documentation states required properties, unknown-property behavior,
normalization, duplication behavior, compatibility rules, and examples of both
valid and invalid input.

Provider documentation names the stable provider identity rather than exposing
an incidental shell command as the public contract.

Rule documentation names the exact rule identity and version, ordered inputs,
policy constants, output contract, and predicate. M1B adds descriptor and
evaluator-digest obligations; M1A documentation must not claim they already
exist.

## Roadmap and changelog rules

- Roadmap 1.0 is the first published baseline.
- Every accepted post-publication roadmap amendment increments the roadmap
  version and adds exactly one canonical changelog entry under that version.
- Pre-publication drafting history is not reconstructed retroactively.
- Milestone status, proof target, dependencies, entry criteria, acceptance
  criteria, Definition of Done, and non-goals must remain distinguishable.
- Candidate milestones are hypotheses and must not be documented as committed
  implementation.

## Pull requests and acceptance evidence

A pull request description identifies:

- proof target;
- milestone and internal gate;
- scope and non-goals;
- changed contracts;
- acceptance criteria;
- validation evidence;
- earlier guarantees covered by regression tests;
- intentional deferrals and known limitations.

Historical records must not claim checks that did not run. GitHub labels and
milestones provide collaboration-state traceability, but they do not replace
executable product evidence.

## Documentation review checklist

- [ ] Every behavioral claim matches implementation and tests.
- [ ] One controlling document owns each contract.
- [ ] Links are relative, valid, and descriptive.
- [ ] Current, planned, candidate, and horizon statements are not conflated.
- [ ] Commands name their shell and are directly executable.
- [ ] Examples use safe repository-relative paths and established variables.
- [ ] Exit codes, errors, normalization, and ordering are documented.
- [ ] Unsupported behavior is explicit rather than silently omitted.
- [ ] No placeholder, conversational dependency, or unverifiable acceptance
      claim remains.
- [ ] README and contributor summaries are updated when their public surface
      changes.
