# baysoz-mcpcontract

[![CI](https://github.com/yazilimbaysoz-svg/baysoz-mcpcontract/actions/workflows/ci.yml/badge.svg)](https://github.com/yazilimbaysoz-svg/baysoz-mcpcontract/actions/workflows/ci.yml)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Maintained by Baysöz Labs](https://img.shields.io/badge/maintained%20by-Bays%C3%B6z%20Labs-orange)](mailto:baysozlabs@proton.me)

**Deterministic offline MCP tool-contract conformance, portability and drift gate with SARIF CI
enforcement — Baysöz Labs <baysozlabs@proton.me>.**

`baysoz-mcpcontract` turns a Model Context Protocol `tools/list` export into an enforceable contract.
It finds schemas that break in real clients, annotations that mislead autonomous agents, secret and
command/path sinks, oversized tool listings, normalized name collisions and semantic drift from a
published baseline. No network calls, no services, no local LLMs: pure Python 3.13+ analysis with a
stable CLI and importable library API.

## Why it exists

Live 2026 ecosystem evidence: clients strip `$ref`/`$defs`/`anyOf`/`oneOf` from tool schemas,
untyped array items prevent agent startup, most reference-server properties lack descriptions, tool
lists cost thousands of tokens per session, and output-shape drift breaks downstream tools. Full
evidence and the portfolio gap analysis are in [docs/MARKET_RESEARCH.md](docs/MARKET_RESEARCH.md).

## Install

```bash
git clone https://github.com/yazilimbaysoz-svg/baysoz-mcpcontract.git
cd baysoz-mcpcontract
uv venv
uv pip install -e .
uv pip install pytest
```

Verify the installed CLI:

```bash
uv run mcpcontract --version
uv run mcpcontract --help
```

## Real CLI output

Verified on 2026-11-23 with the installed CLI (`uv run mcpcontract ...`):

```text
$ mcpcontract --version
mcpcontract 0.1.0 | Baysöz Labs <baysozlabs@proton.me>

$ mcpcontract check tests/fixtures/tools_clean.json --profile enterprise-strict --format text
baysoz-mcpcontract 0.1.0 | profile enterprise-strict
Baysöz Labs <baysozlabs@proton.me>

Sources: 1 | findings: 0 (error=0, warning=0, note=0)

PASS: no contract violations detected.

Reported by Baysöz Labs <baysozlabs@proton.me>

$ mcpcontract check tests/fixtures/tools_unsafe.json --profile claude-code-2026 --format text  # selected findings
baysoz-mcpcontract 0.1.0 | profile claude-code-2026
Baysöz Labs <baysozlabs@proton.me>

Sources: 1 | findings: 15 (error=13, warning=2, note=0)

[ERROR  ] MCP005 shell_exec annotations.destructiveHint @ tests/fixtures/tools_unsafe.json
          high-risk operation requires annotations.destructiveHint=true
          fix: Set annotations.destructiveHint/readOnlyHint to match the tool's actual effect.
[ERROR  ] MCP003 shell_exec inputSchema.$defs @ tests/fixtures/tools_unsafe.json
          schema construct '$defs' is not portable to profile claude-code-2026
          fix: Inline or flatten the construct, or select a profile that supports it.
[ERROR  ] MCP012 shell_exec inputSchema.properties.command @ tests/fixtures/tools_unsafe.json
          free-form command/query property 'command' is an injection sink
          fix: Replace free-form command/query inputs with enumerated operations or a validated grammar.
[ERROR  ] MCP002 shell_exec inputSchema.properties[batch].items @ tests/fixtures/tools_unsafe.json
          array items have no type or composition keyword
          fix: Correct schema keyword types, required members, enum/default values and regex patterns.
[WARNING] MCP007 shell_exec inputSchema.properties[file_path] @ tests/fixtures/tools_unsafe.json
          path-like property 'file_path' has no containment constraint
          fix: Constrain path/URL properties with pattern, enum, const or a documented containment rule.
[ERROR  ] MCP006 shell_exec outputSchema.properties[api_key] @ tests/fixtures/tools_unsafe.json
          secret-like property 'api_key' is exposed in the output schema
          fix: Mark secret inputs with writeOnly or format=password and never emit them in outputs.

Reported by Baysöz Labs <baysozlabs@proton.me>
```

## Usage

```bash
# Gate a tools/list export against the baseline portability profile
uv run mcpcontract check manifest.json --profile mcp-2025-06-18 --format text

# Strict enterprise gate with SARIF for GitHub code scanning
uv run mcpcontract check ./manifests/ \
  --profile enterprise-strict \
  --baseline ./baselines/production.json \
  --format sarif --output results.sarif

# JSON for custom CI dashboards
uv run mcpcontract check manifest.json --format json

# Inspect policy or canonicalize a manifest for golden diffs
uv run mcpcontract profiles --name claude-code-2026
uv run mcpcontract rules --rule MCP011
uv run mcpcontract normalize manifest.json --output canonical.json
```

Exit codes: `0` = gate satisfied, `1` = findings at or above `--fail-on` (default `error`),
`2` = invalid input. Use `--fail-on warning` for stricter gates or `--fail-on never` for reporting.

## Architecture

```
exported tools/list JSON/JSONL
          |
      loader.py -> Manifest
          |
      analyzer.py
        |-- schema_audit.py (refs, cycles, feature gating, cost)
        |-- annotation, sink, collision and drift policies
          |
      Finding[] with stable SHA-256 fingerprints
          |
      reports.py -> text | json | sarif 2.1.0 -> CI gate
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for module boundaries, determinism guarantees and
the full rule catalogue. [docs/PLAN.md](docs/PLAN.md), [SECURITY.md](SECURITY.md) and
[CHANGELOG.md](CHANGELOG.md) complete the enterprise documentation set.

## Library use

```python
from baysoz_mcpcontract.analyzer import analyze
from baysoz_mcpcontract.loader import load_manifests, merge_manifests
from baysoz_mcpcontract.profiles import get_profile

manifests = load_manifests(["manifest.json"])
baseline = merge_manifests(load_manifests(["production.json"]), source="production")
findings = analyze(manifests, get_profile("enterprise-strict"), baseline)
assert not [finding for finding in findings if finding.severity == "error"]
```

## Quality gates

```bash
uv venv && uv pip install -e . && uv pip install pytest
uv run pytest -q
ruff check --select E,F,W,S,B .
semgrep --config p/default --error .
```

## Attribution

Created and maintained by **Baysöz Labs <baysozlabs@proton.me>**. Licensed under the
[MIT License](LICENSE). No legal entity suffix is used or implied.
