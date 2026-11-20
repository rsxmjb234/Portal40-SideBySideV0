---
inclusion: auto
name: Jira access
description: How to read and update Jira tickets from this workspace using the REST API helper
---

# Jira Access

The MCP Jira server tools may not load in every session. When they don't, use `_jira_api.py` in the project root — a Python helper that calls the Jira REST API v3 directly.

## How it works

- Reads credentials from `~/.kiro/settings/mcp.json` (the same MCP config file) at runtime
- Uses Python's built-in `urllib` — no pip install needed
- Credentials never appear in shell commands (the safety system blocks that)

## Usage

```python
from _jira_api import jira_get, jira_put

# Read a ticket
issue = jira_get('/rest/api/3/issue/IN-3737?fields=summary,status')
print(issue['fields']['summary'])

# Update a ticket (ADF format for description)
jira_put('/rest/api/3/issue/IN-3737', {
    'fields': {
        'summary': 'New title',
        'description': { 'version': 1, 'type': 'doc', 'content': [...] }
    }
})
```

## Quick test

```
python.exe -c "from _jira_api import jira_get; i = jira_get('/rest/api/3/issue/IN-3737?fields=summary'); print(i['key'], i['fields']['summary'])"
```

## Why not MCP directly?

The Jira MCP server (`sutharlabs.jira-mcp`) is configured in `~/.kiro/settings/mcp.json` and works in the IDE, but its tools don't always appear in the agent's tool catalog. This happens when the MCP server didn't connect before the session started. The REST API helper is the reliable fallback. `node` is also not on PATH in the shell environment (Kiro's bundled node is internal to the IDE process).

## Jira instance

- URL: `https://nyec.atlassian.net`
- Key project: IN (e.g., IN-3737)
- Description format: Atlassian Document Format (ADF), not markdown
