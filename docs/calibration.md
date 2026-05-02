# Calibration

This page tracks real-world calibration from the multi-model soak in `benchmarks/soak/`.

The v0.3.0-alpha.1 infrastructure is checked in, but the full 50-run soak is not committed here. Maintainers should run the matrix, classify findings in each `human_classification.md`, then update this document before a wider public announcement.

## Soak Matrix

- Repositories: 10 pinned Python repositories in `benchmarks/soak/repos.toml`
- Models: 5 configured models in `benchmarks/soak/models.toml`
- Planned runs: 50
- Primary output: `agent-fix-plan`
- Human classification labels: true-positive, false-positive, disputed

## Rule Calibration

| Rule | TP rate | FP rate | Recommended default | Notes |
| --- | ---: | ---: | --- | --- |
| parse-error | pending | pending | blocking | Should remain high confidence when parser location is precise. |
| missing-runtime-dependency | pending | pending | blocking | Watch for vendored/local package naming ambiguity. |
| circular-dependency | pending | pending | blocking/review | Type-only cycles should stay review-needed. |
| unused-module | pending | pending | review-needed | Dynamic loading and frameworks are the main FP surface. |
| unused-symbol | pending | pending | review/manual | Public API and framework callbacks need conservative treatment. |
| duplicate-code | pending | pending | review-needed | Similar shape can still represent different domain concepts. |
| high-complexity | pending | pending | review-needed | Thresholds may need per-project tuning. |
| boundary-violation | pending | pending | configured severity | Depends on whether rules match intended architecture. |

## Calibration Procedure

1. Run a dry plan first:

   ```bash
   python benchmarks/soak/run.py --repo requests --model qwen-9b --dry-run
   ```

2. Run pyfallow-only shakedown:

   ```bash
   python benchmarks/soak/run.py --repo requests --model qwen-9b --execute --skip-opencode
   ```

3. Run the full matrix when opencode/Ollama credentials and local models are ready:

   ```bash
   python benchmarks/soak/run.py --repo all --model all --execute
   ```

4. Fill each generated `human_classification.md` from `findings.json`.
5. Update the table above with per-rule true-positive and false-positive rates.
6. If any rule exceeds a 30% false-positive rate, record a mitigation in `DECISIONS.md` before release.

## Current Status

Calibration data is pending. Until the full soak is classified, v0.3.0-alpha.1 messaging should describe the analyzer as early and evidence-carrying, not as production-perfect.
