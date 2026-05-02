# Publishing Checklist

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
- Set real project URLs in `pyproject.toml` before the v0.1.0 release.
- Update version consistently.
- Update `CHANGELOG.md`.
- Verify `examples/demo_project` commands still work.

## Before First GitHub Release

- Create the GitHub repository.
- Push code.
- Check GitHub Actions on all configured Python versions.
- Set repository description:
  `Python-first static codebase intelligence for agents and reviewers.`
- Add topics:
  `python`, `static-analysis`, `code-intelligence`, `ai-agents`, `sarif`, `dead-code`, `architecture`.
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
