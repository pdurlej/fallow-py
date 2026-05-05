# 0005 — Alpha-incremental release strategy

**Date:** 2026-05-04
**Status:** accepted
**Phase:** A5
**Authors:** Claude Opus 4.7 (orchestrator), Codex (executor), operator (`pdurlej`) decision-maker

## Context

After Phase A landed (5 atomic commits A1-A5), pyfallow needed a release decision before TestPyPI publish. Pre-Phase-A versions were `pyfallow 0.3.0-alpha.1` and `pyfallow-mcp 0.1.0-alpha.1`. Phase A introduced a **breaking change** to MCP wire format: `safe_to_remove.decision` switched from hyphen to underscore namespace (per ADR 0001). Whatever release strategy we choose has to bump versions.

Three options considered:

- **(α) Alpha-incremental:** bump to `pyfallow 0.3.0a2` and `pyfallow-mcp 0.1.0a2`, retain alpha tag
- **(β) Skip-to-stable:** publish `0.3.0` and `0.1.0` non-alpha
- **(γ) Minor bump (still alpha):** `0.4.0a1` / `0.2.0a1`, bigger semver delta to signal breaking change

## Decision

**(α) Alpha-incremental.** Versions bumped to `0.3.0a2` and `0.1.0a2` (PEP 440 normalized form of the previous `0.3.0-alpha.X` style).

Rationale: a stable tag (option β) before Phase B would mis-sell the analyzer's state. Phase B has HIGH-severity engineering findings still unfixed (Tarjan recursion crash, walrus operator FP, two confirmed framework FPs on SQLAlchemy and async generators, MCP root sandboxing, etc.) — see Phase B issues #4-#15. Calling Phase A "stable" while those known defects ride on top would either lie to users or force an immediate `0.3.1` patch sprint. Neither is healthy.

Option γ (minor bump) was rejected because the breaking change is contained to MCP `safe_to_remove.decision` field, and `pyfallow-mcp` was not yet on PyPI — there are no external clients to migrate. The semver "breaking change" weight is mostly performative in this case. Alpha label communicates instability well enough.

Subsequent releases follow the same pattern (a3, a4, ...) until Phase B/C land based on dogfood evidence (per ADR 0008), at which point the next release drops the alpha tag as `0.3.0` stable. That tag transition is operator's deliberate decision, not automated.

## Consequences

**Positive:**
- TestPyPI publish completed cleanly. URLs:
  - https://test.pypi.org/project/pyfallow/0.3.0a2/
  - https://test.pypi.org/project/pyfallow-mcp/0.1.0a2/
- Fresh-venv install smoke (Python 3.12.12) passed: `pyfallow --version`, `pyfallow analyze`, `pyfallow-mcp --help` all worked. A1 invariant verified live on installed package.
- README and changelog can honestly say "alpha — fixes incoming during dogfood window."

**Negative:**
- Production PyPI publish is intentionally not done yet. Users wanting to install pyfallow from pypi.org will get the stale `0.1.0` (whoever previously held the name; pdurlej confirmed account ownership). Workaround: pin from TestPyPI per `docs/dogfood.md` until `0.3.0` stable lands.

**Neutral:**
- BW vault item for TestPyPI token (`test.pypi.org`, custom field `API token`) was retrieved by orchestrator with operator's explicit BW_SESSION authorization in chat. Production PyPI publish remains operator's manual click; orchestrator does not handle the prod-PyPI flow.

## References

- Implementation: PR #2 (Forgejo) — commit `11c0a31`, branch `feat/phase-a-ship-blockers`
- TestPyPI upload: orchestrator night shift 2026-05-04, BW item `test.pypi.org`
- Smoke verification: PR #1 + PR #2 comments by `claude` user
- Phase B issues #4-#15 (Forgejo) — what's blocking the alpha→stable transition
