import os
import json

class AgentCreator:
    """
    Handles the dynamic generation, registration, and templating of new specialized AI agents.
    Allows the CEO Agent to expand the workforce dynamically.
    """
    
    def __init__(self, agents_dir: str = "agents", registry_path: str = "configs/agents_registry.json"):
        self.agents_dir = os.path.abspath(agents_dir)
        self.registry_path = os.path.abspath(registry_path)
        
        # Ensure directories exist
        os.makedirs(self.agents_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        
        # Initialize registry file if not present
        if not os.path.exists(self.registry_path):
            self._save_registry({})

    def create_agent(self, name: str, role: str, goals: list, rules: list, responsibilities: list, workflows: list, tools: list) -> str:
        """
        Creates a new agent markdown profile, saves it to agents/ directory, and registers it.
        Returns the path to the newly created agent profile.
        """
        # Sanitize name for filename
        safe_name = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in name.lower()])
        if not safe_name.endswith(".md"):
            filename = f"{safe_name}.md"
        else:
            filename = safe_name
            
        file_path = os.path.join(self.agents_dir, filename)
        
        # Format the frontmatter and content
        markdown_content = self.generate_markdown_profile(
            name=name,
            role=role,
            goals=goals,
            rules=rules,
            responsibilities=responsibilities,
            workflows=workflows,
            tools=tools
        )
        
        # Write to disk
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
            
        # Register the agent
        self.register_agent(name, filename, role)
        
        print(f"[AgentCreator] Successfully created and registered agent '{name}' at {file_path}")
        return file_path

    def register_agent(self, name: str, filename: str, role: str):
        """
        Adds the newly created agent to the registry configuration.
        """
        registry = self._load_registry()
        registry[name] = {
            "filename": filename,
            "role": role,
            "status": "active",
            "created_by": "CEOAgent"
        }
        self._save_registry(registry)

    def generate_markdown_profile(self, name: str, role: str, goals: list, rules: list, responsibilities: list, workflows: list, tools: list) -> str:
        """
        Formats agent attributes into the standardized YAML frontmatter + markdown template.
        """
        frontmatter_parts = [
            "---",
            f"name: {name}",
            f"role: {role}",
            "goals:"
        ]
        for goal in goals:
            frontmatter_parts.append(f"  - {goal}")
            
        frontmatter_parts.append("tools:")
        for tool in tools:
            frontmatter_parts.append(f"  - {tool}")
            
        frontmatter_parts.append("rules:")
        for rule in rules:
            frontmatter_parts.append(f"  - {rule}")
            
        frontmatter_parts.append("---")
        frontmatter = "\n".join(frontmatter_parts)
        
        # Markdown body
        body_parts = [
            f"# {name} Agent",
            "",
            "## Role Definition",
            f"You are the {role}.",
            "",
            "## Responsibilities"
        ]
        for resp in responsibilities:
            body_parts.append(f"1. **{resp.split(':', 1)[0].strip()}**: {resp.split(':', 1)[1].strip() if ':' in resp else resp.strip()}")
            
        body_parts.append("")
        body_parts.append("## Workflows")
        for index, flow in enumerate(workflows, 1):
            if isinstance(flow, dict):
                flow_title = flow.get("title", f"Workflow {index}")
                flow_steps = flow.get("steps", [])
                body_parts.append(f"### {flow_title}")
                for step_idx, step in enumerate(flow_steps, 1):
                    body_parts.append(f"{step_idx}. {step}")
            else:
                body_parts.append(f"### Workflow {index}")
                body_parts.append(str(flow))
            body_parts.append("")
            
        return frontmatter + "\n\n" + "\n".join(body_parts)

    def _load_registry(self) -> dict:
        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_registry(self, registry: dict):
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=4)

    @staticmethod
    def get_example_template() -> str:
        """
        Returns a clean markdown template for future agents.
        """
        return """---
name: [AgentName]
role: [Detailed Role Title]
goals:
  - [Goal 1: Clear, measurable target]
  - [Goal 2: Performance expectations]
tools:
  - [tool_one: brief description of when to use it]
  - [tool_two: brief description]
rules:
  - [Rule 1: Always format output in a specific way]
  - [Rule 2: Never modify files without confirmation]
---

# [AgentName] Specialist Agent

## Role Definition
Provide a detailed explanation of what this agent represents and its domain expertise.

## Responsibilities
1. **[Responsibility Area 1]**: Detailed description of what the agent does in this domain.
2. **[Responsibility Area 2]**: Detailed description of what the agent does in this domain.

## Workflows
### [Workflow Name 1]
1. [Step 1: First action]
2. [Step 2: Decision or iteration]
3. [Step 3: Verification and output formatting]
"""

# Test verification
if __name__ == "__main__":
    creator = AgentCreator(agents_dir="agents", registry_path="configs/agents_registry.json")
    # Generate an example template agent for users/developers to read
    template_dir = "agents/templates"
    os.makedirs(template_dir, exist_ok=True)
    with open(os.path.join(template_dir, "agent_template.md"), "w", encoding="utf-8") as f:
        f.write(creator.get_example_template())
    print("Example template written to agents/templates/agent_template.md")
