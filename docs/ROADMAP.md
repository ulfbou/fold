# Fold Roadmap

**Roadmap version:** 1.0

Fold milestones prove thesis increments. This roadmap is a claim about order, not a feature backlog. Each milestone must establish a capability that later milestones depend on, add the smallest surface needed to prove it, and preserve every previously accepted guarantee.

A milestone may enter implementation only when its acceptance-ready criteria pass. It is complete only when its Definition of Done passes without unresolved exceptions.

## Product thesis

Fold compresses declared collaboration state into a minimal working surface and reconstructs every rendered field from its declared source or a named, versioned derivation.

**No hidden inference. No hidden state. No unrecoverable decisions.**

Fold is a repository-resident collaboration-state condenser. It is not an agent, workflow engine, autonomous task selector, probabilistic inference framework, or remote state store.

## Roadmap structure and status

The roadmap separates permanent **invariants**, ordered proof **milestones**, evidence-gated **candidate milestones**, and a measured release **horizon**.

Statuses are:

- **Complete**: accepted proof; later defects become correction obligations rather than retroactive erasure.
- **Current**: acceptance-ready work authorized for implementation.
- **Planned**: dependency order accepted, but entry evidence incomplete.
- **Candidate**: a fully described hypothesis that requires promotion before implementation.
- **Horizon**: a measured operating state, not a feature commitment.

Numbering preserves design history and dependency discussion. It does not authorize candidate implementation.

## Roadmap invariants

These constraints apply to every milestone. They are permanent product contracts, not milestones themselves.

### 1. Three field kinds

Every collaboration-state field is exactly one of:

- **Declared**: authored in a schema-versioned Fold artifact.
- **Recovered**: deterministically read from an authoritative source through a named provider.
- **Derived**: deterministically computed from graph inputs by an exact, versioned rule.

Representation metadata is not a fourth field kind. Graph schema versions, field counts, compression measurements, and similar facts belong to a separate graph envelope and must be computed mechanically from the validated graph or recovered from an explicit source.

The graph envelope carries its own schema version. Every envelope claim is a public claim subject to invariant 2 (claim-code parity). The complete envelope claim set is: envelope schema version, tool version, declared field count, recovered field count, derived field count, verified field count, compression ratio, derivation count, declarative burden, unconsumed recovery names, and referenced rule identities, versions, and evaluator digests. Envelope claims are computed from the validated graph, never stored alongside it, never carried over from a previous run, and never affected by renderer choice.

### 2. Claim-code parity

Every behavioral claim in the README, CLI help, schema, contract, rule description, or roadmap must be enforced by code or proved by a test. Documentation must not claim behavior that executable evidence does not support.

### 3. Inspectable rule semantics

Every derived field names:

- an exact rule ID;
- an exact rule version;
- an ordered input set;
- an inspectable canonical rule descriptor;
- the evaluated input values;
- the resulting value.

A rule descriptor is bound to its evaluator by a semantic implementation digest recorded in the descriptor and verified in CI. The digest is computed from a canonical semantic representation defined by the rule-registry contract; it excludes non-semantic formatting, comments, source locations, and other mechanically identified presentation-only changes. The digest is evidence that the registered implementation matches the descriptor, not the public identity of a rule. Any semantic evaluator change that leaves the descriptor or rule version unchanged is an invariant failure. Descriptor-only editorial changes that do not alter identity, ordered inputs, policy constants, predicate, or output contract do not require an evaluator change or rule-version increment.

Runtime values come from graph inputs. Any policy constant that affects semantics must be visible in the versioned rule definition. Fold never resolves a derivation against a different version implicitly.

### 4. Determinism

Canonical output is byte-identical for identical `(graph inputs, referenced rule identities and versions, referenced evaluator digests, envelope schema version, tool version)` tuples. No other input affects canonical output. Environment, locale, wall clock, hostname, user identity, terminal, and process identity are not inputs.

This requires:

- canonical field order;
- canonical path order;
- stable serialization;
- no timestamps in deterministic views;
- locale-independent formatting;
- no random identifiers;
- no terminal-dependent changes to redirected canonical output.

Determinism is tested by hashing the tuple and asserting that two runs with the same tuple produce byte-identical canonical output. A changed component must change canonical output only when the controlling schema or exact referenced rule descriptor declares that component output-affecting; tests enumerate those declared dependencies rather than deciding relevance after observing output.

### 5. One evaluated graph

Renderers and gates consume one validated graph. They do not independently recover state, evaluate rules, manufacture fields, or reinterpret values.

### 6. Gates on the hot path

Enforcement is part of a command users run in the normal workflow. A parallel validator that can be routinely skipped does not satisfy a gate requirement.

### 7. Separate measurements

Fold measures separately:

- **Compression ratio**: the count of recovered collaboration-state fields divided by the count of declared collaboration-state fields, excluding any field that is present in both roles. Fields present in both are counted under verified fields, reported separately.
- **Derivation count**: derived collaboration-state fields that appear in at least one renderer, contribute to a rendered derivation, or are consumed by a gate.
- **Declarative burden**: fields a user must still maintain explicitly.

Measurements must not count graph metadata as collaboration-state fields, count themselves, or be inflated by low-value fields.

No field counts toward compression unless it appears in at least one renderer's output, is named as an input to a rule that appears in a renderer's output, or is consumed by a gate. Recovered fields that satisfy none of these are excluded from compression and listed by canonical field name in the envelope under `unconsumedRecoveries`. A non-empty list is an invariant failure under invariant 8, not merely an informational metric.

### 8. No unconsumed fields

A collaboration-state field must serve at least one working renderer, explanation, or gate. Speculative fields do not enter the graph.

### 9. Non-regression

A milestone may not weaken, contradict, silently reinterpret, or leave unverified an earlier accepted contract. A deliberate semantic change requires an explicit versioned decision and migration path.

### 10. Evidence before mechanism

The roadmap commits to proofs and invariants. A mechanism becomes binding only when the preceding proof makes it necessary and repository evidence supports it.

## Common acceptance-ready criteria

Every milestone must satisfy these conditions before implementation begins:

- The proof target is stated as one falsifiable outcome.
- The dependency on prior milestones is explicit.
- In-scope and out-of-scope behavior is documented.
- Public contracts affected by the work are identified.
- Required authoritative inputs are available.
- The proposed implementation does not require an unresolved ontology or schema decision.
- Acceptance criteria are executable or mechanically inspectable.
- Regression coverage for all affected earlier guarantees is identified.
- The work fits one reviewable milestone and can be delivered through bounded PRs.
- No required behavior depends on conversational memory.
- Evidence is proportional to contract risk: reuse existing executable evidence when it already proves an unchanged obligation; add new evidence only for new or changed behavior.
- Acceptance records link to controlling contracts and executable evidence rather than restating them.

If any item fails, the milestone is not acceptance-ready. The next action is to resolve the missing decision or evidence, not begin implementation. Governance work must remain the minimum needed to make the proof mechanically reviewable.

## Common Definition of Done

Every milestone is complete only when:

- All milestone-specific acceptance criteria pass.
- All applicable earlier milestone tests continue to pass.
- The complete supported test suite passes in CI.
- Canonical human and JSON output remain deterministic across separate processes.
- Public documentation matches implemented behavior.
- CLI help, schemas, rule descriptors, tests, and implementation agree.
- Error behavior and exit codes are covered by focused tests.
- No unrelated feature surface was added.
- No hidden inference, hidden state, or implicit rule substitution was introduced.
- Changed files pass formatting, syntax, static, and repository checks configured for the milestone.
- The PR contains acceptance evidence and declares any intentional deferral.
- The default branch changes only through an accepted PR using Conventional Commits.
- No unresolved regression, ambiguity, missing evidence, or acceptance exception remains.

## M0: Minimal checkable graph

**Status:** Complete.

### Proof target

Fold can combine declared and recovered repository state, render a compact working surface, explain fields, serialize graph state, and enforce one explicit scope-drift check without separate interpretations.

### Established surface

- schema-versioned `.fold/task.json`;
- `fold task`;
- `fold explain`;
- `fold explain --json`;
- `fold task --check`;
- declared, recovered, and derived provenance shapes;
- recovered Git HEAD and changed paths;
- deterministic rendering under the tested surface;
- plain drift reporting and explicit check failure.

### Accepted limitations carried into M1

M0 proved the architectural direction but did not make every claim mechanically trustworthy. The following are mandatory M1 foundation obligations:

- remove hard-coded metric counts;
- separate graph metadata from collaboration-state fields;
- validate duplicate names, missing inputs, cycles, and exact rule identities;
- complete porcelain-v2 semantic change parsing and coverage;
- make deletion behavior match one documented contract;
- prove exit codes and cross-process determinism;
- establish CI for supported Python versions.

These obligations do not reopen M0. They constrain the next accepted state.

## M1: Trustworthy recursive provenance

**Status:** Current.

### Proof target

Every rendered collaboration-state field belongs to a validated acyclic graph, every derivation resolves an exact versioned rule, and explanation reconstructs the result recursively to authoritative source leaves with equivalent canonical human and JSON semantics.

### Dependency

M1 preserves M0's compact task surface, schema/renderer/gate separation, drift check, and provenance categories. It strengthens their enforcement rather than replacing them.

### Ordered acceptance gates

M1 is one public milestone with two internal acceptance gates. M1A must pass before M1B can be accepted. These gates do not create an M0.1 milestone.

- **M1A, foundation honesty:** make the existing graph, recovery, metrics, exits, determinism, and documentation mechanically truthful.
- **M1B, recursive proof:** add exact rule resolution, graph validation, and recursive equivalent explanations over the honest foundation.

### Scope

#### Foundation honesty (M1A)

- Compute graph metadata from the validated graph rather than constants.
- Keep graph metadata outside the `FieldNode` set.
- Enforce envelope/field agreement: recomputing the envelope from the validated graph must produce byte-identical envelope content. Any mismatch is an invariant failure, not a warning.
- Parse one Git porcelain-v2 observation into deterministic semantic change records.
- Preserve staged, unstaged, untracked, renamed, deleted, and unmerged change kinds.
- Make path handling safe for spaces and component boundaries.
- Establish the documented exit-code contract, including an invariant-failure code.
- Add cross-process determinism tests.
- Establish supported-version CI containing pytest on the supported matrix, the cross-process determinism check, descriptor-digest verification, and a non-regression run of the M0 suite.
- Expose `fold --version` from the authoritative package version used by release and determinism evidence.

#### Rule registry (M1B)

- Resolve rules by exact `(rule_id, rule_version)`.
- Never substitute another version implicitly.
- Register `scope-drift` with one consistent exact version.
- Keep evaluators in-tree as Python code.
- Expose an inspectable canonical descriptor containing identity, inputs, output contract, policy constants, and documented predicate.
- Include the semantic implementation digest in the canonical descriptor. `fold explain` renders the digest alongside the rule ID and version. CI verifies that every registered rule's descriptor digest matches its canonical semantic evaluator representation.
- Increment a rule version when observable rule semantics change, including identity-relevant changes to ordered inputs, policy constants, predicate, or output contract. Formatting, comments, source relocation, and refactoring proven by the canonicalization contract to preserve semantics do not bump the version.
- Define and test the canonical semantic representation before digest verification becomes an acceptance gate; digest churn alone must never force rule-version churn.
- Treat unknown rules and version mismatches as invariant failures.

#### Graph validation (M1B)

- Reject duplicate field names.
- Reject missing derivation inputs.
- Reject graph cycles.
- Reject unregistered rule identities and versions.
- Require every recursive explanation branch to terminate at declared or recovered source leaves.
- Validate before rendering or gate evaluation.

#### Recursive explanation (M1B)

- Include field name, value, and classification.
- Include provider and stable locator for source-backed leaves.
- Include exact rule ID, version, canonical rule descriptor, ordered inputs, evaluated input values, and output for derived fields.
- Recursively render every derivation input.
- Render canonical human and JSON forms from the same evaluated graph.

#### Scope-drift semantics

- Treat declared scope as an allowed repository-relative component-prefix set.
- Report non-deletion changes outside scope as drift.
- Report deletion outside scope without treating it as drift in rule identity `scope-drift@1.0`.
- Treat equal or descendant paths as covered.
- Allow declared scope to be broader than actual changes.
- Treat an empty change set as aligned.

### Non-goals

- role projections;
- capability enforcement;
- ceremony tiers;
- external providers;
- rule DSL or user-authored executable rule language;
- plugin architecture;
- historical graph persistence;
- agents or autonomous task selection.

### Acceptance-ready criteria

M1 may enter implementation only when:

- `docs/data-model.md` defines graph invariants and graph-envelope metadata.
- `docs/rules.md` defines exact rule identity, descriptor semantics, registry behavior, and version-change policy.
- `docs/contracts.md` defines porcelain change kinds, deletion behavior, determinism, and exit codes.
- One exact `scope-drift` version is used consistently across all controlling documents.
- The schema contract and implementation agree on whether `tests` contains paths or commands.
- The current M0 test suite is available as a non-regression baseline.
- The supported Python versions and CI matrix are declared.
- Every M1 acceptance item maps to at least one planned test.
- No unresolved requirement depends on a JSON rule DSL or historical persistence.

### Acceptance criteria

M1 is acceptable when:

- invalid graphs fail before any renderer or gate consumes them;
- exact rule lookup succeeds only for registered ID/version pairs;
- missing and mismatched versions never fall forward to another version;
- `fold explain FIELD` recursively reaches source leaves and shows values;
- canonical JSON represents the same recursive semantics as human explanation;
- graph metadata reflects actual validated graph structure and cannot self-inflate;
- recomputing the envelope from the validated graph produces byte-identical envelope output, and a mismatch fails the run rather than warning;
- changed paths with spaces and all documented porcelain-v2 kinds are parsed correctly;
- `scope-drift@1.0` matches the documented deletion and path-boundary contract;
- plain task rendering warns on drift and returns success;
- explicit checking returns the contract-violation exit code on drift;
- exit codes `0` through `5` have focused proof;
- repeated cross-process output comparisons are byte-identical;
- all M0 behavior remains available unless an explicit versioned correction is documented.

### Definition of Done

- All common Definition of Done items pass.
- The rule registry, graph validation, recursive explanation, Git parser, metrics envelope, and CLI error contract have focused tests.
- At least one end-to-end repository fixture proves task rendering, recursive explanation, canonical JSON, and checking from one evaluated graph.
- The supported Python CI matrix passes.
- README and documentation describe only verified M1 behavior.
- No hard-coded field counts or fabricated declarative backlog remain.
- No renderer-side cycle suppression remains.
- No rule body is represented as an unvalidated executable JSON language.

## M2: Role projections

**Status:** Planned.

### Proof target

Multiple roles can receive bounded cognitive views of one canonical graph without changing field values, provenance, derivation semantics, or authority.

### Dependency

Role projections depend on M1's validated graph and recursive provenance. A view cannot be trusted before the underlying graph is trustworthy.

### Scope

- Define role projection artifacts with an explicit schema.
- Add `fold task --role <name>`.
- Keep canonical field explanation role-independent.
- Add a role-view explanation that states why a field is shown or hidden.
- Keep `fold explain FIELD` and canonical graph JSON role-independent.
- Treat any `fold explain FIELD --role <name>` form as a separate projection envelope that explains visibility without changing the canonical field.
- Treat roles as renderers over one graph, not derivations or gates.

### Non-goals

- permissions;
- authorization;
- action enforcement;
- role-dependent values;
- separate role graphs;
- Lead/Senior workflow implementation beyond projection semantics.

### Acceptance-ready criteria

M2 may enter implementation only when:

- sustained M1 use identifies two proposed roles whose projection field sets differ by at least one canonical graph field, and each differing inclusion or exclusion is justified in the corresponding role artifact descriptor;
- each proposed role has a bounded field-selection need;
- canonical graph and role-view envelopes are clearly separated;
- field visibility can be defined without changing values or provenance;
- no desired behavior requires capability enforcement.

### Acceptance criteria

- two roles render task surfaces from the same graph whose canonical selected-field-name sets are unequal and whose complete set difference is justified by their role artifact descriptors;
- canonical graph JSON is identical regardless of role projection;
- a role cannot change, replace, or reinterpret a field;
- role-view explanation identifies the projection rule for every shown or hidden field;
- unknown roles fail explicitly;
- role output remains deterministic.

### Definition of Done

- All common Definition of Done items pass.
- Projection schemas and selection semantics are documented and tested.
- Canonical explanation remains role-independent.
- Role-view tests prove differing surfaces without graph divergence.
- No capability or workflow-engine semantics are introduced.

## M3: Local recovery expansion

**Status:** Planned.

### Proof target

Fold measurably reduces declarative burden by adding deterministic repository-local recovery providers rather than adding declarations.

### Dependency

M3 depends on M1's provider provenance, deterministic graph, and honest metrics. It may benefit from M2 views but must not require them.

### Candidate local providers

Candidates must be justified individually. Possible examples include:

- Git tags and distance from the nearest tag;
- configured upstream identity and locally observable ahead/behind state;
- tracked filesystem summaries that serve a renderer or gate.

The candidate list is not a commitment.

### Non-goals

- GitHub issues or checks;
- network-dependent observations;
- remote state synchronization;
- provider plugins;
- fields added solely to increase the compression ratio.

### Acceptance-ready criteria

M3 may enter implementation only when:

- real Fold use identifies a repeatedly handwritten field with an authoritative local source;
- the recovered value serves a working renderer, explanation, or gate;
- source availability and failure semantics are specified;
- deterministic recovery is possible without network access;
- the field has an operational consumer under invariant 7.

### Acceptance criteria

- each new field replaces or prevents a meaningful declaration;
- each provider has a stable identity and normalized deterministic output;
- unavailable or invalid sources follow explicit error semantics;
- compression improvement is reported without counting metadata or unused fields;
- no new declaration is added merely to configure recovery unless unavoidable and justified.

### Definition of Done

- All common Definition of Done items pass.
- Every provider has focused normal, boundary, unavailable, and deterministic tests.
- The milestone report identifies the declarative burden reduced by each provider.
- No network dependency or plugin boundary is introduced.

## M4: Explainable ceremony derivation

**Status:** Planned.

### Proof target

Operational ceremony can be derived predictably from explicit obligations and recovered facts through an exact, versioned, recursively explainable rule, without classifying intent from a diff.

### Dependency

M4 depends on M1's exact rules and recursive provenance and on sufficient authoritative inputs established by earlier milestones.

### Scope

- Define one ceremony result consumed by a renderer or gate.
- Define an exact versioned rule with explicit inputs and visible policy constants.
- Explain the complete derivation recursively.
- Keep declared scope and obligations authoritative.

### Non-goals

- machine-learning classification;
- diff-based intent inference;
- unexplained light/medium/heavy labels;
- consumer-impact or test-coverage derivations without authoritative models;
- automatic workflow execution.

### Acceptance-ready criteria

M4 may enter implementation only when:

- real Fold use demonstrates repeated manual ceremony selection;
- the required inputs already exist as authoritative graph fields;
- the result changes a working surface or hot-path gate;
- policy constants and boundary cases are agreed and versionable;
- the rule can be explained without reading hidden repository state.

### Acceptance criteria

- the ceremony result is reproducible from graph inputs alone;
- explanation shows rule identity, version, descriptor, input values, constants, and output;
- boundary fixtures prove every tier or outcome transition;
- changing semantics requires a new rule version;
- the rule never infers task intent from changed paths alone.

### Definition of Done

- All common Definition of Done items pass.
- One ceremony rule is production-ready and consumed.
- No unused derived fields are added.
- No classifier, agent, or workflow engine is introduced.

## M5: Capability-boundary decision

**Status:** Candidate.

### Proof target
A bounded action can be allowed or rejected from explicit graph state without turning Fold into a workflow engine or treating a role view as authority.

### Dependency and entry criteria
M5 depends on accepted M2 use showing that projection is insufficient, a stable observable action identity, explicit authority inputs, agreed failure and override semantics, and evidence that enforcement can occur at a Fold-controlled hot-path gate without autonomous workflow execution.

### Candidate scope
Define one versioned action descriptor and authorization rule, reuse the canonical evaluated graph, and recursively explain allow and deny outcomes.

### Non-goals
Generic permissions, identity management, policy administration, unobserved `may` or `mayNot` clauses, autonomous execution, and reproduction of Collab workflow semantics.

### Acceptance criteria
The same action and graph tuple produces the same result; allow and deny outcomes expose exact rules and inputs; role views cannot change authorization; unknown actions fail explicitly; and the gate operates on the action path.

### Definition of Done
All common DoD items pass, promotion evidence is recorded, one bounded action is enforced and explained, and Fold remains outside workflow execution.

## M6: External observation snapshots

**Status:** Candidate.

### Proof target
A volatile external fact enters Fold as an immutable observation snapshot with source identity, observation identity, freshness, and deterministic rendering of the captured value.

### Dependency and entry criteria
M6 depends on M1 provenance and is promoted only when a repeatedly needed external fact has no authoritative local provider, can be captured separately from rendering, and has explicit freshness, unavailable, invalid, and stale semantics without creating a remote state store.

### Candidate scope
Define a versioned snapshot schema; record provider, locator, observation identity, value, and freshness evidence; separate acquisition from canonical evaluation; render the same snapshot without network access.

### Non-goals
Live network reads during canonical rendering, background synchronization, credential platforms, remote stores, provider plugins, or a fourth field kind.

### Acceptance criteria
Canonical evaluation consumes captured state; identities and freshness are explicit; failures follow documented exits; equal snapshots render byte-identically; changed observations change the determinism tuple.

### Definition of Done
All common DoD items pass and one provider has acquisition, snapshot, validation, freshness, failure, and determinism tests with no implicit refresh path.

## M7: DX transport projection

**Status:** Candidate, cross-cutting.

### Proof target
A validated Fold graph snapshot is transported through the repository's authoritative current DX v2.0 production implementation without Fold defining or partially reimplementing DX.

### Dependency and entry criteria
M7 requires a stable graph serialization, repeated non-agentic transport need, defined receiving workflow and mutability, and an available authoritative DX integration boundary. It may be promoted independently of M5 and M6.

### Candidate scope
Project Fold-owned serialization files, use the authoritative DX implementation for production and verification, deliver `.dx.txt`, and preserve graph identity and read-only intent.

### Non-goals
A Fold DX parser or encoder, DX v1.x, ZIP carriers, transport as a field kind, transport-defined semantics, or hidden delivery.

### Acceptance criteria
The carrier maps to one validated graph serialization; production and verification use the authoritative implementation; rule versions and provider identities are preserved; transport failure cannot masquerade as graph success.

### Definition of Done
All common DoD items pass, a round trip proves semantic identity, and no DX implementation is duplicated.

## M8: Collab bridge

**Status:** Candidate.

### Proof target
Repeated manual translation between Fold and Collab is reduced through an ownership-preserving bridge without either system reimplementing the other.

### Dependency and entry criteria
M8 requires real drift evidence, documented controlling state and ownership boundaries, a minimal versioned exchange contract, explicit conflict behavior, and proof that neither product must duplicate the other's delivery machinery.

### Candidate scope
Define one directional exchange, record origin and mapping version, detect stale or contradictory state, and explain ownership of each exchanged claim.

### Non-goals
Ontology merger, workflow execution in Fold, Fold-rule evaluation in Collab, premature bidirectional synchronization, or silent conflict resolution.

### Acceptance criteria
One repeated translation is removed or checked; origin and version survive exchange; conflicts fail explicitly; replay is deterministic and idempotent; ownership remains bounded.

### Definition of Done
All common DoD items pass, workflow evidence and ownership mapping are recorded, and one bridge direction is production-ready.

## M9: Multi-repository state

**Status:** Candidate.

### Proof target
One real task combines repository-specific evidence across repositories while preserving authority, pinned observation identity, and recursive provenance.

### Dependency and entry criteria
M9 requires a task that cannot be represented honestly in one repository or one external snapshot, explicit repository identities and revisions, and defined consistency and partial-unavailability semantics.

### Candidate scope
Define a repository-set envelope, pin each observation, namespace fields without erasing source ownership, and explain incomplete, divergent, stale, and cross-repository derived states.

### Non-goals
Distributed transactions, repository orchestration, automatic mutation, a global remote store, or an ambiguous flattened namespace.

### Acceptance criteria
Every field resolves to a repository source or exact cross-repository rule; the set enters the determinism tuple; revision mismatch fails; canonical output is stable; single-repository work remains unchanged.

### Definition of Done
All common DoD items pass and one real fixture proves identity, pinning, recursive explanation, and failure semantics without orchestration.

## M10: Reimagined operating state

**Status:** Horizon.

### Proof target
Fold is the normal human interface to repository-resident collaboration state because sustained use shows lower declared burden, deterministic recursive provenance, and earlier hot-path contract detection.

### Dependency and entry evidence
M10 requires accepted M0 through M4 and only promoted candidates justified by evidence. Assessment requires at least twenty completed real tasks over at least three calendar months. Each task records declared, recovered, derived, verified, and user-maintained field counts from the validated graph and records the schema/tool identity that produced them. Every newly declared field must either replace an earlier declaration or include a justification naming the specific invariant number and obligation it preserves.

For horizon evidence, declarative burden is the number of distinct collaboration-state fields that a user must author or edit for the task after Fold-controlled defaults and recovery have been applied. Task evidence records the canonical field names requiring user maintenance; narrative estimates do not count. Burden reduction is demonstrated only by comparable task classes with their comparison basis recorded. Changes in task scope are reported separately rather than attributed to Fold.

### Horizon criteria
Compact Fold surfaces are the normal access path; invariant 7 metrics show reduced burden without gaming; all fields trace to sources or exact rules; evaluator identities and envelope claims are inspectable; gates are on the hot path; adopted projections preserve one graph; candidates exist only by promotion evidence; contract failures are detected earlier without loss of trust or determinism.

### Non-goals
Success by feature count, requiring all candidates, adoption volume as sole proof, or hiding exceptions behind a release label.

### Acceptance record
The decision cites task evidence, metric history, accepted proofs, omitted candidates, and unresolved limitations. Insufficient evidence leaves the horizon unaccepted.

## Roadmap amendments

The roadmap is a versioned artifact subject to the same claim-code parity and determinism requirements as code.

A roadmap change is one of:

- **Correction**: fixes a documented contradiction, ambiguity, omission, or demonstrably wrong statement without changing an accepted contract. Requires one sentence of justification and a diff.
- **Promotion**: changes a candidate milestone or internal gate to `Current`. Requires its entry criteria to pass, a falsifiable proof target, acceptance-ready criteria in the common format, a Definition of Done in the common format, and recorded evidence.
- **Demotion**: changes a `Current` or `Planned` milestone or internal gate to `Candidate`. Requires evidence that its dependency, invariant, or proof is incomplete and a statement of the effect on dependent work.
- **Restructuring**: changes taxonomy, numbering, grouping, or status vocabulary without weakening milestone contracts. Requires a rationale, an old-to-new identifier mapping, and a non-regression comparison of every affected contract.
- **Invariant change**: modifies a roadmap invariant. Requires an explicit justification naming the earlier invariant, the new invariant, and the migration path for every dependent contract.

This roadmap's version is established as `1.0` when the roadmap is first
accepted into the default branch. Every accepted post-publication amendment
increments the roadmap version and is recorded as exactly one changelog entry
under that new version. The magnitude of the increment carries no amendment
category or compatibility meaning.

Every roadmap change accepted after first publication is recorded in
[Roadmap Changelog](roadmap-changelog.md) with its category, rationale,
and effect on released contracts. The changelog begins with the first change
accepted after the initial roadmap publication. Pre-publication drafting
history requires no retroactive entries. Invariant changes additionally
require a roadmap version increment and a statement identifying which
milestones were re-accepted under the new invariant set.
 

### Tag policy

Milestones are labels for humans; tags are for tools. A version tag is applied when a proof becomes accepted, not merely when a milestone PR is merged. The accountable maintainer records acceptance through the roadmap amendment process before applying a tag. Internal gates may be tagged only when their proof and applicable DoD pass independently. For the current sequence, accepted M1A and M1B may be tagged `v0.1.1` and `v0.2.0` respectively. Gate acceptance is recorded as a Promotion of that internal gate; the tag does not by itself change milestone status.

## Reimagined release horizon

M10 is the complete release-horizon contract. It is a measured operating state and does not require every candidate milestone.

## Anti-roadmap

The following are excluded unless future evidence overturns the boundary through an explicit roadmap decision.

### No rule DSL

Rules remain in-tree code with canonical inspectable descriptors. Fold does not build a compiler, optimizer, general expression language, or user-authored executable rule runtime.

### No embeddings or vector stores

Fold's compression and provenance are symbolic and deterministic, not probabilistic.

### No remote state store

Fold's authoritative working state remains repository-resident. External observations, if ever added, are explicit snapshots rather than a new hidden source of truth.

### No agent control loop

Agents may consume Fold output. Fold does not plan, decide, or execute autonomous work.

### No plugin marketplace

Providers remain in-tree until a proven independent consumer and maintenance case justify a boundary.

### No web UI

Canonical graph and CLI contracts remain authoritative. A presentation layer must not become a second interpretation or source of truth.

### No speculative compatibility machinery

Versioning and migration support are added for actual released contracts, not hypothetical future consumers.

## Cross-cutting delivery policy

### Git and pull requests

- `master` is the default branch.
- After repository bootstrap, every change to `master` arrives through a PR.
- Conventional Commits are required.
- Issues and milestones are used when they add useful scope, acceptance, planning, or traceability.

### Schema versioning

- Additive compatible schema changes increment the minor version.
- Breaking shape or semantic changes increment the major version.
- Renames are breaking changes.
- Unknown properties remain rejected unless a schema version explicitly allows them.

### Deprecation

A released field or contract is not silently removed. Any deprecation policy must define:

- the last version that accepts the old form;
- the warning behavior;
- the removal version;
- the migration path.

No universal one-minor-version rule is assumed before Fold has evidence that it fits actual releases.

### Contract lifecycle
Lifecycle machinery is introduced only for contracts that have actually been released or have more than one supported version. Until then, exact identity and the general deprecation contract are sufficient.

When a released rule, provider, schema, or serialized graph contract is superseded, its controlling document must state: the supported identity or version set; which version new artifacts emit; whether older forms are read, rejected, or migrated; the exact migration path when migration is supported; and the removal condition for deprecated forms. Providers additionally document replacement or retirement semantics. No component silently upgrades, falls forward, or substitutes another rule or provider identity.

Compatibility code without a released compatibility obligation is prohibited by invariant 10.

### Documentation parity

Every rule, provider, exit code, schema, invariant, and public behavior must have one controlling documented contract and executable evidence.

### Metric reporting

Each release reports:

- declared field count;
- recovered field count under invariant 7's consumer-based counting rule;
- derived field count under invariant 7's consumer-based counting rule;
- compression ratio;
- known declarative burden reduced or introduced;
- the reason when no metric moves.

Metric movement is evidence, not an automatic success criterion. A release may be valuable because it strengthens trust without increasing compression. Compression is intentionally conservative: excluded or unchanged fields are reported as context, never reclassified merely to improve the ratio. Declarative-burden evidence is the preferred measure of user-maintenance reduction; compression remains a structural diagnostic rather than a target to optimize.

## Acceptance record template

Each milestone or milestone PR should record:

```markdown
## Proof target

<One falsifiable outcome>

## Acceptance-ready evidence

- [ ] Dependencies are accepted
- [ ] Contracts are complete
- [ ] Inputs are available
- [ ] Acceptance criteria map to tests
- [ ] Non-regression surface is identified
- [ ] Scope and non-goals are explicit

## Acceptance evidence

- [ ] <Milestone-specific criterion>
- [ ] <Milestone-specific criterion>

## Definition of Done

- [ ] Full supported test suite passes
- [ ] Deterministic output checks pass
- [ ] Earlier milestone guarantees pass
- [ ] Documentation and implementation agree
- [ ] Exit codes and failures are tested
- [ ] No unrelated scope remains
- [ ] PR contains validation evidence
- [ ] No unresolved exception remains

## Deferred candidates

- <Explicitly deferred item and reason>
```

## The property to protect

Fold must remain honest enough to detect violations of its own claims early. If a later milestone makes claims harder to enforce, lets renderers diverge from the graph, hides policy inside code, or turns named rules into unexplained labels, the roadmap has failed even if more features ship.

The primary measure is not feature count. It is how quickly and mechanically Fold detects a broken collaboration contract.
