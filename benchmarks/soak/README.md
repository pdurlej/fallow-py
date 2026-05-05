# pyfallow Multi-Model Soak Harness

This directory contains reproducible infrastructure for the v0.3 real-world soak. It does not check in full run artifacts.

Basic usage:

```bash
python benchmarks/soak/run.py --list
python benchmarks/soak/run.py --repo requests --model qwen-9b --dry-run
python benchmarks/soak/run.py --repo requests --model glm-5-1 --execute --skip-opencode
python benchmarks/soak/run.py --repo all --model all --execute
```

Generated repositories live under `benchmarks/soak/workspace/` by default. Generated artifacts live under `benchmarks/soak/results/<repo>/<model>/`.

Each run writes:

- `plan.json`: deterministic run plan and command lines
- `findings.json`: pyfallow `agent-fix-plan` output when execution is enabled
- `agent_output.md`: opencode output when opencode execution is enabled
- `time.json`: timing and return-code metadata
- `human_classification.md`: reviewer template for TP/FP/disputed calibration

The harness uses only Python stdlib. It shells out to `git`, `python -m pyfallow`, and optionally `opencode` when `--execute` is passed.
