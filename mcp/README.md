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
