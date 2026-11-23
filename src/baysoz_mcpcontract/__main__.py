# SPDX-License-Identifier: MIT
# Baysöz Labs <baysozlabs@proton.me>

"""Module entry point for python -m baysoz_mcpcontract."""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
