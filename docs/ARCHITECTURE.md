# Architecture — Baysöz Labs <baysozlabs@proton.me>

## Purpose

`baysoz-mcpcontract` is a deterministic offline oracle for MCP tool contracts. It answers one
question: can this `tools/list` document be published to target clients without breaking their
parsers, misleading their safety heuristics, or silently changing an existing contract?

## Pipeline

```
JSON / JSONL exports
        |
        v
   loader.py  ----> Manifest(source, tools)
        |
        +--> baseline export --> merge_manifests() --> Manifest("published")
        |
        v
   analyzer.py
        |-- schema_audit.py   recursive JSON Schema walk, $ref resolution, feature gating
        |-- annotation policy readOnly/destructive honesty and high-risk verb classification
        |-- sink policy       command/query injection and path containment checks
        |-- collision policy  normalized tool-name ambiguity across servers
        `-- drift engine      required/type/enum/default/annotation/output baseline diff
        |
        v
   Finding[] (rule_id, severity, path, message, remediation, sha256 fingerprint)
        |
        v
   reports.py --> text | json | sarif 2.1.0 --> stdout or file --> CI exit status
```

## Modules

| Module | Responsibility |
| --- | --- |
| `model.py` | Immutable `Tool`, `Manifest`, `Profile`, `Finding` and verb/name classifiers. |
| `profiles.py` | Four portability profiles and the 13-rule catalogue with stable IDs. |
| `loader.py` | Reads `tools/list` responses, wrapper objects, arrays, standalone tools and JSONL streams. |
| `schema_audit.py` | Recursive schema validation, local `$ref` resolution/cycle detection, cost metrics. |
| `analyzer.py` | Orchestrates structural, safety, collision and drift findings. |
| `reports.py` | Canonical text, JSON and SARIF renderers. |
| `cli.py` | `check`, `profiles`, `rules`, `normalize` commands and exit-code policy. |

## Determinism contract

- No clock, randomness, environment-dependent paths, network calls or LLM calls in analysis.
- All rendered JSON uses sorted keys and compact/constant separators where applicable.
- Findings are sorted by `(source, tool, path, rule_id, message)`.
- Fingerprints are the first 16 hex characters of SHA-256 over the finding's canonical material.
- Rule IDs and severities are stable across releases; new rules must be added, never renumbered.

## Portability profiles

Profiles are explicit, inspectable policy objects, not claims of vendor truth:

- `mcp-2025-06-18`: full JSON Schema composition support, generous budgets.
- `claude-code-2026`: rejects `$ref`, `$defs`, `anyOf`, `oneOf`; requires annotations.
- `gemini-antigravity-2026`: rejects untyped items and composition; tighter budgets.
- `enterprise-strict`: flat schemas, full descriptions, annotations and structured mutating outputs.

## Rule families

`MCP001` structure, `MCP002` schema validity, `MCP003` unsupported feature, `MCP004` documentation,
`MCP005` annotation honesty, `MCP006` secret surface, `MCP007` path containment, `MCP008` bloat,
`MCP009` normalized name collision, `MCP010` output contract, `MCP011` baseline drift, `MCP012`
command sink, `MCP013` reference integrity.

## Failure model

Invalid CLI input and unreadable manifests return exit code 2. Policy findings return 0 or 1
according to `--fail-on`. SARIF output always includes the complete rule catalogue so CI systems can
render suppressions without a second data source.

## Extension points

Add a profile in `profiles.py`, add a rule to the catalogue plus an analyzer check, and cover it with
an adversarial fixture. Keep analysis purely functional so the same manifest always produces the same
report.
