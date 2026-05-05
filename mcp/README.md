# pyfallow-mcp

MCP server package for `pyfallow`.

Install locally from this repository:

```bash
python -m pip install -e ../
python -m pip install -e .
pyfallow-mcp --root /path/to/repo
```

Claude Code `mcp.json` example:

```json
{
  "mcpServers": {
    "pyfallow": {
      "command": "pyfallow-mcp",
      "args": ["--root", "/path/to/repo"]
    }
  }
}
```

The core `pyfallow` package remains stdlib-only. MCP dependencies live in this integration package.

Tools:

- `analyze_diff`: diff-aware pyfallow findings with `agent-fix-plan` classification
- `agent_context`: compact project map for coding agents
- `explain_finding`: deterministic remediation guidance
- `safe_to_remove`: conservative removal classification
- `verify_imports`: pre-edit prediction for planned imports

`analyze_diff` returns the same grouped policy shape as CLI `--format agent-fix-plan`:

```json
{
  "blocking": [],
  "review_needed": [],
  "auto_safe": [],
  "manual_only": [],
  "findings": []
}
```

Agents should prefer the grouped fields (`blocking`, `review_needed`, `auto_safe`, `manual_only`).
The flat `findings` list is kept for backward compatibility and contains the same findings in grouped
order.
