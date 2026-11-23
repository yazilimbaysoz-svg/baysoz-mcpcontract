# Market Research — Baysöz Labs <baysozlabs@proton.me>

Research date: 2026-11-23. Method: `gh search repos`, `gh search issues`, and manual review of
public issue bodies in the MCP ecosystem. All star counts are observations at research time, not
forecasts.

## 1. Signal mining: what is actually large and active

`gh search repos --stars='>3000' --updated='>2026-10-01' --sort=stars` is dominated by agent
harnesses and coding agents, not by another CRUD utility. The durable, high-star substrate beneath
that wave is the Model Context Protocol tool ecosystem:

| Repository (observed via `gh search repos`) | Stars | Why it matters |
| --- | ---: | --- |
| `modelcontextprotocol/servers` | 92,192 | De facto reference tool corpus; changes to tool contracts break every downstream agent. |
| `modelcontextprotocol/python-sdk` | 24,948 | Primary server/client implementation surface. |
| `modelcontextprotocol/inspector` | 11,349 | Interactive debugging, not a CI contract gate. |
| `modelcontextprotocol/modelcontextprotocol` | 9,755 | Specification and dialect authority. |
| `modelcontextprotocol/registry` | 7,494 | Distribution point where portable manifests become infrastructure. |
| `modelcontextprotocol/go-sdk` | 5,384 | Cross-language conformance pressure. |
| `modelcontextprotocol/conformance` | 150 | Protocol-level tests; no tool-contract drift/portability gate. |

The gap is not "yet another MCP server". It is the missing deterministic gate between a tool author
and the many clients that consume the same `tools/list` document.

## 2. Pain points mined from live open issues

1. **Client-side schema destruction.** [anthropics/claude-code#111857](https://github.com/anthropics/claude-code/issues/111857)
   (opened 2026-11-23) reports that `$ref`, `$defs`, `anyOf` and `oneOf` are stripped from MCP tool
   schemas. A schema that validates in the author's SDK can therefore reach the model as a different,
   weaker contract. A static gate must flag constructs that do not survive a target client.
2. **Untyped array items break startup.** [gnoviawan/troupe#1981](https://github.com/gnoviawan/troupe/issues/1981)
   (2026-11-23) reports that `automation_apply_ops` has untyped `ops` items and Gemini agents fail
   on start. This is a deterministic schema defect, not an LLM-quality problem.
3. **Missing property documentation is systemic.** [modelcontextprotocol/servers#5647](https://github.com/modelcontextprotocol/servers/issues/5647)
   (2026-11-21): "git: 21 of 32 tool input properties have no description". Undescribed properties
   cause wrong agent arguments; the cost is measurable and gateable.
4. **Credential leakage through error/output paths.** [modelcontextprotocol/servers#5646](https://github.com/modelcontextprotocol/servers/issues/5646)
   asks for tests that error paths carry no credential values. Secret-shaped input and output
   properties need explicit policy.
5. **Tool manifests are a fixed token tax.** [earthobservations/wetterdienst#4318](https://github.com/earthobservations/wetterdienst/issues/4318)
   describes "slimmer tool schemas, the largest fixed cost of a session (~14k tokens for the tool
   list and instructions)". Bloat must be bounded before publishing.
6. **Output-shape drift breaks chains.** [modelcontextprotocol/servers#5641](https://github.com/modelcontextprotocol/servers/issues/5641)
   reports `git_branch` leaking a CLI `*` prefix and breaking `git_checkout`, `git_diff`, `git_show`
   and `git_merge`. Tool outputs are contracts consumed by other tools; drift needs a baseline gate.
7. **Path and symlink semantics are contract semantics.** [modelcontextprotocol/servers#5644](https://github.com/modelcontextprotocol/servers/issues/5644)
   shows that a graph file path can be a symlink and that a write replaces the link rather than its
   target. Path-like input properties without containment constraints are a recurring risk class.
8. **Interface drift is hard to diagnose.** [modelcontextprotocol/servers#5636](https://github.com/modelcontextprotocol/servers/issues/5636)
   reports `interface-diff` discarding a git error and reporting the wrong cause. A canonical,
   diffable manifest and stable finding fingerprints reduce this class of failure.

## 3. Why the existing Baysöz Labs portfolio does not cover this

The repository inventory was read from `existing-repos.json`. Closest neighbours and their boundaries:

- `baysoz-reachoracle`: SBOM/AST vulnerability reachability — packages and symbols, not agent tool contracts.
- `baysoz-queryoracle`: PromQL conformance — query language fixtures, not JSON Schema tool interfaces.
- `bolaforge`: OpenAPI 3.1 authorization plan compilation — HTTP authorization, not MCP tool annotations.
- `baysoz-actionlock`: GitHub Actions lockfiles — CI dependency pins, not client-side schema portability.
- `atr-parity-gate`: cross-engine detection-rule parity — detection rules, not `tools/list` schemas.
- `envpair` / `envlens` / `baysoz-logmask`: configuration drift and redaction, not typed agent I/O.
- `planradius`: Terraform plan blast radius — infrastructure plans, not tool-contract drift.

No existing project audits MCP tool schemas for client portability, annotation honesty, injection
surface, secret exposure, schema bloat and baseline drift in one deterministic CI gate.

## 4. Product decision

**Selected project:** `baysoz-mcpcontract` — an offline Python 3.13+ CLI and importable library that
turns MCP `tools/list` exports into a signed-off contract. It emits text, JSON and SARIF 2.1.0
reports with stable rule IDs and fingerprints, and exits non-zero on configured severities.

**Why Python 3.13 + uv:** the analysis is pure graph/JSON work; the standard library (`json`, `re`,
`hashlib`, `dataclasses`, `argparse`) is sufficient. No heavy services, no database, no browser, no
local LLM, no network at analysis time. `uv` supplies reproducible environments and one-command
quality gates.

**Why this is not a toy:** the engine performs recursive JSON Schema resolution with local `$ref`
pointer resolution and cycle detection, composition-feature gating per client profile, nested
property documentation coverage, credential-surface classification, command/path sink analysis,
canonical byte/token budgeting, normalized tool-name collision detection, and a semantic baseline
diff over required parameters, types, enums, defaults, annotations and output schemas. Thirteen
stable rule families are documented and tested with adversarial fixtures.

## 5. Release criteria

The project ships only if unit/integration tests, Ruff (`E,F,W,S,B`) and Semgrep (`p/default`,
`--error`) are clean, and a live adversarial Tribunal run confirms that every reported finding is
reproducible from the input manifest with no stubbed or invented behaviour.
