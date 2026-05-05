# Fallow Python Agent Context

## Project Overview

- Root: `examples/demo_project`
- Entrypoint: `src/app/main.py`
- Demo signals: missing dependency, unused dependency, cycle, duplicate, complexity hotspot, boundary violation

## Recommended Inspection Order

1. Fix `missingdep` or declare it if runtime code needs it.
2. Review the `app.cycle_a` / `app.cycle_b` import cycle.
3. Inspect `app.domain.service` because it violates the demo boundary rule.
4. Review duplicate blocks in `dupe_one.py` and `dupe_two.py`.
5. Treat dead-code candidates as review items, not automatic deletions.

## Known Uncertainty

The demo includes dynamic import uncertainty through `importlib.import_module(NAME)`.

