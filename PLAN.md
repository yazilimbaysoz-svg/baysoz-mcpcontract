# Plan — Baysöz Labs <baysozlabs@proton.me>

## Phase 0 — Evidence and boundary setting (complete)

- Inspected `existing-repos.json` and excluded adjacent domains already covered.
- Mined `gh search repos` and `gh search issues` for high-star MCP ecosystem signals.
- Selected tool-contract portability, safety and drift gating as the unclaimed production need.

## Phase 1 — Enterprise skeleton (complete)

- `src/baysoz_mcpcontract/`, `tests/`, `docs/`, `.github/workflows/ci.yml`.
- Documentation: `MARKET_RESEARCH.md`, `ARCHITECTURE.md`, `PLAN.md`, `SECURITY.md`, `CHANGELOG.md`,
  `README.md`, MIT `LICENSE`.
- Explicit Baysöz Labs <baysozlabs@proton.me> attribution in every public file and CLI surface.

## Phase 2 — Engine (complete)

- Deterministic loaders for `tools/list`, arrays, standalone tools and JSONL.
- Recursive schema audit with local `$ref` resolution, cycle detection and feature gating.
- Safety, documentation, bloat, collision, output and drift rule families.
- Text, JSON and SARIF 2.1.0 renderers with stable fingerprints.

## Phase 3 — Quality gates (complete — 2026-11-23)

Required commands, in order:

```
uv venv
uv pip install -e .
uv pip install pytest
uv run pytest -q
ruff check --select E,F,W,S,B .
semgrep --config p/default --error .
```

Definition of done: zero test failures, zero Ruff findings, zero Semgrep findings. Verified result:
32 tests passed, 0 Ruff findings, 0 Semgrep findings (325 rules, 39 files). GitHub Actions tags were
pinned to full commit SHAs to clear the supply-chain lint rule.

## Phase 4 — Supreme Grand Jury Tribunal (complete — UNANIMOUS PASS, 2026-11-23)

- Correctness juror: PASS — all 15 adversarial findings map to concrete defects in the input document.
- Determinism juror: PASS — repeat analyses and reports are byte-identical, fingerprints stable.
- Security juror: PASS — 13/13 rules present; secret, command-sink, path and `$ref` cycle defects confirmed.
- Documentation juror: PASS — attributed `--version`, `--help`, rules and SARIF driver verified.
- Operations juror: PASS — exit codes 0 (clean), 1 (policy failure), 0 (`--fail-on never`), 2 (bad profile).
- Verdict: no stubs, no hallucinations, unanimous release approval.

## Phase 5 — Publication (pending)

- Create the public repository under `yazilimbaysoz-svg` with description and topics.
- Write the strictly valid showcase JSON result file without touching other showcase files.
