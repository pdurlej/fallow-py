# Agent Integration

pyfallow is designed to give coding agents a deterministic static-analysis checkpoint before they claim Python work is complete. The recommended integration path is the `pyfallow-mcp` package plus an agent rule or skill that tells the model when to call it.

## Install From A Checkout

```bash
python -m pip install -e ".[dev]"
python -m pip install -e ./mcp
pyfallow-mcp --root /absolute/path/to/repo
```

The core `pyfallow` package remains stdlib-only at runtime. MCP dependencies live in the separate `pyfallow-mcp` package.

## Claude Code

Copy the bundled skill into a repository-local Claude skills directory:

```bash
mkdir -p .claude/skills
cp -R examples/claude-skill/pyfallow-cleanup .claude/skills/
```

Configure the MCP server:

```json
{
  "mcpServers": {
    "pyfallow": {
      "command": "pyfallow-mcp",
      "args": ["--root", "/absolute/path/to/repo"]
    }
  }
}
```

The skill is in [`examples/claude-skill/pyfallow-cleanup/`](../examples/claude-skill/pyfallow-cleanup/). It instructs the agent to call pyfallow before commits, after multi-file Python edits, and before marking work complete.

## Cursor

Copy the Cursor mirror rule into your project:

```bash
mkdir -p .cursor/rules
cp examples/cursor-rules/pyfallow.mdc .cursor/rules/pyfallow.mdc
```

The rule is always-on for Python files and asks Cursor to use MCP when available, or fall back to the CLI:

```bash
pyfallow analyze --root . --since HEAD --format json --min-confidence medium
```

## Recommended Agent Workflow

1. Call `pyfallow.analyze_diff(since="HEAD", min_confidence="medium")` before commit, or use the branch base ref for PR cleanup.
2. For each finding, call `pyfallow.explain_finding`.
3. Auto-fix only findings classified as `auto_safe`.
4. Show `review_needed` findings to the user.
5. Stop on `blocking` findings. Do not commit or claim completion.
6. Re-run diff analysis after edits.

Blocking findings include parse/config errors, missing runtime dependencies, circular dependencies, and architecture boundary violations.

## Tools

- `analyze_diff`: diff-aware findings for the current change
- `agent_context`: concise project map for planning and review
- `explain_finding`: remediation guidance and safety classification
- `safe_to_remove`: conservative removal classification by fingerprint
- `verify_imports`: current Sprint 2 stub returning `not_implemented`; full pre-edit verification is planned next

## Release Assets

Small zip bundles are checked in under `examples/` for first-release convenience:

- `examples/claude-skill/claude-skill-pyfallow-cleanup-v0.3.0.zip`
- `examples/cursor-rules/cursor-rules-pyfallow-v0.3.0.zip`

They contain the same text files as the source directories and should be regenerated when those files change.

## Limitations

Agent triggers are heuristic. Claude Code skills and Cursor rules improve the odds that a model runs pyfallow at the right time, but they cannot guarantee deterministic tool use. CI should still run `pyfallow analyze --fail-on warning --min-confidence medium` or an equivalent baseline-aware command.
