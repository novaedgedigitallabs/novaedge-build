# Tools Directory

This folder is designated for third-party integrations, custom script bindings, and external services callable by agents.

## Future Architecture: Dynamic Tool Execution
To register a new tool for agents to call:
1. Create a Python script in this folder (e.g., `web_search.py` or `db_query.py`).
2. Add its functional definition to the tools schema in `main.py`.
3. Map the runtime call routing under `execute_tool()` inside `main.py`.
4. Include the tool name in the agent's markdown YAML metadata frontmatter (`tools: [...]`).
