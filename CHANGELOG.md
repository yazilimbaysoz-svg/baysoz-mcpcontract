# Changelog — Baysöz Labs <baysozlabs@proton.me>

All notable changes to this project are documented here. Format follows Keep a Changelog.

## [0.1.0] — 2026-11-23

### Added

- Deterministic MCP `tools/list` loader for JSON, wrapper responses, arrays, standalone tools and
  JSONL streams.
- Recursive JSON Schema audit with local `$ref` resolution, cycle detection, composition-feature
  gating, documentation coverage and cost metrics.
- Thirteen stable rule families covering structure, validity, portability, documentation, annotation
  honesty, secret surfaces, path containment, bloat, name collisions, output contracts, drift,
  command sinks and reference integrity.
- Four inspectable portability profiles: `mcp-2025-06-18`, `claude-code-2026`,
  `gemini-antigravity-2026` and `enterprise-strict`.
- Baseline drift detection with severity-graded findings.
- Text, JSON and SARIF 2.1.0 reporters with stable finding fingerprints.
- CLI commands: `check`, `profiles`, `rules`, `normalize`.
- Enterprise documentation, MIT license, CI workflow and adversarial test suite.

Maintained by Baysöz Labs <baysozlabs@proton.me>.
