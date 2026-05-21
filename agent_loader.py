import os
import re

try:
    import yaml
except ImportError:
    yaml = None

class AgentLoader:
    """
    Dynamically loads and parses markdown-based AI agents from the agents/ directory.
    Supports YAML frontmatter for structured metadata and extracts markdown text blocks.
    """
    
    def __init__(self, agents_dir: str = "agents"):
        # Resolve absolute path to the agents directory
        self.agents_dir = os.path.abspath(agents_dir)
        if not os.path.exists(self.agents_dir):
            os.makedirs(self.agents_dir, exist_ok=True)

    def load_agent(self, agent_name: str) -> dict:
        """
        Loads an agent by name (e.g., 'ceo' or 'ceo.md').
        Returns a dictionary containing parsed frontmatter and clean agent instructions.
        """
        # Clean file name
        if not agent_name.endswith(".md"):
            filename = f"{agent_name}.md"
        else:
            filename = agent_name
            
        file_path = os.path.join(self.agents_dir, filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Agent profile '{filename}' not found in {self.agents_dir}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse YAML frontmatter and raw markdown content
        metadata, markdown_content = self._parse_file_content(content)
        
        # Build system prompt/instructions from the parsed contents
        system_prompt = self._compile_system_prompt(metadata, markdown_content)
        
        return {
            "name": metadata.get("name", agent_name.replace(".md", "")),
            "role": metadata.get("role", "Specialized Agent"),
            "goals": metadata.get("goals", []),
            "tools": metadata.get("tools", []),
            "rules": metadata.get("rules", []),
            "metadata": metadata,
            "raw_markdown": markdown_content,
            "system_prompt": system_prompt
        }

    def list_available_agents(self) -> list:
        """
        Scans the agents/ directory and returns list of names of available agents.
        """
        if not os.path.exists(self.agents_dir):
            return []
        return [f.replace(".md", "") for f in os.listdir(self.agents_dir) if f.endswith(".md")]

    def _parse_file_content(self, content: str) -> tuple:
        """
        Splits the file into YAML frontmatter and Markdown body.
        """
        metadata = {}
        markdown_body = content
        
        # Regex to capture YAML block between triple hyphens at start of file
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        
        if frontmatter_match:
            frontmatter_str = frontmatter_match.group(1)
            markdown_body = content[frontmatter_match.end():]
            
            # Try to parse using PyYAML
            if yaml:
                try:
                    metadata = yaml.safe_load(frontmatter_str) or {}
                except Exception as e:
                    print(f"[Warning] Failed to parse frontmatter via YAML: {e}. Falling back to manual parsing.")
                    metadata = self._manual_parse_frontmatter(frontmatter_str)
            else:
                metadata = self._manual_parse_frontmatter(frontmatter_str)
                
        return metadata, markdown_body.strip()

    def _manual_parse_frontmatter(self, frontmatter_str: str) -> dict:
        """
        Fallback simple parser for frontmatter in case PyYAML is not installed.
        Supports key-value pairs and simple list bullet points.
        """
        metadata = {}
        current_key = None
        
        for line in frontmatter_str.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            
            # Check if this is a list item under a key
            if line_str.startswith("-") and current_key:
                val = line_str[1:].strip()
                # Remove quotes if present
                if val.startswith(('"', "'")) and val.endswith(('"', "'")):
                    val = val[1:-1]
                if not isinstance(metadata[current_key], list):
                    metadata[current_key] = []
                metadata[current_key].append(val)
                continue
                
            # Key-Value split
            if ":" in line_str:
                parts = line_str.split(":", 1)
                key = parts[0].strip()
                val = parts[1].strip()
                
                # Check if it starts a list or holds value
                if not val:
                    metadata[key] = []
                    current_key = key
                else:
                    if val.startswith(('"', "'")) and val.endswith(('"', "'")):
                        val = val[1:-1]
                    metadata[key] = val
                    current_key = None
                    
        return metadata

    def _compile_system_prompt(self, metadata: dict, markdown_content: str) -> str:
        """
        Compiles structural metadata and raw markdown instructions into a detailed system prompt.
        """
        local_mode = os.getenv("LOCAL_MODEL_MODE", "false").lower() == "true"
        
        def _stringify_list(items):
            res = []
            for item in items:
                if isinstance(item, dict):
                    # For YAML lists of single key-value dicts (e.g. - tool_name: tool_desc)
                    for k, v in item.items():
                        res.append(f"{k}: {v}")
                else:
                    res.append(str(item))
            return res

        prompt_parts = []
        if local_mode:
            prompt_parts.append(f"ROLE: {metadata.get('name', 'Agent')} - {metadata.get('role', 'Specialist')}")
            if metadata.get("goals"):
                # Only include first 3 goals max
                goals_list = _stringify_list(metadata["goals"])[:3]
                prompt_parts.append("GOALS: " + " | ".join(goals_list))
            if metadata.get("rules"):
                rules_list = _stringify_list(metadata["rules"])[:2]
                prompt_parts.append("RULES: " + " | ".join(rules_list))
            if metadata.get("tools"):
                prompt_parts.append("TOOLS: " + ", ".join(_stringify_list(metadata["tools"])))
            
            # Aggressively compress markdown content for local models
            compact_md = re.sub(r'#+\s+', '', markdown_content)
            compact_md = re.sub(r'\n{2,}', '\n', compact_md)
            compact_md = re.sub(r'[*_`#>]', '', compact_md)  # Strip markdown formatting
            compact_md = re.sub(r'\s{2,}', ' ', compact_md)  # Collapse whitespace
            # Truncate to max 500 chars to save tokens
            if len(compact_md) > 500:
                compact_md = compact_md[:500] + "..."
            prompt_parts.append("CONTEXT:\n" + compact_md.strip())
        else:
            prompt_parts.append(f"# IDENTITY")
            prompt_parts.append(f"Name: {metadata.get('name', 'AI Agent')}")
            prompt_parts.append(f"Role: {metadata.get('role', 'Specialized Workforce Unit')}\n")
            
            if metadata.get("goals"):
                prompt_parts.append("## PRIMARY GOALS")
                for goal in _stringify_list(metadata["goals"]):
                    prompt_parts.append(f"- {goal}")
                prompt_parts.append("")
                
            if metadata.get("rules"):
                prompt_parts.append("## OPERATIONAL RULES & CONSTRAINTS")
                for rule in _stringify_list(metadata["rules"]):
                    prompt_parts.append(f"- {rule}")
                prompt_parts.append("")

            if metadata.get("tools"):
                prompt_parts.append("## ASSIGNED TOOLS (Capabilities)")
                for tool in _stringify_list(metadata["tools"]):
                    prompt_parts.append(f"- {tool}")
                prompt_parts.append("")
                
            prompt_parts.append("# PROFILE DETAILS & INSTRUCTIONS")
            prompt_parts.append(markdown_content)
        
        return "\n".join(prompt_parts)

# Simple self-test validation when run directly
if __name__ == "__main__":
    loader = AgentLoader(agents_dir="agents")
    try:
        ceo_data = loader.load_agent("ceo")
        print("CEO Loaded Successfully!")
        print(f"Name: {ceo_data['name']}")
        print(f"Role: {ceo_data['role']}")
        print(f"Goals count: {len(ceo_data['goals'])}")
        print(f"Tools count: {len(ceo_data['tools'])}")
    except Exception as e:
        print(f"Self-test failed: {e}")
