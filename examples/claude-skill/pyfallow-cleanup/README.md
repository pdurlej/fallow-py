# pyfallow-cleanup Claude Code Skill

This example skill tells Claude Code when and how to call the `pyfallow-mcp` server during Python cleanup, review, and commit workflows.

## Install

From this repository:

```bash
mkdir -p .claude/skills
cp -R examples/claude-skill/pyfallow-cleanup .claude/skills/
python -m pip install -e ".[dev]"
python -m pip install -e ./mcp
```

Configure the MCP server in Claude Code:

```json
{
  "mcpServers": {
    "pyfallow": {
      "command": "pyfallow-mcp",
      "args": ["--root", "/absolute/path/to/your/repo"]
    }
  }
}
```

Restart Claude Code after installing the skill and MCP server.

## Manual Smoke Test

1. Open a Python repository with a Git history.
2. Edit 3 Python files, including one intentionally missing dependency import.
3. Ask Claude Code to finish or commit.
4. Confirm the skill calls `pyfallow.analyze_diff`.
5. Confirm blocking findings stop the commit path.
6. Confirm review-needed findings are surfaced instead of auto-fixed.

`pyfallow.verify_imports` is included in the skill surface, but v0.2 intentionally returns `not_implemented`; use it only as a stable call shape for the v0.3 implementation.
