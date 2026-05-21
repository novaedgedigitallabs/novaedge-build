import json
from tools.base_tool import BaseTool

class ListAgentsTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_agents"

    @property
    def description(self) -> str:
        return "Lists all available specialized agents in the system."

    @property
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }

    def execute(self, args: dict, context: dict = None) -> str:
        """
        Retrieves the list of available agents.
        """
        if context and "system" in context:
            system = context["system"]
            agents = system.loader.list_available_agents()
            # Also read from registry to be comprehensive
            registry_agents = []
            if hasattr(system, 'creator') and hasattr(system.creator, '_load_registry'):
                try:
                    registry_agents = list(system.creator._load_registry().keys())
                except Exception:
                    pass
            
            # Combine unique names
            all_agents = list(set(agents + registry_agents))
            return json.dumps({"available_agents": all_agents, "status": "success"})
        else:
            # Fallback if no context
            import os
            agents_dir = os.path.abspath("agents")
            if os.path.exists(agents_dir):
                agents = [f.replace(".md", "") for f in os.listdir(agents_dir) if f.endswith(".md")]
                return json.dumps({"available_agents": agents, "status": "success"})
            return json.dumps({"available_agents": [], "status": "error", "message": "Agents directory not found."})
