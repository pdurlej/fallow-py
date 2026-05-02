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

- `analyze_diff`: diff-aware pyfallow findings
- `agent_context`: compact project map for coding agents
- `explain_finding`: deterministic remediation guidance
- `safe_to_remove`: conservative removal classification
- `verify_imports`: pre-edit prediction for planned imports
