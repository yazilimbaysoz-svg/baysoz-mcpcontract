# Security Policy — Baysöz Labs <baysozlabs@proton.me>

## Scope

This project analyses untrusted MCP tool manifests. It does not execute tools, spawn servers, send
network requests, load local models or read files other than those passed on the command line.

## Threat model and mitigations

| Threat | Mitigation |
| --- | --- |
| Malformed JSON / hostile schemas | Pure parsing; recursion depth and property budgets are profile-limited. |
| `$ref` cycles and pointer escape | Only local `#/` pointers are resolved; cycles are reported as `MCP013`. |
| Regex denial of service in patterns | Patterns are compiled for validity only; the tool never evaluates them against attacker input. |
| Credential leakage in tool I/O | `MCP006` flags secret-shaped inputs and outputs; no values are logged. |
| Command/path injection sinks | `MCP012` and `MCP007` flag unconstrained command, query and path properties. |
| Silent contract downgrade | `MCP011` compares against a published baseline and gates breaking changes. |
| Unstable CI results | No clock, randomness or environment data in analysis; stable finding fingerprints. |

## Safe usage

- Run `mcpcontract check` on exported manifests in CI before publishing a tool server.
- Keep baseline snapshots in version control and review every `MCP011` finding.
- Treat SARIF output as build evidence; it contains file paths and tool names, not secret values.
- Do not place real credentials in fixtures; use inert placeholders.

## Vulnerability reporting

Report security issues privately to **baysozlabs@proton.me** with a minimal reproducer, affected
version and expected impact. Please do not open public issues for undisclosed vulnerabilities.

## Security gates

Every change must pass `semgrep --config p/default --error .` and `ruff check --select E,F,W,S,B .`
in addition to the full test suite. Security-relevant rule changes require a new adversarial test.

Maintained by Baysöz Labs <baysozlabs@proton.me>.
