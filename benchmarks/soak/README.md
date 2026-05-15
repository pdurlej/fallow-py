# fallow-py Multi-Model Soak Harness

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
- `findings.json`: fallow-py `agent-fix-plan` output when execution is enabled
- `agent_output.md`: opencode output when opencode execution is enabled
- `time.json`: timing and return-code metadata
- `human_classification.md`: reviewer template for TP/FP/disputed calibration

The harness uses only Python stdlib. It shells out to `git`, `python -m fallow_py`, and optionally `opencode` when `--execute` is passed.

## GLM/OpenCode guardrails

The soak harness treats GLM-5.1 and other non-frontier models as candidate generators, not autonomous maintainers. Larger contexts can make the model drift from the task, so `run.py` now applies these guardrails before invoking OpenCode:

- `opencode --pure` is always used.
- A per-run sterile `HOME` is created under the result directory.
- The generated OpenCode config sets `share: disabled` and `mcp: {}`.
- Shell, web fetch/search, and external-directory access are denied.
- File edits/writes require approval; the harness records model output instead of opening PRs.
- Project-level OpenCode config files cause the OpenCode step to skip by default until reviewed.
- The prompt explicitly tells the model not to invent findings, not to remove unrelated code to satisfy fallow-py, and to return `no_patch` when evidence is ambiguous.

For Z.ai Coding Plan users, `glm-5-1` uses the Coding endpoint:

```text
https://api.z.ai/api/coding/paas/v4
```

Set `Z_AI_API_KEY` in the parent shell before executing the GLM row. Do not use the general Z.ai API endpoint for Coding Plan quota; it is billed separately and may return an insufficient-balance error even when Coding Plan is active.

Unsafe escape hatches exist only for manual debugging:

```bash
python benchmarks/soak/run.py --repo requests --model glm-5-1 --execute --allow-host-opencode-config
python benchmarks/soak/run.py --repo requests --model glm-5-1 --execute --allow-project-opencode-config
```

Do not use those flags for publishable dogfood evidence unless the evidence log explains why the extra authority was necessary.
