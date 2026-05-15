# Publishing Checklist

## Current Public State

- Forgejo canonical repo: `https://git.pdurlej.com/pdurlej/fallow-py`.
- GitHub mirror: `https://github.com/pdurlej/fallow-py`.
- Current alpha versions: `fallow-py 0.3.0a3` and `fallow-py-mcp 0.1.0a3`.
- GitHub repository topics are set. Forgejo topics require an operator/admin account;
  `codex` cannot update them with its current permissions.

## Before Pushing

- Remove generated files: `build/`, `dist/`, `*.egg-info/`, caches, `.DS_Store`, and local editor state.
- Run `python -m compileall -q src tests`.
- Run `python -m pytest -q`.
- Run CLI smoke commands for JSON, text, SARIF, baseline, and agent-context output.
- Run `python -m build`.
- Run `python -m twine check dist/*`.
- Inspect README for current commands and non-affiliation language.
- Inspect `LICENSE`.
- Inspect GitHub templates.
- Verify project URLs in `pyproject.toml` still point at `pdurlej/fallow-py`.
- Update version consistently.
- Update `CHANGELOG.md`.
- Verify `examples/demo_project` commands still work.

## Before First GitHub Release

- Create the GitHub repository.
- Push code.
- Check GitHub Actions on all configured Python versions.
- Set repository description:
  `Deterministic Python codebase intelligence for AI agents before they claim done.`
- Add topics:
  `python`, `static-analysis`, `code-intelligence`, `ai-agents`, `sarif`, `dead-code`, `architecture`, `dependency-analysis`.
- Check GitHub Community Standards.
- Create the release from the changelog.
- Do not publish to PyPI until package metadata and name ownership are confirmed.

## Before PyPI

- Confirm package name availability.
- Build locally.
- Run `twine check`.
- Upload to TestPyPI first.
- Install from TestPyPI in a clean virtual environment.
- Run CLI smoke commands from the TestPyPI install.
- Only then publish to PyPI.
